# TETRA 仅保留组成分数，停用未校准宿主链接

2026-10-24，用户明确选择“保留标准 TETRA 相似度分数，停用未校准的宿主链接”。这是独立的方法输出决策，不是提高阈值、修改真值或宣布校准通过。

## 当前行为

`tetra_markov256_v1` 的逐记录、双链、256维Markov z-score和Pearson计算不变。原有长度边界、负分、不可评分状态和完整比较集合保留。`sequence_scores.tsv`保留sample/plasmid/MAG身份与method/score/profile_status，追加 `host_taxonomy`，方便核对分类输入；taxonomy是MAG的分类信息，不表示质粒宿主。

不再应用阈值或生成 `threshold`/`threshold_pass`。状态为 `threshold_status=not_applied_uncalibrated`、`association_status=disabled_uncalibrated`。`sequence_method.json`明确 `host_links_enabled=false` 和科学验收失败的原因。无MAG、短序列或不可评分仍不是生物学阴性。

`sequence_links.tsv`保留原六列空表头作为直接调用的兼容产物，没有任何宿主关联行。HOST_LINKING也不将该文件混入统一links通道，另发 `sequence_scores`；其他证据方法的连接规则不变。旧的workflow `link_min_similarity` 设置不再传入节点；直接R脚本仍接受合法旧 `--min-similarity`，输出明确的弃用/忽略提示，0或1都不能重新启用链接。没有新的未验证阈值开关。

Markdown、备用HTML和RMarkdown报告明确TETRA分数不是宿主归属、未校准链接已停用。旧输出目录中既有链接不会被回溯修改；历史TETRA边应移除，使用新输出目录重新生成下游结果。不要把本次表头兼容产物与历史非空链接混合。

## 科学结论和验收范围

55来源的分组留出基准仍按原预登记规则判为失败：选定阈值0.9534655970247977的完整质粒留出precision57.1%、recall14.3%；历史0.7也未经验证。原始指标、数据分组和失败分析均不改写。科学基准失败不会因链接停用变成通过；TA-039仅按用户决定关闭“未校准分数被发作宿主链接”的S0风险。

本批检查包括独立逐窗口标量数值参考、旧/当前相同输入的分数逐字一致与链接差异、旧阈值不能启用链接、两个锁定真实DNA数值控制、分类源字节保护、实际HOST_LINKING可选/空/重复键场景、MAG下游路由和报告。数学自匹配、切片及无关DNA不是已知宿主真值；MAG分类器/分箱器观察替身与原生R/I/O检查分开记录。初始自匹配测试错误要求浮点相关值精确等于1，实际为1-2.22e-16；保留失败记录，改用1e-12数值容差并额外严格核对旧/新分数字符串完全一致。具体次数、命令、源hash、失败尝试和限制见 `results/tool-audit/20261024-tetra-scores-only/receipt.json`。

未来如需自动TETRA宿主链接，须重新提出方法与独立校准/留出验收。本次不提供绕过验收的开关。校准研究工具仍可读取完整分数表，但不会写回生产配置或恢复链接。
