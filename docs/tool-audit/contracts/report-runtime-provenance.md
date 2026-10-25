# 报告的实际任务来源（TA-016，进行中）

2026-10-25。当前只完成共识、结构判断和报告消费者的第一批实现，TA-016继续开放。工作证据：`results/tool-audit/20261025-report-provenance/`。此前九项局部接受receipt及718来源清单保持冻结；本批是后续候选增量。

## 当前实现

`PLASMID_CONSENSUS`、`PLASMID_STRUCTURE`在实际Bash脚本中从`BASH_SOURCE[0]`复制完整引擎脚本；Nextflow随后在同一任务环境实际探测`Rscript --version`，并对脚本副本执行SHA256。原生`eval`的值保留在原任务缓存中。`task_provenance`输出携带实际process、原meta、命令文件、探测命令/结果和原任务校验值。

`reportEvidence`将这一个显式输出变为带文件输入的`runtime_command`事件。图节点分析保留内部analysis ID，并从原meta恢复样本ID。其他输出的完成/版本证据语义保持。报告以deep内容缓存接收命令文件，先核对原任务SHA再渲染；缺文件、重复身份、不完整探测或校验不符均失败，不静默删除记录。

完整脚本字节、SHA、实际探测及原始/分析样本身份进入`report_data.json`；`methods.md`和HTML展示来源、SHA和探测结果。显式说明这些是原任务记录，resume可复用旧任务；不把缓存输出称作新执行。无RMarkdown时的HTML也包含相同方法信息。`r-digest`列为直接依赖，当前实际版本0.6.39；它只用于来源校验，不改变科学算法。

Nextflow的[eval输出](https://docs.seqera.io/nextflow/reference/process/inputs-outputs)在任务环境中执行；[官方调试说明](https://training.seqera.io/latest/side_quests/debugging/)说明`.command.sh`为执行脚本。本批以实际脚本字节/原生探测/缓存对照为依据，不以文档替代运行证明。没有收集全量环境变量或复制含环境配置的`.command.run`。

## 已执行验证

- `prototype-validation.json`：正常目录及scratch的脚本副本与实际`.command.sh`逐字节一致；原生Bash版本与直接调用一致。冷运行3完成、原UUID恢复3缓存；故意子程序37失败且收集器不运行。原型另测topic机制，生产仍通过既有显式report事件连接。
- `native-runtime-v3/run.json`：五个实际R任务加一个RMarkdown报告，共6COMPLETED；含独立图节点身份及scratch场景。当前17个报告单元方法通过。完整源DNA、样本统计、五份脚本字节/SHA、直接R版本和HTML/方法摘要独立核对。
- 同一原UUID恢复6CACHED。仅在私有task命令副本上作等长、保持mtime的样本参数篡改，五个科学任务保持缓存，REPORT实际失败并指出校验不符；新输出目录无报告。还原后6CACHED，报告数据SHA恢复原值，全部科学FASTA/TSV未改变。
- `existing-report-controls-v3/run.json`：旧的延迟输出、旧发布目录忽略、原样恢复、输入改变恢复、关闭及失败控制继续通过。5场景8trace=4完成/3缓存/1预期失败，外部延迟写入器是明确控制，不是生物工具。
- `consensus-regression-v2/run.json`：五组原有共识/结构正、负、空和额外分类输入共10原生R完成；退役来源、外来ID、空序列三例各实际退出2且不发布。只有模块元数据新增，科学输入/阈值/算法未改。
- `gplas-current-r-metadata/run.json`：原完整图节点分支精确UUID恢复，当前两个R节点重跑、四任务缓存；完整原图/最终DNA/27成员/22候选分箱的独立检查通过。缓存不是新的分类或科学样本。

失败尝试保留：首版独立检查器误设FASTA为单行，实际输出为合法换行，随后保留ID/全部DNA断言并按FASTA规则读入；原检查器与6任务记录仍在。两次本地驱动器漏设Nextflow路径、0任务的启动错误另列，不归为仓库科学错误。v2的真实运行先于HTML fallback补充，最终当前证据使用v3；不覆写旧记录。

## 仍需完成

1. 逐个生产者接入实际命令和原生版本记录；当前只有两个R生产者，旧版本输出仍明确可能是静态声明。cohort任务需记录完整样本域，不能套用单样本meta。
2. 为实际数据库/模型/固定程序资源保存完整文件身份，关联到真正消费它们的任务；验证缓存及资源改变情形。不能用目录名、版本文本或事后包安装代替资源内容身份。
3. 记录实际执行环境/容器digest及完整依赖来源，区分声明tag、真实探测与未知项。当前没有OCI、远程或AWS认证。
4. 完成所有消费者、报告自身来源及相关原生/框架/端到端回归后，再对TA-016统一复核。当前原生控制不是分类性能或独立生物学真值；不缩小原验收要求。
