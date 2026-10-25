# 全节点真实数据测试覆盖矩阵

> 2026-10-21 更新：SCAPP 检测与 binning 已按用户要求移除，相关旧运行仅作历史证据，旧套件不再存在。当前状态见 `docs/tool-audit/status.md`。

每个 process 节点的真实数据测试策略与状态。状态：`done` 已有真实运行通过；
`vendored` 复用 vendored nf-core 模块自带测试；`new` 需要本仓库新增 nf-test 套件；
`blocked` 依赖大型数据库/外部仓库，记录为环境阻塞（不 stub、不 skip、不放宽断言）。
纯 Groovy 子工作流（SAMPLE_ID_VALIDATION、SHORT_READ_MULTIQC_INPUTS）无独立 process，
由 P0 与各平台套件间接覆盖。

数据：全部来自 nf-core/test-datasets（锁定 revision + blob SHA1）、工具官方固定版本
小数据库、ENA 公开真实样本；锁文件见 `*.lock.json`，适配器 `prepare_data.py`。

## QC / 上游

| 节点 | 域 | 策略 | 状态 |
| --- | --- | --- | --- |
| FASTP | qc | P1 vendored 真实运行 | done (RESULTS.md) |
| FASTQC (raw/clean) | qc | P1 vendored 真实运行 | done |
| MULTIQC | qc | vendored 套件；venv 提供 multiqc | vendored |
| NANOPLOT | qc | vendored 套件（ont/hybrid） | vendored |
| FILTLONG | qc | vendored 套件（ont） | vendored |
| DORADO_BASECALL | basecalling | 无容器声明→native dorado + 官方 fast 模型 + test-datasets pod5 | new |
| SAMTOOLS_FASTQ | qc | vendored samtools 套件 | vendored |
| SAMTOOLS_SORT | qc | P1 vendored（1 项 CSI 字节差异未决） | done（1 失败未决） |
| HIFIADAPTERFILT | qc | 新套件，gallus pacbio 真实 reads | new |
| BOWTIE2_BUILD/ALIGN (host) | host-deplete | P2 平台套件驱动；native bowtie2 | new(经 P2) |
| MINIMAP2_ALIGN (host) | host-deplete | 同上，native minimap2 | new(经 P2) |
| SAMTOOLS_VIEW (host) | host-deplete | 同上 | new(经 P2) |

## 组装与组装 QC

| 节点 | 策略 | 状态 |
| --- | --- | --- |
| MEGAHIT | P1 vendored 真实运行 | done |
| SPADES (metaspades/hybridspades) | vendored 套件 | vendored |
| FLYE | vendored 套件 | vendored |
| MEDAKA | vendored 套件 | vendored |
| HIFIASM_META | native 编译 hamtv0.3.5 + gallus pacbio（fixture 过稀疏，仅执行契约） | done (w2-hifiasm) |
| OPERA_MS | jar + minigut hybrid 数据 | new |
| QUAST | vendored 套件 + small-real pUTI89 | done (small-real) |

## 覆盖度与丰度

| 节点 | 策略 | 状态 |
| --- | --- | --- |
| BOWTIE2_BUILD/ALIGN (coverage) | P2 平台套件；native | new(经 P2) |
| MINIMAP2_ALIGN (coverage) | 同上 | new(经 P2) |
| SAMTOOLS_MERGE | 同上 | new(经 P2) |
| COVERM_CONTIG (×2) | P2 平台套件；native coverm | new(经 P2) |
| COVERM_ABUNDANCE(_LONG) | 同上 | new(经 P2) |

## 质粒检测

| 节点 | 策略 | 状态 |
| --- | --- | --- |
| GENOMAD | small-real pUTI89 + 裁剪库 | done |
| PLATON | 新套件 + platon db（固定版本） | new |
| PLASME | 新套件 + PlasMe 模型 | new |
| PLASX | 新套件 + plasX model/annotations | new |
| SCAPP_DETECT | 新套件，真实组装图 | done（真实通过：SPADES --meta fastg + scapp 全管线，w2-nodes-results.md） |
| PLASMID_CONSENSUS | small-real pUTI89 | done |
| PLASMID_STRUCTURE | small-real pUTI89 | done |

## 下游注释 / typing / 分箱

