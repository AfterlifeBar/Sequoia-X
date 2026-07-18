# PROGRESS.md — 进展日志

## 格式与纪律

- **每个工作 session 结束前追加一条**，最新条目在最上（倒序）。
- 条目格式：日期 / 标题 / 做了什么（含相关 PR、分支、提交）/ 遗留问题或下一步。
- 区分「上游」（sngyai/Sequoia-X 的历史）与「fork 后」（本仓库的工作）。
- 只写事实；无法核实的内容标注"待确认"。

---

## 2026-07-18 · fork 后 · 起草项目交接文档

- 新增 `AGENTS.md`（交接说明）、本文件、`docs/adr/0001~0003`（架构决策记录），
  目的：项目状态完整保存在仓库内，任何接手者（人或 AI）只看仓库即可上手。
- 以 PR 形式提交（分支 `docs/handover-docs`），待合并。

## 2026-07-18 · fork 后 · PR #2 性能优化合入 master（squash 提交 7bccd46）

- `data/engine.py`：新增 `preload()`，全市场行情一次性加载进内存，供逐股策略复用，
  避免每个策略重复开连接。
- 新增 `core/board.py`：涨跌停幅度按板块代码前缀自适配
  （主板 10% / 创业板·科创板 20% / 北交所 30%，容差 `LIMIT_EPS = 0.005`），
  替代旧的固定阈值魔法数（1.095 / 0.905），修正创业板/科创板/北交所的误判。
- 新增 `tests/test_board.py`。

## 2026-06-10 · fork 后 · PR #1「个人自用化增强」合入 master（squash 提交 8b9cef0）

- 本地结果备份：新增 `notify/recorder.py`（`LocalRecorder`），
  写 `RESULTS_DIR` 下的 `history.csv` + 每日 Markdown 复盘。
- 范围过滤：新增 `core/universe.py`，watchlist 交集 / 代码前缀黑名单（排除科创/北交所）/
  ST 过滤，作为统一后置过滤覆盖全部策略（`main.py` 中在策略选股后统一调用）。
- 策略开关：`ENABLED_STRATEGIES` 配置项 + `--only` CLI 参数（后者优先）。
- 试跑模式：`--dry-run`（不推送飞书）/ `--no-sync`（跳过联网增量同步）。
- 新增 `tests/test_universe.py`、`tests/test_recorder.py`。

## 2026-05-09 · 上游 · 最后一次提交（444c0db，PR #91）

- backfill 增加重试和自动重连，解决长连接超时问题。
- 此后上游无新提交（截至 2026-07-18）。

## 2026-04-26 · 上游 · 日 K 数据源 akshare → baostock

- 数据层全面切换 baostock（后复权日 K → 本地 SQLite），摆脱东方财富反爬；
  日 K 全链路移除 akshare。
- 注：`private_placement`（定增公告监控）策略仍使用 akshare，
  `pyproject.toml` 中保留了该依赖。

## 2026-03-13 · 上游 · V2 重构（8177132「Sequoia-X V2 王者回归」）

- 基于现代 Python 工程化标准从零重构：OOP 架构、`sequoia_x/` 分层包结构
  （core / data / strategy / notify）、向量化计算、增量数据更新。

## 2018-03-16 · 上游 · 项目首个提交

- 仓库历史最早可追溯至 2018-03-16（Initial commit），早期为旧版选股脚本，
  中间多年低活跃，直至 2026-03 的 V2 重构。
