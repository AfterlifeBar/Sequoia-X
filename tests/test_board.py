"""板块涨跌停幅度判定测试。"""

import pytest

from sequoia_x.core.board import LIMIT_EPS, limit_pct


@pytest.mark.parametrize(
    "symbol,expected",
    [
        ("600000", 0.10),  # 沪市主板
        ("601318", 0.10),
        ("000001", 0.10),  # 深市主板
        ("001979", 0.10),
        ("300750", 0.20),  # 创业板
        ("301029", 0.20),
        ("688981", 0.20),  # 科创板
        ("830879", 0.30),  # 北交所（8 开头）
        ("430047", 0.30),  # 北交所（4 开头）
        ("920819", 0.30),  # 北交所（920 开头）
    ],
)
def test_limit_pct_by_board(symbol: str, expected: float) -> None:
    assert limit_pct(symbol) == expected


def test_main_board_threshold_matches_legacy() -> None:
    """主板按新规则算出的涨停阈值应≈旧的魔法数 1.095（差异在容差量级内）。"""
    up = (1 + limit_pct("600000")) * (1 - LIMIT_EPS)
    assert up == pytest.approx(1.0945)
    assert abs(up - 1.095) < 1e-3


def test_bj_eleven_percent_not_limit_up() -> None:
    """北交所涨 11%：旧规则(10%)会误判涨停，新规则(30%)不应判为涨停。"""
    prev_close = 100.0
    close = 111.0  # +11%
    up = (1 + limit_pct("830879")) * (1 - LIMIT_EPS)  # 30% 板
    assert close < prev_close * up  # 未触及北交所涨停
    # 对照：若按主板 10% 规则则会被误判
    legacy_up = 1.095
    assert close >= prev_close * legacy_up
