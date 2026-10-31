# 短读长 protocol 实现与使用

更新：2026-10-31。[文档导航](docs/README.md) · [使用指南](docs/usage.md) · [平台路线](docs/platform-workflows.md) · [开发指南](docs/development.md) · [实施状态](docs/protocol-implementation-status-20261031.md)。

本入口对应 `docs/protocol-requirements-audit-20261030.md` 的生产功能改造；不包含 benchmark 模块。
默认平台入口保留，使用 `-profile short_read_protocol,conda`（或 `mamba`）启用新链。新扩展声明了 Conda 环境；尚未提供所有新增工具的统一 OCI 镜像，不能把 Docker profile 当成这一入口的已验证部署方式。

```bash
nextflow run main.nf -profile short_read_protocol,conda \
  --samplesheet samples.tsv -params-file protocol-resources.json \
  --outdir results/protocol
```

`protocol-resources.json` 需要提供已准备好的资源路径：

```json
{
  "plasmaag_source": "/resources/PlasMAAG-fixed",
  "genomad_db": "/db/genomad",
  "bakta_db": "/db/bakta",
  "mob_suite_db": "/db/mob-suite",
  "amrfinderplus_db": "/db/amrfinderplus",
  "eggnog_db": "/db/eggnog",
  "checkm2_db": "/db/checkm2/CheckM2_database/uniref100.KO.1.dmnd",
  "gtdbtk_db": "/db/gtdbtk",
  "mostplas_source": "/resources/MOSTPLAS",
  "plsdb_fasta": "/db/plsdb/plasmids.fasta",
  "plsdb_hosts": "/db/plsdb/hosts.tsv",
  "ancombc2_formula": "group + batch",
  "ancombc2_random_formula": "(1 | subject_id)",
  "ecology_formula": "group + batch",
  "ecology_block": "subject_id",
  "protocol_host_strata": "group,batch",
  "protocol_host_subject": "subject_id"
}
```

CheckM2 路径类型以已有模块的资源接口为准；GTDB-Tk 使用完整数据库目录。没有协变量/重复测量时，保留默认 `group`，随机效应与 block/subject 留空；不要照抄示例中不存在的字段。样本表保留额外元数据，`collection_date`、`site`、`environment` 用于候选事件和暴露画像。

PLSDB 标签表字段为 `reference_id`、`host_taxonomy`，ID 必须与 FASTA 对应。MOSTPLAS 目录需要原版 `test.py`、`models.py`、`functions.py`、`genus_index.txt` 和 `checkpoint/checkpoint.pth.tar`。包装器在任务私有副本中替换输入、输出和阈值常量，并补上上游 `functions.py` 遗漏的 `Bio.Seq.Seq` 导入，复用原始模型与特征实现；兼容修改记入 `status.json`。环境使用 CPU 版 PyTorch。

## 数据链与实体

1. 原始成对 ID/顺序检查、原始文件 SHA256、SeqKit 统计；fastp 后汇总保留率。去宿主时用 SAMtools `-f 12 -F 2304`，只保留两个 mates 均未比对且属于主记录的成对 reads。
2. metaSPAdes 完整图/路径和全部成对 reads 进入现有 PlasMAAG cohort 实现。PlasMAAG plasmid bins 成为主候选，cellular bins 进入现有 CheckM2/GTDB-Tk 链；geNomad 只补未进入 plasmid bin 的 contigs。
3. `entity_id` 保存 bin 实体；DNA 记录仍以 contig 为单位。不会把无序 bin contigs 串接成一个虚假的完整质粒。候选保留原始样本/contig/bin、两个工具的原始分数和图证据状态，不重复计算 PlasMAAG 内部使用的 geNomad 证据。身份分为高可信 bin、质粒样 contig、未确定片段，与结构等级独立。
4. 复用已有 strand-invariant 精确目录，再用 vendored nf-core MMseqs2 做 99% identity、90% 双向覆盖（`cov-mode 0`）、greedy representative clustering（`cluster-mode 2`）。独立支持的近完整序列、仅预测环化的候选、未知片段分别聚类；背景序列只做精确合并。阈值是未校准的工程初值。
5. 所有样本回贴同一冻结参考；注释只对该目录的质粒代表序列运行。Bakta 保留序列 ID，eggNOG 直接消费 Bakta 蛋白；所有整合坐标为代表序列上的 1-based inclusive 坐标。近重复成员不能直接继承代表序列的精确坐标。

