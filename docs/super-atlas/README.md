# 五家公司证券投资超级图册

发布版本 `atlas-2026-11-20.1`。阶段 17 冻结基线为 `98d1d2e0fd31aa4031cc83e51638fafb38d7c22e`。五家公司估值均用 2026-11-12 各市场当地未复权收盘及当时可用披露。发布时未见阶段 18 验收版本。权益与项目事项沿用 11 月 19 日首轮跟踪并回核公开附件。

- [离线图册](atlas.html) 包含正文、互动图表、底表和方法卡。下载为单文件后可断网阅读。
- [可编辑 JSON](atlas-editable.json) 在超级图册编辑页合并导入。编辑页另有保存、原生导图、归档和历史回载。
- [覆盖 CSV](coverage.csv)、[覆盖 JSON](coverage.json) 和[覆盖验收](coverage-acceptance.csv)对应工作台里的记录。
- [首轮跟踪](follow-up.csv)可由公开来源编号追溯。项目预算、分红实施与期后回购使用各自的时点。机械权益算术固定其他估值输入。

工作台默认入口为 [本机工作台](http://127.0.0.1:8780/)，成果中心路径为 `/research/`，连续图册为 `/atlas/`，原生编辑为 `/showcase?space=securities-atlas`。原工作台的 `#updates` 仍可登记资料及方法。公司页的当前 Fact 现读 ReviewStore，历史阶段各自显示发布快照。

在项目根目录执行：

```text
python -X utf8 scripts/build_super_atlas.py
python -X utf8 app/generic_host.py --port 8780
python -X utf8 scripts/check_super_atlas.py --url http://127.0.0.1:8780
```

生成器从已发布底表和模型重建。用 `--output` 可生成第二份可比较的构建。新种子使用新版本号并留在 `seeds/`。已编辑内容与历史在本地 `runtime/final-showcase/securities-atlas/`，发布种子重建与工作中的编辑分开。若新种子补入新编号，旧编号的编辑和归档保持。原件保留在公司本地来源区及本轮本地取证目录，公开 URL、原件版本和路径见覆盖清单。

实际投资决定以上游记录为准。需要验证的经营缺口见各公司专题末尾和阶段 17 跟踪。浏览器验收使用独立目录保存与回载，不写入研究账本。
