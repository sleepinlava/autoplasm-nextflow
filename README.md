# AutoPlasm (Nextflow)

AutoPlasm 宏基因组质粒分析流程的独立 Nextflow DSL2 实现 —— 不依赖 ABI Python
运行时，可直接 `nextflow run` 执行。权威设计来源是 ABI 插件的
`pipeline_dag.yaml`（`src/abi/plugins/metagenomic_plasmid/`，ABI 仓库），
本仓库的阶段划分、平台分支、默认开关与该规范一一对应。

支持五个平台：`illumina` / `ont` / `pacbio_hifi` / `hybrid` / `assembly`
（一次运行一个平台，由 `--platform` 选择）。

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
`nextflow.config`，与 ABI `config_default.yaml` 保持一致。

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
| 07 | `07_host_prediction/` | MetaPhlAn4（默认）/Kraken2/PlasmidHostFinder(assembly)；`07_host_prediction/mag/` 为可选 MAG 链；宿主-质粒关联（默认关） |
| 08 | `08_annotation/` | 默认 Bakta + AMRFinderPlus + ISEScan + IntegronFinder；可选 Prodigal、ABRICATE、RGI/CARD、eggNOG-mapper、MOB-suite |
| 09 | `09_comparative_genomics/` | 默认 MMseqs2 跨样本聚类；可选 BLASTn、MUMmer、clinker |
| 10 | `10_abundance/` | bowtie2/minimap2 → samtools → CoverM；hybrid 有 `short/` 与 `long/` 两套 |
| 11 | `11_diversity/` | 多样性（≥3 样本）、内部效应量法差异丰度、可选 DESeq2 |
| 12 | `12_network/` | FastSpar 共现网络（≥20 样本） |
| — | `tables/` | 合并的 contig/plasmid 丰度长表 |
| — | `report/` | 汇总 Markdown/HTML 报告 + methods.md |

## 样本表

见 `assets/samplesheet_schema.md` 与 `assets/samplesheet_example.tsv`。
列：`sample_id, group, read1, read2, long_reads, assembly, pod5, bam,
host_reference, notes`，按平台需要填写。

`sample_id` 必须全表唯一，并符合 `[A-Za-z0-9][A-Za-z0-9_.-]*`。点号、连字符和双下划线均可保留，例如 `A__B.v1`；空值、空白、斜线和其他字符会在流程启动时按样本表行号报错。此约束用于保证输出文件名和 shell 参数具有唯一、明确的样本身份。

丰度合并由流程按每个 CoverM 文件的元数据显式传入样本 ID。独立调用
`bin/merge_abundance.R` 时也应使用与 `--tables` 顺序对应的 `--sample-ids`；
为兼容旧调用保留的文件名推断无法无歧义处理点号和后缀相似的样本名。

## 主要参数（默认值镜像 config_default.yaml）

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
  `--network_min_samples 20`。
- 宿主-质粒关联默认关闭：`--host_plasmid_linking true` 开启，
  `--host_linking_methods 'co_abundance,sequence,long_read'`、
  `--host_linking_optional_methods hotspot`（或 `crispr`，尚未实现）。

当前 CRISPR 宿主-质粒关联尚未实现。开启宿主关联并把 `crispr` 加入可选方法时，流程会提前明确失败；关闭该方法不影响其他关联类型。可选方法 `hotspot` 接入 [HOTSPOT](https://github.com/Orin-beep/HOTSPOT)（Transformer 宿主预测，蛋白/复制子特征，高置信），需要预先克隆其仓库并下载模型库，经 `--hotspot_home`、`--hotspot_db`、`--hotspot_models` 传入。Hybrid 的 MetaPhlAn 宿主 profile 使用短读长，每个样本只生成一份 profile。

FastQC 报告以样本、阶段和 read 端命名，例如 `S1.raw.R1_fastqc.zip` 与 `S1.clean.R2_fastqc.html`。FASTQ 输入本身不重写；FastQC 内部记录的输入名也带有相同身份，例如 `S1.raw.R1.fastq.gz`。MultiQC 汇总 raw/clean FastQC ZIP 与 fastp JSON，不重复暂存 HTML。

## 数据库准备

ABI 不自动下载数据库，本流程同样要求预先准备并通过参数传入路径：

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

## 与 ABI 实现的差异（已知简化）

- ABI 的 `plasmid_consensus` handler 实际只拷贝 geNomad/SCAPP 结果；本实现
  按 DAG 文档化了四种共识策略（intersection/majority_vote/weighted_vote/
  single_tool）的完整实现，权重阈值取"支持权重占启用工具总权重 ≥ 0.5"。
- `plasmid_structure` 与 ABI 算法一致（header 环化标记 + 20–1000 bp 精确
  末端重叠）。
- 序列相似性宿主关联简化为四核苷酸组成余弦相似度 + GC 惩罚（ABI 还建模
  密码子使用）；长读桥接基于 Rsamtools 的 SAM/BAM 解析（同一条读段同时
  比对到质粒与非质粒 contig，默认 MAPQ≥20 过滤）。
- 差异丰度"内部效应量法"为 Welch t 检验 + Hedges' g + BH 校正，默认按
  Maaslin2/ANCOM-BC 惯例过滤低流行度 contig（--min-prevalence 0.1）；
  CoverM 无原始计数，DESeq2/FastSpar 以取整 coverage 作为计数代理（与 ABI
  DESeq2 脚本相同的约定）。
- 报告为汇总版（样本质粒数、环化数、启用的分析板块），HTML 由
  `assets/plasmid_report.Rmd` 模板渲染（rmarkdown+pandoc 缺失时回退为简版
  静态页），不是 ABI 的完整图文报告。
- hybrid 平台的跨样本统计使用短读丰度链；contig 覆盖度合并长短读 BAM。
- PLASMe/PlasX/COPLA 等工具输出列格式存在版本差异，解析器做了宽松启发式
  处理（按列名候选匹配）。
