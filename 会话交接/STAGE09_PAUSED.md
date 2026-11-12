# 09阶段暂停接续
暂停时间：2026-11-11T12:57:41.943Z；用户明确要求暂停，等待恢复。
基线：codex/three-company-foundation，ba2fa7a3c83611ebd867c315549427e6e602506c；开始时工作区干净、远端一致。
已读09总提示词、适用规则、来源主技能、新方法与审阅材料；来源工程未修改。基线保护指纹在.local/stage09/baseline.json。
已实施但整体未验收、未commit、未push：
- scripts/sync_knowledge.py增量导入24张K41—64，实际current_methods共73；保留原40及E01—09；事件记录shared/updates.json，三处关联ID更正留原值。docs/stage09-knowledge-diff.json。
- 本轮12项来源valuation_chain专项已实际执行通过，docs/stage09-cashflow-tests.txt。依赖3处代码差异已审阅，保存在.local/stage09/upstream-code-diff.json；尚未更新依赖锁和恢复包，当前新进程仍会因旧锁失败，不称升级完成。
- app/valuation.py、scripts/recalculate_valuation.py、engine/outputs/generic_host/project-adapter已有计算、经验正文及依赖追踪增量，尚未整体编译/浏览器验证。共享runtime尚无valuation_chain.py，故现阶段不要直接运行正式计算或导出。
- 已独立初始化companies/US_ISRG_直觉外科，未复制既有公司账本/资料；SEC submissions官方索引.local/stage09/submissions.json，身份代码CIK/Nasdaq/财年已读，US GAAP/USD仍需正文核验。
- scripts/collect_isrg.py限速下载已启动后因用户暂停停止，状态见.local/stage09/download.log和公司sources/catalog.json（如已保存）；脚本PDF分支仍引用缺失fitz，需要改为已有pypdf或安装后再接续。manifest只在脚本结束生成，恢复前核对已下载catalog与raw，不能据目录称已全部接入。
未完成：依赖兼容与完整恢复包、幂等/作用域测试、ISRG全部资料与失败清单/内容核验、四公司研究增量、五公司成果、浏览器/重启/独立克隆/原件账本保护验收、分批commit/push。
原四公司Fact/候选未改变，不批量核准、不生成买卖结论。恢复先查实时Git和下载状态，保留当前增量；勿重新创建ISRG。