`--protocol_complete_ids confirmed_ids.txt` 是可选的独立完整性证据断言，内容为每行一个精确序列 ID（`seq_` 加规范序列 SHA256）。可先查看目录/成员表确定这些 ID，再根据组装图、read 支持或外部证据审查并提供。它不是自动完整性评分；不得仅从环化标签或模型分数生成此文件。经近重复聚类后，支持状态随同类代表映射保留。默认还允许“PlasMAAG 高可信单 contig bin（原始分数 ≥0.7）、来自带图的重建、并有环化预测”进入近完整候选门控，记录为 `predicted_near_complete`，不会记作独立确认闭合。仅有环化标签、仅有分数或多 contig bin 均不满足此门控。其他序列保留 `circular_candidate`/片段状态；没有合格输入时，MobMess systems 与 MOSTPLAS 输出资格状态。

`catalogue/` 内保留 `candidate_evidence.tsv`、`sources.tsv`、`members.tsv`、`features.tsv`、`structure.tsv`、代表序列、片段序列和带 SHA256 的 manifest。ID 是序列身份，不是 plasmid system ID，也不是完整分子认证。

## 定量、统计与宿主

- 计数单位为合格 proper paired fragment：两端均为主比对、同一参考、MAPQ ≥10 且不等于255，`NM / aligned_query_length ≤ 0.02`。每个 query name 计一次；重叠 mates 每个碱基只算一次。输出平均/中位深度、覆盖广度、RPKM/TPM、低 MAPQ 比对比例与过滤统计。深度/广度统计基于同一合格 pair 集合。
- 初始检出规则为 breadth ≥0.75 且 mean depth ≥1；`protocol_min_breadth`、`protocol_min_depth` 和 `protocol_max_mismatch_rate` 可显式配置。片段检出不等于整条质粒存在。阈值需要后续独立校准，本次不实现 benchmark。
- 多样性和差异分析消费质粒表。vegan 提供 TSS Bray、PCoA、PERMANOVA、betadisper；推断排除空样本并记录，历史基础矩阵仍明确标注两个空样本距离置0的兼容约定。公式、block、秩及剩余自由度显式检查。单组保留排序，不制造组间检验。
- ANCOMBC 2.8.0 的 `ancombc2()` 消费真实整数 counts，支持固定/随机公式、检出率过滤、结构零、BH、global/pairwise 和敏感性分析。系数及两两比较表追加 `ci_low_*`/`ci_high_*`：基于上游标准误的95%逐项正态 Wald 近似区间，未做区间的多重校正，方法记入 status。生态推断同时导出 `ordination.tsv` 和 `ordination.pdf`。零特征、空样本、重复数不足输出资格状态；有资格但运行失败时不会退回 Welch。原 Welch 保留为单独的探索分析，protocol 默认关闭。
- MobMess 系统 ID 根据 backbone 序列成员生成稳定哈希。系统丰度仅汇总单一系统的非片段成员，排除 fragment-linked 和多系统歧义成员；coverage 为成员深度之和，不解释成 system copy number。
- MAG 初筛为 completeness ≥50%、contamination ≤10%，这不等于 MIMAG high-quality 认证。`MAG_quality_flags.tsv` 按 completeness ≥50%、contamination <10% 标记中等质量，否则低质量；>90%/<5% 另标为完整度/污染度高质量候选。未评估 MIMAG 要求的 rRNA/tRNA，不能认证高质量。同一参考上的 MAG 位点按 bin 成员映射，排除同时属于多个不同 MAG 的共享位点及质粒位点；MAG 深度/广度按有效长度加权。它是保守的唯一位点丰度，非独立的 CoverM genome estimator。
- PLSDB 要求 ≥99% identity、≥90% 双向 HSP 并集覆盖，不累加重叠 HSP。MOSTPLAS 仅对上述门控下的近完整候选代表预测 host range；预测资格不等于分子完整性认证。
- 质粒—MAG 共丰度直接调用 FastSpar，而非 MetaPhlAn/Spearman。按指定分类协变量分层，每层每个 subject 保留按 sample ID 排序后的首个观测，至少20个独立、非空样本；运行 bootstrap/p-values，针对质粒—MAG 边做 BH。层间不合并为因果宿主结论，也不声称校正任意连续混杂；连续协变量需先定义合理的分层设计。

