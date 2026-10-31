# AutoPlasm (Nextflow)

AutoPlasm 是宏基因组质粒分析的独立 Nextflow DSL2 实现，以 `nextflow run`
为执行入口，无外部控制平面依赖。运行前需准备所选工具、环境、数据库和样本表。
默认参数以 `nextflow.config` 为准，平台路线和使用方式见下方文档。

支持五个平台：`illumina` / `ont` / `pacbio_hifi` / `hybrid` / `assembly`
（一次运行一个平台，由 `--platform` 选择）。

短读长 protocol 的使用入口见 [PROTOCOL.md](PROTOCOL.md)：`-profile short_read_protocol,conda`。该入口使用 PlasMAAG 主候选、冻结代表目录、成对定量、质粒生态/ANCOM-BC2，以及可选系统、宿主、进化和菌株分析；不包含 benchmark。

## 文档

- [使用指南](docs/usage.md)：样本、资源、运行、恢复和结果检查。
- [平台流程路线](docs/platform-workflows.md)：五个平台与短读长 protocol 的输入、分支和输出。
- [交互式流程图](docs/analysis-framework.html)：通用五平台演示，不模拟 protocol profile。
- [方法与结果边界](docs/methods-and-limits.md)：定量、结构、宿主与统计解释。
- [开发指南](docs/development.md)与[文档导航](docs/README.md)。

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
GTDB-Tk、MMseqs2、BLAST 等），本流程复用 vendor 在 `modules/nf-core/` 的
模块（上游来源版本与 git SHA 固定于 `modules.json`，存在本地接口及资源溯源补丁；
升级时须审查并保留这些契约）；发布路径与参数经 `conf/nfcore_*.config` 按域配置。无官方实现的质粒
专用工具（PLASMe、PlasX、Platon、gplas2、PlasMAAG、Recycler、COPLA、
PlasmidHostFinder、clinker、nucmer/MUMmer 链、FastSpar 及自研统计脚本）保留
自研模块；各工具的额外资源与部署边界应分别核对。

执行 profile：`-profile conda` / `mamba`（每个模块自带 conda 环境）、
`-profile docker` / `-profile singularity`（模块自带 biocontainers/Wave 镜像）。
例外（无公共包/镜像，需手动安装到 PATH）：**Dorado**（ONT POD5 basecalling）与
**OPERA-MS**（默认 hybrid 组装器；也可改用 `--hybrid_assembler hybridspades`）。

## 可选图分箱资源

选择 `gplas2` 时提供 `--gplas_source` 的固定完整源码；仅接收同次 metaSPAdes 或 hybridSPAdes 的 GFA，并对图节点重新运行所选分类器及共识。资源准备入口为 `tests/prepare_gplas_resources.py`，版本和原生证据见 [gplas契约](docs/tool-audit/contracts/gplas-native.md)。

选择 `plasmaag` 时提供 `--plasmaag_source` 的固定完整源码和 geNomad 数据库。当前限 Illumina + metaSPAdes/MEGAHIT，输入为全组装和原始配对 reads 的完整样本集合，至少8 CPU。`tests/prepare_plasmaag_resources.py` 准备85个固定上游文件及163个远程归档哈希锁；当前 Linux64 锁含 x86_64_v4 包，执行前核对目标CPU。可选 `--plasmaag_conda_prefix` 指定内部环境缓存；默认保持上游图算法和训练参数，`--plasmaag_genomad_splits` 可显式设置内存分区。

## 流程阶段

