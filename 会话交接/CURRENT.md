# 当前交接

本轮完成五家公司证券分析研究稿及条件DCF。信息与价格窗口为2026-11-12各交易所当地收盘。先打开 [五家公司证券分析](../docs/research14-index.html)，或重启现有工作台，从左侧「五家公司证券分析」进入。报告及模型在各公司 `work/research14/index.html`，根成果目录可查MD、HTML、依据JSON。[证券时点、方法和缺口](../docs/14_五家公司证券分析.md)。

16张经营桥和45条既有经营情景保留，新模型独立估计现金税、营运资本、租赁/设备投入与权益桥，跑通15条条件估值。ISRG财年应收余额误取准备金已在新版纠正，历史保留。涪陵长租赁比较列、安琪理财比较列及泡泡回购披露时点的处理见各公司 `corrections.json`。

先答 [ISRG R12-FIRST-8](../companies/US_ISRG_直觉外科/work/research12/review-batch.html)，其余五批各8项在同一研究总览。当前104条原候选绑定有效，五家Fact均0。人审与投资决定仍空。各公司报告末尾列可改变价值的证据。行业直接可比倍数样本不足，市场比较使用滚动自身倍数及条件区间。复算 `python -X utf8 scripts/recalculate_research14.py --check`。验收见 [本轮记录](../docs/research14-acceptance.json)。
