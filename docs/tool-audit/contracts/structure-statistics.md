# 结构与统计结果语义

2026-10-20；基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

TA-036：bin/plasmid_structure.R 的 itr_ok 分支直接输出 is_circular=true。实际原脚本运行：人工 ITR-only 序列输出 true、method=itr、overlap=25。末端反向重复本身不足以证明环状：[原始研究 PMID 9695931](https://pubmed.ncbi.nlm.nih.gov/9695931/) 报道带末端反向重复的线性质粒。该反例证明当前推断规则不成立，不表示人工序列已获实验拓扑真值，也不能简单将所有 ITR 改判为线性。需要分开 repeat_type、拓扑证据、unknown 状态，并以独立已知拓扑及图/reads 证据验证。现有 warning 不消除 true 字段的错误含义。

TA-037：同一次运行中 >linear not_circular 的无末端重复序列输出 true/header_marker/overlap=0。_circular 固定子串命中否定标记。应定义精确 token、值及冲突规则。

测试逻辑：tests/r_mock/run_r_mock_tests.sh:179-184 只覆盖 DTR 阳性与普通线性阴性，未覆盖 ITR 与否定标记；记入已有 TT-002 的语义覆盖范围，不重复累计测试问题。

正常数值对照：A=[1,2,4]、B=[8,11,14]，每组 3 个样本，原 differential_abundance.R 返回 Welch p=0.021424、log2fc=-2.237039；独立 scipy.stats.ttest_ind(equal_var=False) 为 0.021424021917151804，Python log2 为 -2.2370387101571954，与六位小数输出一致。仅证明此单 feature 正常内部统计分支；不替代 DESeq count 单位、跨样本实体或空/退化边界验证。

完整命令、退出码、输入与原输出：results/tool-audit/20261020-structure-stats/run.json 及同目录。使用原生 R 和本地包，未运行 FASTSPAR 生物学网络。ASSEMBLY 的空 reads/MAG/coverage 通道与声明边界已阅读，未增加无证据故障结论。

## 网络过滤边界

TA-038：原 network_prepare.R 使用 6 样本整数 raw_count fixture：common 仅 S0-S4 各10，singleton 仅 S5 为10。默认 min-prevalence=0.2 去除 singleton 后，仍输出 common 的 S5=0 列，日志却报告 0 empty samples。删除全零样本发生在过滤前，没有对最终矩阵复核。应定义过滤后 eligibility 与 insufficient-data 状态，不能仅靠入口 n_samples 放行。完整输入/输出、原命令与退出码在 results/tool-audit/20261020-network-boundary/。没有执行 FastSpar，不声称其一定退出失败或已量化相关偏差。

[FastSpar v1.0.0 README](https://github.com/scwatts/fastspar/blob/v1.0.0/README.md)（blob 0c0d19a72adb19ec1ccadba094766074e21359b1）明确要求 absolute OTU counts。网络脚本将 coverage 取整用作 count proxy，不能据此视作计数单位已验证；与已有 TA-012 的单位风险一起评估，但不将 DESeq 的诊断直接等同于 FastSpar 的实际行为。该版本文档把相关估计和 bootstrap p-value 分为独立步骤；当前只声明 correlation/covariance，缺 p-value 本身不新增为 CLI 缺陷。

P3 nodes-cross-sample-fastspar.nf.test 的“square matrix”断言实际只比较 header 和首数据行的列数，没有检查所有行数/标签、有限性、对称性、取值范围或 covariance；NETWORK_PREPARE 的最终样本矩阵也未核对。补充已有 TT-002 的断言覆盖问题。该 fixture 是真实 ENA contig abundance，不是已验证质粒网络真值，保留其明确范围。

### TA-038门控补证

2026-10-20：20个样本，每个仅有一个独有feature、raw_count10，默认prevalence0.2把全部20个feature滤除；NETWORK_PREPARE输出0feature×20sample矩阵。局部实际Nextflow调用原NETWORK_PREPARE/FASTSPAR模块，harness复制CROSS_SAMPLE的pre-preparation非空行filter，FastSpar仅替换为清楚标记的观察型CLI writer。trace显示两原process均执行；下游.command.out记录features0/samples20。证明门控检查发生在过滤之前，未验证最终矩阵适用性，不证明真实FastSpar退出0或任何模型结果。

全部fixture、config、命令、trace、工作目录.command.sh和observer源码保留results/tool-audit/20261020-network-gate/。任务1CPU/1GB，无下载，启动前df可用119G；receipt的磁盘bytes为运行后采样，不能伪称运行前测量。不能将本局部harness升级为完整CROSS_SAMPLE/P4通过。

## 2026-10-20 TA-037 表头解析修复

表头阳性限精确circular=true/topology=circular token或首个序列ID的_circular后缀；否定token和_not_circular ID后缀禁用header推断，冲突写warning。未修改DTR/ITR算法、低复杂度过滤或拓扑字段定义。新增5项回归方法，修复前5个失败子场景；最终5/5通过（9.894秒）。原PLASMID_STRUCTURE wrapper两任务均exit0，7条混合标记记录的ID/调用/方法匹配预期、空FASTA输出仅表头。证据：results/tool-audit/20261020-structure-header-fix/receipt.json及wrapper.json、原trace/work命令。

TA-037关闭；TA-036的ITR环状推断仍未决。fixture是人工解析/重复序列，不能替代已知生物学拓扑或容器环境认证。此前仅靠否定、部分或冲突header判阳性的结果可能改变，需重新生成结构和依赖报告；未判header阳性不能解释为确认线性。

## 2026-10-21 TA-036 ITR 拓扑误判修复

固定真实参考 NC_003903.1（SCP1，356023 bp）GenBank 标记 linear，完整 FASTA 与 GenBank ORIGIN 核酸一致；[1991年独立原始实验研究](https://pmc.ncbi.nlm.nih.gov/articles/PMC207291/)通过凝胶/酶切/杂交等支持其线性拓扑并报道末端反向重复。原脚本实际输出 true/itr1000，构成真实反例。新逻辑保留 ITR 检测、seed21/延伸上限1000和低复杂度过滤，ITR-only 改为 false/unknown，不解释为确认线性。DTR/明确 header 仍只是 circular_candidate。原八列保留、追加 repeat_type（经过过滤的重复类型）、topology_status、topology_evidence；header 分支原 overlap 算法未改变。

原 wrapper 对 SCP1、真实 pUTI89 NC_007941.1 原 FASTA、明确据其独立 GenBank circular 注释派生的 header 输入、人工 DTR+ITR、空输入五任务通过。pUTI89 没有终端重复/header 的原 FASTA 正确保持 unknown；已知环状并不意味着 FASTA 本身可支持环状推断。原 REPORT 一任务核对五样本总数/环状候选数，ITR-only 不再增计；报告明确 false 不表示线性。报告目录是显式新建并在结构完成后准备，TA-015仍未决。

13结构单元方法（含原5header）、3报告方法、54 R smoke 断言、原 PLASMID_DETECTION 三路由26任务通过。后者分类器是明确 observer，消费者是实际 R；不认证分类推理、组装图/reads闭环证据、镜像/nf-test/完整平台或拓扑灵敏度。数据与固定 SHA、命令、trace、前后表在 results/tool-audit/20261021-structure-topology/receipt.json；测试数据锁 tests/structure-reference.lock.json。TA-036 局部修复 verified，重新生成受影响结构/报告以去除原 ITR 假环状记录。
