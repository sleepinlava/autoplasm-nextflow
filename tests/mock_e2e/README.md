# 最小端到端 mock 测试

实际执行生产入口 `main.nf`，使用真实 Nextflow 调度、生产模块中的 shell
脚本及仓库 `bin/` Python 实现。仅在本次子进程的 PATH 中替换外部生信命令。
这不是 `-stub-run`，也不是生物学准确性或真实软件安装验收。

## 数据

固定种子 `20261016`；6 个样本，两组各 3 个，满足默认差异分析重复数。
样本名包含点号、双下划线、连字符。每个样本包含一条 4 kb 模拟质粒和一条
12 kb 模拟染色体的双端 FASTQ（150 bp、350 bp 插入片段），附组装 FASTA
和长读 FASTQ。共 7,798 对短读，输入约 614 KiB。

序列为随机合成 DNA；**真实 geNomad 不保证将其识别为质粒**。本测试由 mock
geNomad 给出预设阳性/阴性结果，mock CoverM 给出已知丰度，检验后续传递。
mock 比对文件是测试占位内容，不是可用于其他软件的 SAM/BAM。
每个样本附 40 条 2 kb 长读。`--long-input mixed` 会加入明确标识为 mock 的
BAM/POD5 JSON 占位文件，以验证输入路由；这些文件不能交给真实 samtools/Dorado。

## 运行

需要 Python 3、Nextflow 26 和 Nextflow 支持的 Java。无需安装生信软件或下载数据库。
在仓库根目录执行；输出目录必须尚不存在，避免旧结果污染：

```bash
python3 tests/mock_e2e/run.py --outdir results/mock-positive
python3 tests/mock_e2e/run.py --outdir results/mock-empty --empty-plasmids
```

平台参数为 `--platform illumina|ont|pacbio_hifi|hybrid`，默认 `illumina`。
例如（同样要求每次使用全新目录）：

```bash
python3 tests/mock_e2e/run.py --platform ont --outdir results/mock-ont
python3 tests/mock_e2e/run.py --platform pacbio_hifi --outdir results/mock-hifi
python3 tests/mock_e2e/run.py --platform hybrid --outdir results/mock-hybrid
python3 tests/mock_e2e/run.py --platform hybrid --hybrid-assembler hybridspades --outdir results/mock-spades
python3 tests/mock_e2e/run.py --platform ont --long-input mixed --outdir results/mock-ont-inputs
```

`--empty-plasmids` 适用于以上四个平台。长读来源可选 `fastq`（默认）、`bam`、
`pod5`、`mixed`；HiFi 不接受 POD5，Illumina 不接受长读来源切换。
ONT/hybrid mixed 包含两份 POD5、两份 BAM、两份 FASTQ；HiFi mixed 为三份 BAM、
三份 FASTQ。较高优先级输入存在时仍保留低优先级输入，检查是否重复处理。

Nextflow 不在 PATH 时可指定 `--nextflow /path/to/nextflow`。
本机验证使用以下环境设置（路径只适用于本机）：

```bash
export JAVA_HOME=/home/sleepinlava/.local/share/mise/installs/java/21.0.12+101.0.LTS
export NXF_VER=26.10.0
export NXF_OFFLINE=true
python3 tests/mock_e2e/run.py --nextflow /tmp/nextflow --outdir results/mock-positive-new
```

只生成输入、不运行流程：

```bash
python3 tests/mock_e2e/generate.py --outdir data/mock-input
```

每次运行保留 `fixture/`、`params.json`、`command.json`、`console.log`、
`nextflow.log`、`trace.tsv`、`work/`、`out/` 和 `validation.json`。
各外部命令在工作目录写 `mock-<command>.json` 标识其替身身份。
缺少 Nextflow、进程失败或断言失败均返回非零退出码。

## 检查内容与覆盖边界

