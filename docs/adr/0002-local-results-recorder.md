# ADR-0002：选股结果本地落盘复盘（history.csv + 每日 Markdown）

- 日期：2026-07-18
- 状态：已接受

## 背景

上游只把选股结果推送到飞书群。飞书消息不利于长期复盘：难以跨日统计
（某策略历史命中率、重复出现的股票）、消息会被冲走，且完全依赖外部服务。

## 决策

新增 `sequoia_x/notify/recorder.py`（`LocalRecorder`），每次策略产生选股结果时
（在范围过滤之后、飞书推送之前调用），向 `RESULTS_DIR`（默认 `data/results/`）追加：

- `history.csv`：明细行 `date,strategy,symbol,name`，便于用任意工具做复盘统计；
- `<YYYY-MM-DD>.md`：当日按策略分节的选股清单，便于人工查阅。

备份失败仅记录日志、不抛异常，与 `FeishuNotifier` 的容错风格一致，不中断主流程。
`data/results/` 已加入 `.gitignore`，落盘内容不进仓库。

## 理由与后果

- 理由：CSV + Markdown 是最朴素、零依赖、人和程序都可读的格式；本地落盘使复盘
  不再依赖飞书。容错设计与推送对齐，备份故障不影响选股主流程。
- 后果：`data/results/` 随时间增长，需使用者自行归档或清理；`--dry-run` 模式下
  也会写本地备份（这是有意为之：试跑同样留痕）。
