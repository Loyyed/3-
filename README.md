# 五家公司证券投资研究工作台

工程目录沿用“三家公司证券投资分析”。原版通用前端与五家公司独立原件/ReviewStore相连，73项共享方法，真实增补、条件计算与版本成果。

双击 `启动研究工作台.cmd`，打开 http://127.0.0.1:8780/ 。总体入口：`总体入口/index.html`；当前操作：`docs/09_知识与研究接续.md`；根成果：`outputs/index.html`。

四家原研究窗口2026-11-10，ISRG截止2026-11-11。已接入资料不代表Fact或完整估值，当前49+55条候选均未人审。实际覆盖、缺件及核验见docs/stage09-*和ISRG sources/coverage.json。

独立恢复：`python scripts/restore_generic_dependency.py --destination <新目录>`，以`RESEARCH_TOOLKIT`或`--toolkit`选择该目录；原件按`python scripts/restore.py --sample`公开URL抽样恢复并核SHA。原PDF、HTML/XBRL全文、OCR、运行配置与凭据只留本地。

历史07阶段说明保留于Git与docs/stage07-*。
