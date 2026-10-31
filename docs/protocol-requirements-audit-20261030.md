# 短读长质粒组产品要求与代码覆盖核查

> 历史快照：正文保留原日期的设计、发现与验证结论，不代表2026-10-31的全部当前状态。最新入口见[文档导航](README.md)、[平台路线](platform-workflows.md)及[实施状态](protocol-implementation-status-20261031.md)。

核查日期：2026-10-30。依据：仓库根目录 `short_read_plasmidome_protocol_v1_1(1).docx` 的 Step 1–20、Benchmark 与附录。文件名为 v1_1，正文标题仍写 Protocol v1.0；本报告以实际正文要求为准。

结论：现有代码具备质控、识别、注释、回贴定量和基础 R 统计能力，但尚未实现该文档定义的完整产品流程。主要问题既包括工具缺失，也包括已经实现的模块未按要求连接。不能以工具文件存在或已有模块测试通过，认定产品要求已覆盖。

本次检查当前工作树（包含已有未提交改动），没有修改生产代码。检查以本地产品文档、生产代码调用关系和少量既有回归测试为依据；没有重新核查文献、下载数据库或运行真实数据全流程。历史工具审计结论不等于本 protocol 的需求验收。

## 关键阻断项

1. **PlasMAAG 没有成为主数据源。** 默认 `plasmid_binning_tools=[]`，短读长默认 MEGAHIT。`subworkflows/illumina.nf:96` 调用 PlasMAAG 后只消费 report events；其 `bins` 未进入候选合并、注释、定量。实际 `ch_plasmids` 来自识别共识（同文件第 116 行）。
2. **目录与下游顺序不符。** 当前先对各样本共识 contigs 做注释，随后 MMseqs2 在比较分支聚类；其代表序列不回流定量和注释。共享定量另建完整序列完全一致（含反向互补）的目录，并非 Step 7 的近重复去冗余质粒目录。
3. **R 统计分析对象不符。** `subworkflows/cross_sample.nf:53,58` 分别把 `ch_contig_merged` 送给 DIVERSITY 和默认差异分析；该表来自全部组装 contigs 的共享参考，而非仅质粒子集。可选 DESeq2 和质粒网络使用 `ch_plasmid_merged`。
4. **ANCOM-BC2 未实现。** 默认差异分析是 base R Welch t 检验、BH 校正和 Hedges' g。可选 DESeq2 仅 `~group`。两者均不能算作文档指定 ANCOM-BC2 的实现。脚本注释出现 ANCOM-BC2 只是引用检出率过滤惯例。
5. **缺少系统组织、指定宿主模型、骨架树和菌株分析。** 未发现 MobMess、MOSTPLAS、MAFFT、IQ-TREE 2、inStrain 的生产模块、环境依赖及调用；也未发现 ANCOMBC 包及 `ancombc2()` 调用。
6. **FastSpar 用途不符。** 现有 FastSpar 是可选质粒—质粒网络。宿主关联实际是质粒丰度与 MetaPhlAn profile 的 Spearman/Pearson，而不是文档要求的质粒—MAG FastSpar 关联及混杂控制。

## Step 1–20 覆盖矩阵

“已有基础”表示主要工具和入口存在，仍须核对全量字段及产品验收；“部分覆盖”表示存在实质性方法、输入、接线或输出缺口；“缺失”表示未发现相应生产实现。此处不提供容易误导的整体完成百分比。

