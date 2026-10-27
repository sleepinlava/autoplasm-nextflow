# 分级测试集合

在仓库根目录运行。上游固定版本、许可和适配说明见 [UPSTREAM.md](UPSTREAM.md)。
本次配置对齐的验证结果见 [PROFILE-RESULTS.md](PROFILE-RESULTS.md)。

| 级别 | 测试目标 | 判定 |
| --- | --- | --- |
| P0 | 11 个输入错误：重复/非法 ID、缺失 mate、必需数据库、未实现的 CRISPR、非法平台/组装器及不兼容工具组合 | 必须明确失败，并且没有成功执行分析任务 |
| P1 | 现有 nf-core fastp、fastqc、samtools/sort、megahit 完整测试 | 保留上游断言及快照；分别统计真实运行与 stub |
| P2 | Illumina、assembly、ONT、hybrid、HiFi 核心流程 | 真实工具运行成功，trace 无失败；共识、结构、组装评估、丰度和报告符合契约 |
| P3 | 单节点真实小数据（`nodes-*.nf.test`，详见 [COVERAGE.md](COVERAGE.md)） | process/workflow 成功 + 输出契约断言；断言用上游固定事实 |
| P4 | 适用的真实 shotgun 多样本与非空质粒统计链路（待验收） | 实际拟合、网络资格与报告；旧 PRJNA848809 为 16S 扩增子，不认证此范围 |

P0/P2 使用 `P0`/`P2` tag，P2 还可按平台 tag 筛选。P1 直接选择已有文件，
没有为了添加 tag 修改上游测试。缺失程序、数据库或网络导致的失败必须报告为环境阻塞，
不能改成 skip、更新快照或用 stub 的成功替代。`--dry-run` 只说明用例可被发现。

## PLASMe 完整模型节点

`nodes-detection-plasme.nf.test` 要求完整官方数据库与已建 BLAST/DIAMOND
索引，版本和校验和见 `tests/plasme-native.lock.json`。设置三个绝对路径：
`AUTOPLASM_PLASME_SOURCE` 为固定官方源码目录，`AUTOPLASM_PLASME_DB` 为
准备好的 DB 目录，`AUTOPLASM_PLASME_INPUTS` 内含完整 pUTI89 的
`pUTI89.fna` 与 `pUTI89.fna.gz`。使用 `envs/plasme.yml` 的原生环境将其
程序放入 PATH，然后运行此文件及 `--profile native`；也可使用已构建的
`containers/plasme/Dockerfile` 镜像和 `--profile podman`。

断言要求真实 Transformer 分数、阳性 ID、完整 DNA、原始报告和运行身份。
plain/gzip 是同一生物样本的两种编码，不计两个科学重复。writer observer、
微型 BLAST 边界与完整模型运行分别记录，均不替代分类准确率基准。
`tests/run_plasme_native.py` 另覆盖 Conda/容器后端及独立 BioPython 解析。

## COPLA 完整参考节点

`nodes-typing-copla.nf.test` 使用完整参考图、全部参考 FASTA 和官方真实质粒。
设置绝对路径 `AUTOPLASM_COPLA_INSTALLATION`、`AUTOPLASM_COPLA_MACSYFINDER`、
`AUTOPLASM_COPLA_GRAPH`、`AUTOPLASM_COPLA_REFLIST`、`AUTOPLASM_COPLA_DATA`；
最后一个目录含完整官方 `NZ_CP028329.1` 序列的 `Lab26.fna` 和
`Lab26.fna.gz`。将固定 COPLA Python3 环境加入 PATH，使用 `--profile native`。
MacSyFinder 保留独立的 Python2 环境，不用 Python3 版本代替。

断言核对官方示例的 PTU-Lab26、完整 DNA/长度、独立候选身份、全部参考的
评估状态和原始产物。无法形成既定 1,000 bp 窗口的参考明确记作不可评估，
外部程序失败不能记作无命中。`tests/run_copla_native.py` 另检查同一样本内的
两条独立官方质粒。CLI observer 和原生 ANI/图函数边界分别记账，不计为
全库分类或科学准确率通过；当前验收状态见 `docs/tool-audit/status.md`。

## uv 隔离环境

```bash
export UV_CACHE_DIR=/tmp/autoplasm-uv-cache
uv sync --project tests/nf-test --locked
# P2 的 Python 工具；含 geNomad 的 TensorFlow 依赖，首次下载较大。
uv sync --project tests/nf-test --locked --extra pipeline
```

Python 固定为 3.12，环境位于本目录 `.venv/`；不要使用 `--active`，以免使用外部环境。
`uv.lock` 锁定完整依赖解析。`--no-sync` 的执行命令保留已经安装的可选依赖。

## MetaBAT2 与长读长关联的语义验收

`nodes-mag-metabat2.nf.test` 分开检查默认空分箱与上游固定宽松参数下的非空
成员输出。后者使用 vendored `tests/nextflow.config` 的原参数，未修改生产默认。
独立 Python 检查固定输入身份、深度表完整 ID/长度/有限数值、全部分箱 DNA、
唯一成员及完整成员分区。MetaBAT2 2.17 的内部簇编号与 FASTA 文件编号独立，
不可直接按编号比较；不以当前分箱数量作为准确率真值。

本轮原生环境锁为 `tests/metabat2-native-linux-64.lock`（Linux64，35 个远程
归档 URL/SHA256，MetaBAT2 2.17 build0、htslib1.20）。它是测试环境锁，不替代
生产模块环境/镜像认证。原生测试需将该环境程序放入 PATH。

`nodes-linking-longread.nf.test` 使用上游 **合成** minigut 及单独构造的跨序列
阳性控制。第一批五条 contig 只是测试分区，不是已知质粒。准备额外控制：

```bash
python3 tests/prepare_longread_controls.py \
  --assembly "$AUTOPLASM_TEST_DATA/minigut.fasta" \
  --output results/nf-test/longread-controls
export AUTOPLASM_LONGREAD_CONTROL_DATA="$PWD/results/nf-test/longread-controls"
```