- Illumina、ONT、PacBio HiFi、hybrid 默认工具链；短读额外开启 raw/clean FastQC。
- hybrid 覆盖默认 OPERA-MS 和替代 hybridSPAdes，生产主入口完整执行。
- 校验每类进程数量和 `COMPLETED` 状态，不将跳过、缓存或空跑计为通过。
- 校验 12 行 contig 丰度、6 行质粒丰度（空场景 0 行）及逐样本精确数值。
- 校验共识、带样本前缀的 catalog、12 行多样性指标、2 行差异结果、报告样本数。
- 空质粒时跳过分型、注释、质粒定量和 catalog，但保留全样本报告和空丰度表。
- 长读 minimap2 检查 ONT/hybrid 使用 `map-ont`，HiFi 使用 `map-hifi`。
- 长读丰度设为短读的两倍；hybrid contig 合并值为两路之和，质粒保留两路表，
  跨样本质粒表须使用短读值。merge 命令检查两路 BAM 实际进入合并。
- 各平台宿主 profile 每样本一份；hybrid 必须只使用短读输入。
- ONT/hybrid MultiQC 暂存目录必须保留全部 6 份 NanoPlot 报告。

未覆盖 assembly 平台、其他短读组装器、宿主去除、medaka、MAG、binning、
宿主关联、DESeq2 和网络分支；未验证真实外部工具运行、数据库、分类性能及
新增 hifiasm_meta Conda 环境的实际安装。HiFi 生产分支当前没有接入 MultiQC，
不会将该任务计为已验证。默认未启用的可选分析不计入通过的任务数。

报告仍扫描 publish 目录。此次补上跨样本统计完成依赖，但其他可选分支的
等待依赖、异步发布和复用旧 outdir 的风险尚未彻底解决；测试强制使用新目录。

## 2026-10-16 实测

追加平台场景全部通过（数字为完成任务数）：

| 平台 | 默认 FASTQ 阳性 | 无质粒 | 混合输入 |
|---|---:|---:|---:|
| ONT | 134 | 78 | 138 |
| PacBio HiFi | 127 | 71 | 130 |
| hybrid / OPERA-MS | 183 | 109 | 187 |

hybridSPAdes 阳性场景另通过 183 个任务；合计 10 个新增场景、1,340 个任务。

Nextflow 26.10.0，Java 21；Illumina 正常场景 **140/140**、空质粒场景 **84/84**，
全部产物断言通过。现有 Python 单元回归 **38/38**。
原有模块回归最终 **7 个套件通过**；真实 QC 和长读来源套件因缺少
FastQC/MultiQC、samtools 未运行，未计为通过。

本次测试定位并修复：

1. Nextflow 26 严格语法无法解析局部闭包的隐式调用，改为 `.call(...)`。
2. geNomad 输出目录改名后内部文件仍沿用组装前缀，导致声明产物缺失；
   现在将需要的三个文件复制到样本命名路径，并保留原始输出目录。
   输出约定依据 [geNomad 官方文档](https://portal.nersc.gov/genomad/quickstart.html)。
3. REPORT 未等待跨样本统计，实测报告错误标记 `11_diversity` 缺失；
   现在等待已启用的统计输出。
4. 原有模块回归工具不识别 Nextflow 的多行版本 banner，已修正解析；
   同时修正测试脚本变量重名、空字符串参数传递、CRISPR 测试参数优先级，
   及 Java 版本日志与实际 `JAVA_HOME` 不一致的问题。
5. ONT/hybrid 多个同名 NanoPlot HTML 导致 MultiQC 暂存冲突，改为按样本传递
   完整 NanoPlot 输出目录。
6. HiFiAdapterFilt 改为在含输入链接的工作目录中通过 `-p` 选择文件，参见
   [官方用法](https://github.com/sheinasim-USDA/HiFiAdapterFilt)。
7. HiFi 组装命令及 Conda 依赖统一为独立的 `hifiasm_meta`，参见
   [官方说明](https://github.com/xfengnefx/hifiasm-meta)，不再把标准 hifiasm
   当作同一工具。后者默认图文件名也与模块预期不同。

失败基线及成功结果保留在仓库 `results/mock-e2e/`，详见
`docs/mock-e2e-validation.md`。
