# 宿主关联本地接口审查

2026-10-20；基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。科学方法和对应上游算法尚未独立定量验证。

sequence：标准TETRA仅保留组成分数。remainder join保留质粒样本、缺bins/tax传[]；nested/gzip MAG、重复host_id拒绝及两域taxonomy保护不变。数值为tetra_markov256_v1，分类信息在sequence_scores.tsv的host_taxonomy列；55来源科学阈值失败后，用户决定停用未校准宿主链接，兼容links表仅表头，统一links通道不发TETRA关联，另发sequence_scores。详见tetra-score-only.md；以下旧调查和时间点记录保留。

long_read：生产流程提供 CONTIG_COVERAGE.out.long_bam（hybrid 不使用 short+long merge），本地脚本过滤 unmapped/secondary/QCfail/duplicate/paired 和低 MAPQ/短比对，要求同 read 有 primary+supplementary，按唯一 read 计数。host_id_type=contig 在输出明确，不能升级解释为已确认物种宿主。query 区间和嵌合读段的科学效应仍需阳性/阴性独立基准，当前未认证。

co_abundance：使用显式 host sample IDs、按共同样本交集、BH 在相关阈值筛选前计算；脚本已有 exploratory/compositional 限制。跨样本 plasmid 实体受 TA-010 影响，缺表/零检出样本处理受 TA-013 影响，不能凭相关计算局部正确给整链放行。

已有 linking 单元用例正在复验；人工用例不算真实工具或宿主准确率验证。未把当前未发现新差异表述为 matched。

## query 几何与独立统计对照

2026-10-20：原 longread_bridge_link.R 对三组人工SAM运行，参考LN=1000、read/QUAL均500、POS/CIGAR在边界内，避免先前4bp toy reference限制。两条独立read各primary p1 + supplementary h1：

- disjoint：200M300S 对200S200M100S，query区间[0,200)、[200,400)，输出score2。
- overlap：两个记录都200M300S，query区间完全重叠，仍输出score2。
- low_mapq：disjoint但MAPQ10，输出空表，日志lowmapq=4。

源脚本scanBam没有保留query起止/strand/clip/SA关系，后续只按QNAME、flag和RNAME集合计数。这说明没有独立验证spanning几何，不能把输出升级为已证实物理宿主关联。[SAM规范](https://samtools.github.io/hts-specs/SAMv1.pdf)将嵌合比对描述为没有大范围重叠的线性比对集合。本次overlap刻意违背该标记语义，仅是consumer鲁棒性反例；未测真实minimap2是否产生这种记录，未证明生产错误率，不新增确定性生产缺陷。下一步需真实aligner的重复区/嵌合阴性、反向链、hard/soft clip和合理重叠容差基准，不能未经方法决策禁止所有小范围重叠。原输出与命令位于 results/tool-audit/20261020-longread-geometry/run.json。

另补共丰度非平凡数值对照：6样本、1 plasmid、3 taxa，Pearson r=±0.92689738158054、0.2；三项整体BH后q=0.01173098894、0.01173098894、0.704。原脚本min-correlation0.6输出正负两条，p/q/score与独立SciPy pearsonr/false_discovery_control在输出精度内一致，证明本fixture下BH使用完整三项假设集而非过滤后两项。完整fixture/检查脚本/receipt在同目录coabundance/。仅Pearson、人工profile；不替代组成数据推断、Spearman exact/ties或真实宿主真值。

## TT-008：重复键回归假通过

2026-10-20原run_module_regressions sequence与sequence-optional在真实Nextflow26.10/native R运行，两个runner exit0。sequence nested目录正例通过；optional的default/no-mag/no-taxonomy各2个COMPLETED任务，no-plasmids没有LINK_SEQUENCE任务，与这些局部routing预期一致。它们使用同一周期序列，不消除TA-039/040方法缺陷。

但duplicate-keys场景未被拒绝：原suite trace有两个S1任务COMPLETED/exit0，任务目录两个S1.sequence_links.tsv分别1行和0行数据，都会发布到同一个最终文件名。suite仍输出全部通过。原因run_nf(expect_success=False)仅禁用subprocess check，并不要求失败；case只查combined stdout/stderr含duplicate或same key，而正常OPTIONAL_LINK打印路径work-duplicate-keys正好匹配。

为避免由runner总exit0误推子workflow状态，单独直接重跑duplicate case，明确原Nextflow workflow exit0，两个任务COMPLETED。此为强证据说明负向断言无效。不是说完整main会接收重复sample ID：原main全表ID guard已有拒绝证据，重复由harness故意注入；subworkflow是否独立拒绝重复需明确契约。不能仅把case目录改名来“修复”，必须要求真实失败和正确诊断。

完整runner日志/trace引用/两个文件hash在results/tool-audit/20261020-sequence-routing/run.json；直接重跑的命令日志、trace和退出状态在duplicate-direct/。原保留工件/tmp/autoplasm-module-regression-ae6_ilzm及/tmp/autoplasm-module-regression-ap_olj7n。生产与原测试尚未修改。

## 2026-10-20 TT-008 负向判定与重复键修复

run_nf 的 expect_success=False 现在必须取得非零退出；重复键场景必须匹配实际 Nextflow 的完整 duplicate emission 诊断，路径中出现 duplicate 不再足够。原序列套件加正确退出断言后实际退出1，暴露原workflow仍成功并发布两个S1结果。随后两个序列join启用failOnDuplicate，并对plasmid、MAG、taxonomy三路重复分别验证拒绝；保留原正常、缺MAG、缺taxonomy、空plasmid四场景。最终4项oracle单元、7场景原序列套件、5场景原CRISPR套件通过。

证据：results/tool-audit/20261020-negative-oracle-fix/receipt.json、各原始log及retained trace。此为人工路由fixture；重复检测按完整metadata键，不能推导全部host linking路径按sample_id唯一，也不提供异步失败前任务/发布的事务回滚。CRISPR disabled main仍因其他输入校验失败，不算成功E2E。TT-008关闭，其他主路径/科学契约仍未决。
