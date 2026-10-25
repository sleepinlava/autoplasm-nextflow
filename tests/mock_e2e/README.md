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
geNomad 给出预设阳性/阴性结果。六个样本的12条DNA均不同，本地contig ID仍重叠，
用于检测把不同序列误当同一特征的错误。mock比对器只做精确匹配，并将实际read ID、
DNA摘要、参考序列、坐标和方向写入JSON；mock CoverM据这些匹配计算计数、覆盖与丰度，
不再根据输出文件名制造预期值。JSON不是可用于其他软件的SAM/BAM，也不代表原生比对效果。
每个样本附 40 条 2 kb 长读。`--long-input mixed` 会加入明确标识为 mock 的
BAM/POD5 JSON 占位文件，以验证输入路由；这些文件不能交给真实 samtools/Dorado。

## 运行

需要 Python 3、Nextflow 26 和 Nextflow 支持的 Java。无需安装生信软件或下载数据库。
在仓库根目录执行；输出目录必须尚不存在，避免旧结果污染：

```bash
python3 tests/mock_e2e/run.py --outdir results/mock-positive
python3 tests/mock_e2e/run.py --outdir results/mock-empty --empty-plasmids
```

平台参数为 `--platform illumina|ont|pacbio_hifi|hybrid|assembly`，默认 `illumina`。
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
- hybrid可选择OPERA-MS或hybridSPAdes；支持选项不等于两种实现都已有本轮完整运行证据。
- 校验实际trace中的每类进程数量、退出0及COMPLETED/CACHED状态；缓存另记，不计作新执行。
- 统一参考目录含12条不同DNA特征，跨六个样本完整重映射，产生72行contig丰度及36行质粒丰度（空场景0行）。
- 逐项核对read来源、实际计数/覆盖/丰度、参考DNA摘要、共识DNA、统计特征域与报告样本数。
- 空质粒时跳过分型、注释、质粒定量和 catalog，但保留全样本报告和空丰度表。
- 长读 minimap2 检查 ONT/hybrid 使用 `map-ont`，HiFi 使用 `map-hifi`。
- 丰度由实际匹配的read数和碱基数决定，不能预设固定倍数；hybrid合并两路匹配，
  质粒保留两路表，跨样本质粒表使用短读值。merge检查两路数据、参考身份及重复read。
- 各平台宿主 profile 每样本一份；hybrid 必须只使用短读输入。
- ONT/hybrid MultiQC 暂存目录必须保留全部 6 份 NanoPlot 报告。

本轮五场景为Illumina阳性160任务、ONT空91、HiFi mixed137、assembly63、
hybrid宿主去除201，共652条当前trace，含明确记录的缓存；无样本丢失。
hybrid中6个长读宿主任务使用真实Minimap2/SAMtools，逐read核对保留结果；
短读宿主过滤仍是传递全部成对reads的命名观察替身，不能宣称真实去宿主。
9项来源反例单元方法检查换reads、换index、混合mates、到达顺序、修改参考及过期任务证据。
保留的失败/中断尝试另列，重放和只读重新核验不增加实际成功任务数。

未验证其他短读组装器、medaka、MAG、binning、宿主关联、DESeq2和网络等可选分支；
未验证全部真实外部工具运行、数据库、分类性能及
新增 hifiasm_meta Conda 环境的实际安装。HiFi 生产分支当前没有接入 MultiQC，
不会将该任务计为已验证。默认未启用的可选分析不计入通过的任务数。

报告读取显式传入的本轮产物，测试仍强制新输出目录。验证器仅读取当前trace对应的
工作目录，过期尝试不能弥补本轮缺失的来源证据。详见docs/tool-audit/contracts/mock-provenance.md。

## 2026-10-16 实测

以下为历史结果，不能作为当前来源/计数/通过状态；本轮2026-10-24记录见上述契约及对应receipt。

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

SPAdes 外部命令 observer 只提供组装 FASTA 等本测试所需接口，不再写入伪 FASTG；它没有实际执行计划与最终迭代来源，不能通过真实图来源校验。Recycler/gplas 图路径由独立原生测试验证；本 mock 不认证图分箱。
