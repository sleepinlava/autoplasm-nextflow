# 分级测试集合

在仓库根目录运行。上游固定版本、许可和适配说明见 [UPSTREAM.md](UPSTREAM.md)。

| 级别 | 测试目标 | 判定 |
| --- | --- | --- |
| P0 | 5 个输入错误：重复 ID、非法 ID、缺失 mate、缺失数据库、未实现的 CRISPR | 必须明确失败，并且没有成功执行分析任务 |
| P1 | 现有 nf-core fastp、fastqc、samtools/sort、megahit 完整测试 | 保留上游断言及快照；分别统计真实运行与 stub |
| P2 | Illumina、assembly、ONT、hybrid、HiFi 核心流程 | 真实工具运行成功，trace 无失败；共识、结构、组装评估、丰度和报告符合契约 |

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

本次使用 Java 21 与 Nextflow 26.10.0。将相应 `java`、`nextflow` 和原生程序加入 PATH，
并设置 `JAVA_HOME`。nf-test 运行时安装示例：

```bash
mkdir -p results/nf-test/runtime
curl -fL https://github.com/askimed/nf-test/releases/download/v0.9.5/nf-test-0.9.5.tar.gz \
  -o results/nf-test/runtime/nf-test.tar.gz
echo 'b7679eb90cdc9642bfa89e9634db02ce6e699de53ad35ef0e2f4847634fc1641  results/nf-test/runtime/nf-test.tar.gz' | sha256sum -c -
tar -xzf results/nf-test/runtime/nf-test.tar.gz -C results/nf-test/runtime
export NFT_BIN="$PWD/results/nf-test/runtime/nf-test"
export NXF_VER=26.10.0
```

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
