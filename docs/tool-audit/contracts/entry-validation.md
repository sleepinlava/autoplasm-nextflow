# 主入口配置校验

2026-10-20，基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

TA-041：main.asList规范化列表，但validateParams只检查平台、两类assembler、部分已知工具数据库与依赖条件，没有检查任意工具名是否属于支持集合。下游以contains精确匹配已知名称。选择 ['genomad','plasem'] 或 typing_tools=['mob_typre'] 不会触发对应工具，也不报告未知名称。此项与TA-007的已知工具/平台不兼容不同；修复应同时形成统一支持矩阵，保留mob_recon/mob_suite等实际已支持别名，不能只采用注释里的不完整枚举。

实际Nextflow26.10探针从当前main.nf抽取原helper/validate函数及workflow列表规范化片段，默认params块从原nextflow.config提取，不改验证逻辑；仅追加AUDIT_VALIDATION_ACCEPTED标记，无process任务：

| 场景 | 退出码 | 通过标记 |
| --- | --- | --- |
| detection=['genomad','plasem'] | 0 | 有 |
| typing=['mob_typre'] | 0 | 有 |
| detection含platon且无DB | 1 | 无 |
| platform=invalid | 1 | 无 |

原源码哈希、提取脚本、配置、命令与stdout/stderr在 results/tool-audit/20261020-entry-validation/run.json 和同目录。这是入口函数局部复现，不声称完整主流程可成功运行未知工具配置；样本表实际内容未进入样本验证，存在表仅用于通过参数存在性检查。

测试P0现有非法平台/assembler与数据库缺失用例有诊断断言，但没有未知工具名、空token、错误类别、别名或平台能力矩阵用例。其trace.succeeded为空也弱于所有analysis任务未提交：启动后失败/终止的任务可能不在succeeded中。应同时核对submitted/trace任务集合，并把样本验证适配任务与分析任务区分清楚。该测试覆盖差异补入TT-002，不伪造当前已有P0已真实运行通过。

必需数据库的非空检查和下游checkIfExists不等于数据库版本/完整性认证。当前未新增此方面确定性缺陷，也未为此额外下载数据库。

## 实际主入口P0局部复验

2026-10-20：使用原main.nf、原项目nextflow.config及原validation.config，实际缓存Nextflow26.10.0。重复ID、非法ID（含空格）、Illumina缺read2三种样本表均exit1，命中各自预期诊断；每次trace数据行0、work下.command.sh数量0。该范围比此前抽取validate函数或SAMPLE_ID_VALIDATION adapter更强，证实这三个完整主入口拒绝路径没有启动分析。

运行命令、log、trace、fixture/hash在results/tool-audit/20261020-main-p0/run.json与同目录。未使用nf-test launcher，因此无本批JUnit，不将此记录冒称nf-test全套通过或P0全部情景认证。未知工具名TA-041等未修复，其他P0组合仍需实测。

首轮CLI同时用了-C项目配置与-c验证配置，验证覆盖项未生效，三个场景均提前在缺geNomad DB检查失败，按expected diagnostic均为False。此runner配置错误已保留initial-config-run.json及各初始目录；修正为一个仅按顺序include原两份配置的combined.config后重跑，未修改生产/原测试或放宽任何断言。这不是生产缺陷。

### 当前validation用例的主入口对照已补齐

剩余8项：geNomad DB缺失、未实现CRISPR、非法platform、非法short/hybrid assembler、Bakta缺DB、MOB typer缺DB、clinker未启用Bakta，全部exit1、预期诊断出现在stderr、trace数据行0且.command.sh0。加上此前3项，当前validation.nf.test中5个显式test加6个表驱动test的11个场景均有原main对照；映射表p0-main-cases.tsv。

原source和原测试不变；combined.config仅按顺序include原配置。保留外层diagnostic在combined output检查后，本次又逐项确认每个expected diagnostic都在stderr，符合原测试的流语义，而非只在stdout看到就计相同断言。实际nf-test loader/插件/JUnit尚未运行，所以称主入口场景对照通过，不称完整nf-test P0框架通过。

