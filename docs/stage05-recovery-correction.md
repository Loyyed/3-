# 独立克隆恢复纠错
首次克隆检测到导出文件SHA不一致。原因：版本化MD/HTML/JSON在Windows写入CRLF，而既有.gitattributes对文本规范化为LF。将根和公司outputs/**设为-text，并重新归一化暂存，保证版本化成果按真实原字节发布。旧提交和本纠错记录保留；最终验收按stage05-git-restore.json。