控制含两条明确构造的技术读段，各跨越已知 4kb+4kb 接点，不是生物学重复或
自然宿主关系真值。SAMtools 导出的 SAM 供独立 Python 复核；生产 R 仍读取
BAM。断言核对原始 DNA/读段/参考域、唯一桥接读段数、样本、分数、长度归一化
和宿主名次。测试比对管道显式传播失败，不允许部分比对掩盖子程序错误。

2026-10-25 实际 nf-test0.9.5 的两套四例及8原生任务通过；6项现有 R 单元测试
使用合法参考长度复验通过。12项实际产物副本对照检查错误结果拒绝；编号重命名
合法对照仍通过。此次为 native 证据，不认证 podman 镜像、MAG 质量或宿主生物学
准确率。版本/输入/失败尝试及完整范围见 `docs/tool-audit/contracts/p3-semantic-oracles.md`。

uv 管理 Python 依赖；Java、Nextflow 及原生生信程序由独立工具路径提供。
本配置不启用 Conda。P1 原生工具为 fastp 1.3.6、FastQC 0.13.0、SAMtools 1.24、
MEGAHIT 1.2.9、pigz 2.8。P2 还需当前工作流要求的 MMseqs2、Prodigal、Bowtie2、
CoverM、minimap2、Flye、Filtlong、HiFiAdapterFilt（含数据库）、hifiasm、Rscript 等；
ONT/hybrid 还需要 NanoPlot。具体依赖以各过程及 `envs/` 的声明为准。
Python extra 不代表这些原生依赖已经安装。

本次使用 Java 21 与 Nextflow 26.10.0。运行时（nextflow 启动器、nf-test 0.9.5）
安装在 `results/nf-test/runtime/`（持久磁盘；/tmp 是 tmpfs，重启会丢失，不要放那里）。
统一环境入口是 `tests/nf-test/env.sh`（设置 JAVA_HOME、PATH、NFT_BIN、NXF_WORK，
并在 SELinux Enforcing 时把 `tests/nf-test/bin/podman` 的 `:z` 重标 shim 放到 PATH 最前）：

```bash
. tests/nf-test/env.sh
```

nf-test 运行时的手动安装（校验和来自官方 release）：

```bash
mkdir -p results/nf-test/runtime
curl -fL https://github.com/askimed/nf-test/releases/download/v0.9.5/nf-test-0.9.5.tar.gz \
  -o results/nf-test/runtime/nf-test.tar.gz
echo 'b7679eb90cdc9642bfa89e9634db02ce6e699de53ad35ef0e2f4847634fc1641  results/nf-test/runtime/nf-test.tar.gz' | sha256sum -c -
tar -xzf results/nf-test/runtime/nf-test.tar.gz -C results/nf-test/runtime
curl -fsSL https://get.nextflow.io -o results/nf-test/runtime/nextflow
chmod +x results/nf-test/runtime/nextflow
```

执行后端：模块声明了 biocontainers 镜像，用 `--profile podman`；无容器声明的
（dorado、hifiasm_meta、opera_ms 及 R 脚本节点的本地回退）用 native（不加 profile）。
native R 节点依赖系统 R 的 data.table/Biostrings/Rsamtools/vegan。容器化 R 节点使用
本地构建的 `autoplasm-r-analysis:latest`（`containers/Dockerfile.r-analysis`，
podman build 即可；上游 bioconductor 基础镜像不含 data.table/vegan/Biostrings/Rsamtools，
已由真实运行验证并修复 Dockerfile）。

首次执行需要网络获取 nf-test 插件和 P1 上游输入。Nextflow 已缓存时可设
`NXF_OFFLINE=true`，但这不会让上游输入下载变为离线操作。

## 数据与执行

准备一次真实格式的上游合成数据。目标必须是新目录，防止混入旧数据：

```bash
uv run --project tests/nf-test --locked --no-sync python tests/nf-test/prepare_data.py \
  --outdir results/nf-test/upstream-data
export AUTOPLASM_TEST_DATA="$PWD/results/nf-test/upstream-data"
```

分级运行，保留退出码与 JUnit：

```bash
uv run --project tests/nf-test --locked --no-sync "$NFT_BIN" test \
  -c tests/nf-test.config tests/nf-test/validation.nf.test \
  --profile native --ci --junitxml results/nf-test/p0.xml --log results/nf-test/p0.log

mapfile -t p1_suites < tests/nf-test/p1-suites.txt
uv run --project tests/nf-test --locked --no-sync "$NFT_BIN" test \
  -c tests/nf-test.config "${p1_suites[@]}" \
  --profile native --ci --junitxml results/nf-test/p1.xml --log results/nf-test/p1.log

uv run --project tests/nf-test --locked --no-sync "$NFT_BIN" test \
  -c tests/nf-test.config tests/nf-test/integration.nf.test \
  --profile native --ci --junitxml results/nf-test/p2.xml --log results/nf-test/p2.log
```

可在 P2 命令后加 `--tag assembly` 等只运行目标平台；`NFT_WORKDIR` 可隔离不同运行的
工作目录。完整日志、Nextflow trace 和 task 命令保存在 `results/nf-test/work/`。
nf-test 还会在根目录创建 `.nf-test/` 插件缓存和 `.nf-test-*.nf` 包装脚本；它们不应提交。
禁止在验证尚未通过时用 `--update-snapshot` 建立“全绿”基线。

## P3/P4：真实小数据节点与多样本

数据适配器有三个真实数据集档位（均固定版本+校验值锁定）：

```bash
# 节点级真实小数据（pUTI89、minigut、sarscov2、gallus、pod5、gbk）
uv run --project tests/nf-test --locked --no-sync python tests/nf-test/prepare_data.py \
  --dataset real-nodes --outdir results/nf-test/real-nodes-data
export AUTOPLASM_TEST_DATA="$PWD/results/nf-test/real-nodes-data"

# 历史 ENA 16S 执行 fixture（PRJNA848809，官方 md5 锁定；不认证 shotgun P4）
uv run --project tests/nf-test --locked --no-sync python tests/nf-test/prepare_data.py \
  --dataset ena-multi --outdir results/nf-test/ena-multi
export ENA_TEST_DATA="$PWD/results/nf-test/ena-multi"
```