这11项并非输入契约完整分母：TA-007平台/图工具能力、TA-041未知工具及其他非法值/矩阵仍缺正式P0；不以11/11消除这些已知缺陷。平台成功路径/真实默认基线仍未认证。全部命令/param/trace/log见20261020-main-p0-remaining/run.json。

2026-10-20 CRISPR guard原suite补验：开启subworkflow/main明确失败且无任务；直接module明确taskexit2；关闭subworkflow正常退出0。main-disabled case在本suite -C配置下因platform缺失提前失败，不能当成完整关闭CRISPR成功运行证据。共享negative-status断言不足归TT-008审查范围，实际guard未复现假通过。

## 2026-10-20 TA-041 真实main输入形式补证

完整main运行25场景（非抽取helper）：13类列表各放一个未知名，全部越过选择校验并在故意缺sample_id的样本表处失败。空/null元素、嵌套列表、尾逗号空项也越过校验；map输入触发未处理的ConfigMap contains运行时错误，不能当作明确参数拒绝。JSON列表[" platon "]被静默忽略，而相同CLI逗号串" platon "触发缺Platon DB检查，确认规范化形式不一致。empty-list、mob_suite/mob_recon和声明optional ABRicate仅作名称控制；不据此宣称路由执行。全部trace0/.command.sh0；退出来自刻意坏样本表/DB防线或map运行时错误，均不能当作unknown-name拒绝通过。

13参数候选全集见tool-selection-registry.tsv，词法覆盖当前44个unique route pair，含已声明但尚未正确路由的optional ABRicate（TA-009），以及已知但显式拒绝的CRISPR；不删能力来制造校验通过。边界与测试要求见contracts/tool-selection-policy.md。原validation.nf.test的11场景不覆盖本契约。

首次父目录22个隔离配置校准漏assembler默认值，日志完整保留但不计本25场景，不把无关启动失败作为选择拒绝。最终原命令/参数/stdout/stderr/trace与hash见results/tool-audit/20261020-tool-selection-main/final/run.json。TA-041仍planned/未决；本轮无生产代码修改、新增认证或完整E2E结论。

## 2026-10-20 TA-041 注册表与消费者规范化修复

main在validateParams及任务提交前校验13类列表的已知名称/类型/空条目，保留mob_suite/mob_recon别名及所有声明能力。未删optional ABRicate或CRISPR以制造通过；TA-009与已知未实现CRISPR的启用拒绝仍独立。Nextflow复制module params，单改父params不会改变子级；初版赋值/replace及strict-syntax前置语句探针已保留，不能当最终证据。最终采用lib/tool_selection.nf纯函数，每个main/子工作流消费者规范化自己的raw值，无ParamsMap修改或内部API依赖。44个unique contains gate及MAG空列表gate均覆盖。新增utility后生产NF102、include170、词法可达96、未解析0。

最终25个真实main对照含19个准确选择拒绝、6个已知解析控制；原11 P0完整重放通过，全部目标错误均在stderr且0trace任务/0.command.sh。validation.nf.test新增19场景，当前30正式P0均有原main对照，但nf-test loader/JUnit尚未运行。三层父/子/孙在13组完整名称的字符串/列表及空值控制均一致；原宿主suite7场景通过，另2个trimmed真实子流程对照均正确调度两样本并保持有/无MAG分支，已纳入runner；MAG纯空白选择不提交索引任务。

TA-041关闭。证据results/tool-audit/20261020-tool-registry-fix/receipt.json、final/final-replay/consumer-probe/trimmed-routes/mag-disabled；P0映射已更新并归档旧11行。增量patch保留TT-008前态且核对hash。不是实际分类器、平台完整E2E、工具DB可用性或科学基准认证；主入口之外直接调用者仍负责名称/类型校验。未知/坏形式旧配置现在明确失败，合法别名和空列表含义保留。
