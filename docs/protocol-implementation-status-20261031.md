# Protocol 功能实施核对（2026-10-31）

依据 `protocol-requirements-audit-20261030.md` 的 Step 1–20 与其引用的设计稿核对当前工作树。原核查报告保留为历史问题清单；其中“本次只核查”的描述不限制本次由用户明确要求的代码改造。

用户已明确：覆盖 P0/P1/P2；不实现 benchmark；跳过需要完整数据库和真实 cohort 的原生端到端验收。以下证据证明代码、实体契约与相应接口/规则，不宣称生物学性能或发布部署验收通过。

| 步骤 | 当前接线与主要交付 | 核对证据与边界 |
| --- | --- | --- |
| 1 输入与可复现性 | `PROTOCOL_INPUT_AUDIT` 检查 paired ID/顺序、原始字节 SHA256、SeqKit；原始样本表和额外元数据进入最终包 | 真实 SeqKit 前端链；相同读数但配对顺序错误的反例；普通/压缩输入字节校验回归 |
| 2 QC | 复用 FASTP/MultiQC；新增 fastp/宿主过滤保留率 | 原生 fastp 前端链；旧主入口 mock 全流程保留 MultiQC 接线；修复未压缩 FASTQ 的错误 `.gz` 别名 |
| 3 可选去宿主 | Bowtie2 + SAMtools `-f 12 -F 2304` 成对过滤，保存统计和参考 SHA256 | 原生链8 pairs→4 nonhost pairs，两个 mate 的全部 ID 与真值一致；无宿主参考时保留 clean reads |
| 4 PlasMAAG 主干 | metaSPAdes 图/reads cohort→已有固定 PlasMAAG 包装器；plasmid/cellular bins 分别进入候选/MAG 链 | `illumina.nf`、`plasmaag_binning.nf`、原生导出器与其回归；本次跳过真实 cohort 重建验收 |
| 5 补充识别 | geNomad 分类全 contigs，候选整合仅补未入 plasmid bin 的序列，保留分数和相关性说明 | 候选来源反例；内部 geNomad 与补充分数不算两条独立证据 |
| 6 统一候选 | 保留 bin 实体、原始样本/contig/分数/图状态；身份与结构/完整性分开 | bin/补充候选及单 contig 组合证据门控回归；不拼接无序 bin contigs |
| 7 保守去冗余 | strand-invariant 精确合并→分层 MMseqs2 99%/90% 双向覆盖；保留代表/成员/来源及片段 | 原生 core 链，校验统一参考与近重复成员映射；阈值仍为未校准工程初值 |
| 8 systems | 原始 MobMess 包含关系与系统组织；稳定 ID、fragment-linked、去歧义系统丰度 | 原生阳性1 system/4成员；片段、多系统成员不得膨胀丰度的反例 |
| 9 结构注释 | 统一代表目录→现有 Bakta；保留 header，导出标准 GFF/FAA/FFN/GenBank | 生产调用、Bakta 既有模块；本次跳过完整数据库 cohort 验收 |
| 10 功能/家族 | Bakta FAA→eggNOG/MMseqs2；质粒/系统基因表、system/sample 功能汇总、Fisher/BH | COG 多字母和样本检出门控回归；实际 R 富集与图形回归；不将未注释视为已证明无功能 |
| 11 AMR/stress/virulence | AMRFinderPlus `--plus`；原始命中、类型/method/scope/证据级别；质粒/样本/系统 ARG 表、环境汇总 | 官方数据库2026-08-07.1与固定上游测试序列：11 AMR、3 VIRULENCE、1 STRESS；其他类别不混入 ARG 矩阵 |
| 12 MGE/ARG 背景 | 原生 ISEScan/IntegronFinder 结果统一代表坐标；ARG 距离、序列窗口模块、边界截断 | 重叠距离与边界反例；窗口哈希定义共享候选，不将局部共位视作可转移单元认证 |
| 13 移动机制 | 原 MOB-typer；接合、动员、未检出、片段证据不足四类，保留原始标记 | 生产 `--multi` 接线与机制等级回归；未检出不能推断不可移动 |
| 14 统一定量 | 全部样本对同版竞争参考；合格 paired fragments、NM/MAPQ、重叠去重、mean/median/breadth、RPKM/TPM/检出率 | 原生 Bowtie2/SAMtools/pysam core counts=4/4/0；真实 BAM 过滤与来源/零样本回归 |
| 15 MAG | cellular bins→原 CheckM2/GTDB-Tk；质量 flags、唯一位点丰度、strain eligibility | 共享/质粒位点排除及有效长度反例；未评估 rRNA/tRNA 时仅给高质量候选，不能认证 MIMAG high quality |
| 16 宿主分级 | PLSDB 双向 HSP 并集覆盖、合格近完整 MOSTPLAS、按协变量/subject 分层的 MAG–质粒 FastSpar | HSP 重叠反例；原始 MOSTPLAS 权重4条预测；原生两层 FastSpar/bootstrap；未知宿主与生态关联不升级为物理连接 |
| 17 生态/差异 | 质粒与 system 两级 vegan/ANCOMBC2，在最终交付前执行；排序 PDF、PERMANOVA/dispersion、随机效应、区间 | 实际 vegan；ANCOMBC2 双组24样本、三组重复测量36样本；检查有限系数/全局 p 值/区间；小合成输入有拟合警告 |
| 18 比较/进化 | 单拷贝非移动核心→MAFFT/IQ-TREE；有向邻接差异与家族着色基因顺序 PDF | 原生4 taxa/3 core树；不合格系统跳过；内部方向改变与整条反向互补反例；实际 R 图已渲染查看 |
| 19 候选模式 | 原始 inStrain 复用定量合格 BAM；稳定样本 ID；A/B/C/D 与支持/反证/替代解释/时空字段 | 原生链排除每样本16个低 MAPQ pairs，保留770 pairs；popANI=1、compared bases=19750；A/B/C/D 正例及跨层、未知分类、无 MGE 等反例；无直接转移/方向认证 |
| 20 报告/包 | 代表级 metadata、矩阵、风险维度、事件表、HTML/PDF、统计、图、源码、实际软件版本/数据库内容身份、manifest | 实际 PDF/哈希与正向风险报告回归；27任务连接空候选路径；主入口预设失败写出真实失败样本/任务/退出码 |

实现入口为 `-profile short_read_protocol,conda`（或 mamba）；原平台入口保留。生产接口、资源字段、初始门槛和当前原生证据路径见仓库根目录 `PROTOCOL.md`。

`tests/protocol/run_connected.py` 运行真实 `SHORT_READ_PROTOCOL` 子流程的空资格路径，不冒充有候选的全资源 cohort。`tests/protocol/run_native_extensions.py` 运行相应原生生产模块；旧主入口 mock 回归只证明编排/报告契约。阈值校准、方法准确性、完整资源 cohort 和 benchmark 均不从这些接口测试推断。

最终记录：95项回归通过；连接子流程27个真实任务通过；旧 Illumina mock 流程178个任务记录通过（154 CACHED、24 COMPLETED）。最终包650个 manifest 条目及516个当前生产源码快照已逐项校验。额外 ANCOMBC2 原生重跑被自动审批服务额度限制阻止，未启动；已有拟合证据与最新公式/资格/版本检查分开记录于 `PROTOCOL.md`。