需要数据库的节点（platon 等）：`tests/nf-test/download_databases.sh` 下载资产到
`results/nf-test/databases/`，全部成功才返回 0；某项失败时继续处理其余项，最后返回非零。
下载先写临时文件，确认非空、归档可读取且已知 SHA256 匹配后发布。
`manifest.txt` 记录 size+sha256，并在重用或重新下载时校验；首次下载产生的本地摘要只是重放锁，不能代替独立上游校验和。
现存文件没有记录时拒绝直接采用，避免把旧的中断下载记成完整数据库；不会删除损坏的现存文件。
运行时导出 `AUTOPLASM_DB="$PWD/results/nf-test/databases"`。各节点仍需按自己的数据锁核对版本与摘要。

可用 `--outdir DIR --asset-list FILE` 指定资产清单。清单是 TSV，每行两列 `name URL`，
或三列 `name URL independent_sha256`；第三列必须是 64 位小写十六进制。
默认清单仍是原来的十项资产，脚本不自动运行任何分析。

下载逻辑回归：`python3 -m unittest discover -s tests -p test_database_downloads.py -v`。
测试使用真实 curl、归档程序与临时本机 HTTP 服务，覆盖截断、空响应、HTTP 失败、损坏文件和重放；
默认十项资产和清单写入故障使用明确的失败模拟，不下载生产数据库。

P3 单节点套件按域拆分（一个文件一个 suite 块；nf-test 不读取同文件后续块）：

OPERA-MS 的真实验证固定在 v0.8.3；源码、完整参考库以及两个原生依赖前缀的
URL/摘要见 `tests/opera-ms-native.lock.json`。内置 SAMtools0.1.19 需要 ncurses5 ABI；
本机 zlib-ng 的 compressBound 会触发其断言，已验证环境使用独立前缀的 zlib1.3.2。
必须在任务环境中把相应兼容库目录和依赖前缀/lib 加入动态库搜索路径；仅 `--help` 检查通过不足以确认可运行。
模块将 gzip 长读解到任务私有文件，保留源文件；检查最终 FASTA 后，还会拒绝缺失覆盖度诊断或含已识别致命子进程错误的结果。
这项检查不代替组装准确率验证。原 P3 用例已通过 nf-test0.9.5/Nextflow26.10.0 的真实执行；
同一数据的早期“成功但内部崩溃”运行明确不验收，完整证据见
`results/tool-audit/20261023-opera-native/receipt.json`。

单独运行原模块契约的入口为 `tests/run_opera_ms_native.py`，接收已经安装并完成数据库准备的
`--opera-root`、设置 PATH/PERL5LIB/动态库的 `--native-env` shell 文件，以及固定的
`--read1 --read2 --long-reads --work-dir`；默认要求成功，负例需显式 `--expect`。
`tests/test_opera_output_validation.py` 检查致命诊断拒绝规则；
`tests/test_opera_ms_interface.py` 是明确的 Perl CLI observer，不是 OPERA-MS 算法运行。
其中带空格文件名只验证包装器参数/解压边界，不认证上游所有内部路径都支持空格。

```bash
. tests/nf-test/env.sh
# native（R 脚本节点）
"$NFT_BIN" test -c tests/nf-test.config tests/nf-test/nodes-comparative-catalog.nf.test --ci
# podman（容器节点）
"$NFT_BIN" test -c tests/nf-test.config tests/nf-test/nodes-detection-platon.nf.test \
  --profile podman --ci --junitxml results/nf-test/w3-platon.xml --log results/nf-test/w3-platon.log
```

历史 ENA 执行用例（16S 扩增子；独立 tag 为 `legacy-16s-execution`，不计 shotgun P4；QUAST 阈值 200，见 ena.config）：

```bash
"$NFT_BIN" test -c tests/nf-test.config tests/nf-test/nodes-cross-sample-ena.nf.test \
  --profile podman --ci --junitxml results/nf-test/w4-ena.xml --log results/nf-test/w4-ena.log
```

## 公开 test profile

`conf/test.config` 与 P2 共用同一配置，使用上面准备的固定版本数据；默认在
`results/nf-test/upstream-data` 查找，`AUTOPLASM_TEST_DATA` 可指定其他绝对路径。
不会自动下载生产数据库。默认测试 Illumina；其他平台仍由 P2 显式传入对应样本表。

```bash
nextflow run . -profile test,docker
# 测试已有组装数据，显式选择匹配的样本表
nextflow run . -profile test,docker --platform assembly \
  --samplesheet "$AUTOPLASM_TEST_DATA/assembly.tsv"
```

小型 geNomad 数据库禁用神经网络分类；只验证真实工具的执行与输出契约，不能
证明质粒检出准确率。typing、host prediction、MAG、linking、comparative 分支关闭。
`resourceLimits` 对上游模块各自声明的资源需求设上限，保留执行后端的选择。

数据适配器的离线单元测试使用 pytest，只隔离 HTTP 传输，检查同长度内容损坏、
截断、已有目录保护，以及校验回执和五平台样本表。它们不计入真实工具运行：

```bash
tests/nf-test/.venv/bin/python -m pytest -q tests/test_prepare_test_data.py
```

## 小型真实质粒测试（pUTI89）

本次实际结果与分类限制见 [SMALL-REAL-RESULTS.md](SMALL-REAL-RESULTS.md)。

