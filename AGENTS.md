# AGENTS.md — 项目交接说明

写给任何接手本项目的人或 AI agent：只看本文件 + 仓库代码即可上手。
进展历史见 `PROGRESS.md`，关键决策见 `docs/adr/`。

## 这是什么

Sequoia-X 是 A 股量化自动选股系统 V2：每日收盘后按多种技术形态扫描全市场
（约 5200 只 A 股），把命中的股票推送到飞书群，并在本地落盘备份结果。

本仓库是上游 [sngyai/Sequoia-X](https://github.com/sngyai/Sequoia-X) 的 **fork**：

- **上游**：负责系统主体架构（V2 重构、baostock 数据层、策略实现、飞书推送）。
  上游最后一次提交为 2026-05-09。
- **本 fork**：在上游 V2 之上叠加一层"个人自用化增强"（详见下文），**不重做架构**。
  增强层以新增模块 + 配置项的方式实现，与上游代码保持低耦合，
  以便未来可选地从上游 rebase / merge 同步。

内置策略（`main.py` 的 `ALL_STRATEGIES` 注册表，`webhook_key` 为开关标识）：

| webhook_key | 策略 | 说明 |
|---|---|---|
| `ma_volume` | MaVolume | 均线 + 放量突破 |
| `turtle` | TurtleTrade | 海龟突破：20 日新高 + 成交额过亿 + 阳线防诱多 |
| `flag` | HighTightFlag | 高而窄的旗形整理突破 |
| `shakeout` | LimitUpShakeout | 涨停洗盘回踩确认 |
| `limit_down` | UptrendLimitDown | 上升趋势中的跌停反包 |
| `rps` | RpsBreakout | 欧奈尔 RPS 相对强度突破 |
| `private_placement` | PrivatePlacement | 定增公告监控（数据源为 akshare，见下文） |

## 技术栈

- Python >= 3.10，pandas 向量化计算
- 日 K 数据：baostock（免费、无注册、无限流），后复权，存本地 SQLite（`data/sequoia_v2.db`）
- 配置：pydantic-settings + python-dotenv（`.env`）
- 终端输出：rich
- 测试：pytest + hypothesis（+ pytest-mock）
- Lint：ruff（配置在 `pyproject.toml`：line-length 100，target py311，select E/F/I/UP）
- 包管理：uv（`uv.lock` 已提交）
- 注意：`private_placement` 策略仍依赖 akshare（`pyproject.toml` 保留了该依赖）；
  2026-04 的"akshare → baostock"切换针对的是日 K 数据层。

## 安装、运行、测试

```bash
uv sync                  # 安装依赖（README 推荐；亦可 pip install .）
uv sync --extra dev      # 连带 dev 依赖（pytest / hypothesis / pytest-mock）

cp .env.example .env     # 填写 FEISHU_WEBHOOK_URL（必填），按需配置其余项

python main.py --backfill   # 首次：回填全市场历史日 K（约 12 分钟）
python main.py              # 日常：增量同步 + 跑策略 + 本地备份 + 飞书推送（2~3 分钟）

pytest                 # 跑测试（testpaths = tests）
ruff check .           # lint
```

## 目录结构（以代码为准）

```
main.py                  # 入口：argparse 分发日常/回填模式，策略注册表 ALL_STRATEGIES
sequoia_x/
├── core/
│   ├── config.py        # pydantic-settings 配置（含全部自用增强配置项）
│   ├── logger.py        # rich 结构化日志
│   ├── universe.py      # 后置范围过滤：watchlist / 前缀黑名单 / ST（fork 新增）
│   └── board.py         # 板块涨跌停幅度判定（fork 新增）
├── data/
│   ├── engine.py        # 数据引擎：baostock 回填 + 增量同步 + preload 内存预加载
│   └── names.py         # 股票名称查询
├── strategy/            # 7 个策略 + base.py 抽象基类
└── notify/
    ├── feishu.py        # 飞书 Webhook 推送
    └── recorder.py      # 本地结果备份 LocalRecorder（fork 新增）
tests/                   # pytest + hypothesis 属性测试
data/                    # SQLite、watchlist.txt、results/（运行时生成，不入 git）
```

（README 的"目录结构"一节停留在上游版本，缺少 fork 新增的模块，以本节为准。）

## fork 的个人化增强（4 项，PR #1 + PR #2 合入）

1. **本地结果备份**（`notify/recorder.py`）：除飞书推送外，每次选股结果写入
   `RESULTS_DIR`（默认 `data/results/`）：`history.csv`（明细，便于复盘统计）
   + `<YYYY-MM-DD>.md`（当日按策略分节的清单）。
2. **自选股池 / 范围过滤**（`core/universe.py`）：`filter_symbols()` 作为统一后置过滤，
   在 `main.py` 中覆盖全部策略结果：watchlist 交集（`WATCHLIST_PATH`）、
   代码前缀黑名单（`EXCLUDE_PREFIXES`，如 `688,8,4` 排除科创/北交所）、ST 过滤（`EXCLUDE_ST`）。
3. **策略开关**：`ENABLED_STRATEGIES`（配置）与 `--only`（CLI，优先级更高），
   取值见上文策略表。
4. **试跑模式**：`--dry-run`（不推送飞书，结果打印终端）/ `--no-sync`（跳过联网增量同步）。
   另：PR #2 新增 `engine.preload()` 全市场行情一次性加载，及 `board.py`
   按板块自适配涨跌停阈值（主板 10% / 创业板·科创板 20% / 北交所 30%）。

## 开发约定

- `master` 为主线；工作分支当天推送到 origin，不囤在本地。
- PR 采用 **squash 合并**（历史上 PR #1、#2 均为 squash）。
- 新改动带测试：新增模块要有对应 `tests/test_*.py`（参考 `test_universe.py`、
  `test_recorder.py`、`test_board.py`）。
- 不改动上游带来的文件去做无关重构；fork 增强优先以新增模块 + 配置项实现，保持与上游低耦合。
- 每个工作 session 结束前把进展追加到 `PROGRESS.md`（最新在上）。

## 当前状态与下一步

- 代码状态：master 含上游截至 2026-05-09 的全部内容 + fork 的 PR #1、#2，测试应全绿。
- **待办 1：落实收盘后自动调度。** README 提到"每日收盘后自动选股"并给了 crontab 示例，
  但仓库中没有落实（无 CI / cron 配置，自动化只在使用者的机器上）。需要选定方案
  （本机 crontab / launchd / 服务器）并验证。
- **待办 2（可选）：与上游同步。** 上游自 2026-05-09 起无新提交；若上游恢复活跃，
  按 ADR-0001 的定位 rebase / merge 上游变更。
