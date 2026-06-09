"""本地结果备份模块：将选股结果落盘为 CSV 与每日 Markdown，便于复盘与查历史。"""

import csv
from datetime import date
from pathlib import Path

from sequoia_x.core.config import Settings
from sequoia_x.core.logger import get_logger
from sequoia_x.data.names import get_stock_names

logger = get_logger(__name__)


class LocalRecorder:
    """本地结果备份器。

    每次 record 会：
    - 向 <results_dir>/history.csv 追加明细行（date,strategy,symbol,name）。
    - 向 <results_dir>/<YYYY-MM-DD>.md 追加当日该策略的选股小节。

    失败仅记录日志、不抛异常（与 FeishuNotifier 的容错风格一致）。
    """

    CSV_HEADER = ["date", "strategy", "symbol", "name"]

    def __init__(self, settings: Settings) -> None:
        self.results_dir = Path(settings.results_dir)

    def record(self, symbols: list[str], strategy_name: str) -> None:
        """将一个策略的选股结果写入本地 CSV 与当日 Markdown。"""
        if not symbols:
            return

        try:
            self.results_dir.mkdir(parents=True, exist_ok=True)
            today = date.today().strftime("%Y-%m-%d")
            names = get_stock_names(symbols)

            self._append_csv(today, strategy_name, symbols, names)
            self._append_markdown(today, strategy_name, symbols, names)
            logger.info(f"本地备份完成 [{strategy_name}]，共 {len(symbols)} 只")
        except Exception as exc:  # noqa: BLE001 - 备份失败不应中断主流程
            logger.error(f"本地备份失败 [{strategy_name}]：{exc}")

    def _append_csv(
        self, today: str, strategy_name: str, symbols: list[str], names: dict[str, str]
    ) -> None:
        csv_path = self.results_dir / "history.csv"
        write_header = not csv_path.exists()
        with csv_path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(self.CSV_HEADER)
            for code in symbols:
                writer.writerow([today, strategy_name, code, names.get(code, "")])

    def _append_markdown(
        self, today: str, strategy_name: str, symbols: list[str], names: dict[str, str]
    ) -> None:
        md_path = self.results_dir / f"{today}.md"
        new_file = not md_path.exists()
        lines: list[str] = []
        if new_file:
            lines.append(f"# Sequoia-X 选股结果 | {today}\n")
        lines.append(f"\n## {strategy_name}（{len(symbols)} 只）\n")
        for code in symbols:
            name = names.get(code, "")
            lines.append(f"- {name}（{code}）" if name else f"- {code}")
        lines.append("")
        with md_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