| 阶段 | 目录 | 内容 |
|---|---|---|
| 00 | `00_input_validation/` | Dorado basecalling（POD5）、samtools BAM→FASTQ |
| 01 | `01_qc/` | fastp（必选）、FastQC/MultiQC（可选）、NanoPlot+Filtlong（ONT）、HiFiAdapterFilt（HiFi）；宿主去除 bowtie2（短读）/minimap2（长读，样本表 `host_reference` 触发） |
| 02 | `02_assembly/` | MEGAHIT(默认)/metaSPAdes（illumina）、metaFlye（ont）、hifiasm-meta（hifi）、OPERA-MS(默认)/hybridSPAdes（hybrid）；`02_assembly/coverage/` 为 contig 覆盖度 |
| 03 | `03_assembly_qc/` | metaQUAST；`03_assembly_qc/polishing/` 为可选 medaka 抛光（ont） |
| 04 | `04_plasmid_detection/` | geNomad（必选）+ 可选 PLASMe/PlasX/Platon；共识整合（plasmidEC 式 ensemble 表）+ 环化/末端重叠检测（`bin/` R 脚本） |
| 05 | `05_plasmid_binning/` | 可选 PlasMAAG、gplas2、MOB-recon、Recycler |
| 06 | `06_plasmid_typing/` | 默认 PlasmidFinder + MOB-typer；可选 COPLA、CONJscan、MacSyFinder |
| 07 | `07_host_prediction/` | MetaPhlAn 群落 profile（reads 路径默认）；Kraken2（仅 illumina 可选）；PlasmidHostFinder（assembly 显式启用）；MAG 与宿主-质粒关联默认关 |
| 08 | `08_annotation/` | 默认 Bakta + AMRFinderPlus + ISEScan + IntegronFinder；可选 Prodigal、ABRICATE、RGI/CARD、eggNOG-mapper、MOB-suite |
| 09 | `09_comparative_genomics/` | 默认 MMseqs2 跨样本聚类（identity 0.95 / target coverage 0.8）；可选 BLASTn、MUMmer、clinker；catalog 未反馈至定量 |
| 10 | `10_abundance/` | 保留各样本候选的本地丰度；另建全部组装序列的共享参考并重映射，向统计及共丰度关联提供统一特征/计数；hybrid 统计只用短读段；assembly 跳过 |
| 11 | `11_diversity/` | 默认质粒多样性（≥3 样本）与内部质粒探索差异分析；可选 plasmid 表 DESeq2（默认关） |
| 12 | `12_network/` | FastSpar 相关 / 协方差矩阵（默认关，≥20 样本）；当前未接 bootstrap / p 值步骤 |
| — | `tables/` | 合并的 contig/plasmid 丰度长表 |
| — | `report/` | 本轮显式输入生成 Markdown/HTML、methods.md、report_data.json 和 report_inputs.json；不扫描发布目录 |

平台边界：当前 `hybrid` 长读路径按 ONT 处理（`map-ont`），不能无条件解释为
任意短读 + HiFi 的混合模式。`pacbio_hifi` 使用 `map-hifi`，但当前未接入 MultiQC。
`assembly` 不实例化 read QC、覆盖度、丰度、MAG、宿主关联或跨样本丰度统计；
默认 MetaPhlAn 在该路径跳过，可显式选择 PlasmidHostFinder。

## 样本表

见 `assets/samplesheet_schema.md` 与 `assets/samplesheet_example.tsv`。
列：`sample_id, group, read1, read2, long_reads, assembly, pod5, bam,
host_reference, notes`，按平台需要填写。

`sample_id` 必须全表唯一，并符合 `[A-Za-z0-9][A-Za-z0-9_.-]*`。点号、连字符和双下划线均可保留，例如 `A__B.v1`；空值、空白、斜线和其他字符会在流程启动时按样本表行号报错。此约束用于保证输出文件名和 shell 参数具有唯一、明确的样本身份。

共享定量按元数据传入每份 CoverM 表的样本 ID，并核对完整样本×特征集合，
缺测量报错，实际零值和全局空参考分别记录在 `tables/sample_states.tsv`。
来源对应见 `10_abundance/shared_reference/catalogue/sources.tsv`；共丰度关联
使用共享序列 ID，其他按样本的结构/宿主证据仍保留原 ID。独立调用
`bin/merge_abundance.R` 时也应使用与 `--tables` 顺序对应的 `--sample-ids`；
为兼容旧调用保留的文件名推断无法无歧义处理点号和后缀相似的样本名。

## 主要参数

SCAPP 检测与 binning 节点已按用户要求移除；旧的 SCAPP 工具选项、共识权重或
预测输入会明确报错。共识表保留 geNomad、PLASMe、PlasX、Platon 四个工具列。

- 工具开关：`--plasmid_detection_tools`（默认 `['genomad']`）、
  `--plasmid_binning_tools`（默认 `[]`）、`--typing_tools`
  （默认 `['plasmidfinder','mob_typer']`）、`--annotation_tools`
  （默认 `['bakta','amrfinderplus','isescan','integronfinder']`）、
  `--host_prediction_tools`（默认 `['metaphlan']`）、`--mag_tools`（默认 `[]`）、
  `--comparative_tools`（默认 `['mmseqs2']`）等。
- 工具/方法列表可用逗号串或字符串列表，两种形式都会逐项去除首尾空白；
  未知名称、空条目、null 条目、嵌套列表和 map 会在分析任务提交前被拒绝。
  空列表或空串保留禁用列表的含义；工具名称合法后仍须满足平台、数据库和依赖条件。
