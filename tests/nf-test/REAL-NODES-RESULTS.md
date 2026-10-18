# 全节点真实小数据测试：2026-10-17

目标：对流水线所有节点用开源真实小数据做真实执行测试，复用 vendored nf-core
测试与 nf-core/test-datasets/ENA/官方数据库，不造合成数据、不用 stub 冒充。
执行后端：podman 容器为主（SELinux shim 见 env.sh），R/native 节点用系统 R 4.6.1
或本地编译/官方二进制。资源上限 2 cpu / 7 GB（`tests/nf-test/nextflow.config`）。
W1（vendored 套件）结果单独见 `results/nf-test/w1-vendored-results.md`。

## 数据（全部固定版本 + 校验值）

| 数据 | 来源 | 锁定 |
| --- | --- | --- |
| pUTI89 质粒、minigut、sarscov2、gallus pacbio、HG002 pod5、streptomyces gbk | nf-core/test-datasets（两个固定 revision） | `real-nodes-datasets.lock.json`（size + git blob sha1） |
| ENA PRJNA848809 d6 期 3 感染 vs 3 对照 | ENA 官方 API 核实 | `ena-multisample.lock.json`（官方 md5 + size） |
| platon db 1.5.0、mobsuite v3.1.8、bakta light v6.0、checkm2 v1.1.0、macsyfinder CONJScan 2.1.0/TXSScan 1.1.4、plasmidfinder db 3.0.3、PHF 仓库 bb9316d1、dorado 2.1.2 + fast 模型 ×2 | Zenodo/Bitbucket/GitHub/ONT CDN 固定版本 | `results/nf-test/databases/manifest.txt`（size + sha256） |

适配器：`prepare_data.py`（github blob 校验 + 通用 url/sha256/md5 + tar 解包），
离线单元测试 8/8（曾真实拦截一个错误的 blob sha1）。

## P3 自建节点套件结果（真实执行，断言为上游固定事实）

| 节点 | 数据 | 结果 | 证据 |
| --- | --- | --- | --- |
| PLASMID_CATALOG_PREPARE | pUTI89 | 通过（>pUTI89\|NC_007941.1，114230 bp） | w2-native.xml |
| MUMMER | pUTI89 自比对 | 通过 | w2-podman.xml |
| CLINKER | streptomyces region001/002 gbk | 通过 | w2-clinker.xml |
| ISESCAN | pUTI89 | 通过（12 个真实 IS 拷贝） | w2-isescan.xml |
| SCAPP_DETECT / SCAPP_BIN | spades fastg(minigut) | 通过 | w2-scapp-detect.xml / w2-scapp-bin.xml |
| RECYCLER | spades fastg + 真实 bam | 通过（修复后） | w2-recycler.xml |
| LINK_SEQUENCE | pUTI89（空 MAG 集） | 通过 | w2-native.xml |
| LINK_LONGREAD | minigut ONT 真实比对 | 通过（263 条桥接证据） | w2-longread-podman.xml |
| LINK_COABUNDANCE | ENA 真实丰度表（空宿主档） | 通过（执行契约） | w2-coabundance.xml |
| SAMTOOLS_INDEX | 真实 bam | 通过 | w2-samtools-index.xml |
| HIFIASM_META | gallus pacbio | 通过（执行契约；fixture 过稀疏无 contig） | w2-hifiasm.xml |
| DORADO_BASECALL | HG002 pod5 | 通过（10 条真实 reads basecall） | w2-dorado.xml |
| PLATON | pUTI89 + 官方 db | 通过（真实分类输出） | w3-platon.xml |
| METABAT2 + JGISUMMARIZE | binning fixture（真实 contigs+BAM） | 通过 | w3-mag-blast.xml |
| BLAST_BLASTN | pUTI89 自建小库 | 通过（真实自比对命中） | w3-blastn.xml |

## W1 vendored nf-core 套件汇总

