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
2. 跨样本统计和共丰度关联使用统一核酸参考重映射；完整序列及反向互补去重，
   不同序列保持分开。这是序列特征目录，不是质粒家族目录。DIVERSITY 与内部
   差异分支读取共享 **contig 表**；MMseqs2 比较目录保持独立。
3. 共享定量保留 MAPQ≥10 的主要比对，CoverM 同时生成 mean/TPM/RPKM/count。
   `raw_count` 是 read 比对数，双端两条 mate 分别计数；DESeq2 与网络拒绝缺失
   或小数计数，不再将 coverage 取整。该输入契约不替代研究设计与模型适配验证。
4. 末端反向重复（ITR）只记录结构证据，单独出现时拓扑为未知；header/DTR
   支持的环状候选仍需独立证据复核，宿主预测和共现连线也不能直接视为确证。
5. mock / 单元回归支持工程行为，不证明真实数据库下的分类性能或生物学结论。

进行可发表的跨样本推断前，仍需完善研究设计、统计模型、结构 / MAG / 宿主
证据复核、真实数据验收及报告溯源。

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

这两条可选能力仍在审计工作批次中。实际生产与框架测试的覆盖、部署限制和失败记录见 [PlasMAAG进度](docs/tool-audit/contracts/plasmaag-native-progress.md)；原生执行通过不代表完整平台、容器、AWS或独立生物学性能验收。

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
| 11 | `11_diversity/` | 默认 contig 多样性（≥3 样本）与内部 contig 差异分析；可选 plasmid 表 DESeq2（默认关） |
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

