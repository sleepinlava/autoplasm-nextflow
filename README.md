# AutoPlasm (Nextflow)

AutoPlasm 是宏基因组质粒分析的独立 Nextflow DSL2 实现，以 `nextflow run`
为执行入口，无外部控制平面依赖。运行前需准备所选工具、环境、数据库和样本表。
默认参数以 `nextflow.config` 为准，实际分支与统计对象以源码为准；
`docs/计划书.md` 保留原设计意图，其中与当前实现的差异见事实审查。

支持五个平台：`illumina` / `ont` / `pacbio_hifi` / `hybrid` / `assembly`
（一次运行一个平台，由 `--platform` 选择）。

## 交互式分析框架与事实审查

- [打开 Nextflow 流程设计网页](docs/analysis-framework.html)：以我们实际设计的
  五平台路由、00–12 阶段、并行模块、参数开关和输出结构为主线；支持流程图点击、
  阶段讲解、共识实验、示例命令和 Markdown 导出，科学审查作为辅助说明保留。
  使用原生 **HTML + CSS + TypeScript**，无框架或 CDN 运行时依赖；浏览器加载已编译的
  `docs/analysis-framework.js`。本地打开时需同时保留同目录 CSS/JS，源码链接需保留仓库结构。
- 页面开发：编辑 [HTML](docs/analysis-framework.html)、[CSS](docs/analysis-framework.css)、
  [TypeScript](docs/analysis-framework.ts) 后，在仓库根目录运行 `tsc -p docs/tsconfig.json`。
  随网页保存的 JS 可直接使用，查看页面无需安装 TypeScript。
- [Computer Use 视觉与交互验收](docs/visual-acceptance.md)：浏览器实际操作、截图、修正项与验收边界。
- [分析计划与证据契约](docs/analysis-framework-plan.md)：科学问题、实验单位、端点、
  验收条件与下一步补强路线。
- [事实可靠性审查](docs/fact-reliability-audit.md)：逐条列出源码依据、文档差异、
  科学解释边界与验证状态。审查基于 2026-10-17 工作区，而非仅基准提交。

分析路线：**定义问题与对照 → 输入 / QC / 组装 → 候选质粒与结构证据 →
分型 / 功能 / 序列比较 → 宿主候选 → 可比定量与群落统计 → 可追溯报告**。
这是科学组织顺序；实际工作流的分型、注释、binning 等分支可并行，编号不代表
所有结果依次传入下一阶段。

当前最关键的结论边界：

1. 默认只有 geNomad，不能表述为默认多工具交叉验证；共识规则分数不是校准概率。
2. MMseqs2 catalog 尚未接回定量；各样本回贴自身候选后合并，不能直接视为
   统一质粒目录上的可比矩阵。DIVERSITY 与内部差异分支实际读取 **contig 表**。
3. 本项目 CoverM 配置只请求 mean/TPM/RPKM，`raw_count` 留空；DESeq2 与网络
   的 coverage 取整回退只是代理，不能当作原始 read/fragment 计数验收。
4. 结构脚本会将通过过滤的 ITR 写成 `is_circular=true`；末端反向重复本身不足以
   证明闭环。结构标记、宿主预测和共现连线均需独立证据复核。
5. mock / 单元回归支持工程行为，不证明真实数据库下的分类性能或生物学结论。

建议先补齐 **统一 catalog 回贴与计数 → 研究设计及统计模型 → 结构 / MAG / 宿主
证据复核 → 真实数据验收及报告溯源**，再进行可发表的跨样本推断。

## 快速开始

```bash
nextflow run . \
    --platform illumina \
    --samplesheet samples.tsv \
    --outdir results/run1 \
    --genomad_db /path/to/genomad_db \
    --bakta_db /path/to/bakta_db \
    --amrfinderplus_db /path/to/amrfinder_db/latest \
    --mob_suite_db /path/to/mob_suite_db \
    --metaphlan_db /path/to/metaphlan_db \
    -profile conda
```

列表参数在命令行用逗号分隔字符串传入，例如
`--plasmid_detection_tools 'genomad,platon'`。所有参数的默认值见
`nextflow.config`。

## 实现基座（nf-core 模块）

