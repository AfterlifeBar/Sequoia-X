"""数据引擎属性测试。"""

import sqlite3
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st

from sequoia_x.core.config import Settings
from sequoia_x.data.engine import DataEngine


def make_engine_in(tmp_dir: str) -> tuple[DataEngine, Settings]:
    """创建使用临时数据库的 DataEngine 实例。"""
    settings = Settings(
        db_path=str(Path(tmp_dir) / "test.db"),
        start_date="2024-01-01",
        feishu_webhook_url="https://example.com/hook",
    )
    engine = DataEngine(settings)
    return engine, settings


# Property 4: (symbol, date) 唯一约束防止重复写入
@given(
    symbol=st.text(min_size=6, max_size=6, alphabet="0123456789"),
    trade_date=st.dates(min_value=date(2024, 1, 1), max_value=date(2025, 12, 31)),
)
@h_settings(max_examples=50, deadline=None)
def test_unique_symbol_date_constraint(symbol: str, trade_date: date) -> None:
    """相同 (symbol, date) 插入两次，数据库中该组合记录数应保持为 1。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine, _ = make_engine_in(tmp_dir)
        row = {
            "symbol": symbol, "date": str(trade_date),
            "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.5,
            "volume": 1000.0, "turnover": 10500.0,
        }
        df = pd.DataFrame([row])
        with sqlite3.connect(engine.db_path) as conn:
            df.to_sql("stock_daily", conn, if_exists="append", index=False, method="multi")
            try:
                df.to_sql("stock_daily", conn, if_exists="append", index=False, method="multi")
            except sqlite3.IntegrityError:
                pass
            count = conn.execute(
                "SELECT COUNT(*) FROM stock_daily WHERE symbol=? AND date=?",
                (symbol, str(trade_date)),
            ).fetchone()[0]
        assert count == 1


def _seed(engine: DataEngine, rows: list[dict]) -> None:
    with sqlite3.connect(engine.db_path) as conn:
        pd.DataFrame(rows).to_sql(
            "stock_daily", conn, if_exists="append", index=False, method="multi"
        )


def _bar(symbol: str, d: str, close: float) -> dict:
    return {
        "symbol": symbol, "date": d,
        "open": close, "high": close, "low": close, "close": close,
        "volume": 1000.0, "turnover": close * 1000.0,
    }


def test_preload_matches_sql_and_lists_symbols() -> None:
    """preload() 后 get_ohlcv/get_local_symbols 走内存，结果应与 SQL 一致。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine, _ = make_engine_in(tmp_dir)
        _seed(engine, [
            _bar("600000", "2024-01-02", 10.0),
            _bar("600000", "2024-01-03", 10.5),
            _bar("000001", "2024-01-02", 20.0),
        ])

        sql_df = engine.get_ohlcv("600000")  # 缓存前走 SQL
        engine.preload()

        assert set(engine.get_local_symbols()) == {"600000", "000001"}
        cached_df = engine.get_ohlcv("600000")  # 缓存后走内存
        pd.testing.assert_frame_equal(
            cached_df[["symbol", "date", "close"]],
            sql_df[["symbol", "date", "close"]],
        )
        # 缺失的 symbol 返回空 df
        assert engine.get_ohlcv("999999").empty


def test_preload_returns_independent_copy() -> None:
    """get_ohlcv 返回的是独立副本，修改它不应污染缓存。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine, _ = make_engine_in(tmp_dir)
        _seed(engine, [_bar("600000", "2024-01-02", 10.0)])
        engine.preload()

        df = engine.get_ohlcv("600000")
        df["ma5"] = 1.0  # 模拟策略写入
        assert "ma5" not in engine.get_ohlcv("600000").columns
