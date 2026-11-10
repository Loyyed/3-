# 三家公司投资研究工作台

双击[启动研究工作台.cmd](启动研究工作台.cmd)，打开 http://127.0.0.1:8780。Python3.10+，主程序标准库，PDF检查使用pypdf。

三公司八主线研究、方法检索与增补持久保存；各公司原Fact账本独立，程序共享。原来源目录保留为companies/<公司>/sources-index.html。

新增合同/讲义/经验：材料与知识增补→标题、来源、版本、用途范围、文本文件或粘贴→登记→填写方法的问题、输入、步骤、停止、反证及成果位置→检查重复/冲突→纳入→方法页关联指定公司并保存研究卡。修订填写旧方法ID及理由，影响记录列受影响研究卡/计算/假设/报告；原文留本地，版本元数据可发布，用户审阅未发生时保持空。

导入元数据、提炼、纳入、关联和实际用户认可分开；关联不证明已按方法完成研究。原件和账本保护见docs/protection-check.json；方法来源shared/knowledge-provenance.json；能力差异docs/能力对照.md。

共享升级：python scripts/check_shared.py --kit <通用工作台路径>，审查差异后备份并更新共享运行时，运行python tests/test_research_workflow.py，再做浏览器复核；禁止分别升级三家公司程序。

恢复：git clone后运行启动器即可恢复程序、知识及已发布更新元数据；原始PDF运行scripts/restore.py下载并核SHA，本地未发布的新增原文需单独备份恢复。.local原文、凭据和缓存不进入Git。
