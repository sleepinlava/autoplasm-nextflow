# TA-041 工具选择输入契约

2026-10-20。当前全集见 `../tool-selection-registry.tsv`；来源为当前 main、配置声明与全部 subworkflow 的工具 contains 分支，该表已与main.toolChoices逐项比对，消费者通过lib/tool_selection.nf规范化。

原定要求（实施验证见下方）：

- 在 main 的数据库检查、样本表路由和任何 process 提交前，统一规范化并校验13类工具/方法列表。
- CLI逗号串与JSON/Groovy字符串列表均逐项trim并采用同一个识别集合。不能出现 `' platon '` 字符串触发DB校验、`[' platon ']`却静默不启用工具的差异。
- 保留明确的空列表/空串禁用含义；含空元素、null、嵌套列表或map不是合法工具名列表，需报告参数、元素位置及值。逗号串内部/结尾空条目应显式处理，不得利用默认split丢弃尾空项。
- 拒绝未知键，给出具体参数、错误值及可选值；不能只因稍后的数据库、assembler或samplesheet错误就把坏选择判为已拒绝。
- 保留已实现别名mob_suite/mob_recon，以及主/可选annotation列表两处已支持的prodigal。已声明optional ABRicate仍须登记，其TA-009路由错误另行解决，不能靠删掉此能力通过校验。
- crispr是已知但显式未实现的能力；保留启用host linking时的明确拒绝及关闭时的既有行为。已知工具的平台/图/reads资格、数据库及跨工具依赖另行校验，不把“名称合法”解释成该路径可用。
- 主入口P0必须检查准确诊断和零任务提交/零.command.sh，加入拼写错误、空条目、格式差异、非法类型以及已知别名控制。完整nf-test框架未恢复时，实际main对照须明确其范围，不冒充框架/JUnit通过。

修复前审查tests/nf-test/validation.nf.test：当时11场景主要覆盖ID、读对、平台/assembler、DB和CRISPR/依赖，当时没有未知工具或列表形状的正式场景。原11/11历史对照不覆盖本契约；现已补充19场景及原main对照。

上述要求已实施，详见本次修复记录；原25场景为修复前对照。修复前行为见results/tool-audit/20261020-tool-selection-main/final/run.json；修复后当前证据见results/tool-audit/20261020-tool-registry-fix/receipt.json；其故意缺sample_id的样本表只用于阻止执行分析，不能认证合法输入E2E。首次隔离配置漏assembler默认值的校准运行保留在父目录，不能计作未知工具拒绝成功。

## 2026-10-20 TA-041 注册表与消费者规范化修复

main在validateParams及任务提交前校验13类列表的已知名称/类型/空条目，保留mob_suite/mob_recon别名及所有声明能力。未删optional ABRicate或CRISPR以制造通过；TA-009与已知未实现CRISPR的启用拒绝仍独立。Nextflow复制module params，单改父params不会改变子级；初版赋值/replace及strict-syntax前置语句探针已保留，不能当最终证据。最终采用lib/tool_selection.nf纯函数，每个main/子工作流消费者规范化自己的raw值，无ParamsMap修改或内部API依赖。44个unique contains gate及MAG空列表gate均覆盖。新增utility后生产NF102、include170、词法可达96、未解析0。

最终25个真实main对照含19个准确选择拒绝、6个已知解析控制；原11 P0完整重放通过，全部目标错误均在stderr且0trace任务/0.command.sh。validation.nf.test新增19场景，当前30正式P0均有原main对照，但nf-test loader/JUnit尚未运行。三层父/子/孙在13组完整名称的字符串/列表及空值控制均一致；原宿主suite7场景通过，另2个trimmed真实子流程对照均正确调度两样本并保持有/无MAG分支，已纳入runner；MAG纯空白选择不提交索引任务。

TA-041关闭。证据results/tool-audit/20261020-tool-registry-fix/receipt.json、final/final-replay/consumer-probe/trimmed-routes/mag-disabled；P0映射已更新并归档旧11行。增量patch保留TT-008前态且核对hash。不是实际分类器、平台完整E2E、工具DB可用性或科学基准认证；主入口之外直接调用者仍负责名称/类型校验。未知/坏形式旧配置现在明确失败，合法别名和空列表含义保留。

后续更新：TA-009已按路由契约修复，两个annotation列表均可启用ABRicate；真实工具搜索仍未认证。当前45个unique normalized route pair，历史44条不作为当前总数。
