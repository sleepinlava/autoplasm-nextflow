# ENA 历史用例的实验类型与验收范围（TT-013）

> 当前状态：2026-10-25 已完成本契约列明局部修复的统一验收；见 [接受记录](../../../results/tool-audit/20261025-consolidated-acceptance/receipt.json). 下文按历史顺序保留尝试及限制。

2026-10-25；原始响应和变更前来源保存在 `results/tool-audit/20261025-p4-assay-audit/`。

PRJNA848809 的 portal 表将 12 个 run 标为 WGS/METAGENOMIC/RANDOM，但所有 experiment title 均指向 16S。抽查 SRR19638267 对应 SRX15688496 的原始 XML，实验设计也明确为 16S。对应原始论文（DOI 10.3390/ijms23158073）第 4.2 节描述 341F/805R 引物 PCR；第 4.5 节将数据关联到该 BioProject。因此，不能单凭结构化 WGS 字段把这组数据认定为适用的 shotgun 质粒验证数据。

来源：[ENA 原始实验](https://www.ebi.ac.uk/ena/browser/api/xml/SRX15688496)、[作者论文](https://www.mdpi.com/1422-0067/23/15/8073)。XML 首次获取失败后重试成功；USDA 论文下载超时保留，不伪造本地全文。论文方法与项目关联通过公开论文检索核对。

原用例仍可显式运行，名称和 tag 改为历史 16S 执行契约，移出 P4 tag；生产科学方法不变。`when` 参数、整个 `then` 断言块、六个分组及十二个下载文件/MD5 均保持原样；独立核对十二个 MD5 与当前 ENA 官方表完全一致。数据锁增加实验类型、来源和冲突说明。QUAST 阈值 200 保留为历史配置，不再把短组装解释为低生物量。

该用例不能认证质粒缺失、质粒丰度、差异或网络的生物学结论，也不能满足真实非空 shotgun P4。TT-003 仍需适用的真实数据、实际非空统计与完整部署验证；不通过降低门槛、复制技术样本或制造质粒阳性来关闭。已有受控原生统计用例仍只认证其数值和执行范围。

`evidence-check.json` 核对实际 run→experiment、原始说明、十二 MD5 和断言字节不变。nf-test dry discovery 单列记录，只证明用例能被发现，不表示实际执行或方法通过。TT-013 的范围修正待与统一来源/补丁验收一起接受；此前 receipt 保持冻结。

2026-10-25 统一复核后，上述局部修复已接受，详见 `results/tool-audit/20261025-consolidated-acceptance/receipt.json` 及同目录 `review.md`、`evidence-recheck.json`。仅关闭列明缺陷；原有在线/全冷部署/完整平台/科学效果限制继续保留，历史ready/待验收文字描述的是当时状态。