- 共识策略：`--consensus_method weighted_vote`（另支持 `intersection` /
  `majority_vote` / `single_tool`），`--consensus_weights
  'genomad:0.6,platon:0.15,plasme:0.15,plasx:0.1'`。
  权重键限 `genomad/platon/plasme/plasx`，不得重复，数值须有限且非负；
  `weighted_vote` 的实际参与工具权重总和须大于零。未指定的工具权重为 1，
  空权重串也沿用此默认；格式或数值错误会在写出共识结果前失败。
  PlasX 按官方 `contig/score` 表解析，严格 `score > 0.5` 才记为阳性；
  分数须为 `[0,1]` 内有限值，等于 0.5 为阴性，完整分数保留在预测表中。
  PLASMe 使用官方的阳性 FASTA 与 TAB 分隔报告，并核对 ID、长度和序列；
  缺文件或两者不一致会失败。原始报告和 FASTA 一并发布，`source_score`
  保留官方分数（BLASTn 命中可为 `nan`）；共识使用明确的阳性调用，
  预测表中的 PLASMe 分数 1 是调用指示值，不是校准后的概率。

- 组装器选择：`--short_read_assembler megahit|metaspades`、
  `--hybrid_assembler opera_ms|hybridspades`。
- 宿主去除：样本表 `host_reference` 列或全局 `--host_reference`。
  ONT、HiFi 和 hybrid 的长读段保留 SAMtools 的未配对输出
  `<id>.host_removed_other.fastq.gz`；若全部被过滤，流程明确报错，
  不再继续空输入组装。hybrid 不自动切换为仅短读段组装。
  旧宿主去除运行可能丢失未匹配宿主的长读段，需从该步骤在新目录重跑。
- 跨样本门控：`--min_diversity_samples 3`、`--min_group_replicates 3`、
  `--network_min_samples 20`。这些是运行 / 脚本门槛，不是功效保证。
  两种差异分析均读取 `min_group_replicates`，要求正整数，默认仍为 3；
  网络最小样本数要求至少为 2 的整数，显式零值会报错。
- 宿主-质粒关联默认关闭：`--host_plasmid_linking true` 开启，
  `--host_linking_methods 'co_abundance,sequence,long_read'`、
  `--host_linking_optional_methods hotspot`（或 `crispr`，尚未实现）。