48 个套件、165 个用例：真实通过 43、stub 通过 51、失败 71。
失败全部按类别如实记录（未更新任何上游快照）：快照差异（task.cpus 嵌入
BAM @PG、md5Reads 镜像构建差异、DB 版本日期内嵌等）、缺未 vendored 的 setup
模块（untar/gunzip/makeblastdb/downloaddb）、nf-test 0.9.5 与个别上游测试的
API 不兼容、瞬时网络、spades 需要 process.memory 默认值。逐套件明细：
`results/nf-test/w1-vendored-results.md`。其中 genomad/multiqc/fastp/megahit/
quast/bowtie2/minimap2/samtools/coverm/prodigal 等已在 P3/P4 的真实接线中
另行验证通过。

## P4：ENA 多样本全链路（nodes-cross-sample-ena.nf.test）

6 个真实样本（3 感染 vs 3 对照）完整跑通 illumina 平台：
fastp/fastqc/megahit/quast/geNomad/consensus/structure/coverm → MERGE_ABUNDANCE →
DIVERSITY（6 样本真实分组）→ DIFFERENTIAL_ABUNDANCE（126 行真实差异结果）→
DESEQ2（空质粒表优雅降级）→ 报告。质粒检出为零（裁剪 geNomad 库 + 低生物量
真实样本），FastSpar 分支按门控合法跳过。证据：results/nf-test/w4-ena.xml/.log。

## 真实数据暴露并已修复的生产问题

1. `modules/binning/recycler.nf`：`-k` 误传 fasta（recycle.py 的 -k 是整数 max_k
   且必填）→ 传 `-k 55`（metaSPAdes 默认）；输入契约改为 tuple(meta, graph, bam)。
2. `modules/assembly/opera_ms.nf`：上游 v0.8.3 的 OPERA-MS.pl 无 shebang →
   改为 `perl OPERA-MS.pl`。
3. `modules/mag/samtools_index.nf`：补容器声明（全流水线唯一缺容器的模块）。
4. `subworkflows/mag_host.nf`：SAMTOOLS_INDEX 桥接改为 mag_tools 非空才运行。
5. `bin/network_prepare.R`：空输入在 dcast 崩溃 → 加空表守卫（与
   deseq2_plasmid.R 既有模式一致）；`subworkflows/cross_sample.nf` 网络分支
   增加"质粒表为空则跳过"门控。
6. `containers/Dockerfile.r-analysis`：基础镜像实际不含
   data.table/vegan/Biostrings/Rsamtools（stopifnot 本会失败）→ 显式安装；
   11 个 R 模块容器切换为本地构建的 `autoplasm-r-analysis:latest`。

## 阻塞（如实记录，不用 stub 冒充）

| 节点 | 原因 |
| --- | --- |
| GTDBTK / EGGNOGMAPPER / RGI / METAPHLAN | 数据库 ~110GB / ~40GB / CARD / ~4GB |
| PLASME | 模型库 12.7GB |
| PLASX | 模型 1.7GB + annotations 需完整 anvio 流程 |
| COPLA / LINK_HOTSPOT | 需外部 refgraph / HOTSPOT 仓库+模型 |
| GPLAS2 / PLASMAAG | 上游仓库 404，无 bioconda 包（证据：w2-nodes-results.md） |
| PLASMIDHOSTFINDER | 镜像无 tag、bioconda 无包、缺 3.6GB 模型且上游 FTP 已下线 |
| OPERA_MS | 本机 perl 5.42 裁剪版缺 Safe/Switch，cpanm 无法自举；模块调用方式已修 |
| SCAPP 在 flye GFA 上 | scapp 0.1.4 仅支持 SPAdES fastg（生产接线正确，仅限 metaspades 路径） |
| sarscov2 pod5 + dorado 2.x | R9.4.1 化学已被 dorado ≥1.0 弃用（故 dorado 测试用 HG002） |

## 备注

- hifiasm_meta（hamtv0.3.5 源码编译）、dorado（官方二进制+模型）按模块注释
  走 native；两者的安装产物在 results/nf-test/runtime/ 与 databases/。
- vendored 套件（W1）的快照差异逐类记录于 w1-vendored-results.md；未更新任何
  上游快照，未修改 vendored 测试。
- 所有 JUnit/log/trace 在 results/nf-test/；测试、锁文件、本文档入 Git，数据不入。
