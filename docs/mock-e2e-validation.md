# 端到端 mock 验证记录（2026-10-16）

> 历史快照：正文保留原日期的设计、发现与验证结论，不代表2026-10-31的全部当前状态。最新入口见[文档导航](README.md)、[平台路线](platform-workflows.md)及[实施状态](protocol-implementation-status-20261031.md)。

结论：修复后，Illumina、ONT、PacBio HiFi、hybrid 流程在外部工具 mock 条件下
均可从主入口运行到报告。
真实生信工具和数据库的端到端运行尚未验证，不能将本结果解释为真实分析可用性验收。

| 场景 | 结果 | 证据（相对仓库根目录） |
|---|---|---|
| 原代码、Nextflow 26 | 编译失败：局部闭包调用无法解析 | `results/mock-e2e/baseline/console.log` |
| 修正语法后 | geNomad 声明输出文件缺失 | `results/mock-e2e/run02/console.log` |
| 修正 geNomad 后 | 流程执行完成，但报告早于统计、缺失 diversity 标记；测试共识行数预期也需纠正为仅阳性行 | `results/mock-e2e/run03/out/report/report.md` |
| 正常阳性 | PASS，140 个任务全部 COMPLETED | `results/mock-e2e/positive/validation.json`、`trace.tsv` |
| 所有样本无质粒 | PASS，84 个任务全部 COMPLETED | `results/mock-e2e/empty/validation.json`、`trace.tsv` |
| Python 单元回归 | 38 项通过 | `python3 -m unittest discover -s tests -p 'test_*.py' -v` |
| 模块回归 | 7 个套件通过、2 个因缺少真实工具未运行 | 下表 |

| 模块套件 | 最终结果 | 日志（位于 `results/mock-e2e/`） |
|---|---|---|
| catalog / coabundance / host-routing / sequence-optional | 通过 | `module-regressions-fixed.log` |
| sequence | 修正测试脚本变量重名后通过 | `regression-sequence.log` |
| sample-ids | 改用 JSON 参数文件保留空字符串后通过 | `regression-sample-ids.log` |
| crispr-guard | 修正测试参数优先级后通过；启用未实现功能会明确拒绝 | `regression-crispr-guard-final.log` |
| longread-source | 未运行：缺 samtools | `module-regressions-fixed.log` |
| qc | 未运行：缺 fastqc、multiqc | `module-regressions-fixed.log` |

完整模块回归 `--suite all` 因失败/缺失依赖返回非零，不能计为整体通过。
修正后三个失败套件分别重跑通过；未把端到端测试中的 mock 命令放入这些
模块回归的 PATH。部分早期日志的 Java 字段显示 PATH 内的 Java 27，但 Nextflow
实际由 `JAVA_HOME` 指定 Java 21；日志函数已修正为优先读取同一 `JAVA_HOME`。

输入生成器：`tests/mock_e2e/generate.py`。测试入口：`tests/mock_e2e/run.py`。
完整说明及复现命令见 `tests/mock_e2e/README.md`。

运行时采用缓存的 `/tmp/nextflow`（26.10.0）、`JAVA_HOME` 指向 Java 21。
所有模拟命令仅在测试子进程 PATH 内生效，未安装或修改全局生信工具。
真实工具预检记录在 `results/mock-e2e/real-tool-preflight.json`；本机原始 PATH
缺少 fastp、geNomad、CoverM 等工具，也未提供数据库配置。

首轮只覆盖 Illumina 默认分支及额外 FastQC；以下为追加的平台测试。
报告扫描 publish 目录的异步发布和旧结果风险仍然存在；补充跨样本统计依赖
并不等于彻底解决报告的全部依赖问题。

## ONT、PacBio HiFi、hybrid 追加验证

