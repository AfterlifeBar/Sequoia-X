"""本地结果备份模块测试。"""

import csv
from datetime import date

from sequoia_x.core.config import Settings
from sequoia_x.notify.recorder import LocalRecorder


def _settings(results_dir: str) -> Settings:
    return Settings(
        _env_file=None,
        feishu_webhook_url="https://example.com/hook",
        results_dir=results_dir,
    )


def _patch_names(monkeypatch, mapping: dict[str, str]) -> None:
    import sequoia_x.notify.recorder as rec_mod

    monkeypatch.setattr(rec_mod, "get_stock_names", lambda syms: mapping)


def test_record_empty_is_noop(tmp_path, monkeypatch) -> None:
    _patch_names(monkeypatch, {})
    rec = LocalRecorder(_settings(str(tmp_path)))
    rec.record([], "MaVolumeStrategy")
    assert not (tmp_path / "history.csv").exists()


def test_record_writes_csv_and_markdown(tmp_path, monkeypatch) -> None:
    _patch_names(monkeypatch, {"600519": "贵州茅台", "000858": "五粮液"})
    rec = LocalRecorder(_settings(str(tmp_path)))
    rec.record(["600519", "000858"], "MaVolumeStrategy")

    today = date.today().strftime("%Y-%m-%d")

    # CSV：含表头 + 两行明细
    csv_path = tmp_path / "history.csv"
    rows = list(csv.reader(csv_path.open(encoding="utf-8")))
    assert rows[0] == ["date", "strategy", "symbol", "name"]
    assert [today, "MaVolumeStrategy", "600519", "贵州茅台"] in rows
    assert [today, "MaVolumeStrategy", "000858", "五粮液"] in rows

    # Markdown：含标题与个股
    md = (tmp_path / f"{today}.md").read_text(encoding="utf-8")
    assert "MaVolumeStrategy" in md
    assert "贵州茅台（600519）" in md


def test_record_appends_across_strategies(tmp_path, monkeypatch) -> None:
    _patch_names(monkeypatch, {"600519": "贵州茅台", "300750": "宁德时代"})
    rec = LocalRecorder(_settings(str(tmp_path)))
    rec.record(["600519"], "MaVolumeStrategy")
    rec.record(["300750"], "TurtleTradeStrategy")

    csv_path = tmp_path / "history.csv"
    rows = list(csv.reader(csv_path.open(encoding="utf-8")))
    # 1 表头 + 2 明细行
    assert len(rows) == 3
    today = date.today().strftime("%Y-%m-%d")
    md = (tmp_path / f"{today}.md").read_text(encoding="utf-8")
    assert "MaVolumeStrategy" in md and "TurtleTradeStrategy" in md
