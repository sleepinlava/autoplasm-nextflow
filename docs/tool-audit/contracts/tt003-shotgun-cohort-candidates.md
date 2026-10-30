# TT-003 shotgun 队列候选评估（2026-10-28，未决定）

legacy 16S 框架执行已通过后，TT-003 剩余部分需要**适用的真实 shotgun 多样本队列**（≥3 重复×2 组、非空统计、非病毒约束下可接受）。本轮对公开 ENA 候选做了筛选，尚未选定，不开始下载。

## 筛选过程

- ENA portal API 按 `library_strategy=WGS + library_source=METAGENOMIC` 及 `base_count<800M` 过滤，考察 run 数较多的研究。
- ZymoBIOMICS 标准品 run 普遍 2GB+，且无天然两组设计，排除（体积与分组均不合）。
- PRJDB4115/PRJDB5315（健康人唾液宏基因组，小 run）：单一条件（健康），无两组结构。
- PRJDA72415（川崎病病原体检测，9 run）：需进一步核对分组与出版信息。
- PRJDB5375（日本东北海岸海洋宏基因组，40 run）：有地点/日期/粒径等天然分组维度（如 Sendai-Bay vs Aline），小 run 约 240–550MB，6 个约 2–3GB；但海洋宏基因组天然含噬菌体/病毒序列。

## 待用户决定的约束问题

用户约束为"禁止病毒样本、病毒专用数据库/模型与病毒功能元素"。任何真实宏基因组队列都不可避免地含有病毒/噬菌体序列：

- 严格读法：海洋/唾液等队列都不能用 → 需要一个人工肠道或单菌混合的 shotgun 设计（仍可能含噬菌体）。
- 宽松读法：约束针对**病毒专用** fixture/数据库/模型（如 sarscov2 测试数据、病毒分类器库），真实环境队列中的本底病毒序列不算"病毒样本"。

在得到明确解释前不下载队列数据。另：若认可 PRJDB5375，6 个小 run 约 2–3GB，当前磁盘余量（约 8G）可行但建议先清理本轮两个新镜像之一（autoplasm-r-analysis 5.05G / 覆盖版 python-slim 保留）。

## 当前状态

TT-003 保持 ready/open；legacy 16S 执行契约部分已完成（见 evidence/20261027-ena-legacy-framework.json），不以此关闭。