| 文档步骤               | 要求                                                                       | 当前代码与默认行为                                                                                                                                                                                                                                                                            | 判定                     |
| ---------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| 1 输入与可复现性       | 稳定样本 ID、配对检查、SeqKit 统计、原始校验和、完整元数据与 manifest      | `main.nf`、`subworkflows/sample_id_validation.nf` 有样本解析/验证；已有资源身份、命令来源记录与 Nextflow 报告。未发现 SeqKit 节点及文档要求的统一原始统计/校验和交付链。主入口仍把旧 `docs/计划书.md` 称作权威设计                                                                            | 部分覆盖                 |
| 2 质控                 | fastp、MultiQC、读数保留统计                                               | `subworkflows/illumina.nf` 接入 fastp、可选 FastQC、默认 MultiQC；需继续验收规定格式的跨样本 retention 表                                                                                                                                                                                     | 已有基础                 |
| 3 可选去宿主           | Bowtie2、SAMtools、成对未比对 reads、去宿主统计                            | Illumina 按参考分支，可跳过；Bowtie2 的未比对 paired FASTQ 进入后续链。不是文档描述的独立 SAMtools 过滤链，仍需核对配对过滤语义、比例汇总与参考版本交付                                                                                                                                       | 部分覆盖                 |
| 4 多样本重建           | PlasMAAG 主流程、metaSPAdes 图、质粒/细胞 bins                             | `subworkflows/plasmaag_binning.nf` 有真实 cohort 收集与运行入口；`bin/plasmaag_inputs.py` 验证并保存 native plasmid/genome/virus 结果。但默认关闭，导出 plasmid bins 未被主分析消费，cellular bins 也未接入 MAG 主链                                                                          | 部分覆盖，主干阻断       |
| 5 补充识别             | geNomad 分类、保留未进 bin 的候选、不重复算独立证据                        | `subworkflows/plasmid_detection.nf` 默认运行 geNomad；目前识别共识直接成为主候选，未实现相对 PlasMAAG bin 的补充候选筛选/去重                                                                                                                                                                 | 部分覆盖                 |
| 6 候选整合与分级       | bins + 未入 bin contigs、来源/证据表、身份与结构等级分开                   | `bin/plasmid_consensus.R`、`bin/plasmid_structure.R` 有共识及结构信息，但没有文档要求的 bin/补充候选统一实体与三层分级、完整 provenance/evidence 契约                                                                                                                                         | 部分覆盖                 |
| 7 保守去冗余           | 完全相同合并、近重复保守聚类、双向覆盖、片段目录与映射                     | 共享参考有完全一致合并和来源映射；比较分支 MMseqs2 默认 95% identity、80% coverage、`--cov-mode 1`，与文档初始 99%/90% 双向覆盖策略不同，片段独立目录和统一代表序列下游契约未形成。文档阈值本身也要求校准                                                                                     | 部分覆盖                 |
| 8 质粒系统             | MobMess、包含关系、system ID、fragment-linked                              | 未发现 MobMess 生产模块；MMseqs2 近似聚类和 COPLA 分型不能直接计作 MobMess systems                                                                                                                                                                                                            | 缺失                     |
| 9 结构注释             | Bakta 对非冗余代表序列输出标准注释                                         | `subworkflows/plasmid_downstream.nf` 默认运行 Bakta；输入仍为每样本共识 contigs，位于统一非冗余目录之前                                                                                                                                                                                       | 部分覆盖                 |
| 10 功能与基因家族      | Bakta 蛋白 → eggNOG、gene-family、presence/absence、system 汇总与富集      | eggNOG-mapper 为可选且默认关闭；实际蛋白由独立 Prodigal/PROTEIN_INPUTS 链提供，未复用 Bakta 蛋白坐标契约。未发现系统级基因矩阵、功能汇总/富集完整实现                                                                                                                                         | 部分覆盖                 |
| 11 ARG                 | AMRFinderPlus、质粒/系统/样本 ARG 矩阵                                     | 默认接入 AMRFinderPlus；有原始工具输出，未发现文档规定的统一 ARG-by-plasmid/sample/system 汇总链                                                                                                                                                                                              | 部分覆盖                 |
| 12 移动元件与 ARG 背景 | IntegronFinder、ISEScan、统一坐标、距离、重复模块、边界截断                | 两工具默认接入；未发现消费 ARG + IS + integron 坐标的 `ARG_context` 和 `mobile_module_candidates` 生成链                                                                                                                                                                                      | 部分覆盖                 |
| 13 分型与移动性        | mob_typer、机制证据等级、不完整性标记                                      | MOB_TYPER 默认运行；已有原始类型输出，未发现文档规定四类证据与 Step 12 联合汇总完整实现                                                                                                                                                                                                       | 部分覆盖                 |
| 14 统一回贴定量        | 所有样本对同版质粒目录，深度/广度/paired counts/检出率/多重比对            | `subworkflows/shared_quantification.nf` 有同一共享参考、Bowtie2/SAMtools/CoverM、真实 read-alignment counts、RPKM/TPM/mean。共享参考含全部 assembly contigs，再提取质粒子集；没有使用 MMseqs2 代表目录。当前共享表缺少 breadth/median/prevalence，paired mates 分开计数而非合格成对 fragments | 部分覆盖                 |
| 15 MAG 质控分类        | PlasMAAG cellular bins → CheckM2/GTDB-Tk、质量分级和 MAG 丰度              | `subworkflows/mag_host.nf` 有多种独立 binner 和可选 CheckM2/GTDB-Tk，默认 `mag_tools=[]`。输入为 assembly/BAM，未接 PlasMAAG cellular bins；未形成指定 MAG 丰度及按质控门槛进入后续分析的完整链                                                                                               | 部分覆盖                 |
| 16 分级宿主推断        | PLSDB 同源 + 近完整 MOSTPLAS + 质粒—MAG FastSpar、未知与证据等级           | 有通用 BLAST 可选分支，但未形成 PLSDB 专用宿主标签/双向覆盖整合；MOSTPLAS 缺失。HOST_LINKING 默认关闭，共丰度消费 MetaPhlAn profile 并做普通相关，不消费 MAG 丰度执行 FastSpar                                                                                                                | 部分覆盖，核心方法缺失   |
| 17 生态与差异分析      | vegan α/β、排序、PERMANOVA/离散度、ANCOM-BC2、协变量/重复测量、system 分析 | vegan α/Bray 已实现；PERMANOVA、betadisper、排序产物未实现；默认输入为全 contig。ANCOM-BC2 缺失，无 system 级生态分析链                                                                                                                                                                       | 部分覆盖，方法及输入偏离 |
| 18 系统比较与进化      | MMseqs2 蛋白家族、核心/附属矩阵、MAFFT、IQ-TREE 2、结构变体                | 现有 MMseqs2 用于核酸候选聚类；可选 MUMmer/clinker 提供部分比对/共线性。缺少系统内蛋白家族、骨架筛选、MAFFT/IQ-TREE 2 和树输出                                                                                                                                                                | 部分覆盖，骨架进化链缺失 |
| 19 菌株与扩散候选      | inStrain profile/compare、A–D 模式、证据/反证/替代解释矩阵                 | 未发现 inStrain 入口，也未发现整合菌株、系统、ARG 模块、宿主及时空信息的候选事件分类器                                                                                                                                                                                                        | 缺失                     |
| 20 最终报告与风险画像  | 多维 risk_profile、统一最终目录和关联表、候选事件、HTML/PDF、manifest      | `bin/generate_report.R` 和 `modules/cross_sample/report.nf` 有 HTML/Markdown/JSON、methods 和命令来源记录；未发现完整多维风险画像、统一系统/事件交付包及 PDF 生成链                                                                                                                           | 部分覆盖                 |

