# 柏楚电子公司分析项目

代码：688188.SH；行业适配：industrial。这是独立项目，初始没有来源、Fact或公司结论。

双击“启动工作台.cmd”，或运行 `python workbench.py serve`。导入资料后，让Agent先读AGENTS.md和会话交接/CURRENT.md，再按技能开始分析；核验时在窗口点击“确认原文与口径”。不需要手动改JSON。

当前报告：[分析报告](outputs/analysis-report.md)；核验记录：[当前证据](evidence/facts.md)；计划：[研究计划](tasks/research-plan.md)。

项目复制后仍可单独运行，包含本次方法与程序快照；以相对路径绑定原件。Python需3.10或更新，核心操作无需额外包。PDF自动文字索引仅在已有pypdf时启用，原PDF仍是核验来源。

原件在sources，底稿在work，真实核验历史在evidence，报告在outputs，内容验收在docs，精简交接在会话交接。签署与内容确认分开，初始签名空白。
