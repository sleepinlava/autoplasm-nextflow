# 平台与选项接线矩阵（静态）

基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。完整平台输入/输出见 platform-matrix.tsv；这是实际源码接线清单，不是已验证支持承诺。五个平台当前真实运行认证均 not_verified。

| 选择 | 代码提供输入的条件 | 不满足时当前行为 | 审计要求 |
| --- | --- | --- | --- |
| SCAPP detection（退役） | 按用户要求移除 | 旧选择在主入口失败，0分析任务 | TA-006/035退役；不计修复通过 |
| SCAPP binning（退役） | 按用户要求移除 | 旧选择在主入口失败，0分析任务 | 历史对象保留，不再声明支持 |
| PlasX | 完整逐样本COG14/Pfam32/十组de novo及原模型，固定来源/锁 | 原生/Conda/nf-test/独立算术有界通过；旧共享注释方法结果需重算；整组装0基因排除支持 | 无独立准确率/OCI/完整平台/AWS认证；contracts/plasx-native.md |
| PLASMe | 正确安装PLASMe1.1、完整模型/DB并提供assembly | 适配器要求官方FASTA/report一致，压缩先解码 | TA-024/053及069–073按完整模型/native/nf-test/Conda/Podman有界verified；同一pUTI89重放不代表独立生物样本或完整平台认证 |
| RGI | annotation_optional_tools包含rgi，card_db为同一JSON版本的prepared目录 | 始终task-local load/main，配置/加载副本不一致则失败 | TA-028实际原生两份完整CARD和downstream通过；wildcard/image/框架及完整平台未认证 |
| Recycler | illumina + metaspades 或 hybrid + hybridspades；同次SPAdes图/k及组装short pairs | 主入口明确拒绝其他组合；支持组合严格join后专用graph-node BAM/BAI | TA-002/003/004/051/052已验证限定接口修复；真实minigut native4任务、受控k33/k55及失败传播通过；当前原P3框架重放通过；完整平台/容器及科学准确率仍未认证 |
| gplas2 | illumina/metaspades 或 hybrid/hybridspades，同次SPAdes GFA | 图节点重新运行同一组分类器/共识，按完整样本域连接；其他组合入口拒绝 | 原生geNomad+gplas及真实框架有界通过，TA-021本批有界verified；完整hybrid/准确率/OCI/AWS未认证；contracts/gplas-native.md |
| plasmaag | Illumina完整cohort的组装+原始配对reads；metaSPAdes三件套或MEGAHIT兼容FASTA | 独立于阳性质粒过滤；按样本恢复ID/meta，缺失/重复/不一致拒绝，至少8CPU | 真实生产/框架/contigs模式产物有界通过；精确锁离线新环境补验通过，在线安装仍受限，TA-018/090本批有界verified；contracts/plasmaag-native-progress.md |
| Kraken2 | is_illumina=true | 其他平台无执行，但仍可能要求 kraken2_db | 缺少兼容性反馈 |
| PlasmidHostFinder | is_assembly=true | 其他平台无执行 | 缺少兼容性反馈 |
| long_read linking | host_plasmid_linking=true 且 has_long_reads=true | Illumina 无执行；assembly 不调用 HOST_LINKING | 应拒绝不支持组合 |
| MetaBAT2 / CONCOCT / SemiBin | 非 assembly，提供匹配assembly/BAM；多个分箱器必须同时选DAS Tool | 单分箱器直达下游；多分箱器按样本汇总DAS，缺/重复键拒绝 | TA-008路由有界verified；CONCOCT实际覆盖/聚类/提取已验，SemiBin默认CPU模型/TA-049无bin有界verified；完整平台/MAG质量未认证 |
| ABRICATE optional | annotation_tools 或 annotation_optional_tools | 关闭/空输入无任务，启用按样本进入模块 | TA-009路由observer已验证，实际搜索未认证 |
| GTDB-Tk | 最终bin列表及完整r232参考库 | 私有fna副本保留原ID/DNA，标准2.7.2流程含ANI预筛选 | TA-076过期CLI修复有界verified；TA-031输入适配ready，真实分类/模型/镜像仍未认证；contracts/gtdb-inputs.md |
| SemiBin | 同一assembly与BAM，2.4.1默认CPU短读长自监督方法 | 允许合法无最终FASTA，保留诊断及显式no_bins；真实.pt检查点发出；stub未知 | TA-049/079 native边界有界verified；官方软件fixture不认证生物学分箱/MAG质量，GPU/镜像/nf-test/全平台未验；contracts/semibin-states.md |
| 蛋白消费者 | 至少一个非空Prodigal蛋白样本；同样本DNA/GFF/AA/CDS严格连接 | 共享一次基因预测；gembase按原contig/位置排序；未知线性、明确闭环环状；零蛋白显式状态且跳过工具/模型下载 | TA-026/027/077/078按真实native有界verified；完整CONJScan2.1.0、官方小eggNOG fixture库、记录的原生归档获取替代。镜像/全量eggNOG/在线模型获取/nf-test/完整平台/科学准确率未认证；contracts/protein-inputs.md |
| COPLA | 选择typing_optional_tools=copla，声明固定安装和完整参考图/list | 每条候选独立分析，保留DNA/ID/长度，工具失败拒绝发布 | TA-019/020/074按完整9894参考、2固定真实阳性及原nf-test有界verified；不代表任意质粒分类准确率 |
| TETRA sequence | 显式选择sequence及匹配MAG；只生成组成分数 | 标准双链256槽、不可评分弃权；不应用阈值、不发宿主链接 | 按用户决定关闭TA-039错误链接风险；55来源科学阈值仍失败，不声称校准通过；contracts/tetra-score-only.md |