不支持 CRISPR 宿主-质粒关联。开启宿主关联并把 `crispr` 加入可选方法时，流程会提前明确失败。可选方法 `hotspot` 接入 [HOTSPOT](https://github.com/Orin-beep/HOTSPOT)，需要预先克隆其仓库并下载模型库，经 `--hotspot_home`、`--hotspot_db`、`--hotspot_models` 传入。其输出属于候选宿主预测，不能直接标为“高置信宿主”。Hybrid 的 MetaPhlAn 群落 profile 使用短读，每个样本只生成一份。

FastQC 报告以样本、阶段和 read 端命名，例如 `S1.raw.R1_fastqc.zip` 与 `S1.clean.R2_fastqc.html`。FASTQ 输入本身不重写；FastQC 内部记录的输入名也带有相同身份，例如 `S1.raw.R1.fastq.gz`。MultiQC 汇总 raw/clean FastQC ZIP 与 fastp JSON，不重复暂存 HTML。

## 数据库准备

RGI 的 `--card_db` 需包含 `card.json` 及与其 `_version` 对应的
`card_database_v<version>.fasta`、`card_database_v<version>_all.fasta`。
流程会在每个任务中以 `--local` 加载并查询该库，核对加载副本的内容和版本，
不再回退到环境中的全局 CARD。旧 RGI 结果若无法证明实际查询库与配置一致，
应在新输出目录重跑该步骤。


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
| `--plasme_db / --plasme_dir` | PLASMe | 完整官方库（含已建索引和模型）/ 官方源码目录 |
| `--platon_db` | Platon | 官方数据库 |
| `--plasx_anvio_source / --plasx_source` | PlasX | 固定 anvi’o7.1 与 PlasX 官方源码目录 |
| `--plasx_cog_db / --plasx_pfam_db` | PlasX | 完整 COG2014（含 COG14/ 的基目录）及 Pfam32.0 原生索引 |
| `--plasx_profiles / --plasx_model` | PlasX | 完整官方 de novo 家族库和模型；流程逐样本自动生成三类注释，旧共享 `--plasx_annotations` 已停用 |
| `--copla_refgraph / --copla_reflist` | COPLA | COPLA 参考图与列表 |
| `--copla_dir` | COPLA | 已准备的官方源码、辅助程序及数据库目录；列表中的参考 FASTA 必须位于该目录内 |
| `--copla_macsyfinder_dir` | COPLA | 独立 Python2/MacSyFinder 1.0.5 环境目录，含 `bin/macsyfinder` |
| `--card_db` | RGI | 含 card.json 与 card_database 序列的目录 |
| `--eggnog_db` | eggNOG-mapper | `download_eggnog_data.py` |
| `--blast_db` | BLASTn | 预构建 BLAST 库目录 |
| `--reference_plasmids` | MUMmer | 参考质粒 FASTA |
| `--plasmidhostfinder_db` | PlasmidHostFinder | 官方数据库（assembly 平台） |

启用某个可选工具但未配置其数据库时，流程在启动阶段直接报错。

COPLA 按每条候选序列分别运行，再按样本汇总 PTU 表；不把样本里的多个候选
拼成一条质粒，也不据此推断多条 contig 属于同一个质粒。只有 FASTA 描述中明确的
`topology=circular` 或 `circular=true` 才使用环状模式，其他未知拓扑按线性处理；
冲突的明确标记会报错。PTU 的原始分数是图分区一致性分数，完整保留，不作为校准概率。

`--copla_dir` 应包含 `bin/copla.py`、`bin/ani.rb`、官方其他辅助程序及其
`databases/` 内 MOBscan、CONJScan、PlasmidFinder、CARD 数据；参考图和列表仍
由各自参数指定，参考目录名称不限。所选图的 accession 必须与列表中的全部
未压缩 `.fna` 参考对应。固定源码为 `santirdnd/COPLA` 的
`6b89285ef16d721d93d3c84f3645e76455ba8621`；环境见 `envs/copla.yml`，
来源与依赖锁见 `tests/copla-native.lock.json`。旧 Perl/Ruby 若缺少
`libcrypt.so.1`，可在安装目录的 `lib/` 放置匹配的兼容库；锁文件记录了已核验的
官方 Debian 包来源和校验和，不需要改动系统或共享 Conda 包。

COPLA 会保留逐候选原始结果、序列映射和运行身份；缺文件、外部程序失败或
参考缺失都会阻止发布该样本的部分汇总。既有 COPLA 样本级合并结果需要重算。

启用 PLASMe 还须设置 `--plasme_dir`，目录内含 `PLASMe.py`、
`bio_script.py`、`trans_data.py`、`trans_model.py`。已核验的源码为
`HubertTang/PLASMe` 的 `4405d5aa82065cf23a9d78de8b70ba261342ad40`；
数据库为 Zenodo `8046934` 的完整 `DB.zip`，需先建立 BLAST/DIAMOND 索引。
`tests/prepare_plasme_database.py` 可校验完整归档并建库；不把模型子集当完整库。
Conda 环境固定在 `envs/plasme.yml`。容器使用仓库内镜像，先从仓库根目录构建：

```bash
podman build --format docker --ignorefile containers/plasme/Dockerfile.dockerignore \
  -f containers/plasme/Dockerfile -t autoplasm-plasme:1.1 .
```

可用 `--plasme_container` 指向已构建的镜像或兼容运行文件。运行记录会保留
源码与依赖身份；对上述固定源码，适配器只修正空查询及外部命令失败传播，
不改模型和阈值。旧版被漏写的 PLASMe 阳性结果需要重跑检测与后续共识。

## Conda 环境

Recycler 需要同次 SPAdes 组装的 FASTG、实际最大 k 及原始短读配对；支持
`illumina + metaspades` 和 `hybrid + hybridspades`，其他组合在入口明确拒绝。
流程会单独提取正向图节点、用 BWA 比对并生成 BAM/BAI，随后核验参考与图的
一致性。没有图边时输出明确的 `skipped_no_graph_edges` 状态。每个结果目录保留
`input_contract.json` 与 `graph_provenance.json`。旧的 contig BAM 输入不满足该契约；
历史 Recycler 结果需重算。非 55 的 k 还涉及 Recycler 0.7 内部默认值修正，结果
兼容性及实际验证范围见 `docs/tool-audit/contracts/recycler.md`。

`-profile conda`（或 `mamba`）下，nf-core 模块使用各自 vendored
`environment.yml`；保留的自研模块使用 `envs/` 下的环境 yml。例外（需手动
安装到 PATH）：**Dorado**（ONT POD5 basecalling）与 **OPERA-MS**（默认
hybrid 组装器，bioconda 已下架；也可改用 `--hybrid_assembler hybridspades`）。

## 方法与结果解释

通用入口的共享参考、计数单位、结构候选、宿主关联与统计模型说明见[方法与边界](docs/methods-and-limits.md)。短读长 protocol 的冻结目录、paired-fragment 定量和交付格式见 [PROTOCOL](PROTOCOL.md)。

模型分数与环化标记属于候选证据，宿主预测和共丰度也不等于物理宿主或直接转移。通用 read counts 与 protocol paired-fragment counts 不可直接合并。
