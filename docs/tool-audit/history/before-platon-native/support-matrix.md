# 平台与选项接线矩阵（静态）

基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。完整平台输入/输出见 platform-matrix.tsv；这是实际源码接线清单，不是已验证支持承诺。五个平台当前真实运行认证均 not_verified。

| 选择 | 代码提供输入的条件 | 不满足时当前行为 | 审计要求 |
| --- | --- | --- | --- |
| SCAPP detection（退役） | 按用户要求移除 | 旧选择在主入口失败，0分析任务 | TA-006/035退役；不计修复通过 |
| SCAPP binning（退役） | 按用户要求移除 | 旧选择在主入口失败，0分析任务 | 历史对象保留，不再声明支持 |
| PlasX | 逐样本注释及模型契约TA-025尚未满足 | 消费者按官方分数表严格>0.5；错误分数拒绝 | TA-023仅消费者修复verified，工具节点未认证 |
| PLASMe | 正确安装PLASMe1.1、完整模型/DB并提供assembly | 适配器要求官方FASTA/report一致，压缩先解码 | TA-024/053及069–073按完整模型/native/nf-test/Conda/Podman有界verified；同一pUTI89重放不代表独立生物样本或完整平台认证 |
| RGI | annotation_optional_tools包含rgi，card_db为同一JSON版本的prepared目录 | 始终task-local load/main，配置/加载副本不一致则失败 | TA-028实际原生两份完整CARD和downstream通过；wildcard/image/框架及完整平台未认证 |
| Recycler | illumina + metaspades 或 hybrid + hybridspades；同次SPAdes图/k及组装short pairs | 主入口明确拒绝其他组合；支持组合严格join后专用graph-node BAM/BAI | TA-002/003/004/051/052已验证限定接口修复；真实minigut native4任务、受控k33/k55及失败传播通过；完整平台/容器/框架及科学准确率仍未认证 |
| gplas2 | illumina + metaspades | 空 plasmid/graph join | TA-007仍未决，需入口拒绝或显式报告不支持 |
| plasmaag | 有 plasmid + coverage table；assembly 无 coverage | assembly 下空 join | 应校验输入能力 |
| Kraken2 | is_illumina=true | 其他平台无执行，但仍可能要求 kraken2_db | 缺少兼容性反馈 |
| PlasmidHostFinder | is_assembly=true | 其他平台无执行 | 缺少兼容性反馈 |
| long_read linking | host_plasmid_linking=true 且 has_long_reads=true | Illumina 无执行；assembly 不调用 HOST_LINKING | 应拒绝不支持组合 |
| MetaBAT2 / CONCOCT / SemiBin | 非 assembly，提供匹配assembly/BAM；多个分箱器必须同时选DAS Tool | 单分箱器直达下游；多分箱器按样本汇总DAS，缺/重复键拒绝 | TA-008路由有界verified；CONCOCT实际覆盖/聚类/提取已验，SemiBin模型及TA-049无bin契约仍未认证 |
| ABRICATE optional | annotation_tools 或 annotation_optional_tools | 关闭/空输入无任务，启用按样本进入模块 | TA-009路由observer已验证，实际搜索未认证 |
| GTDB-Tk | 最终bin列表及完整r232参考库 | 私有fna副本保留原ID/DNA，标准2.7.2流程含ANI预筛选 | TA-076过期CLI修复有界verified；TA-031输入适配ready，真实分类/模型/镜像仍未认证；contracts/gtdb-inputs.md |
| SemiBin | 同一assembly与BAM，2.4.1默认CPU短读长自监督方法 | 允许合法无最终FASTA，保留诊断及显式no_bins；真实.pt检查点发出；stub未知 | TA-049/079 native边界有界verified；官方软件fixture不认证生物学分箱/MAG质量，GPU/镜像/nf-test/全平台未验；contracts/semibin-states.md |
| 蛋白消费者 | 至少一个非空Prodigal蛋白样本；同样本DNA/GFF/AA/CDS严格连接 | 共享一次基因预测；gembase按原contig/位置排序；未知线性、明确闭环环状；零蛋白显式状态且跳过工具/模型下载 | TA-026/027/077/078按真实native有界verified；完整CONJScan2.1.0、官方小eggNOG fixture库、记录的原生归档获取替代。镜像/全量eggNOG/在线模型获取/nf-test/完整平台/科学准确率未认证；contracts/protein-inputs.md |
| COPLA | 选择typing_optional_tools=copla，声明固定安装和完整参考图/list | 每条候选独立分析，保留DNA/ID/长度，工具失败拒绝发布 | TA-019/020/074按完整9894参考、2固定真实阳性及原nf-test有界verified；不代表任意质粒分类准确率 |
| TETRA sequence | 显式选择sequence及匹配MAG；只生成组成分数 | 标准双链256槽、不可评分弃权；不应用阈值、不发宿主链接 | 按用户决定关闭TA-039错误链接风险；55来源科学阈值仍失败，不声称校准通过；contracts/tetra-score-only.md |

环境 profile 清单为 conda/mamba/docker/podman/singularity/test。config-selectors.tsv当前登记148条selector、ext参数或includeConfig声明；实际Nextflow26.10.0隔离展开默认/5后端/test/5组合共12唯一场景已按当前配置重放。尚未证明全部模块closure、selector优先级或可执行环境/镜像完整就绪；见evidence/profile-resolution.json。

include-edges.tsv当前含212个导入符号；reachability.tsv记录109个当前生产文件、主入口词法可达102个。其余文件是未被主入口 include 的候选闲置模块，不能仅凭不可达推断应删除。生成命令：python3 docs/tool-audit/scripts/scan_wiring.py。无缺失 include 路径；此图仅说明定义可达，不能证明分支启用、tuple 契约或运行成功。

GPLAS2 即使存在 metaspades graph channel，当前传入 FASTG 也不等于其 GFA 契约，且 prediction 传的是 FASTA；见 TA-021。PlasMAAG 即使有 coverage table 也不等于 reads/contigs manifest；见 TA-018。

| HOTSPOT | 固定0e3e3013、显式完整DB/models/program输入、正常CPU模式 | 原始谱系+严格链接转换+运行/转换状态；无特征不能伪装阴性 | TA-046/080/081有界原生/锁定Conda/cached失效已验；非科学准确率/GPU/镜像/nf-test/AWS；contracts/hotspot-native.md |