环境 profile 清单为 conda/mamba/docker/podman/singularity/test。config-selectors.tsv当前登记155条selector、ext参数或includeConfig声明。当前实际Nextflow26.10.0隔离展开默认/5后端/test/5组合共12唯一场景全部重放通过，当前新增gplas/PlasMAAG选择器与默认值纳入；配置SHA前后不变、0分析任务，重放不增加独立场景分母。尚未证明全部模块closure、selector优先级或可执行环境/镜像完整就绪；见evidence/profile-resolution.json。

include-edges.tsv当前含223个导入符号；reachability.tsv记录112个当前生产文件、主入口词法可达105个。其余文件是未被主入口 include 的候选闲置模块，不能仅凭不可达推断应删除。生成命令：python3 docs/tool-audit/scripts/scan_wiring.py。无缺失 include 路径；此图仅说明定义可达，不能证明分支启用、tuple 契约或运行成功。

旧 GPLAS2 的FASTG/FASTA prediction与旧PlasMAAG的coverage接口已在当前工作批次替换。对应TA-021/018及TA-007/089/090已完成固定来源、接线和列明原生/测试证据的有界复核；旧实现的缺陷描述不能继续当作当前代码行为。

| HOTSPOT | 固定0e3e3013、显式完整DB/models/program输入、正常CPU模式 | 原始谱系+严格链接转换+运行/转换状态；无特征不能伪装阴性 | TA-046/080/081有界原生/锁定Conda/cached失效已验；非科学准确率/GPU/镜像/nf-test/AWS；contracts/hotspot-native.md |

| Platon | 固定1.7+完整v1.5.0 DB；accuracy+meta；Linux64锁 | 阳性/无检出/长度未评估分开；子工具/worker失败阻止发布，内容资源参与deep缓存 | TA-005/082–086原生/nf-test/Conda有界verified；同一阳性重放不代表多生物重复，非科学性能/OCI/完整平台；contracts/platon-native.md |

| MOB_SUITE_ANNOT/MOB_RECON | 按样本和阶段发布，默认copy | 原模块+输出替身验证缓存/冷运行发布及work清理后保留 | 仅发布契约，不认证MOB算法/安装/数据库；contracts/mob-publication.md |
