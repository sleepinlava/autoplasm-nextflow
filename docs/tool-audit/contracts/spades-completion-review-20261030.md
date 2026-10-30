Takeaway: SPAdes 4.1.0正常带警告完成的图来源验证已通过，TA-097仅按执行完成判定范围接受，警告不代表组装质量合格。

本轮独立复核了现有SPAdes完成标记候选修复。固定版本源码明确区分正常带警告完成和异常带警告结束，旧守卫会拒绝前者。当前原生minigut任务完成，保留的真实无警告K33组装也通过了同一来源验证。新增反例发现候选实现可能采用较早的成功标记，并把状态横幅和重复摘要算作警告，现已修复。完整图、最终复制计划、K配置与日志身份继续受原有检查约束，警告原文被保留。该结论只接受执行完成判定，不接受警告的生物学影响或完整组装效果。

## Scientific context and question

沿用已有minigut读段和已完成的SPAdes官方E. coli K33技术夹具，不下载新数据或模型，不运行病毒功能。任务是判断真实完成的SPAdes图能否正确进入下游，保留错误/警告的可追溯性；不是比较组装算法性能。旧台账“没有真实运行通过严格标记”的概括不准确：保留的真实K33无警告产物通过，已据此更正当前验收描述。

## Question, lifecycle, and endpoint

证据目录沿用`results/tool-audit/20261029-ta097-review/`，有界验收日期为2026-10-30。[验收receipt](../../../results/tool-audit/20261029-ta097-review/receipt.json)绑定当前生产helper、SPADES模块、测试、固定上游源码与原始结果SHA。第一次沙箱运行因Python多进程绑定本地socket被拒绝而失败；经过工具批准的同输入原生重跑COMPLETED/0。两个尝试都保留，未把环境失败解释为组装质量失败。

## Key findings

- 固定4.1.0的`spades.py`与`support.log_warnings`将正常完成输出为`finished.`或`finished WITH WARNINGS!`；异常路径另有`finished abnormally and WITH WARNINGS!`。三种标记不能混用。
- 当前实现按最后一次可见启动和最后一个终态标记判定，要求完整行与K阶段、Copy files、终态的先后顺序，拒绝后续异常、未完成新启动及伪造后缀。14项单元方法通过；修复前新增反例有7个失败断言。
- 新原生SPADES任务的暂存helper与当前源文件、命令副本与`.command.sh`均逐字节一致；最终K55来源链通过，实际下游图读取器接受290个正向节点。
- 10个CLI对照：冻结旧helper拒绝同一带警告真实产物；当前接受真实带警告和真实无警告产物；7个独立日志反例正确拒绝，无成功来源JSON。原图/计划/配置/日志字节未改动。
- 当前原生日志有2条实际警告，分别由不同K阶段发出，同内容在最终摘要重复一次。旧候选的4计数混入横幅/摘要；现记录2个发出事件及完整原文，`warning_count_unit=emitted_lines_excluding_summary`。不按“不同警告类型”计数。
- 10项Recycler图参考单元回归通过。新字段不改变原schema、K和图SHA约束。

## Interpretation

接受带警告的正常执行避免把上游允许的完成状态误判为崩溃。日志中的“Failed to determine erroneous kmer threshold. Threshold set to: 0”仍是需要科学解释的警告，不被改成质量通过。来源守卫采用记录策略：保留所有发出的警告，包括未知内容，不对警告做隐式白名单或质量批准。目录名、版本字符串或单一标记都不能替代图字节和计划/K配置的一致性检查。

## Artifacts

- Results：`native-retry/work/ee/1b981948db6b1b27f24279ca27b9ad/`中的真实压缩contigs/scaffolds和图产物。
- QC：同任务的`spades-iface.spades.log`及`spades-iface.warnings.log`；未生成独立科学质量评估。
- Provenance：`cli-review.json`、`cli-review/`逐命令记录、原生trace、图来源JSON、单元红绿日志和receipt。
- Model synthesis：本文说明警告、执行状态与科学质量结论之间的界限。

## Limitations and blockers

TA-097仅此有界执行契约接受。无警告K33是复读既有真实产物，不算新组装；负例仅修改隔离日志，不算真实失败生物样本。没有证明全部`--continue`/`--restart-from`组合、全部后端或完整Illumina/hybrid/ONT的组装准确率。TA-016完整来源、TA-091资源身份及其余全流程关卡仍开放。旧718项正式清单不重写，本批单独绑定来源。

## Recommended next step

保留警告供下游科学审查，继续TA-091未完成资源契约及TA-016剩余生产者；不要把本次图来源通过解释成整个SPAdes或Recycler科学效果放行。
