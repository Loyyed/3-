# 三家公司证券投资分析

直接打开[总体入口](总体入口/index.html)，进入三个公司资料工作台。各公司双击启动工作台.cmd打开通用交互程序。Python 3.10+；PDF校验依赖pypdf。

原件独立复制到各公司sources/raw，保留原文件名并校验两端SHA；移动原资料库不影响本工程。Git仅发布元数据、方法、代码与成果。恢复原件运行scripts/restore.py，按公开URL下载并严格核对指纹。完整原件与正文缓存本地忽略。

验收证据：docs/entry-link-checks.json、docs/browser-validation.json、docs/company-validation.json、docs/recovery-test.json。覆盖表在各公司sources/coverage.html。全部1414份原件可解析；正文仅完成六份报告的Agent身份和期间抽核。缺口详见docs/已知问题.md。
分支codex/three-company-foundation，已提交push；最后一次精确HEAD与远端核验回执保留在.local/final-publication-receipt.json，避免提交哈希自引用。
