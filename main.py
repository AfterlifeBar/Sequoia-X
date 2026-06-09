"""Sequoia-X V2 主程序入口。

运行模式：
  python main.py                     # 日常模式：8进程增量补数据 + 跑策略 + 飞书推送（2~3分钟）
  python main.py --backfill          # 回填模式：baostock 拉全市场历史K线（首次/补数据用，约12分钟）

自用调试开关（可叠加）：
  python main.py --dry-run           # 跑策略 + 写本地备份，但不推送飞书，结果打印到终端
  python main.py --no-sync           # 跳过联网增量同步，直接用本地库跑（任意时间快速验证）
  python main.py --only ma_volume,turtle  # 本次只跑指定 webhook_key 的策略（覆盖 ENABLED_STRATEGIES）
  python main.py --dry-run --no-sync       # 不联网、不推送，纯看选股结果
"""

import argparse
import sys
from dotenv import load_dotenv
load_dotenv()

from datetime import date

import socket
socket.setdefaulttimeout(10.0)

from sequoia_x.core.config import get_settings
from sequoia_x.core.logger import get_logger
from sequoia_x.core.universe import filter_symbols
from sequoia_x.data.engine import DataEngine
from sequoia_x.notify.feishu import FeishuNotifier
from sequoia_x.notify.recorder import LocalRecorder
from sequoia_x.strategy.base import BaseStrategy
from sequoia_x.strategy.high_tight_flag import HighTightFlagStrategy
from sequoia_x.strategy.limit_up_shakeout import LimitUpShakeoutStrategy
from sequoia_x.strategy.ma_volume import MaVolumeStrategy
from sequoia_x.strategy.turtle_trade import TurtleTradeStrategy
from sequoia_x.strategy.uptrend_limit_down import UptrendLimitDownStrategy
from sequoia_x.strategy.rps_breakout import RpsBreakoutStrategy
from sequoia_x.strategy.private_placement import PrivatePlacementStrategy


# 策略注册表（新增策略在此追加即可）。每个策略的 webhook_key 作为唯一开关标识。
ALL_STRATEGIES: list[type[BaseStrategy]] = [
    MaVolumeStrategy,
    TurtleTradeStrategy,
    HighTightFlagStrategy,
    LimitUpShakeoutStrategy,
    UptrendLimitDownStrategy,
    RpsBreakoutStrategy,
    PrivatePlacementStrategy,
]


def _select_strategy_classes(
    enabled: set[str], only: set[str], logger
) -> list[type[BaseStrategy]]:
    """根据 --only 与 ENABLED_STRATEGIES 过滤要运行的策略类。

    优先级：--only（若提供）> enabled（配置）> 全部启用。
    """
    active = only or enabled  # --only 覆盖配置
    if not active:
        return ALL_STRATEGIES

    selected = [cls for cls in ALL_STRATEGIES if cls.webhook_key in active]
    unknown = active - {cls.webhook_key for cls in ALL_STRATEGIES}
    if unknown:
        logger.warning(f"忽略未知策略标识：{', '.join(sorted(unknown))}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Sequoia-X V2 选股系统")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="回填模式：通过 baostock 拉取全市场历史 K 线（约12分钟）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试跑模式：跑策略 + 写本地备份，但不推送飞书，结果打印到终端",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="跳过联网增量同步，直接用本地库跑（任意时间快速验证）",
    )
    parser.add_argument(
        "--only",
        default="",
        help="本次只跑指定 webhook_key 的策略，逗号分隔（覆盖 ENABLED_STRATEGIES）",
    )
    args = parser.parse_args()

    try:
        # 1. 初始化配置
        settings = get_settings()

        # 2. 初始化日志
        logger = get_logger(__name__)
        logger.info("Sequoia-X V2 启动")

        # 3. 初始化数据引擎
        engine = DataEngine(settings)

        if args.backfill:
            # ── 回填模式：单线程保守拉历史 K 线，自动多轮重跑 ──
            logger.info("进入回填模式...")
            all_symbols = engine.get_all_symbols()
            engine.backfill(all_symbols)
            logger.info("Sequoia-X V2 回填模式运行完成")
            return

        # ── 日常模式：单次 API 补今天 + 策略 + 推送 ──
        if args.no_sync:
            logger.info("--no-sync：跳过联网增量同步，使用本地库")
        else:
            logger.info("开始拉取最新快照...")
            count = engine.sync_today_bulk()
            logger.info(f"快照同步完成，写入 {count} 只股票")

        # 4. 按配置/CLI 选定要运行的策略
        only_keys = {k.strip().lower() for k in args.only.split(",") if k.strip()}
        strategy_classes = _select_strategy_classes(
            settings.enabled_strategy_keys(), only_keys, logger
        )
        strategies: list[BaseStrategy] = [
            cls(engine=engine, settings=settings) for cls in strategy_classes
        ]
        logger.info(
            "本次启用策略："
            + (", ".join(c.webhook_key for c in strategy_classes) or "（无）")
        )

        notifier = FeishuNotifier(settings)
        recorder = LocalRecorder(settings)

        # 5. 遍历策略：选股 → 范围过滤 → 本地备份 →（非 dry-run）推送
        for strategy in strategies:
            strategy_name = type(strategy).__name__
            logger.info(f"执行策略：{strategy_name}")

            selected: list[str] = strategy.run()
            selected = filter_symbols(selected, settings)
            logger.info(f"{strategy_name} 选出 {len(selected)} 只股票")

            if not selected:
                logger.info(f"{strategy_name} 无选股结果，跳过")
                continue

            recorder.record(selected, strategy_name)

            if args.dry_run:
                logger.info(f"[dry-run] {strategy_name}: {' '.join(selected)}")
            else:
                notifier.send(
                    symbols=selected,
                    strategy_name=strategy_name,
                    webhook_key=strategy.webhook_key,
                )

    except Exception:
        try:
            _logger = get_logger(__name__)
            _logger.exception("主流程发生未捕获异常，程序终止")
        except Exception:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    logger.info("Sequoia-X V2 运行完成")


if __name__ == "__main__":
    main()