## R 包和分析模块的实际使用

| 模块                                                        | 实际执行                                                                                                            | 是否满足文档                                                                |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `DIVERSITY` → `bin/diversity.R`                             | 真正加载 vegan、data.table；调用 vegan diversity/vegdist，计算 richness、Shannon、Gini-Simpson、Pielou、Bray–Curtis | 仅基础指标满足；对象错误，缺排序/PERMANOVA/离散度/重复测量设计与 systems    |
| `DIFFERENTIAL_ABUNDANCE` → `bin/differential_abundance.R`   | 默认开启；data.table + stats::t.test + p.adjust(BH)，效应量 Hedges' g，按 group 两两比较 coverage                   | 未使用 ANCOM-BC2；不支持所要求的协变量和重复测量                            |
| `DESEQ2` → `bin/deseq2_plasmid.R`                           | 默认关闭；真正加载 DESeq2，读取整数 raw_count，设计 `~group`                                                        | 是有效的独立可选方法，但不是指定 ANCOM-BC2，也未提供完整协变量/重复测量设计 |
| `NETWORK_PREPARE` → `bin/network_prepare.R` → FastSpar      | R 整理质粒矩阵，外部 FastSpar 输出 correlation/covariance                                                           | 是质粒共现网络；不能算作 Step 16 质粒—MAG 宿主关联                          |
| `LINK_COABUNDANCE` → `bin/coabundance_link.R`               | 质粒丰度与 MetaPhlAn 宿主 profile，stats::cor 或相应矩阵计算，Spearman/Pearson                                      | 不符合指定 FastSpar + MAG 丰度方法；没有协变量控制链                        |
| `PLASMID_CATALOG_PREPARE` → `bin/plasmid_catalog_prepare.R` | R 整理候选 FASTA/样本信息，之后交给外部 MMseqs2                                                                     | 存在 R 整理模块，但不是系统组织或生态分析包                                 |
| `REPORTING` → `bin/generate_report.R`                       | R 汇总，rmarkdown 可用时渲染 HTML，否则生成简化 HTML                                                                | 报告框架存在；不代表缺失的风险和事件分析已经完成                            |