凡 nf-core/modules 有官方实现的工具（bowtie2、minimap2、samtools、CoverM、
fastp、FastQC、MultiQC、NanoPlot、Filtlong、HiFiAdapterFilt、MEGAHIT、SPAdes、
Flye、QUAST、medaka、geNomad、Prodigal、Bakta、AMRFinderPlus、ABRicate、
IntegronFinder、RGI、eggNOG-mapper、MOB-suite、PlasmidFinder、MacSyFinder/
CONJScan、MetaPhlAn、Kraken2、MetaBAT2、CONCOCT、SemiBin2、DAS Tool、CheckM2、
GTDB-Tk、MMseqs2、BLAST 等），本流程直接使用 vendor 在 `modules/nf-core/` 的
官方模块（版本与 git SHA 固定于 `modules.json`，可用 `nf-core modules update`
升级）；发布路径与参数经 `conf/nfcore_*.config` 按域配置。无官方实现的质粒
专用工具（PLASMe、PlasX、Platon、SCAPP、gplas2、PlasMAAG、Recycler、COPLA、
PlasmidHostFinder、clinker、nucmer/MUMmer 链、FastSpar 及自研统计脚本）保留
自研模块并补齐了容器指令。

执行 profile：`-profile conda` / `mamba`（每个模块自带 conda 环境）、
`-profile docker` / `-profile singularity`（模块自带 biocontainers/Wave 镜像）。
例外（无公共包/镜像，需手动安装到 PATH）：**Dorado**（ONT POD5 basecalling）与
**OPERA-MS**（默认 hybrid 组装器；也可改用 `--hybrid_assembler hybridspades`）。

## 流程阶段

| 阶段 | 目录 | 内容 |
|---|---|---|
| 00 | `00_input_validation/` | Dorado basecalling（POD5）、samtools BAM→FASTQ |
| 01 | `01_qc/` | fastp（必选）、FastQC/MultiQC（可选）、NanoPlot+Filtlong（ONT）、HiFiAdapterFilt（HiFi）；宿主去除 bowtie2（短读）/minimap2（长读，样本表 `host_reference` 触发） |
| 02 | `02_assembly/` | MEGAHIT(默认)/metaSPAdes（illumina）、metaFlye（ont）、hifiasm-meta（hifi）、OPERA-MS(默认)/hybridSPAdes（hybrid）；`02_assembly/coverage/` 为 contig 覆盖度 |
| 03 | `03_assembly_qc/` | metaQUAST；`03_assembly_qc/polishing/` 为可选 medaka 抛光（ont） |
| 04 | `04_plasmid_detection/` | geNomad（必选）+ 可选 PLASMe/PlasX/Platon/SCAPP；共识整合（plasmidEC 式 ensemble 表）+ 环化/末端重叠检测（`bin/` R 脚本） |
| 05 | `05_plasmid_binning/` | 可选 PlasMAAG、gplas2、MOB-recon、SCAPP、Recycler |
| 06 | `06_plasmid_typing/` | 默认 PlasmidFinder + MOB-typer；可选 COPLA、CONJscan、MacSyFinder |
| 07 | `07_host_prediction/` | MetaPhlAn 群落 profile（reads 路径默认）；Kraken2（仅 illumina 可选）；PlasmidHostFinder（assembly 显式启用）；MAG 与宿主-质粒关联默认关 |
| 08 | `08_annotation/` | 默认 Bakta + AMRFinderPlus + ISEScan + IntegronFinder；可选 Prodigal、ABRICATE、RGI/CARD、eggNOG-mapper、MOB-suite |
| 09 | `09_comparative_genomics/` | 默认 MMseqs2 跨样本聚类（identity 0.95 / target coverage 0.8）；可选 BLASTn、MUMmer、clinker；catalog 未反馈至定量 |
| 10 | `10_abundance/` | reads 回贴各样本共识候选 → CoverM；hybrid 分 `short/` 与 `long/`；assembly 跳过 |
| 11 | `11_diversity/` | 默认 contig 多样性（≥3 样本）与内部 contig 差异分析；可选 plasmid 表 DESeq2（默认关） |
| 12 | `12_network/` | FastSpar 相关 / 协方差矩阵（默认关，≥20 样本）；当前未接 bootstrap / p 值步骤 |
| — | `tables/` | 合并的 contig/plasmid 丰度长表 |
| — | `report/` | 汇总 Markdown/HTML 报告 + methods.md；目前仍扫描 publish 目录，完整性需复核 |

平台边界：当前 `hybrid` 长读路径按 ONT 处理（`map-ont`），不能无条件解释为
任意短读 + HiFi 的混合模式。`pacbio_hifi` 使用 `map-hifi`，但当前未接入 MultiQC。
`assembly` 不实例化 read QC、覆盖度、丰度、MAG、宿主关联或跨样本丰度统计；
默认 MetaPhlAn 在该路径跳过，可显式选择 PlasmidHostFinder。

