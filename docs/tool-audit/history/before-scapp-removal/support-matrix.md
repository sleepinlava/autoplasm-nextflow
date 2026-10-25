# 平台与选项接线矩阵（静态）

基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。完整平台输入/输出见 platform-matrix.tsv；这是实际源码接线清单，不是已验证支持承诺。五个平台当前真实运行认证均 not_verified。

| 选择 | 代码提供输入的条件 | 不满足时当前行为 | 审计要求 |
| --- | --- | --- | --- |
| SCAPP detection | illumina + metaspades | 空 reads/graph channel，工具不运行 | TA-007，入口拒绝或显式报告不支持 |
| SCAPP binning | illumina + metaspades | 空 graph/read join | 同上 |
| Recycler | illumina + metaspades 或 hybrid + hybridspades；同次SPAdes图/k及组装short pairs | 主入口明确拒绝其他组合；支持组合严格join后专用graph-node BAM/BAI | TA-002/003/004/051/052已验证限定接口修复；真实minigut native4任务、受控k33/k55及失败传播通过；完整平台/容器/框架及科学准确率仍未认证 |
| gplas2 | illumina + metaspades | 空 plasmid/graph join | 同上 |
| plasmaag | 有 plasmid + coverage table；assembly 无 coverage | assembly 下空 join | 应校验输入能力 |
| Kraken2 | is_illumina=true | 其他平台无执行，但仍可能要求 kraken2_db | 缺少兼容性反馈 |
| PlasmidHostFinder | is_assembly=true | 其他平台无执行 | 缺少兼容性反馈 |
| long_read linking | host_plasmid_linking=true 且 has_long_reads=true | Illumina 无执行；assembly 不调用 HOST_LINKING | 应拒绝不支持组合 |
| CONCOCT / SemiBin | 非 assembly，提供 assembly+BAM | 运行结果未进最终 bins | TA-008 |
| ABRICATE optional | 文档要求 annotation_optional_tools；代码只查 annotation_tools | 文档方式选用无执行 | TA-009 |

环境 profile 清单为 conda/mamba/docker/podman/singularity/test；实际版本和容器覆盖必须由 `nextflow config` 与任务命令解析。config-selectors.tsv 登记 130 条 selector、ext 参数或 includeConfig 声明，尚未做运行时优先级求值。

include-edges.tsv 含 162 个导入符号；reachability.tsv 记录 main.nf 的词法可达闭包（95/101）。其余文件是未被主入口 include 的候选闲置模块，不能仅凭不可达推断应删除。生成命令：python3 docs/tool-audit/scripts/scan_wiring.py。无缺失 include 路径；此图仅说明定义可达，不能证明分支启用、tuple 契约或运行成功。

GPLAS2 即使存在 metaspades graph channel，当前传入 FASTG 也不等于其 GFA 契约，且 prediction 传的是 FASTA；见 TA-021。PlasMAAG 即使有 coverage table 也不等于 reads/contigs manifest；见 TA-018。