复用 [nf-core 的 pUTI89 序列](https://github.com/nf-core/test-datasets/blob/618f1541382c4ad49eff566dadf13d5ccbd0ebb4/data/genomics/prokaryotes/plasmids/pUTI89/pUTI89.fna.gz)：
FASTA 标识 `NC_007941.1`，完整序列 114,230 bp，压缩下载 35,478 bytes。
加上固定版本 geNomad 测试数据库 5,912,894 bytes，总计 5,948,372 bytes，
约 5.67 MiB。`plasmid-datasets.lock.json` 独立锁定两个文件，不下载其他平台数据。

```bash
uv run --project tests/nf-test --locked --no-sync python tests/nf-test/prepare_data.py \\
  --dataset plasmid --outdir results/nf-test/small-plasmid
export AUTOPLASM_TEST_DATA="$PWD/results/nf-test/small-plasmid"
uv run --project tests/nf-test --locked --no-sync "$NFT_BIN" test \\
  -c tests/nf-test.config tests/nf-test/plasmid.nf.test \\
  --profile native --ci --junitxml results/nf-test/small-real.xml \\
  --log results/nf-test/small-real.log
```

先按上文安装 Python pipeline extra，并准备 MMseqs2、ARAGORN、Prodigal、R 及
Biostrings/data.table。`native` 要求所有程序在 PATH；也可选择已配置的容器后端。
这是真实完整参考质粒的 assembly 输入测试，不是原始测序 reads 的组装测试。
断言参考 accession、长度、contig 数、样本归属以及共识、结构、报告产物；
小型数据库不能作为检出准确率基准，因此单独记录实际分类，不把分类值用首次输出
锁成快照。也不把参考序列的环状注释等同于 FASTA 自带末端重复证据。

### Native Bowtie2 sample-association regression

`tests/run_native_alignment_pairing.py` runs the actual CONTIG_COVERAGE and
PLASMID_ABUNDANCE workflows and the verbatim Illumina/hybrid host-removal
components with distinct synthetic references/reads and forced reverse index
completion. It checks BAM SQ/LN/QNAME, mapped records, independently calculated
CoverM mean coverage, and exact host/nonhost read retention. It does not certify
full platform workflows, minimap2, container images, or biological performance.

The explicit native prefixes must provide Bowtie2 2.5.4/SAMtools 1.21/pigz 2.8
and CoverM 0.7.0/SAMtools 1.24 respectively; the script verifies these versions.
With Nextflow 26 on PATH, use a fresh isolated output directory:

```bash
python3 tests/run_native_alignment_pairing.py \
  --bowtie-prefix /path/to/bowtie2-prefix \
  --coverage-prefix /path/to/coverm-prefix \
  --work-dir /path/to/empty-regression-directory
```

The audit's explicit dependency locks and original failing/verified runs are
retained under `results/tool-audit/20261020-alignment-keyed-fix/` and
`results/tool-audit/20261020-bowtie2-native-pairing/`. These are native
counterparts, not nf-test/JUnit results. The existing mock E2E oracle limitations
(TT-001) are separate and remain open.

### Recycler same-graph input contract

Production SPAdes emits the FASTG and same-task maximum-k provenance together.
Recycler receives original short-read pairs, a dedicated canonical graph-node
BWA BAM and its adjacent BAI. Graph/hash/k/reference/index checks precede the
actual tool. The entry point rejects platforms/assemblers without these inputs.
The native preparation stack is BWA0.7.19 / SAMtools+htslib1.22.1; Recycler is0.7.
Declared images and exact native environment locks are separate evidence.

`bin/recycler_graph_reference.py` exports actual unprimed graph sequences even
when a reverse record appears first. Removing a prime from reverse sequence
names alone is incorrect. The provenance collector uses the successful final
SPAdes copy plan/config/graph bytes; it does not guess k from headers or the
largest directory. Independent unit cases:

```bash
python3 -m unittest discover -s tests -p test_recycler_graph_reference.py
python3 -m unittest discover -s tests -p test_spades_graph_provenance.py
```

The standalone native structural suite accepts reverse-first graphs and
rejects primed BAM references, missing/corrupt BAI and other malformed inputs:

```bash
python3 tests/run_recycler_input_validation.py \
  --recycler-prefix /path/to/recycler-0.7-prefix \
  --samtools-prefix /path/to/samtools-prefix \
  --work-dir /path/to/empty-guard-test-directory
```

The official upstream BAM has only14 oriented references and is not a complete
graph-node production BAM. Original-module regressions use
`tests/nextflow/recycler_native.nf` (SPAdes bundled pairs and real provenance)
and `tests/nextflow/recycler_contract.nf` (explicit artificial graph/metadata
fixtures for known sequence/k and rejection cases). Their native recipes,
locks, trace, task scripts and semantic checks are retained in
`results/tool-audit/20261021-recycler-production-fix/`.

The real minigut suite now uses the original SPAdes graph/pairs and dedicated
preparation; assertions check provenance/state and exact output identities.
Its FASTG basename follows the configured SPAdes prefix. Zero cycles are
allowed as an execution-contract result, not a biological recall claim.
`skipped_no_graph_edges` explicitly identifies a graph with no possible cycle;
other tool errors fail. Recycler0.7's three omitted internal k defaults use
the same requested k; controlled k33/k55 cycles cover the boundary-length
false-negative fix. Default55 output compatibility and non55 historical
recomputation requirements are recorded in the audit contract.

Native runs are not nf-test loader/JUnit or container certification, full
platform E2E, or scientific performance benchmarks.


### RGI 本地CARD选择的原生回归

`tests/rgi-database-scope.lock.json` 锁定完整 CARD3.3.0/3.2.8 官方归档、RGI6.0.8上游真实质粒和VIM-77参考。先按锁文件URL取得数据和RGI6.0.8/KMA1.6.11原生环境；准备脚本只读本地输入、校验SHA256，不下载或覆盖既有准备目录。设置 `RGI_PREFIX`、`CARD_330_ARCHIVE`、`CARD_328_ARCHIVE`、`RGI_PLASMID_FASTA` 为相应绝对路径后：

```bash
python3 tests/prepare_rgi_scope.py \
  --output-dir /tmp/rgi-scope-fixtures \
  --prefix "$RGI_PREFIX" \
  --card-330-archive "$CARD_330_ARCHIVE" \
  --card-328-archive "$CARD_328_ARCHIVE" \
  --plasmid-fasta "$RGI_PLASMID_FASTA"
python3 tests/run_rgi_database_scope.py \
  --work-dir /tmp/rgi-scope-run \
  --fixture-dir /tmp/rgi-scope-fixtures --prefix "$RGI_PREFIX"
python3 tests/run_rgi_downstream.py \
  --work-dir /tmp/rgi-downstream-run \
  --fixture-dir /tmp/rgi-scope-fixtures --prefix "$RGI_PREFIX"
python3 -m unittest discover -s tests -p test_rgi_card_validation.py -v
```

原生runner要求PATH中有可用Nextflow；以上是独立原生模块/子工作流回归，不表示nf-test框架/JUnit或镜像已运行。数据库scope测试分开生产默认参数和固定上游的low_quality/include_loose/include_nudge/clean/debug参数，后者保留NDM-1 Perfect100断言；不要把两种方法的输出差异当作数据库回归失败。VIM-77属于精确参考sanity，随机DNA是人工阴性，不能推导临床AMR性能。当前真实执行证据与限制见 `docs/tool-audit/contracts/rgi-database.md`。
# MAG 结果路由和 DAS Tool 导出（独立原生验证）

`tests/run_mag_selection_validation.py --work-dir <新目录> --replay-main-registry`
执行原 main 拒绝用例及 MAG 依赖矩阵；多分箱器未选 DAS Tool、无分箱器却选择
汇总/质量/分类的配置必须在分析任务启动前失败。重放不增加独立场景分母。

将 `results/tool-audit/runtime/bin` 加入 PATH 后，运行：

```bash
python3 tests/run_mag_routing.py --work-dir <新目录> \
  --das-prefix <DAS_Tool1.1.7前缀> --bgzip-prefix <含bgzip的前缀> \
  --concoct-prefix <CONCOCT1.1.0前缀>
```

这是原 MAG_HOST、真实 gzip/上游 FASTA 转表辅助程序、真实 R 宿主关联的接线验证。
分箱器、DAS 汇总和质量/分类 CLI 使用明确 observer，BAM/数据库是假输入。
断言检查样本/分组、数量、ID、DNA、全部汇总输入、消费者实际暂存和原 R 输出。
GTDB observer 仅观察暂存，不能证明其真实扩展名筛选或分类；不计完整 P3。

真实 DAS Tool 数据和独立预期结果锁定在 `tests/dastool-sample.lock.json`，按其中
URL 获取7个官方1.1.7文件至同一目录，然后执行：

```bash
python3 tests/prepare_dastool_sample.py <样本目录>
python3 tests/run_dastool_export.py --work-dir <新目录> \
  --fixture-dir <样本目录> --prefix <DAS_Tool1.1.7前缀>
```

真实节点使用完整官方 gut assembly 和4组预测，以固定上游 Run1 成员表与汇总表
检查15个 bin 的数量、成员、长度和逐条 DNA；不是重新生成期望值。
阳性使用生产参数和默认 score0.5；无接受 bins 控制使用真实低分 bin 与明确的
测试阈值0.9，不改变生产默认。上游在此情形主动停止，测试必须确认失败传播、
正确诊断和没有部分发布文件。可选 `--old-config` 用于保留前态无 FASTA 反例。
这些入口不等于 nf-test 框架/镜像认证，也不验证分箱器、CheckM2、GTDB 模型或科学准确率。

# CONCOCT 压缩输入、BED坐标与空提取（独立原生验证）

使用固定CONCOCT1.1.0（生产py39构建）与setuptools70环境。输入文件见
`tests/concoct-sample.lock.json`，需要其固定官方composition.fa；不会重生成期望DNA。

```bash
python3 tests/run_concoct_io.py --work-dir <新目录> \
  --fixture <锁定的composition.fa> --prefix <CONCOCT1.1.0前缀>
python3 tests/run_concoct_mag.py --work-dir <另一新目录> \
  --fixture <锁定的composition.fa> --prefix <CONCOCT1.1.0前缀>
```

第一组17场景调用真实cut/extract helper及原包装器，检查plain/gzip/GZ、含空格路径、
切片DNA不变、BED边界与原DNA逐条对应、非重叠/末段合并、空成员表、损坏gzip、
未知contig、错表头及未审查source拒绝。失败诊断从实际任务stderr检查，避免只在
Nextflow显示的命令文本里搜到关键字而误判。

第二组在原MAG_HOST执行真实索引/切片/覆盖度/分箱/合并/提取六节点，每样本一次。
两个样本使用相同固定真实DNA的plain/gzip版本和明确构造的合法映射BAM；使用生产
默认参数，包括chunk1999、overlap1900、clusters400、seed1、iterations500。
只修正原helper的BED坐标步长，不改切片策略。bin检查证明成员/原DNA一致与可复现，
不证明生物学分箱准确率；BAM不是实际测序/比对效果基准。

MAG路由入口现在需要`--concoct-prefix`，实际cut/merge/extract辅助脚本由该前缀提供，
不使用fake cut helper绕过生产source校验；核心分箱器/质量/分类observer范围仍显式区分。
新增empty-concoct检查验证空成员经真实merge/extract成功后，质量/分类不运行且原R
关联输出为空。所有独立原生入口均非nf-test框架/镜像或五平台P4认证。

# DAS Tool 可选自定义数据库（独立原生验证）

使用DAS1.1.7 r44hdfd78af_1/R4.4环境，正例6个完整数据库文件以
`tests/dastool-db.lock.json`锁定包及文件SHA256，输入和独立15-bin预期结果使用
`tests/dastool-sample.lock.json`。先按DAS导出入口生成同一官方assembly的真实
Prodigal蛋白文件，再运行：

```bash
python3 tests/run_dastool_custom_db.py --work-dir <新目录> \
  --fixture-dir <固定官方gut样本目录> --prefix <DAS1.1.7前缀> \
  --proteins <同一assembly真实生成的DASToolRun1_proteins.faa>
```

正例覆盖含空格目录、目录basename为db、未显式指定数据库的原默认分支，使用实际
完整DB与原生DAS，核对全部15个bin的固定独立成员、大小、数量与DNA；不修改生产
score0.5或导出选项。含空格DB被Nextflow暂存为固定dastool_db名称，避免上游bash/R
内部按空格拆分；--dbDirectory使用1.1.7真实拼写。

缺文件、零长度文件、文件冒充目录，在实际DAS搜索启动前必须明确失败且无部分发布。
另一个明确受控负例保留全部真实reference FASTA，只把两个lookup换为不匹配的测试ID，
放在basename为db的目录下；DAS必须报告No single copy genes predicted。该对照验证
实际读入指定DB，防止静默回退内置DB；它不是生物学阴性或灵敏度基准。正例始终使用
完整正版六文件，不使用裁剪/伪造DB冒充正例。全部输入及内置DB在运行前后核验不变。

可选--old-module指定冻结原module进行错误参数的原生反例；不将失败前态覆盖为成功。
当前生产MAG_HOST仍传[]使用默认内置DB；此项扩展的是module声明的可选接口。测试
不等于镜像/nf-test框架/完整平台或用户自定义DB生物学有效性认证。

### 结构拓扑与报告回归（TA-036，原生局部验证）

`python3 tests/run_structure_topology.py --work-dir <fresh-directory> --references <locked-reference-directory>`

依赖 Nextflow、R/data.table/Biostrings；两份参考的下载 URL、accession、完整文件/核酸 SHA256、长度与 GenBank 拓扑见 `tests/structure-reference.lock.json`。SCP1 NC_003903.1 的线性拓扑另有原始实验研究支持（PMID1847368）。原脚本对其输出 true/itr1000，修复后保留 itr1000 而拓扑 unknown；不从 ITR 反推线性。pUTI89 原始 FASTA 无闭环证据时保持 unknown；另一个明确依据独立 GenBank 注释添加 header 的输入才应产生 header 候选。人工 DTR/ITR 和空结果仅为规则/格式对照。

原 PLASMID_STRUCTURE 五任务、原 REPORT 一任务核对 ID/长度/重复/候选数量，报告不把 ITR-only 计为环状。runner 在生产者完成后显式准备全新报告目录，不能据此关闭生产 publishDir 屏障问题 TA-015。13 项结构单元方法、3 项报告方法、54 项 R smoke 和原检测路由26任务另验；分类器为 observer，不是分类器/图或 reads/完整平台/nf-test 框架/镜像或科学性能认证。

### 统一核酸参考与重映射（TA-010/011/012）

新目录按全长核酸或反向互补精确去重，保留 SHA256 序列 ID、来源表、逐样本候选状态；不做 ANI/家族或环状旋转聚类。生产四个 reads 平台均提供全部样本的组装及原始共识输出（含空候选），统计与 co_abundance 使用共享表；本地覆盖度保留给 MAG/局部链接。hybrid 统计只用短读段。

公开入口 `tests/run_shared_quantification.py`：参数 `--work-dir`、`--references`（structure-reference.lock.json 的两个原始 FASTA）、`--bowtie-prefix`（2.5.4）、`--coverm-prefix`（0.7.0）、`--minimap-prefix`（2.30/SAMtools1.23.1）、`--python-prefix`（3.12），以及 `--modes short map-ont map-hifi`。实际原节点和 CROSS_SAMPLE/HOST_LINKING 消费者共19+18+18任务验证同名异序列、同序列改名/反向互补、无本地候选仍测量、显式零样本、计数/覆盖度、独立 Bray-Curtis 与已明确控制宿主profile的r=1。reads 是固定真实 DNA 上按源序列唯一性预选坐标的明确模拟输入；不是湿实验数据或性能基准。

`tests/run_shared_quantification_edges.py` 的参数为 `--work-dir`、`--reference`（锁定pUTI89 FASTA）、`--bowtie-prefix`、`--coverm-prefix`、`--python-prefix`。真实 mapper 的三边界场景：完整近似序列仅在读段区域外改一个碱基，所有等价读段应被低MAPQ过滤；全局空参考只运行目录和汇总两个任务且保留4样本状态；故意少一个样本测量必须失败且无最终统计表发布。最初 MAPQ≥1 测试实际发现 Bowtie2 ties=1，保留该失败证据，最终策略为 MAPQ≥10/排除未知255与非主要比对。

Python目录/测量15方法（同时使用3.12验证）、原始计数4方法、既有identity7/numeric6/merge5方法及R smoke54断言覆盖接口；不把方法数当作独立生物学案例数。`mock_e2e/run.py` 同步新共享任务数、DNA对应特征ID及独立指定的mock计数，hybrid统计断言短读数值。其计数依然是明确observer按文件名给出的控制值，TT-001旧oracle局限保留；原生独立映射数据补证不等于该mock已变成真实模型。

DESeq2固定部署1.42的完整正例/零计数环境尚未执行（本机模型1.52），TA-011不能据此称部署正例通过；图/reads拓扑、FastSpar模型、完整真实平台、镜像/nf-test及报告发布屏障TA-015不由本批认证。全零网络过滤后的eligibility TA-038、单特征alpha TA-014及剩余metadata边界继续未决。

### 本轮报告输入、可选完成链与缓存（TA-015/017）

`python3 tests/run_report_inputs.py --work-dir <fresh-directory>` 需要Nextflow26.10、R/jsonlite/rmarkdown及pandoc；报告R脚本和模板作为path输入，测试实际Rmd HTML与JSON/Markdown数值。5场景包含：延迟可选writer且禁止发布仍被本轮记录；无可选任务与旧目录/旧样本隔离；resume不变缓存；同名输入改变重算；可选失败阻止报告。8个trace条目为4完成/3缓存/1预期失败，不混算成8个全新阳性任务。writer/检测数据是明确控制的接口fixture，不是分类或注释效果验证。

`test_generate_report.py` 现13方法（保留原3方法），新增严格显式manifest/samplesheet及错配拒绝，不以默认0掩盖损坏/缺文件。CLI不再支持--outdir发现；R smoke相应传清单，并把结构fixture改为生产实际的质粒FASTA子集。五份产品report.md/report.html/methods.md/report_data.json/report_inputs.json均需发布；本轮文件同名采用编号暂存防止碰撞。

mock_e2e新增assembly平台并核对报告JSON/HTML/Markdown、实际trace producer与板块状态；注入旧样本和空network目录，不能把目录存在当完成证据。5平台正例+空质粒共788连接任务仍是明确外部CLI替身+实际R/Python，不升级真实模型认证；TT-001旧的按文件名给mock覆盖度/计数局限继续开放。实际共享定量55任务、结构6任务和MAG32任务回归另记。

方法文字只能说明已记录的输出；process报告版本可能是静态声明，不足以证明所有实际运行版本。完整CLI/数据库/模型身份仍是TA-016开放项，不能把默认参数、启用工具列表或文件夹当作完整方法学证据。历史结构/共享运行中TA-015未验证的限制只对应各自scope，本批报告专用suite补上本轮完成链及发布/缓存证据。

### 长读段宿主去除与测试替身（TA-033/057、TT-006/010）

`tests/run_long_read_host_removal.py --work-dir <fresh-dir> --minimap-prefix <2.30-prefix> --samtools-prefix <1.24-prefix> --before-dir <frozen-before>` 需要 Nextflow26.10 与原生工具；固定版本 Minimap2 自带排序 SAMtools1.23.1，过滤/FASTQ 使用1.24。before-dir 是修复批次保留的三平台及旧 mapper 源码，不自动取当前 HEAD。

八个受控场景共53条trace（修复前31、修复后22），验证旧三平台均错误消费 stdout、修复后 map-ont/map-hifi 精确保留未匹配宿主的正反向 reads/DNA/非恒定质量值、不同宿主参考/无参考样本归属、全被过滤时明确 QC 失败。故障包装器实际调用原生 mapper 后故意退出7：旧模块被 sort 的0掩盖，现原失败码向下传播、无后续消费者或BAM发布。该故障是注入的退出码，不声称原生 mapper 自发崩溃。

`python3 -m unittest discover -s tests -p 'test_mock_*py' -v` 包含6个替身方法：SAMtools仅支持显式标记的未配对fixture，遵循 -0 并拒绝未建模的配对输入；Bowtie2遵循最后扩展名前插入 .1/.2、%替换和无扩展名命名。它仍然是短读段全部传递的接口 observer，不模拟宿主分类。宿主profile来源按实际暂存的配对reads/DNA/质量验证，不再只匹配clean文件名。

`tests/mock_e2e/run.py` 的 `--with-host-removal --host-minimap-prefix <2.30-prefix> --host-samtools-prefix <1.24-prefix> --long-input mixed` 让两样本使用不同宿主参考，另外四样本走无参考分支；ONT/HiFi/hybrid(OPERA)共496任务中仅18个宿主长读工具任务为原生，其余外部CLI为observer，R/Python真实执行。再验ONT全无参考144任务。FASTQ/BAM/POD5（HiFi不含POD5）输入为明确fixture，末端组装器输入逐记录核对，不是实际组装/检测效果验证。HybridSPAdes额外尝试因observer环境缺真实SPAdes计划解析依赖失败，保留原日志且不计通过；本批不认证该完整分支。共享定量三模式55原生任务另验。

未配对长读宿主过滤消费 `<id>.host_removed_other.fastq.gz`；全被过滤时终止，hybrid不自动改为短读单独组装。版本、阈值和预设保持不变。未进行镜像、远端执行器、nf-test框架或科学灵敏度/特异度基准；TT-001计数oracle问题仍开放。

### TETRA 256维数值、输入保护与阈值校准

用户确认采用标准TETRA并单独校准阈值。本地 `tests/test_tetra_math.py` 的8方法独立逐窗口计算；`test_sequence_similarity_link.py` 现11接口方法，低复杂度profile在零阈值也不得生成关联。`tests/run_tetra_sequence.py` 的两个原LINK_SEQUENCE任务使用锁定pUTI89/SCP1真实DNA作明确自匹配/碎片等控制，24配对分数、分类marker、输入不变和完整方法状态均核对；这是数值/接口控制，不是已知宿主准确率基准。

`tests/run_sequence_taxonomy_input.py --work-dir <fresh> --before-dir <frozen-before>` 3个原任务复现旧taxonomy.tsv重定向截断源文件（任务仍0），并验证当前单表及双域同名输入均不变、分类准确。only disposable fixtures用于反例。HOST_LINKING可选/重复键11任务和54R smoke另验。原nf-test no-MAG场景仍仅为空结果，未升级为阳性/框架认证；新native harness不等于nf-test JUnit。

所有比较保存在sequence_scores.tsv，method JSON明确tetra_markov256_v1与uncalibrated；0.7仍未校准。`bin/calibrate_sequence_threshold.py` 用具证据的显式标签和质粒/宿主组均隔离的calibration/holdout集合；7方法/3CLI控制只验证统计工具，人工0.8不得写回默认。完整数据约束、方法差异和待做真实宿主校准见 `docs/tool-audit/contracts/tetra-sequence-method.md`。TA-039仍ready/open；TA-040与新TA-058局部修复另记。

2026-10-22统计边界补验：`tests/run_statistics_eligibility.py` 以原生R/FastSpar1.0.0和明确计数fixture检查非空正例、0/1特征、全零、过滤后新零列及缺失生产者；13场景37条trace（含3预期失败），不能当作nf-test框架或真实ENA科学效果通过。`tests/run_statistics_cache.py` 只改变独立临时项目中的脚本/辅助库，检查resume失效条件；旧module+新helper反例用于修复过程回归，不冒充基线已有helper。原生共享定量三模式现为58任务，六个平台/空结果场景793任务中外部工具仍为observer。FastSpar固定1.0.0实际要求至少4个特征，过滤后样本数必须再次达标；历史coverage-only ENA表需按统一参考重映射产生整数raw_count。P4断言已加强有限指标、完整样本与实际执行分支，但nf-test launcher及完整真实P4尚未运行，TT-003仍open。详见 `results/tool-audit/20261022-statistics-eligibility/receipt.json`；旧段落TA-013/014/038未决为历史scope，当前状态以台账为准。

DESeq2 部署版本补验使用 `tests/run_deseq2_model.py --deseq-prefix <locked1.42-prefix> --python-prefix <3.12-prefix> --before-dir <frozen-before> --work-dir <new-dir>`，独立 `tests/deseq2_reference.R` 从宽矩阵调用官方 API，核对联合多组模型、逐对结果、受控强信号方向和数值；不复用生产导入/状态函数作为真值。新状态区分实际模型拟合和未拟合条件，合法全零不是“显著性为零”。`tests/run_statistics_input_names.py` 核对四节点输入源不变及同名输入/输出，旧 DESeq 输入改写对照明确使用允许的原生 1.52 栈，不冒充默认 1.42 镜像；只改写私有 fixture。`-resume` 案例使用独立项目会话，未变缓存与阈值改变重算分别检查。完整 nf-test/真实非空 ENA P4 与镜像尚未认证，TT-003 仍未关闭；主台账和最终 receipt 为准，早期环境准备/失败尝试不能当作模型通过。

### Platon当前原生验收（2026-10-24）

原P3文件保留plain与锁定上游gzip阳性，并检查14列、明确状态及子工具/worker无错误。生产参数仍为1.7 accuracy+meta；完整资源锁在 `tests/platon-native.lock.json`，Linux64环境锁在 `envs/platon-linux-64.lock`。本批native overlay实际执行两个用例，非Podman证明。独立输入传输测试现在必须显式提供 `AUTOPLASM_PLATON_PREFIX`、`AUTOPLASM_PLATON_NATIVE_DB`、`AUTOPLASM_PLATON_INTERFACE_FASTA`；缺少时明确skip，不再以观察替身或任意短序列宣称真实Platon通过。设置 `AUTOPLASM_PLATON_INTERFACE_ROOT` 可在指定目录保留任务记录。命令、JUnit及全部范围限制见 `results/tool-audit/20261024-platon-native/receipt.json`。

### PlasX完整自动注释验证（2026-10-24）

`nodes-detection-plasx.nf.test`实际运行生产两阶段：逐样本anvi’o7.1 COG2014/Pfam32及完整十组de novo家族，再用原模型评分。设置`AUTOPLASM_PLASX_ROOT`指向完整资源目录，包含primary/、anvio-primary-complete/、COG_2014/、Pfam_v32/、profiles/及原始系数文件；原始数据和模型锁在`tests/plasx-native.lock.json`，两阶段分别使用351包和63包Linux64显式锁。可用`tests/prepare_plasx_resources.py prepare --outdir <新资源目录> --anvio-prefix <351包环境> --cache <已有下载缓存>`重建全部公共资源；准备会运行原生索引程序，需要足够磁盘及进程通信权限。重建器返回的生产参数使用`sources/anvio`、`sources/plasx`及`model/`；本P3资源根目录采用上述审计布局，重建后需为同一完整资源设置对应目录/文件别名，不能省略资源。

必须使用提供生产配置的原生或Conda overlay，不再使用无依赖的Python容器冒充PlasX。P3断言同时检查两任务、三类注释、原生运行记录、样本状态域及标准库独立计数/logistic算术；不把本次自动输出更新成“独立生物真值”快照。`tests/run_plasx_native.py --workflow <有execution.json的冷运行目录> --source <官方源码> --model <原模型> --output <新核验目录>`可单独核对既有执行，`--prefix <原生环境>`另执行未修改官方predict对照；`--products`只验证产物，不能代替执行证据。整个组装0基因目前原生明确失败，排除支持；无COG/Pfam命中及未评分contig另行核验。

本批仍按receipt和JUnit决定验收，不能仅凭新增P3文件或资源准备成功宣称通过。更多范围、官方预计算表与当前自动注释的差异及失败尝试见`docs/tool-audit/contracts/plasx-native.md`。

## 固定的上游测试前置模块

`prerequisites/`保存8类测试专用helper，按各consumer在`modules.json`中的固定commit获取；24个代码/环境/metadata文件、原MIT许可和完整来源见`source-lock.json`。10个vendored suite的14处setup引用现在指向此目录，生产工具版本和模块登记保持不变。更新consumer后须同步核对这些来源。

`docs/tool-audit/scripts/check_vendored_prerequisites.py`检查literal路径、源文件Git blob和consumer版本。实际nf-test `--dryRun`只执行发现：它打印的PASSED不能算已执行测试。真实归档I/O另由`tests/run_upstream_prerequisites.py`对固定FASTA、匹配版本的工具prefix、meta和CRC错误传播检查；这不认证其他需要模型/数据库的P1用例。原HiFi下载模块使用master数据库，实际运行前需另外固定其数据身份。完整范围见`docs/tool-audit/contracts/vendored-prerequisites.md`。


### TA-091 目录资源续接（2026-10-26，候选）

当前目录资源输入使用缓存查找前的紧凑内容/布局身份，不再将目录 glob 列表逐文件 staging。`tests/run_resource_identity.py` 检查实际 Groovy 实现与独立 Python oracle；`tests/run_resource_consumers.py --work-dir <新目录>` 分别修改15个资源输入，在13个实际消费者上核验目标重算、其他任务缓存和还原。后者是明确的 stub/version/PHF CLI observer，不是分类器推理。

固定 anvi’o 主归档含13个 Git 子模块占位，原解包树中有3个断链。完整枚举明确拒绝该树，不跳过断链。资源准备器现按 `tests/anvio-submodules.lock.json` 的原提交、长度和SHA补齐全部13个子模块，并分别验证原1185个源码摘要和各子模块摘要。运行准备器的驱动 Python 需支持 `tarfile` 的 data filter（Python3.12+）；实际anvi’o工具继续使用原3.7环境，方法和数据库不变。已有原解包树可用 `python3 tests/prepare_anvio_submodules.py --source <原解包树> --archives <锁定归档缓存> --output <新的完整源码目录>` 生成完整副本，再设置生产 `--plasx_anvio_source`。PlasX P3可用 `AUTOPLASM_ANVIO_SOURCE` 覆盖其源码目录，其他资源仍由 `AUTOPLASM_PLASX_ROOT` 提供。

恢复控制绑定冷运行的精确 session UUID；并发驱动各用独立工作目录下的 `.nextflow/history`。运行名或未指明会话的 `-resume` 不能代替本轮实际任务状态断言。当前证据及尚未覆盖的隐式环境/模型以 `docs/tool-audit/contracts/resource-directory-cache.md` 和本轮receipt为准；TA-091未正式接受。
