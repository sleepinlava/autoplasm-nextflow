# 分级测试集合

在仓库根目录运行。上游固定版本、许可和适配说明见 [UPSTREAM.md](UPSTREAM.md)。
本次配置对齐的验证结果见 [PROFILE-RESULTS.md](PROFILE-RESULTS.md)。

| 级别 | 测试目标 | 判定 |
| --- | --- | --- |
| P0 | 11 个输入错误：重复/非法 ID、缺失 mate、必需数据库、未实现的 CRISPR、非法平台/组装器及不兼容工具组合 | 必须明确失败，并且没有成功执行分析任务 |
| P1 | 现有 nf-core fastp、fastqc、samtools/sort、megahit 完整测试 | 保留上游断言及快照；分别统计真实运行与 stub |
| P2 | Illumina、assembly、ONT、hybrid、HiFi 核心流程 | 真实工具运行成功，trace 无失败；共识、结构、组装评估、丰度和报告符合契约 |
| P3 | 单节点真实小数据（`nodes-*.nf.test`，详见 [COVERAGE.md](COVERAGE.md)） | process/workflow 成功 + 输出契约断言；断言用上游固定事实 |
| P4 | ENA 真实多样本（PRJNA848809，3 感染 vs 3 对照）跨样本统计 | 全链路到多样性/差异/DESeq2/网络/报告，分组来自真实样本元数据 |

P0/P2 使用 `P0`/`P2` tag，P2 还可按平台 tag 筛选。P1 直接选择已有文件，
没有为了添加 tag 修改上游测试。缺失程序、数据库或网络导致的失败必须报告为环境阻塞，
不能改成 skip、更新快照或用 stub 的成功替代。`--dry-run` 只说明用例可被发现。

## uv 隔离环境

```bash
export UV_CACHE_DIR=/tmp/autoplasm-uv-cache
uv sync --project tests/nf-test --locked
# P2 的 Python 工具；含 geNomad 的 TensorFlow 依赖，首次下载较大。
uv sync --project tests/nf-test --locked --extra pipeline
```

Python 固定为 3.12，环境位于本目录 `.venv/`；不要使用 `--active`，以免使用外部环境。
`uv.lock` 锁定完整依赖解析。`--no-sync` 的执行命令保留已经安装的可选依赖。

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

# ENA 真实多样本（PRJNA848809，d6 期 3 感染 vs 3 对照，官方 md5 锁定）
uv run --project tests/nf-test --locked --no-sync python tests/nf-test/prepare_data.py \
  --dataset ena-multi --outdir results/nf-test/ena-multi
export ENA_TEST_DATA="$PWD/results/nf-test/ena-multi"
```

需要数据库的节点（platon 等）：`tests/nf-test/download_databases.sh` 下载官方固定版本
数据库到 `results/nf-test/databases/` 并在 `manifest.txt` 记录 size+sha256；
运行时导出 `AUTOPLASM_DB="$PWD/results/nf-test/databases"`。

P3 单节点套件按域拆分（一个文件一个 suite 块；nf-test 不读取同文件后续块）：

```bash
. tests/nf-test/env.sh
# native（R 脚本节点）
"$NFT_BIN" test -c tests/nf-test.config tests/nf-test/nodes-comparative-catalog.nf.test --ci
# podman（容器节点）
"$NFT_BIN" test -c tests/nf-test.config tests/nf-test/nodes-detection-platon.nf.test \
  --profile podman --ci --junitxml results/nf-test/w3-platon.xml --log results/nf-test/w3-platon.log
```

P4（ENA 跨样本全链路；quast 阈值为真实低生物量样本下调到 200，见 ena.config 注释）：

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
