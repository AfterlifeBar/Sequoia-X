"""股票名称查询模块：通过 baostock 批量查询纯数字代码对应的股票名称。

供飞书推送（feishu.py）与本地备份（recorder.py）、范围过滤（universe.py）复用。
"""

from sequoia_x.core.logger import get_logger

logger = get_logger(__name__)


def get_stock_names(symbols: list[str]) -> dict[str, str]:
    """通过 baostock 批量查询股票名称，返回 {纯数字代码: 名称} 映射。

    Args:
        symbols: 纯数字代码列表，如 ['000001', '600519']。

    Returns:
        {code: name} 映射；查询失败的代码不出现在结果中。
    """
    if not symbols:
        return {}

    import baostock as bs

    mapping: dict[str, str] = {}
    bs.login()
    try:
        for code in symbols:
            prefix = "sh" if code.startswith(("6", "9")) else "sz"
            rs = bs.query_stock_basic(code=f"{prefix}.{code}")
            while rs.next():
                row = rs.get_row_data()
                mapping[code] = row[1]  # 第2个字段是股票名称
    except Exception as exc:  # noqa: BLE001 - 查名失败不应中断主流程
        logger.warning(f"查询股票名称失败：{exc}")
    finally:
        bs.logout()

    return mapping