## 样本表

见 `assets/samplesheet_schema.md` 与 `assets/samplesheet_example.tsv`。
列：`sample_id, group, read1, read2, long_reads, assembly, pod5, bam,
host_reference, notes`，按平台需要填写。

`sample_id` 必须全表唯一，并符合 `[A-Za-z0-9][A-Za-z0-9_.-]*`。点号、连字符和双下划线均可保留，例如 `A__B.v1`；空值、空白、斜线和其他字符会在流程启动时按样本表行号报错。此约束用于保证输出文件名和 shell 参数具有唯一、明确的样本身份。

丰度合并由流程按每个 CoverM 文件的元数据显式传入样本 ID。独立调用
`bin/merge_abundance.R` 时也应使用与 `--tables` 顺序对应的 `--sample-ids`；
为兼容旧调用保留的文件名推断无法无歧义处理点号和后缀相似的样本名。

## 主要参数

- 工具开关：`--plasmid_detection_tools`（默认 `['genomad']`）、
  `--plasmid_binning_tools`（默认 `[]`）、`--typing_tools`
  （默认 `['plasmidfinder','mob_typer']`）、`--annotation_tools`
  （默认 `['bakta','amrfinderplus','isescan','integronfinder']`）、
  `--host_prediction_tools`（默认 `['metaphlan']`）、`--mag_tools`（默认 `[]`）、
  `--comparative_tools`（默认 `['mmseqs2']`）等。
- 共识策略：`--consensus_method weighted_vote`（另支持 `intersection` /
  `majority_vote` / `single_tool`），`--consensus_weights
  'genomad:0.6,platon:0.15,plasme:0.15,plasx:0.1'`。
- 组装器选择：`--short_read_assembler megahit|metaspades`、
  `--hybrid_assembler opera_ms|hybridspades`。
- 宿主去除：样本表 `host_reference` 列或全局 `--host_reference`。
- 跨样本门控：`--min_diversity_samples 3`、`--min_group_replicates 3`、
  `--network_min_samples 20`。这些是运行 / 脚本门槛，不是功效保证；DESeq2
  脚本目前另有写死的每组 ≥3 条件，不读取 `min_group_replicates`。
- 宿主-质粒关联默认关闭：`--host_plasmid_linking true` 开启，
  `--host_linking_methods 'co_abundance,sequence,long_read'`、
  `--host_linking_optional_methods hotspot`（或 `crispr`，尚未实现）。