| 节点 | 策略 | 状态 |
| --- | --- | --- |
| PLASMIDFINDER | vendored 套件（自带小库） | vendored |
| MOB_TYPER / MOBSUITE_RECON | 新套件 + mobsuite db | new |
| COPLA | refgraph/reflist 外部仓库 | blocked |
| MACSYFINDER_DOWNLOAD/SEARCH | macsydata 固定版本模型 | new |
| BAKTA | bakta light db | new |
| AMRFINDERPLUS | amrfinderplus db | new |
| ABRICATE | 自带库 | new |
| ISESCAN | pUTI89 fasta | done (12 IS copies, w2-isescan.xml) |
| INTEGRONFINDER | vendored 套件 | vendored |
| PRODIGAL | vendored 套件 + small-real 间接 | vendored |
| RGI | CARD 库 | blocked |
| EGGNOGMAPPER | eggNOG 库 ~40GB | blocked（vendored stub 单独统计） |
| PLASMAAG | 其自带资源固定版本 | blocked（PyPI/bioconda 无包，仅 GitHub 完整 conda 环境，w2-nodes-results.md） |
| GPLAS2 | 真实组装图 + 自带 mlplasmids 模型 | blocked（PyPI/bioconda 无包，上游仓库已删，w2-nodes-results.md） |
| SCAPP_BIN / RECYCLER | 新套件，真实组装图 | SCAPP_BIN done（真实通过）；RECYCLER done（套件真实运行并失败：recycle.py -k 为 required 参数，w2-nodes-results.md） |

## 宿主预测

| 节点 | 策略 | 状态 |
| --- | --- | --- |
| METAPHLAN | 库 ~4GB 边界 | blocked（视磁盘再评估） |
| KRAKEN2 | 用真实测试序列自建迷你库 | new |
| PLASMIDHOSTFINDER | 官方小模型固定版本 | blocked（镜像无 tag+bioconda 无包+CBS FTP 模型目录已移除，w2-nodes-results.md） |

## MAG

| 节点 | 策略 | 状态 |
| --- | --- | --- |
| SAMTOOLS_INDEX / METABAT2 ×2 / CONCOCT ×5 / SEMIBIN / DAS_TOOL ×3 | 新套件：minigut 组装 + 真实 bam | SAMTOOLS_INDEX / METABAT2 链 done（w2 / w3-mag-blast）；CONCOCT / DAS_TOOL vendored 通过（W1）；SEMIBIN 真实训练完成、上游测试 API 不兼容（W1） |
| CHECKM2 | checkm2 测试库 | new |
| GTDBTK | 库 ~110GB | blocked |

## 宿主关联（linking）

| 节点 | 策略 | 状态 |
| --- | --- | --- |
| LINK_COABUNDANCE / MERGE_ABUNDANCE_FOR_LINK | 多样本真实丰度（ENA 子集） | new |
| LINK_SEQUENCE | pUTI89，空 MAG 集 | done (w2-native) |
| LINK_LONGREAD | minigut ONT 真实比对（263 bridges） | done (w2-longread-podman) |
| LINK_HOTSPOT | 需克隆 HOTSPOT 仓库+模型 | blocked |
| CRISPR | 未实现，P0 已验证明确报错 | done (P0) |

## 比较（comparative）

| 节点 | 策略 | 状态 |
| --- | --- | --- |
| PLASMID_CATALOG_PREPARE | pUTI89 | done (w2-catalog) |
| MMSEQS2 (easy-cluster) | 同上；native mmseqs | new |
| BLASTN | 自建小库（pUTI89） | done (w3-blastn) |
| MUMMER | pUTI89 自比对 | done (w2-podman.xml) |
| CLINKER | test-datasets prokaryote gbk | done（w2-nodes-results.md） |

## 跨样本统计

| 节点 | 策略 | 状态 |
| --- | --- | --- |
| MERGE_ABUNDANCE | ENA 真实多样本 | new |
| DIVERSITY | 同上 | new |
| DIFFERENTIAL_ABUNDANCE | 同上（≥3 重复/组） | new |
| DESEQ2 | 同上 | new |
| NETWORK_PREPARE / FASTSPAR | 同上 | new |
| REPORT | small-real pUTI89 | done |

## 阻塞清单（启用方法见 REAL-NODES-RESULTS.md）

GTDB-Tk (~110GB)、eggNOG (~40GB)、MetaPhlAn (~4GB)、RGI/CARD、HOTSPOT、COPLA
refgraph。这些是环境/数据阻塞，不是测试通过。

2026-10-24 Platon有界增量：当前原生产模块、固定1.7/完整v1.5.0数据库在nf-test0.9.5 native overlay中两个plain/gzip P3用例通过，代码/数据库/命令/断言见 results/tool-audit/20261024-platon-native/receipt.json。另8单元、2原生传输方法、完整库无检出与错误/缓存/Conda控制单列；同一pUTI89重放不算独立生物学重复。旧w3单例缺源码hash，不替代本次证据；未扩大到镜像或完整平台。
