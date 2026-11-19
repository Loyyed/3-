# 当前交接

2026-11-19 阶段17见 [五家公司证券研究定稿和证据](../docs/research17/index.html)。阶段16快照继续保留。纠错 E17-01 将同日对照统一到阶段15冻结模型基准，涪陵、安琪和柏楚分别为 13.98、97.91、98.66 元，柏楚较阶段15下降 5.91 元。沿用 2026-11-12 各市场当地截点及原估值路径。单页对照、公司临界点和期后跟踪在同一入口。原披露 Fact 仍从 ReviewStore 读取。验收运行 `python -X utf8 scripts/check_research17.py`。

2026-11-19 阶段16以 769e6e4 为比较基线。见 [五家公司结论及全部证据表](../docs/research16/index.html)。延用 2026-11-12 各交易所当地收盘及信息截止。新增驱动留出、安琪 β 与价格临界线、泡泡季度约束和现金租金、ISRG 分类经营反解，以及涪陵、柏楚的渠道或产品条件。期后项目公告独立展示。ReviewStore 当前原披露188条，核验账本历史按原绑定。复算 `python -X utf8 scripts/recalculate_research16.py --check`。

2026-11-19 阶段15入口见 [五家公司证券分析与核验全表](../docs/research15/index.html)。工作台同名侧栏可按公司筛选、打开六批原顺序及下载完整 CSV/JSON。原估值日沿用 2026-11-12。复算运行 `python -X utf8 scripts/recalculate_research15.py --check`。阶段14裁定 141 条及 11 个跳转已入账，新增原报表与后续比较栏一致的年度收入 Fact 单列。缺项和未采纳的口径保留在阶段15表。

本轮完成五家公司证券分析研究稿及条件DCF。信息与价格窗口为2026-11-12各交易所当地收盘。先打开 [五家公司证券分析](../docs/research14-index.html)，或重启现有工作台，从左侧「五家公司证券分析」进入。报告及模型在各公司 `work/research14/index.html`，根成果目录可查MD、HTML、依据JSON。[证券时点、方法和缺口](../docs/14_五家公司证券分析.md)。

16张经营桥和45条既有经营情景保留，新模型独立估计现金税、营运资本、租赁/设备投入与权益桥，跑通15条条件估值。ISRG财年应收余额误取准备金已在新版纠正，历史保留。涪陵长租赁比较列、安琪理财比较列及泡泡回购披露时点的处理见各公司 `corrections.json`。

先答 [ISRG R12-FIRST-8](../companies/US_ISRG_直觉外科/work/research12/review-batch.html)，其余五批各8项在同一研究总览。当前104条原候选绑定有效，五家Fact均0。人审与投资决定仍空。各公司报告末尾列可改变价值的证据。行业直接可比倍数样本不足，市场比较使用滚动自身倍数及条件区间。复算 `python -X utf8 scripts/recalculate_research14.py --check`。验收见 [本轮记录](../docs/research14-acceptance.json)。
