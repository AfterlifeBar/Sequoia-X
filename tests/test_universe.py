"""范围过滤模块测试。"""

from sequoia_x.core.config import Settings
from sequoia_x.core.universe import filter_symbols, load_watchlist


def _settings(**kwargs) -> Settings:
    """构造测试用 Settings，避免读取真实 .env。"""
    kwargs.setdefault("feishu_webhook_url", "https://example.com/hook")
    return Settings(_env_file=None, **kwargs)


def test_empty_symbols_passthrough(tmp_path) -> None:
    s = _settings(watchlist_path=str(tmp_path / "nope.txt"))
    assert filter_symbols([], s) == []


def test_no_filters_unchanged(tmp_path) -> None:
    s = _settings(watchlist_path=str(tmp_path / "nope.txt"), exclude_prefixes="")
    symbols = ["600519", "000858", "688981"]
    assert filter_symbols(symbols, s) == symbols


def test_watchlist_intersection_preserves_order(tmp_path) -> None:
    wl = tmp_path / "watchlist.txt"
    wl.write_text("000858\n600519  # 茅台\n# 注释行\n", encoding="utf-8")
    s = _settings(watchlist_path=str(wl))
    assert filter_symbols(["600519", "300750", "000858"], s) == ["600519", "000858"]


def test_load_watchlist_strips_comments_and_blanks(tmp_path) -> None:
    wl = tmp_path / "watchlist.txt"
    wl.write_text("# header\n\n600519\n000858 # 五粮液\n", encoding="utf-8")
    assert load_watchlist(str(wl)) == {"600519", "000858"}


def test_load_watchlist_missing_file_is_empty(tmp_path) -> None:
    assert load_watchlist(str(tmp_path / "missing.txt")) == set()


def test_exclude_prefixes(tmp_path) -> None:
    s = _settings(
        watchlist_path=str(tmp_path / "nope.txt"),
        exclude_prefixes="688,8,4",
    )
    symbols = ["600519", "688981", "830000", "430047", "000858"]
    assert filter_symbols(symbols, s) == ["600519", "000858"]


def test_exclude_st_mocked(tmp_path, monkeypatch) -> None:
    import sequoia_x.data.names as names_mod

    monkeypatch.setattr(
        names_mod, "get_stock_names",
        lambda syms: {"000005": "ST星源", "600519": "贵州茅台"},
    )
    s = _settings(watchlist_path=str(tmp_path / "nope.txt"), exclude_st=True)
    assert filter_symbols(["600519", "000005"], s) == ["600519"]
