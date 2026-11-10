# 可复现操作

restore.py是从Git恢复本地原件的正式路径：python scripts/restore.py --sample（各公司抽样）或不加--sample恢复全部可恢复原件，SHA不符立即停止。

build_local.py用于首次空白工程从既有资料库建立，明确传入--root --kit --materials --library；它会更新Agent机器生成元数据，不应对已有人工核验工程直接重跑。verify_intake.py保留本轮实际执行脚本快照，其绝对环境路径需适配后使用。

运行各公司workbench.py validate可动态核当前来源；初始化与核查使用Python3.12和pypdf，程序核心标准库。恢复/页面浏览不需要旧资料库。