当前 CRISPR 宿主-质粒关联尚未实现。开启宿主关联并把 `crispr` 加入可选方法时，流程会提前明确失败。可选方法 `hotspot` 接入 [HOTSPOT](https://github.com/Orin-beep/HOTSPOT)，需要预先克隆其仓库并下载模型库，经 `--hotspot_home`、`--hotspot_db`、`--hotspot_models` 传入。其输出属于候选宿主预测，尚未在本项目数据上校准或验收，不能直接标为“高置信宿主”。Hybrid 的 MetaPhlAn 群落 profile 使用短读，每个样本只生成一份。

FastQC 报告以样本、阶段和 read 端命名，例如 `S1.raw.R1_fastqc.zip` 与 `S1.clean.R2_fastqc.html`。FASTQ 输入本身不重写；FastQC 内部记录的输入名也带有相同身份，例如 `S1.raw.R1.fastq.gz`。MultiQC 汇总 raw/clean FastQC ZIP 与 fastp JSON，不重复暂存 HTML。

## 数据库准备

本流程不自动下载数据库，需要预先准备并通过参数传入路径：

| 参数 | 工具 | 获取方式（参考） |
|---|---|---|
| `--genomad_db` | geNomad（必选） | `genomad download-database <dir>` |
| `--bakta_db` | Bakta | `bakta_db download --output <dir>` |
| `--amrfinderplus_db` | AMRFinderPlus | `amrfinder -u`（指向 `<dir>/latest`） |
| `--mob_suite_db` | MOB-typer | `mob_init -d <dir>`（MOB-recon 与 PlasmidFinder 使用工具自带库，无需配置） |
| `--metaphlan_db` | MetaPhlAn4 | `metaphlan --install --db_dir <dir>` |
| `--kraken2_db` | Kraken2 | 标准/自定义 Kraken2 库 |
| `--gtdbtk_db` | GTDB-Tk | GTDB release 参考数据 |
| `--checkm2_db` | CheckM2 | `checkm2 database --download --path <dir>`（启用 checkm2 时必填） |
| `--plasme_db / --platon_db` | PLASMe / Platon | 各自官方数据库 |
| `--plasx_annotations / --plasx_model` | PlasX | PlasX 官方注释与模型文件 |
| `--copla_refgraph / --copla_reflist` | COPLA | COPLA 参考图与列表 |
| `--card_db` | RGI | 含 card.json 与 card_database 序列的目录 |
| `--eggnog_db` | eggNOG-mapper | `download_eggnog_data.py` |
| `--blast_db` | BLASTn | 预构建 BLAST 库目录 |
| `--reference_plasmids` | MUMmer | 参考质粒 FASTA |
| `--plasmidhostfinder_db` | PlasmidHostFinder | 官方数据库（assembly 平台） |

启用某个可选工具但未配置其数据库时，流程在启动阶段直接报错。

## Conda 环境

`-profile conda`（或 `mamba`）下，nf-core 模块使用各自 vendored
`environment.yml`；保留的自研模块使用 `envs/` 下的环境 yml。例外（需手动
安装到 PATH）：**Dorado**（ONT POD5 basecalling）与 **OPERA-MS**（默认
hybrid 组装器，bioconda 已下架；也可改用 `--hybrid_assembler hybridspades`）。

## 验证状态

以下分日期记录为既有历史记录，不代表本次框架审查重跑了全部测试。
本次检查及未执行项见 [审查记录](docs/fact-reliability-audit.md#本次验证)。
工作区仍有未提交的实现修改，历史通过数不能替代对当前状态的验收。

2026-10-17 nf-core 化改造（`refactor/nf-core-modules` 分支）：约 50 个 process
替换为 `modules/nf-core/` vendored 官方模块。验证（Nextflow 26.10.0 + Java 21）：

- mock 端到端 **9 个场景全部通过**：illumina(146 任务) / ont(128) /
  pacbio_hifi(121) / hybrid+opera_ms(177) / hybrid+hybridspades(177) /
  illumina 无质粒(90) / ont+pod5(134) / ont+bam(134) / pacbio_hifi+mixed(124)。
  外部生信命令为显式 mock，不代表真实工具/数据库验收。
- `pytest tests/ -q`：**42 项通过**（含共识 ensemble schema 与 gz MAG 新用例）。
- `python tests/run_module_regressions.py --suite all`：catalog / sequence /
  sample-ids / coabundance / host-routing / sequence-optional / crispr-guard
  全部通过；qc（缺真实 fastqc/multiqc）与 longread-source（缺真实 samtools）
  按设计报“未运行”，与基线一致。
- `nextflow lint main.nf subworkflows modules conf tests/nextflow`：0 error。
- 共识输出新增 plasmidEC 式 ensemble 列（各工具判定、`plasmid_count`、
  `combined_prediction`），`plasmid_call` 等既有列不变。

历史验证记录：

2026-10-16 新增主入口 mock 端到端测试：Illumina 正常场景 140 个任务通过，
无质粒场景 **84 个任务通过**。使用真实 Nextflow 26.10.0 和仓库 Python 脚本，
外部生信命令使用显式 mock；不代表真实工具/数据库验收。复现方法见
[`tests/mock_e2e/README.md`](tests/mock_e2e/README.md)，失败基线与修复记录见
[`docs/mock-e2e-validation.md`](docs/mock-e2e-validation.md)。

同日追加 ONT、PacBio HiFi、hybrid：默认阳性分别通过 **134 / 127 / 183** 个任务；
包含无质粒、BAM/POD5/FASTQ 输入路由、hybridSPAdes 在内的 **10 个新增场景、
1,340 个任务全部通过**。同样为外部工具 mock 验证；完整矩阵和未覆盖范围见上述记录。

以下为先前修复轮次的历史记录：

- 本轮 Python 回归使用标准库 `unittest`，运行命令为
  `python3 -m unittest discover -s tests -p 'test_*.py' -v`。
- 本次工作区该命令运行 **38 项通过**。当前执行环境没有 Nextflow、FastQC、
  MultiQC 或 samtools；因此 `python3 tests/run_module_regressions.py --suite all`
  按设计以非零状态报告各集成套件“未运行”，没有将其计为通过。
- 本次检查环境为 Python 3.15.0、Java 27，`NXF_SYNTAX_PARSER` 未设置；
  由于没有 Nextflow，无法确认 Nextflow 26 严格语法下的解析与执行结果。
- Nextflow 模块回归命令为 `python3 tests/run_module_regressions.py --suite all`；
  它要求 Nextflow 26，并对 catalog、sequence、sample ID、co-abundance、
  host routing、可选 MAG、long-read 来源、CRISPR 拒绝保护和真实 FastQC/MultiQC
  分别运行模块测试。
  缺少依赖时会以非零状态报告“未运行”，不会把缺失工具计为通过。
- 先前提交 `ecb200e` 曾在 Nextflow 25.04.6（Java 21）运行 `-preview` 和配置
  解析；这些是本轮改动前的历史检查，不能替代当前 Nextflow 26 模块验证。
- 本轮没有真实数据库端到端运行。DAS Tool 的输入/输出接口、其他脚本读取
  publish 目录时的旧结果风险，以及按 contig 名直接做跨样本关联的生物学
  可比性，仍需独立处理。

## 实现说明与已知简化

- 共识整合（`plasmid_consensus`）完整实现了四种策略
  （intersection/majority_vote/weighted_vote/single_tool），权重阈值取
  "支持权重占参与工具总权重 ≥ 0.5"。默认只启用 geNomad；严格多数要求
  支持数大于半数，single_tool 取 geNomad 判定。实际参与共识取决于收到的工具
  结果；启用工具的缺失 contig 记录按未支持处理，不是独立的染色体鉴定。
- `plasmid_structure` 使用 header 标记，以及 **21 bp** 种子的精确 DTR / ITR
  与低复杂度过滤；ITR 延伸上限 1000 bp，DTR 并非统一限制在 1000 bp 内。
  当前通过过滤的 ITR 也产生 `is_circular=true`，存在解释风险；该字段只能作
  候选结构标记，不能视为已证实完整环状质粒。需要组装图与跨接 reads 等复核。
- 序列组成宿主关联当前使用 **TETRA 风格的四核苷酸 z-score 向量 Pearson
  相关**，并非旧版文档的“余弦相似度 + GC 惩罚”，也不建模密码子使用。
  它是组成启发式，不是宿主后验概率或分类学鉴定。
- 长读桥接通过 Rsamtools 解析 SAM/BAM，要求同一 read 有 primary 与
  supplementary 记录，支持质粒与非质粒 contig 连接；默认 MAPQ≥20，并过滤
  secondary、QC-fail、duplicate、paired 等标记。桥接仍可能来自嵌合、重复或
  整合，不能单独证明游离质粒的宿主。
- 共丰度关联输出 Spearman/Pearson、Jaccard、p 值和对所有测试对作 BH 校正的
  q 值；脚本 `max-qvalue` 默认 1.0，流程未传显著性筛选阈值。即使额外按 q 值
  筛选，也不消除组成性、混杂或特征不可比问题，仍应按探索性解释。
- MAG 最终通道当前默认接 MetaBAT2，启用 DAS Tool 时以其输出替换；CONCOCT
  单开未进入最终通道，SemiBin 输出也未接入最终通道或 DAS Tool 输入。
  CheckM2 和 GTDB-Tk 都读取最终通道，不能把“启用任一 binner”理解为完整 MAG 链。
- 差异丰度"内部效应量法"为 Welch t 检验 + Hedges' g + BH 校正，默认按
  `--min-prevalence 0.1` 过滤低流行度 contig；它不是 MaAsLin2 或 ANCOM-BC 的
  实现，也未建模配对 / 批次。DESeq2 当前为 `~ group`。
- CoverM 支持 `count`，但本项目 `conf/nfcore_upstream.config` 只请求
  `mean tpm rpkm`，合并表的 `raw_count` 为空；DESeq2 / FastSpar 回退到
  coverage 取整代理。要作计数推断，需先提供可追溯的计数及 read/fragment 分配
  规则，并验证模型适配性。参见 [CoverM 官方能力](https://github.com/wwood/CoverM)
  与 [DESeq2 官方输入说明](https://www.bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html)。
- 多样性当前基于 contig coverage；Bray–Curtis 默认未做 TSS，脚本虽支持
  `--beta-normalization tss`，流程模块尚未传入。全零样本对的 NaN 被转为 0
  并警告，不能将此解读为生物学上相同。
- 报告为汇总版（样本质粒数、环化数、启用的分析板块），HTML 由
  `assets/plasmid_report.Rmd` 模板渲染（rmarkdown+pandoc 缺失时回退为简版
  静态页）。
- hybrid 平台的跨样本 **质粒** 表使用短读丰度链；**contig** 覆盖度合并长短读
  BAM，因此默认多样性 / 内部差异并非仅基于短读。
- PLASMe/PlasX/COPLA 等工具输出列格式存在版本差异，解析器做了宽松启发式
  处理（按列名候选匹配）。
