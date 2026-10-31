# 历史开发验证记录

从根 README 迁移的原日期记录；不作为当前版本的完整验收结论。最新结果见[实施状态](protocol-implementation-status-20261031.md)与[开发指南](development.md)。

## 验证状态

以下分日期记录为既有历史记录，不代表本次框架审查重跑了全部测试。
本次检查及未执行项见 [审查记录](fact-reliability-audit.md#本次验证)。
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
[`tests/mock_e2e/README.md`](../tests/mock_e2e/README.md)，失败基线与修复记录见
[`docs/mock-e2e-validation.md`](../docs/mock-e2e-validation.md)。

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