2026-10-16，Nextflow 26.10.0、Java 21；所有场景均为 6 个样本，生产 `main.nf`
实际执行，外部命令为 mock。下列 **10 个新增场景、1,340 个任务全部通过**，
每个场景均校验任务数量、样本 ID、丰度数值、共识、catalog、统计和报告产物。
每项证据为 `results/mock-e2e/<目录>/validation.json` 和同目录 `trace.tsv`。
汇总见 `results/mock-e2e/multi-platform-summary.json`。改动后的 Illumina
回归另完成 **140/140** 个任务（`illumina-regression`），所有 trace 退出码均为 0。

| 平台 / 场景 | 完成任务 | 结果 | 目录 |
|---|---:|---|---|
| ONT / FASTQ 阳性 | 134 | PASS | `ont-positive-fixed` |
| ONT / 无质粒 | 78 | PASS | `ont-empty` |
| ONT / POD5、BAM、FASTQ 混合输入 | 138 | PASS | `ont-mixed-input` |
| HiFi / FASTQ 阳性 | 127 | PASS | `pacbio_hifi-positive` |
| HiFi / 无质粒 | 71 | PASS | `pacbio_hifi-empty` |
| HiFi / BAM、FASTQ 混合输入 | 130 | PASS | `pacbio_hifi-mixed-input` |
| hybrid / OPERA-MS 阳性 | 183 | PASS | `hybrid-positive-fixed` |
| hybrid / 无质粒 | 109 | PASS | `hybrid-empty` |
| hybrid / POD5、BAM、FASTQ 混合输入 | 187 | PASS | `hybrid-mixed-input` |
| hybrid / hybridSPAdes 替代组装器 | 183 | PASS | `hybrid-spades` |

混合输入场景同时提供低优先级输入，检查 ONT/hybrid 的 POD5 > BAM > FASTQ
以及 HiFi 的 BAM > FASTQ 选择规则。BAM/POD5 文件为标记为 mock 的 JSON，
只验证路由与任务依赖，不验证真实二进制格式解码或 basecalling。

长读与短读给定不同的 mock 覆盖度：长读为短读两倍，hybrid contig 合并为
两路之和；hybrid 质粒 short/long 表各有 6 份，跨样本表仅使用 short 数值。
同时验证 minimap2 preset、两路 BAM 均参与 merge、宿主 profile 每样本仅一份且
hybrid 仅使用短读、NanoPlot 6 个样本输出均进入 MultiQC。

追加测试发现并处理：

1. `ont-baseline`、`hybrid-baseline` 实际触发 Nextflow `input file name collision`：
   多个 NanoPlot HTML 同名。现在向 MultiQC 传递带样本名的完整目录。
2. `pacbio_hifi-baseline` 的接口 mock 拒绝了 `hifiadapterfilt.sh -t 1 ../long.fastq.gz`。
   依据 [HiFiAdapterFilt 官方接口](https://github.com/sheinasim-USDA/HiFiAdapterFilt)，
   现在把输入链接放入当前目录，使用 `-p` 指定前缀。
3. 核对 [hifiasm-meta 官方说明](https://github.com/xfengnefx/hifiasm-meta) 与
   [Bioconda recipe](https://github.com/bioconda/bioconda-recipes/blob/master/recipes/hifiasm_meta/meta.yaml)
   后，将组装命令和依赖统一为 `hifiasm_meta`，移除标准 `hifiasm` 的错误替代。
   此项由源码/文档核对发现；没有宣称执行过真实组装器。
4. `ont-positive`、`hybrid-positive` 失败来自 mock 检查器未跟随目录符号链接，
   并非新的生产流程错误。修正测试检查器后在 `*-positive-fixed` 全新目录复跑通过。

本轮仍未覆盖 assembly、宿主去除、medaka、MAG/binning、宿主关联、DESeq2、
FastSpar 等可选分支。HiFi 当前工作流没有接入 MultiQC，未计入成功任务数。
新增 Conda 依赖尚未实际安装；真实工具、数据库及算法准确性仍需独立验收。