## P1/P2 与交付

- AMRFinderPlus 4.2.7 启用 `--plus`，按原生 `Element symbol / Type / Subtype` 列整合 AMR、STRESS、VIRULENCE。`amrfinder_hits.tsv` 保留全部原始列，`amrfinder_elements.tsv` 保留类型、scope、method 和检测证据级别；完全匹配、局部命中、同源候选不能混作已证实功能。质粒/样本/系统 ARG 矩阵及 ARG 邻域仅统计 AMR；毒力和应激候选单独进入风险画像及按环境汇总。未检出已收录毒力基因不等于全面毒力筛查阴性。
- ARG、IS、integron 统一坐标、最近距离、边界截断、序列定义的 ARG 邻域候选；MOB-typer 保留原始机制预测，另分为接合系统检出、动员特征检出、未检出已知系统、片段证据不足四类。
- MMseqs2 蛋白家族、稀疏 presence/absence 表、系统核心/附属基因、system/sample 功能汇总与 Fisher/BH 富集。多个 COG 字母分别归类；样本功能表仅汇总达到检出门槛的代表序列。稀疏表的未列出组合为0，全部代表序列域见 catalogue。基因顺序邻接差异保留方向、对整条反向互补不敏感，作为结构变异候选；另导出按家族着色的系统基因顺序 PDF，不排除断裂组装或基因调用差异，也不是核苷酸比对图。
- 每个系统独立筛选单拷贝保守蛋白，排除已注释移动蛋白和 ARG 邻域；默认至少4个可比成员、3个核心家族，才调用 MAFFT 和 IQ-TREE 2。没有全局质粒树，也不把筛选当作排除了全部重组。
- inStrain 仅在至少75%的 MAG 长度可由唯一位点归属、且平均深度 ≥5、breadth ≥0.75 的样本中 profile/compare；共享同一参考与 scaffold-to-bin 表。直接复用定量时已生成的合格 BAM，确保两端均满足 MAPQ/NM 门槛，不受 inStrain 默认低 MAPQ 策略影响。该中间 BAM 仅在启用 strain 时保留在 work 中，不重复发布大文件。近菌株候选门槛为 popANI ≥0.99999、coverage overlap ≥0.75、compared bases ≥10000，均为显式工程初值。
- A/B/C/D 候选事件分别表示近菌株与系统共同出现、不同分类宿主候选中的共享系统、不同系统的相同 ARG/MGE 序列窗口、证据不足的共同检出。保留支持、反证、替代解释和时间/地点；无物理宿主证据时不升级为直接转移结论。
- `final/delivery/` 输出冻结 FASTA、metadata、原始 paired-count/TPM 宽矩阵、长格式 coverage、prevalence、宿主证据、ARG/MGE/系统产物、菌株及事件表、多维 `risk_profile.tsv`、HTML/PDF、参数、执行脚本、生产源码快照和 SHA256 manifest。不合并成未经校准的风险分数；毒力维度限于 AMRFinderPlus 参考库已收录候选。
- 质粒与 system 的生态/ANCOMBC2 都在生成最终包之前运行，统计表、资格状态、区间及图一并进入执行证据目录；`CROSS_SAMPLE` 在 protocol 模式下不重复计算这两项。
- `software_manifest.tsv` 汇总实际版本输出、运行探针及 R 包清单；`database_manifest.tsv` 复用各资源在缓存查找前已计算的内容身份，导出资源路径、SHA256、文件数及字节数，不重新遍历数据库。上游发出的 release/date 标签保留于软件版本表及原始 `execution_records.json`；未发出人类可读 release 标签时，以内容指纹冻结资源，不推断其发布日期。
- `pipeline_info/` 另存 Nextflow trace/report/timeline、成功或失败的 `run_state.json` 与 `failed_samples.tsv`。仅在失败任务标签匹配输入 sample ID 时归属样本，其余明确标为 workflow/cohort 或未确定。resume 保留被复用任务的原始命令来源；`trace.tsv` 描述最近一次调用。