依赖声明：`envs/r_analysis.yml` 包含 r-vegan、data.table、jsonlite、digest、rmarkdown、Biostrings、Rsamtools；`envs/deseq2.yml` 包含 DESeq2。未声明 ANCOMBC。R 公共镜像仍是 `autoplasm-r-analysis:latest`，R base/DESeq2 的 Conda 声明含范围版本；需要进一步冻结环境及记录真实包版本，而不能只记录 Rscript 版本。依赖声明存在也不等于每个包在某项分析中实际调用。

基础指标额外边界：默认 Bray–Curtis 不做 TSS；脚本支持 `--beta-normalization tss`，但 Nextflow DIVERSITY 节点未传该参数。两个全零样本的未定义 Bray 值按兼容约定写为 0，status 中有说明；正式生态推断需预先定义空样本处理规则。

## 建议实施顺序

1. P0：建立专用短读长 protocol 配置和统一实体契约；PlasMAAG plasmid/cellular bins 真正进入主链，geNomad 只补未入 bin 候选，保留候选来源、质量和片段状态。
2. P0：建立全流程一致的候选/代表序列/成员 ID；完成保守去冗余，所有样本对冻结目录定量，注释复用代表序列和统一基因坐标。可保留竞争背景以降低误比对，但必须区分统计对象。
3. P0：生态模块改接质粒矩阵；接入 ANCOMBC::ancombc2、显式设计公式及协变量/个体字段，补 PERMANOVA、betadisper、排序和输入资格检查。当前 Welch 方法可保留为另行命名的探索分析。
4. P1：接入 MobMess，建立 system IDs、片段关联和系统级矩阵；完善 eggNOG 与 ARG/MGE 的坐标整合、功能及移动模块产物。
5. P1：补 PLSDB 参考宿主整合、近完整输入门控下的 MOSTPLAS、MAG 质控/丰度、质粒—MAG FastSpar 和分级证据输出。
6. P2：补系统内蛋白家族、MAFFT/IQ-TREE 2、inStrain 与候选扩散分类；生成多维风险画像、规定结果包和完整版本 manifest。
7. 发布前：固定 demo/cohort 与独立 benchmark 数据、数据库版本和校验和；按产品矩阵完成真实端到端验收及科学性能验证。

这些是后续实施建议，本次仅做核查，不自动改变现有方法、默认值或此前明确决定。

## 本次验证记录

已读取 DOCX 的完整正文和表格文本；文档包中无 comments/footnotes/endnotes 部件。图示并非本报告方法结论的唯一依据，未对文档排版做审稿。

对 `main.nf`、配置、Illumina/PlasMAAG/识别/注释/共享定量/MAG/宿主/比较/跨样本子流程、R 脚本和环境声明进行了静态检查。对缺失工具同时检查生产目录、调用和环境，未把代码注释中的名称算作实现。

复用了现有单元测试：

- `python -m unittest discover -s tests -p 'test_shared_catalogue.py' -v`：8 项通过。
- `python -m unittest discover -s tests -p 'test_shared_abundance.py' -v`：7 项通过。
- `python -m unittest discover -s tests -p 'test_diversity_semantics.py' -v`：7 项通过。
- `python -m unittest discover -s tests -p 'test_deseq2_status.py' -v`：18 项通过。

合计 40 项通过。本机实际包检查：vegan 2.7.6、data.table 1.18.6.1、DESeq2 1.52.0、Biostrings 2.80.2、Rsamtools 2.28.0、rmarkdown 2.32；ANCOMBC 未安装。本机包检查不证明生产容器环境已冻结。

测试只验证现有目录/定量/R 指标契约，不验证未实现的 ANCOM-BC2、MobMess 或新 protocol 全流程，也不构成科学性能 benchmark。
