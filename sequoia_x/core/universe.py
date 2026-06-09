"""范围过滤模块：对策略选出的结果做后置过滤（自选股池 / 前缀黑名单 / ST）。

统一在 main.py 对每个策略的返回结果调用 filter_symbols，
覆盖全部策略（含直接读全表、绕过 get_local_symbols 的 RPS 策略）。
"""

from pathlib import Path

from sequoia_x.core.config import Settings
from sequoia_x.core.logger import get_logger

logger = get_logger(__name__)


def load_watchlist(path: str) -> set[str]:
    """读取自选股池文件，返回纯数字代码集合。

    文件格式：每行一个代码，支持 '#' 注释与空行。
    文件不存在或为空时返回空集合（表示不限制 / 全市场）。
    """
    p = Path(path)
    if not p.exists():
        return set()

    codes: set[str] = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            codes.add(line)
    return codes


def filter_symbols(symbols: list[str], settings: Settings) -> list[str]:
    """对策略结果做范围过滤，保持原有顺序。

    过滤顺序：
    1. 自选股池：若 watchlist_path 文件非空，只保留交集。
    2. 前缀黑名单：剔除 exclude_prefixes 中任一前缀开头的代码。
    3. ST 过滤：若 exclude_st，查名后剔除名称含 "ST" 的代码。

    Args:
        symbols: 策略选出的纯数字代码列表。
        settings: 全局配置。

    Returns:
        过滤后的代码列表（保持入参顺序）。
    """
    if not symbols:
        return symbols

    result = list(symbols)

    # 1. 自选股池交集
    watchlist = load_watchlist(settings.watchlist_path)
    if watchlist:
        result = [s for s in result if s in watchlist]

    # 2. 前缀黑名单
    prefixes = settings.exclude_prefix_list()
    if prefixes:
        result = [s for s in result if not s.startswith(tuple(prefixes))]

    # 3. ST 过滤（需联网查名，故仅在开启时执行）
    if settings.exclude_st and result:
        from sequoia_x.data.names import get_stock_names

        names = get_stock_names(result)
        result = [s for s in result if "ST" not in names.get(s, "").upper()]

    if len(result) != len(symbols):
        logger.info(f"范围过滤：{len(symbols)} → {len(result)} 只")

    return result
