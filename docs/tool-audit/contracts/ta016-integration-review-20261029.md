Takeaway: 当前报告来源增量的集成复核发现并修复五类问题，四条原生验证路径已到达报告终点，TA-016仍未完成。

本轮接续工作区已有的报告来源候选，检查其进入子工作流和最终报告后的行为。真实Nextflow执行确认了文件名、版本探针、共享参考身份和空参考样本域四类集成失败，报告反例另确认了cohort信息丢失及校验不足。修复后，嵌套别名、20样本统计链、4样本共享参考链和3样本空参考链均生成报告。逐份检查确认报告中的28条来源记录与各自产生任务的脚本字节、SHA和样本域一致。统计数据是技术控制，共享参考链使用既有细菌/质粒DNA和模拟reads，不能据此验收真实shotgun科学效果。下一步应检查比较基因组队列身份及其报告接线，并继续现有资源身份和真实数据验收。

## Scientific context and question

目标是承接现有审查及外部编辑器完成的增量，验证细菌/质粒流水线的来源记录能否在真实嵌套调用、缓存和报告中保持正确。以当前代码、既有receipt和实际任务为依据，没有推定每一处修改的作者。遵守`user-constraints.md`的不使用病毒元素要求；未下载数据、安装模型或启动远程/收费计算。

## Question, lifecycle, and endpoint

实际使用本地Nextflow 26.10.0、原生Python/R、FastSpar 1.0.0及既有Bowtie2/CoverM环境。所有本轮启动的验证任务均已终态；失败尝试保留，缓存任务不另算原生执行。没有创建NGS Workbench注册运行；Rosalind/NGS技能用于证据审查，BioNeMo加速不适用本轮契约验证。

证据根目录：`results/tool-audit/20261029-cohort-integration-review/`。来源清单、trace统计和限制见[integration-review.json](../evidence/20261029-ta016-integration-review.json)。原正式接受清单和旧候选receipt均未替换。

## Key findings

| 问题 | 已观察反例 | 本轮修复 |
| --- | --- | --- |
| 嵌套/别名文件名不一致 | NETWORK_ALIAS生成固定文件，eval却查找带命名空间的文件，任务失败 | 8个cross_sample模块的校验路径与声明输出保持一致；MERGE_ABUNDANCE本轮仅静态修正 |
| cohort身份校验及信息保留 | 原20测试通过；扩展23测试出现13个失败子断言及2个错误；重复/数值/对象成员和缺失身份可被接受，输出缺少成员 | 验证字符串数组、非空唯一已知成员、与process一致的身份；JSON和methods保留成员；允许合法过滤子集 |
| FastSpar版本探针为空 | 6个统计任务完成，REPORT因空stdout失败；CLI实际将版本写到stderr | 探针显式`2>&1`，报告保留实际输出及探针命令 |
| 共享参考被当成样本 | 19个前置任务完成，REPORT拒绝不在样本表中的`shared_reference` | 建索引meta携带catalogue输入的cohort样本集合，保留原参考ID和科学参数 |
| 全局空参考丢失cohort | 2个生产者完成，REPORT拒绝空样本域；没有映射任务但存在完整样本状态 | SHARED_ABUNDANCE_TABLES从实际`quantification/sample_states.tsv`提取成员 |

| 验证路径 | 最终trace | 独立报告复核 |
| --- | --- | --- |
| 嵌套NETWORK_ALIAS→REPORT | 2 COMPLETED | 3样本，1条cohort来源 |
| 生产CROSS_SAMPLE | 2 COMPLETED + 5 CACHED；此前6分析任务已完成 | 20样本、8特征，6条cohort来源；DESeq2实际拟合completed，FastSpar非空输出 |
| 生产共享参考→宿主链接/跨样本→REPORT | 最终6 COMPLETED + 14 CACHED；首轮修复后19 COMPLETED + 1 CACHED | 4样本、19条来源，其中7条cohort；三份量化/状态TSV与既有坐标对照结果逐字节一致 |
| 空参考共享量化→REPORT | 2 COMPLETED + 1 CACHED | 3个零结果样本、2条cohort来源；无映射任务 |

`tests/check_report_runtime_provenance.py`读取最终manifest暂存的来源文件，解析实际路径，与同任务`.command.sh`逐字节比较，再核对报告JSON脚本/SHA/探针/样本域及methods和HTML中的SHA。REPORT自身命令副本也与原件一致。23项报告单元及15项共享参考/量化单元通过。

## Interpretation

单节点完成或编译通过不足以接受这些增量：命名空间、跨样本身份、stderr和空任务通道都影响集成。本轮使用生产子工作流和实际报告消费者揭示并修复这些问题，保留`001`、`1`、`NA`字符串样本身份。科学参数、序列处理和计数规则未更改；共享链三份量化表与既有证据一致。

## Artifacts

- Results：证据目录中`cross-sample/out/11_diversity/`的R统计/DESeq2输出、`cross-sample/out/12_network/`的FastSpar矩阵及`shared/out/tables/`的量化/状态表，均为技术控制。
- QC and visual reports：四条路径的`out/report/`或`after/out/report/`中实际HTML/JSON；空参考报告保留三个零结果样本。
- Provenance：各轮trace、日志、任务脚本；`report-checks.json`记录四个实际REPORT workdir；`unit-before.log`/`unit-after.log`保留红绿对照，`shared-units.log`记录15项回归。
- Model synthesis：本文及机器可读审查证据；不是新科学分析或Workbench注册执行回执。

## Limitations and blockers

TA-016保持`in_progress`。刷新台账确认111项问题、5项未决；旧摘要未纳入2026-10-28已登记但未接受的TA-097。28条记录来自四条技术验证路径，不能当成28个独立生物学验证或完整生产者覆盖。20样本合成计数不能完成TT-003真实shotgun验收。MERGE_ABUNDANCE文件名修正未独立运行。初版harness因closure变量漏写`def`编译失败，保留在`before.log`，不计生产反例。

静态检查还发现COMPARATIVE将MMSEQS2的`plasmid_catalog`作为普通样本meta传给报告，存在类似共享参考问题，尚未动态验证。catalog_prepare自来源仍作为普通evidence传输，尚未证明完整runtime_command嵌入。完整数据库/模型/环境、TA-091、TA-097、TA-031、TT-003、M0–M4及真实平台验收继续开放。

## Recommended next step

2026-10-30接续：本文发现的COMPARATIVE伪样本身份和目录来源已完成实际修复/检验，见[比较分支审查](comparative-provenance-review-20261030.md)；TA-097另有[有界接受](spades-completion-review-20261030.md)。下段保留本轮结束时的计划。

先动态验证COMPARATIVE的catalogue来源和MMSEQS2队列身份，再检查尚只有编译证据的生产者及完整报告覆盖；按严重度继续TA-091资源身份、TA-097警告完成标记审查、TA-031完整r232和TT-003适用真实shotgun验证。不得把局部通过升级为全流水线放行。