`plasmid_metadata.tsv` 按代表序列一行汇总稳定 ID、长度、序列状态、身份/结构证据、系统及成员等级、来源样本、检出率、ARG/毒力/应激候选、移动性和宿主证据类型。原始候选来源的多行记录保留在 `catalogue/candidate_evidence.tsv`，不与代表序列元数据混用。`samplesheet.tsv`/`metadata.tsv` 保留原始样本元数据；`checksums.txt` 为带 sample/mate 的 TSV 字节校验表；`raw_read_stats.tsv` 汇总 SeqKit 的原始统计。两级统计文件分别带 `plasmids.`/`systems.` 前缀。

资源不足时可显式关闭 `--protocol_host_models false`、`--protocol_evolution false`、`--protocol_strain false`。关闭并不表示相应生物学阴性。完整 profile 需要资源与相应环境；不能用接口回归测试代替真实工具全流程或科学性能验收。

## 上游复用来源

- [nf-core/modules](https://github.com/nf-core/modules)：已有 QC、组装、比对、注释、MAG 与 MMseqs2 模块继续复用。
- [PlasMAAG](https://github.com/RasmussenLab/PlasMAAG)：复用仓库现有固定源码/运行包装。
- [ANCOMBC](https://github.com/FrederickHuangLin/ANCOMBC/tree/RELEASE_3_20)：直接调用包的模型，不自行重写统计方法。
- [MobMess](https://github.com/michaelkyu/MobMess/tree/97c0cfc0f810062e32dcf34f700b1fc8be8029a4)、[PlasX utilities](https://github.com/michaelkyu/PlasX/tree/5c9acfd00a597da27ef5261acf72dbaf2117b645)：固定环境中的上游实现。
- [MOSTPLAS](https://github.com/wzou96/MOSTPLAS/tree/4aad570b42549c08bb0ce7e097868f46ae1cab85)：建议使用此源码版本和对应原始权重。
- [AMRFinderPlus](https://github.com/ncbi/amr)、[官方输出解释](https://github.com/ncbi/amr/wiki/Interpreting-results)：保留 upstream 类型、方法、scope 与原始命中；`--plus` 的结果不等于全面毒力或表型检测。
- [FastSpar](https://github.com/scwatts/fastspar)、[inStrain](https://github.com/MrOlm/inStrain)：调用原始 CLI；MAFFT/IQ-TREE 2 使用固定 Conda 版本。

## 验证入口

```bash
python -m unittest discover -s tests -p 'test_protocol_*.py' -v
python tests/protocol/run_core.py --outdir /tmp/protocol-core \
  --runtime-root /path/to/native-tool-prefixes --python /path/to/python-with-pysam
```

`run_core.py` 使用真实 Nextflow、MMseqs2、Bowtie2、SAMtools/pysam，输入是固定合成序列和已知 reads，验证实体与计数接线；不是 benchmark。`tests/protocol/host_association.nf` 是原生分层 FastSpar/bootstrap 接口入口。环境和权重未准备好的工具，须另行完成原生资源验收。

扩展模块的原生接口回归可使用已安装的对应 Conda 环境执行，例如：

```bash
python tests/protocol/run_native_extensions.py --component ancombc2 \
  --runtime /path/to/ancombc2-prefix --outdir /tmp/native-ancombc2 \
  --random-formula '(1 | subject)'
python tests/protocol/run_native_extensions.py --component strain \
  --runtime /path/to/instrain-prefix --outdir /tmp/native-strain
```

同一入口还支持 `evolution`、`mobmess`、`mostplas`。MobMess 使用 `--source /path/to/MobMess`；MOSTPLAS 使用 `--source /path/to/MOSTPLAS --sequence-source /path/to/MobMess`，后者提供固定上游测试序列。每次使用新的输出目录；命令、Nextflow trace、原生结果及断言结果分别保存在该目录。ANCOMBC2 的 `--groups 2` 覆盖双组分支。运行环境须允许 R 和 inStrain 在本机创建并行工作进程。

`--component amrfinderplus --runtime /path/to/amrfinderplus-prefix --source /path/to/ncbi-amr-test-data --database /path/to/versioned-amrfinder-database` 会加载实际 `short_read_protocol` profile，并串联原生 AMRFinderPlus 与生产注释整合模块，核对三类命中和 ARG 矩阵隔离。

ANCOMBC 2.8.0 的环境固定 CVXR 1.0.15 和与 Matrix ABI 匹配的 lme4 构建。该版本简化混合模型的正则会遗漏首位 `group`；包装器仅在本次 R 进程内修正这一正则，并写入 `status.json`，避免把未移除组别的同模型比较当成全局检验。双组只运行系数检验，三个及以上组才启用 global/pairwise。inStrain 固定为可安装的 1.12.0，profile/compare 共享显式 scaffold-to-bin 表，并按原生 `compared_bases_count` 字段汇总候选证据。

该兼容补丁按完整变量名移除组别，不误删 `group_batch` 一类协变量；`tests/protocol/check_ancombc2_compat.R` 使用已安装包的真实函数验证5种公式的简化结果，不执行拟合或修改包命名空间。有正计数但仅单组/无 group 列时，ANCOMBC2 明确输出不适用状态，不在构造对比矩阵时中止整个报告链。

### 本次验证范围（2026-10-30–31）

- 新增协议回归：15 项通过，含真实 pysam BAM、vegan 推断、PDF 生成，以及分层资格、完整性门控和 A/D 候选证据反例。
- 本次修复后复跑协议、共享目录/丰度、统计身份与输入契约、diversity、DESeq2 状态及 PlasMAAG 输入回归，共88项通过；记录在 `results/protocol-validation/20261031/regression.log`。
- 补齐 typed AMRFinderPlus、质量标记、置信区间和排序 PDF 后，同一套回归扩展为89项并通过，记录在 `results/protocol-validation/20261031/regression-typed-annotation.log`。
- 最终功能回归为95项并全部通过，含22项 protocol 用例；当前日志为 `results/protocol-validation/20261031/regression-completion.log`。最终连接包的650个 manifest 条目通过字节数/SHA256校验，其中516个生产源码快照与当前工作树完全一致。
- 真实 Nextflow + MMseqs2/Bowtie2/SAMtools/pysam：近重复目录合并后，三个样本的质粒 paired-fragment counts 分别为 4、4、0；保留零候选样本。
- 真实 FastSpar 1.0.0：两个各20个样本的分层，分别运行9次 bootstrap 的接口回归，核对每层64个 p-values。生产默认仍为1000次；此回归不验证宿主关联准确性。
- 真实 MobMess（固定源码提交）：上游包含关系阳性序列集生成1个 system、4个成员，并进入系统丰度汇总。
- 真实 MOSTPLAS（固定源码提交及原始 checkpoint）：4条合格测试序列完成模型预测，权重 SHA256 为 `42d43a6f2eceb30cd6d57b6ede0a3b085f059fcc152b12f6a0f3ee62d0b12205`。
- 真实 MAFFT 7.526 / IQ-TREE 2.4.0：4个成员、3个单拷贝核心家族生成骨架树；不合格系统明确跳过。
- 真实 ANCOMBC 2.8.0：24样本双组系数检验通过；36样本三组、含 batch 和受试者随机截距的模型通过，检查了实际有限的系数与全局 p 值及两两比较。小规模合成输入仍有上游特征数及部分拟合收敛警告，保留于任务日志；此测试不验证科学性能。
- 真实 inStrain 1.12.0：两份 BAM 完成 profile/compare，MAG 级 popANI=1、compared bases=19775；稳定样本 ID 映射通过核对。
- 复用合格 BAM 的最终 inStrain 链：每个样本16个“仅一个 mate 为低 MAPQ”的 pairs 均被排除，保留770 pairs；popANI=1、compared bases=19750。过滤与定量复用同一实现，未添加第二套过滤规则。
- 真实 AMRFinderPlus 4.2.7 + 官方数据库2026-08-07.1：固定 NCBI 上游测试序列提交 `9f0987075f2787ba0566a73e172c340aff63f8af`，经实际 protocol profile 和注释整合模块得到15个命中（11 AMR、3 VIRULENCE、1 STRESS）；验证其方法、原始列及 ARG 矩阵计数。上游测试序列仅用于接口验证，不视为真实质粒目录或 benchmark。
- ANCOMBC2 三组混合模型追加区间后的原生回归通过；vegan 排序 PDF 和正向毒力/应激报告回归通过。
- 真实 SeqKit 2.10.1 / fastp 1.3.6 / Bowtie2 / SAMtools 前端链：8个原始 pairs 中4个宿主 pairs 被排除，保留的两份 FASTQ 均与4个 nonhost read ID 完全一致，保留率0.5；输入为未压缩 FASTQ，修复了原模块将其误命名为 `.gz` 导致 igzip 解码失败的问题。
- 真实 MMseqs2 蛋白家族模块经实际 protocol profile：12条蛋白形成3个家族、每族4条，蛋白 ID 全部保留。
- `run_connected.py` 将候选目录、统一定量、系统/注释/MAG 汇总、两级生态统计、宿主、进化及最终交付放在同一个实际 `SHORT_READ_PROTOCOL` 子流程内运行。3个样本全部无合格候选时，27个真实任务完成，最终 HTML/PDF 保留全部样本、不生成阳性风险或事件。该测试不运行上游重建，也不验证有候选时的全资源 cohort。
- A/B/C/D 正向及反例、COG 多类别、功能汇总、基因方向/整条反向互补、实际 R 基因顺序 PDF、软件版本/数据库身份导出均有针对性回归。预设 FASTP 失败的主入口测试确认失败样本、任务、退出码与失败状态被保留；上游失败不会再被额外的“PlasMAAG cohort is empty”覆盖。
- 既有 Illumina mock 全流程：178 个任务记录通过，其中154个 CACHED、24个 COMPLETED；外部工具是明确替身，Nextflow 与仓库 R 逻辑真实执行。另复用了共享目录/丰度、统计身份/完整矩阵、PlasMAAG 输入和报告来源回归。
- 完整 profile 的 DAG 通过 Nextflow preview。上述扩展原生模块分别通过小规模接口回归，尚未完成同一真实 cohort、完整数据库资源下的端到端验收；不能据此宣称生物学或部署验收通过。本次扩展原生证据保存在 `results/protocol-validation/20261031/`。

未实现、未运行 benchmark 模块。
按用户要求，跳过需完整数据库和真实 cohort 的原生端到端验收；不以局部接口测试替代该项验收结论。

额外的最后一次 ANCOMBC2 原生拟合复验因自动审批服务额度限制未启动（不是安全判定）。此前双组/三组拟合及区间验证已通过；最新单组/缺失分组资格分支、实际包版本读取，以及已安装 ANCOMBC 函数的5种简化公式已另行核对，未把这些检查记成新的完整拟合。