当前 CRISPR 宿主-质粒关联尚未实现。开启宿主关联并把 `crispr` 加入可选方法时，流程会提前明确失败。可选方法 `hotspot` 接入 [HOTSPOT](https://github.com/Orin-beep/HOTSPOT)，需要预先克隆其仓库并下载模型库，经 `--hotspot_home`、`--hotspot_db`、`--hotspot_models` 传入。其输出属于候选宿主预测，尚未在本项目数据上校准或验收，不能直接标为“高置信宿主”。Hybrid 的 MetaPhlAn 群落 profile 使用短读，每个样本只生成一份。

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
  header 阳性标记限于独立的 `circular=true`、`topology=circular` token，
  或序列 ID 的 `_circular` 后缀；`not_circular`、`circular=false`、
  `topology=linear` 等否定标记禁用 header 阳性推断。冲突标记会写入 warning；
  序列重复证据仍独立评估，未命中 header 阳性不等于证实线性拓扑。
  `repeat_type` 记录通过过滤的 `dtr`/`itr`/`dtr+itr`/`none`；单独 ITR
  保留 `method=itr` 和重复长度，`is_circular=false`、`topology_status=unknown`、
  `topology_evidence=none`。只有 header/DTR 支持环状候选，标为
  `topology_status=circular_candidate`；false/unknown 不代表已证实线性。
  原八列保留，追加三个证据字段；环状候选数量仍需组装图与跨接 reads 等复核。
- Platon 固定 1.7，发布原始阳性 TSV/FASTA、详细 JSON、运行记录和明确状态。
  `no_plasmids` 表示本次评估无检出，`not_assessed_length_filter` 表示所有序列
  不在该工具的长度范围；两者不能当作已证实的染色体鉴定。gzip 在任务内解压，
  数据库文件内容参与缓存，子工具或工作线程错误会阻止发布。四处上游零命中日志
  错误仅修复日志，不改变搜索、过滤或共识投票规则；见
  [Platon 原生契约](docs/tool-audit/contracts/platon-native.md)。
- 序列组成关联采用 TETRA 的双链256维 z-score Pearson 相关：
  按每条 FASTA 记录分别计数，再汇总 MAG 计数；不跨 contig 拼接。
  不能计算完整向量的低复杂度输入不产生伪造的零分或关联。
  `sequence_scores.tsv` 保留所有比较（含未过阈值和无法评分），
  `sequence_method.json` 记录方法与可评分状态；旧关联分数需要重算。
  55份来源的独立分组留出基准未通过阈值验收，因此**停用TETRA宿主链接**。
  `sequence_links.tsv`仅保留空表头，不进入统一宿主关联通道；分数不是宿主归属或概率。
  旧 `link_min_similarity` 参数不再用于此节点；直接脚本的 `--min-similarity`
  仅兼容旧调用，明确提示忽略，不能重新启用链接。分类信息保留在分数表的
  `host_taxonomy`列，不输出阈值通过标记。方法、基准失败与结果迁移见
  [TETRA 方法与校准](docs/tool-audit/contracts/tetra-sequence-method.md)。
- 长读桥接通过 Rsamtools 解析 SAM/BAM，要求同一 read 有 primary 与
  supplementary 记录，支持质粒与非质粒 contig 连接；默认 MAPQ≥20，并过滤
  secondary、QC-fail、duplicate、paired 等标记。桥接仍可能来自嵌合、重复或
  整合，不能单独证明游离质粒的宿主。
- 共丰度关联输出 Spearman/Pearson、Jaccard、p 值和对所有测试对作 BH 校正的
  q 值；脚本 `max-qvalue` 默认 1.0，流程未传显著性筛选阈值。即使额外按 q 值
  筛选，也不消除组成性、混杂或特征不可比问题，仍应按探索性解释。
- MAG 单独选择 MetaBAT2、CONCOCT 或 SemiBin 时，其 bins 直接进入最终通道。
  同时选择多个分箱器必须在 `--mag_tools` 中显式加入 `das_tool`，否则入口报错；
  选择 DAS Tool 时，汇总全部已选分箱器的可用结果并导出 FASTA。
  CheckM2、GTDB-Tk 与序列宿主关联接收同一套最终 bins；质量/分类工具及 DAS Tool
  不能在没有分箱器时单独启用。CONCOCT 已适配 plain/gzip，并修正重叠切片的 BED
  坐标步长；切片参数保持不变，空成员表不伪造 FASTA。旧默认重叠路径的覆盖度和
  bins 可能受错误坐标影响，应在新目录重算。SemiBin 合法无 bins、GTDB-Tk 文件
  扩展名等独立问题仍在审查中，完整 MAG 链尚未认证。
- 差异丰度"内部效应量法"为 Welch t 检验 + Hedges' g + BH 校正，默认按
  `--min-prevalence 0.1` 过滤低流行度 contig；它不是 MaAsLin2 或 ANCOM-BC 的
  实现，也未建模配对 / 批次。DESeq2 当前为 `~ group`。
- 共享定量使用全部样本组装序列竞争参考，完整 DNA/反向互补一致才去重；
  不折叠相近序列、片段或环状起点旋转，不能解释为家族丰度。参考中任一来源被
  共识判为质粒的序列进入质粒子表，逐来源判断保留在 `sources.tsv`。
  排除未比对、secondary、supplementary 和未知 MAPQ=255，仅保留 MAPQ≥10；
  Bowtie2 并列最佳匹配可能 MAPQ=1，不能只过滤 MAPQ=0。该阈值是明确的
  分配策略，不能保证唯一生物学来源，也会损失相近参考共享区域的计数。
  CoverM 在同一过滤 BAM 上计算 mean/TPM/RPKM/count，末端排除为0；计数为
  read 比对数，双端 mate 分开，不称为 fragment 数。hybrid 跨样本只用短读段，
  不混合长短读计数。DESeq2 / FastSpar 严格要求非负整数 `raw_count`，缺失不会
  回退 coverage。旧统计和共丰度结果需在新目录重新计算，不能与旧本地 ID 表混用。
  本地 MAG/链接用覆盖度路径及其原参数另行保留。参见 [CoverM 固定版本能力](https://github.com/wwood/CoverM/tree/v0.7.0)
  与 [DESeq2 官方输入说明](https://www.bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html)。
- 多样性当前基于 contig coverage；Bray–Curtis 默认未做 TSS，脚本虽支持
  `--beta-normalization tss`，流程模块尚未传入。全零样本对的 NaN 被转为 0
  并警告，不能将此解读为生物学上相同。
- 报告为汇总版（本轮样本的质粒数、环状候选数、已观察到输出的分析板块），HTML 由
  `assets/plasmid_report.Rmd` 模板渲染（rmarkdown+pandoc 缺失时回退为简版
  静态页）。输入来自声明的文件及分支输出记录，忽略旧样本和空发布目录；缺少当前
  样本的 FASTA/共识/结构、样本或特征不一致会失败。未观察到输出可能表示禁用或
  空输入门控，不表示已执行且无生物学命中。方法只列出有记录的 producer，并将
  版本声明与请求配置分开；完整 CLI、数据库/模型身份仍未全部记录，不能当作完整
  可复现方法。清单中的文件路径可能指向工作目录，不是原始数据的自包含归档。
  独立调用 `generate_report.R` 需提供 `--manifest` 和 `--samplesheet`；旧的
  `--outdir` 扫描接口已移除，不能用共享发布目录替代本轮输入。
- hybrid 平台的跨样本 **质粒** 和 **contig** 表均由统一参考上的短读重映射提供；
  局部 MAG 等用途的覆盖度仍可合并长短读 BAM。
- PLASMe/PlasX/COPLA 等工具输出列格式存在版本差异，解析器做了宽松启发式
  处理（按列名候选匹配）。

跨样本统计现在先核对完整样本清单、逐样本定量状态和完整特征矩阵。缺失测量、重复样本/特征或不一致的质粒子集会失败；真实零值与全局空目录保留预期样本。多样性按每个样本计算，单特征和全零输入有有限数值及状态说明。网络在流行率过滤后再次去除全零样本，只有至少4个特征且满足 `network_min_samples` 的矩阵进入 FastSpar，并发布筛选状态。分析脚本及辅助库作为任务输入参与缓存判断。DESeq2固定部署模型及TETRA真实宿主阈值仍有独立验收项，见 `docs/tool-audit/status.md`。

DESeq2 为全分组联合拟合后逐对比较，保留默认 ratio 大小因子、原计数过滤与 BH 校正。`11_diversity/deseq2_status.tsv` 记录全体输入样本、进入设计/拟合的样本、实际模型版本及未拟合原因。全零、过滤后零文库或无法计算 ratio 大小因子时不会伪造统计值、补计数或静默删除样本。独立 R 脚本仍支持显式 `--sf-type poscounts`；工作流默认不会自动切换估计方法。普通整数矩阵避免固定部署 1.42 的 table 类型兼容失败。四个统计节点分别暂存丰度和样本表，输入与结果同名也不会改写上游文件。分组标签通过标准 TSV 引号转义保留。
