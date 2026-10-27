# 工作总结与分层提交（2026-10-26）

最新提交与执行计划见[2026-10-27状态](work-status-20261027.md)。当前109项问题/8未决；有效资源清单43对（38候选/5待完成）。本页按批次保留历史记录，较早章节的数量是当时状态。

## 做了什么

按 `docs/tool-interface-audit-plan.md` 同时检查生产代码、工作流连接、测试逻辑与证据归属。当前问题台账共107项：99项完成有界局部验证，2项按用户要求退役，6项未决（新增S0 TA-092/093已有候选验证，尚未正式接受）。文件清单、运行任务数和缓存命中数均不是审计通过率或独立生物样本数；全流程尚未放行。

- **工具接口与错误传播**：修复并在各自限定范围验证 OPERA-MS 最终结果选择、Recycler 图/BAM/k 一致性、QC 样本身份、检测共识序列遗漏、COPLA 候选独立调用、RGI 数据库隔离、CONCOCT/SemiBin 状态及 helper 文件缓存依赖等。完整模型的 Platon、PLASMe、PlasX、gplas、PlasMAAG 等已有真实节点证据，具体输入、环境与限制以各契约和 receipt 为准。
- **已批准的方法与流程调整**：移除 SCAPP；多 MAG 分箱器必须显式使用 DAS Tool，单分箱器直连；建立统一核酸参考目录并重映射；PlasX 逐样本生成完整注释；gplas 对原图节点重新分类；GTDB-Tk 2.7.2 使用包含 ANI 预筛选的官方流程；未知拓扑按线性处理。标准 TETRA 数值实现和55来源分组基准已执行，但科学阈值未达标，按用户决定只保留相似度分数，停用未校准宿主链接。这些调整可能改变既往结果可比性，单列方法提交。
- **测试逻辑**：增强完整 DNA、样本/序列 ID、单位、产物身份、非空结果、错误传播和缓存恢复断言；恢复14个缺失的 vendored 测试引用；实际运行相关 nf-test/P3，保留失败尝试及替代实现。ENA 的12份输入经官方记录和引物证据确认属于16S，移出真实 shotgun P4 验收范围，未拿空结果替代非空统计验证。
- **审计记录**：建立问题、来源、调用关系、配置、测试、真实节点和清理台账。最近正式接受批次为 `20261025-consolidated-acceptance`，新增关闭9项；正式来源清单718项，包含未改动基线，不能解释为718个通过的模块。当前 main 的75个既有拒绝场景及12种配置展开已有证据，不能替代完整动态连接或端到端运行。
- **AWS**：已通过浏览器检查登录后的控制台和服务约束，尚未创建本次验证的收费资源、上传数据或启动云端分析。既有额度观察有日期限制；额度余额不是本次运行费用上限。

## 正在做什么

| 级别 / 问题 | 当前工作与证据 | 尚未完成 |
| --- | --- | --- |
| S0 / TA-091 | 实际 Nextflow 26.10 已复现目录缓存错误复用。本次续接以 NIO 替换当前紧凑指纹调用方的 glob，v2 纳入目录/链接/权限；22属性场景及16轮缓存控制通过。COPLA两个候选及9894参考的完整原生运行已完成；PlasX、PlasMAAG等当前候选回归、缓存对照和来源补丁已有独立记录。 | 41个消费者—资源对已列清单；31个显式身份输入已接入21个模块文件/22个process定义，SemiBin默认环境资源路径已接线并作有界原生/缓存/上下文与框架验证；其余4个待接线，SemiBin可选FGS分支已有候选验证，其他分支/读取边界亦未验收。显式接口的完整读取边界、可选输入及平台验证也未全部完成。TA-091保持S0未决，不能据局部成功宣布全仓库通过。 |
| S0 / TA-092 | 原生ABRicate掩盖真实BLAST失败为exit0/零命中；当前候选pipefail+close检查已通过真实错误、正常完整输出和合法零命中。 | 精确1.0.1适配器待独立接受；完整环境/OCI/provider范围未认证。 |
| S0 / TA-093 | IntegronFinder单条未知拓扑默认为环状；现有批准规则要求未知线性。完整原始输入下候选与原显式线性、显式环状对照分别一致。 | 联合资源/方法补丁待独立接受；完整可选模式、环境/平台未验收。 |
| S2 / TA-016 | 共识、结构节点记录实际任务脚本、版本探测和 SHA；报告在渲染前检查身份与校验值。17个报告单元方法及有界原生/恢复/篡改控制通过。 | 其他生产者、数据库/模型、完整环境/容器及报告自身来源仍不完整；本批报告增量未正式接受。 |
| S2 / TA-031 | GTDB-Tk 2.7.2 参数和输入接口已作实际解析/CLI验证。 | 完整 r232 数据库上的真实分类尚未完成。 |
| S2 / TT-003 | 已纠正16S数据的验收分类，保留原始测试与来源。 | 适用的真实 shotgun 多样本、非空统计/网络/报告 P4 验证尚未完成。 |

首次整理提交以718项正式清单为源码边界。当时工作区有18个清单文件被后续报告/缓存工作改变；另有5个相关新文件。这23个候选文件继续留在工作区，不提交为已验收代码。已逐字节找回18份正式前像；仅向 Git 索引写入前像，不回退正在运行的工作区。来源和排除清单见 `evidence/20261026-submission-source-state.json`。

## 接下来怎么做

1. **继续处理 S0**：本批完整COPLA重试及其他选定原生对照已完成；下一步处理其余4个隐式环境消费者及SemiBin剩余ORF/可执行文件读取集合、可选数据库/前缀读取集合和部署配置，补齐相应缓存及原生验证后独立复核TA-091。
2. **完成 S2**：补齐实际报告来源，执行完整 GTDB r232 分类和适用真实 shotgun 非空 P4；严格区分真实工具、显式 observer、缓存及科学基准。
3. **完成全流程验收**：补足 M0 动态配置与完整 channel 连接、默认真实基线和各声明支持平台/后端，验证固定 OCI 镜像。已有局部成功不替代这些工作。
4. **实施 AWS 真实验证**：先准备本项目的固定数据、云端引擎兼容性、镜像 digest、最小权限和具体费用估算；核实执行区域与费用上限后再启动收费资源，最后核对产物并清理不再需要的资源。
5. **持续清理**：保留可重放来源和必要最终产物，按清理台账移除失效中间文件与无用环境；逻辑文件大小与实际释放空间分别记录。

## 分层、分级、分类提交

严重度 S0–S3 描述缺陷影响；测试等级 P0–P4 描述验证范围，两者分别记录。以下为顺序提交系列，验收证据对应最终组合源码；不声称每个中间提交均独立完成全流程验证。

| 顺序 / 层次 | 分类 | 内容与级别 | 边界 |
| --- | --- | --- | --- |
| 01 / 工具适配 | assembly-qc | QC、组装、Recycler 图与比对接口，S0/S1优先 | 正式接受的接口源码 |
| 02 / 工具适配 | detection-typing | PLASMe、Platon、COPLA 输出、失败与部署契约 | 不含当前目录指纹候选修复 |
| 03 / 工具适配 | optional-binning | gplas、PlasMAAG 固定源码、依赖与子进程边界 | 图节点重分类的流程接线另列06 |
| 04 / 工具适配 | annotation-host | RGI、IntegronFinder、HOTSPOT 接口与数据库身份 | TETRA方法和MacSyFinder拓扑另列06 |
| 05 / 工具适配 | mag-interfaces | CONCOCT、SemiBin、DAS Tool 输入输出与错误语义 | 分箱器选择规则另列06 |
| 06 / 方法及流程 | approved-methods-integration | 用户批准的方法变化、共享参考统计、SCAPP退役和公共入口/消费者接线 | 明确结果兼容性变化；共享入口改动作为一个完整集成层 |
| 07 / 验证 | tests | 断言、原生入口、fixture/来源锁及vendored引用修复；P0–P4分别记账 | 只提交正式清单中的测试；失败/未完成候选不计通过 |
| 08 / 仓库维护 | repository-hygiene | 忽略测试运行目录与临时日志 | 不纳入数据库、模型、凭据或原始运行产物 |
| 09 / 证据 | audit | 计划、契约、问题/运行/验收台账、来源补丁及本总结 | 如实列出6项未决和未完成AWS验证 |

逐文件分组见 `submission-plan.tsv`。本次仅形成本地提交；提交引用与最终源码一致性检查记录于 `submission-commits.tsv`。


## 本次续接（2026-10-26，TA-091候选，未正式接受）

先按S0优先级完成COPLA超时现场检查、完整枚举修复和目录/链接/权限缓存边界控制。新证据位于 `results/tool-audit/20261026-resource-identity/`；契约见 `contracts/resource-directory-cache.md`，消费者盘点见 `resource-directory-consumers.tsv`。这批是前述分层提交之后的工作区增量，不改变718项正式接受清单、99项有界验证或4项未决的结论；已有报告来源候选继续保留。

当前源码的geNomad和PLASMe原生冷执行/不变恢复/资源损坏/还原4轮对照均通过；检测子工作流3场景28任务通过（分类器observer、真实R消费者）。22属性场景和16轮缓存控制不能替代COPLA或其他消费者的完整验证。源码SHA、预期失败和初始PATH失败重试均见 `evidence/20261026-resource-identity.json`。


## 显式资源消费者续接（2026-10-26，仍为未接受候选）

完成本批24份证据汇总，见 [候选证据](evidence/20261026-resource-consumers.json)；完整receipt及原始运行在 `results/tool-audit/20261026-resource-consumers/`。119条运行源码哈希比较全部匹配当前文件；当前730项快照与正式718项接受清单分别保存，不能据快照项数增加验收数量。102个工作区候选路径由TA-091补丁与保留的TA-016报告补丁分别覆盖，正向应用精确匹配当前源码，反向还原精确匹配HEAD；没有重置工作区或提交候选代码。

- COPLA完整运行两个候选及9894参考，冷运行约69分钟，输出PTU-X4与PTU-Lab26；不变恢复、私有源码等长同mtime损坏失败、还原缓存对照通过。
- PlasX完整两阶段原生运行完成，196基因、39个评分contig与原始predict算术差最大2.22e-16；预计算示例的家族计数有17处差异，不能把它当独立生物学真值。anvi’o完整13个固定git子模块已验证并接入资源准备；私有主源码损坏/还原缓存通过，其他PlasX资源键未逐一原生变异。
- PlasMAAG原始两样本fixture/200epochs完成，115个质粒bin、129个成员的DNA与成员/元数据独立核对通过；既有测试专用VAMB参数保留。gplas、Platon、HOTSPOT、DAS Tool、蛋白输入与RGI选定原生回归完成。均为限定软件契约证据，不代表科学准确率或OCI/全平台通过。
- 13个真实process定义的显式stub/CLI observer缓存控制完成32轮：15个私有资源等长同mtime变化只重执行目标消费者，恢复复用原缓存。MAG/检测路由使用显式分类/分箱observer和真实R；160任务illumina集成为mock；GTDB仅接口，无完整r232分类。75个既有main拒绝场景重放通过，不增加场景分母；gplas/Platon原生nf-test分别1/2例通过。

保留所有失败及被替代尝试：缺失子模块、受限IPC、超时、命名resume/共享history、驱动PATH/依赖、严格语法和重复log参数。3个未改动模块的既有vendored比较链另记待复核，不算本批修复。正式结论保持99项有界验证、2项用户退役、4项未决；TA-091仍为S0。下一步继续8个隐式资源对及读取边界审查，随后按原计划处理S2、真实shotgun P4、完整平台/镜像与AWS准备和验证。


## 根路径定位后续修复（TA-091仍开放）

上批119条源码匹配是当时的冻结快照。随后真实Nextflow验证发现：根目录名含`[]`、`*`或`?`时，默认glob定位会拒绝实际存在的目录。共享入口现以`glob:false`按字面定位；6个正常/特殊根目录身份一致，1个缺失字面路径即使存在匹配兄弟也被拒绝，全部7场景通过。13个既有observer消费者重放均为CACHED且哈希与原冷运行相同；该证据只验证定位/缓存，不验证工具对所有特殊路径的shell参数支持。

见 [后续候选证据](evidence/20261026-resource-root.json)。上批receipt/补丁保持原样，只有共享入口源码已被本次后续修复替代；三份顺序补丁覆盖103个候选路径，正向精确匹配当前字节、反向精确还原HEAD。正式718项接受清单仍未变。

8个隐式资源消费者已完成本地入口静态复核，实际资源解析/变异对照继续待办。已用实际安装的SemiBin2.4.1源码确认默认自训练与可选预训练分支不同，默认还读取包内`marker.hmm`；后续须审查实际读取集合，不能为指纹工作擅自切换方法。静态复核详见 `results/tool-audit/20261026-resource-root/implicit-entrypoint-review.json`。


## 隐式资源探测试验（TA-091仍开放）

在实际SemiBin2.4.1 CPU环境完成默认marker资源的原生探测机制试验，见 [候选证据](evidence/20261026-runtime-resource-pilot.json)。探测process关闭自身缓存，每次resume先输出稳定资源身份；复制的生产消费者仅增加身份/校验脚本输入及执行前校验，原科学命令与完整官方40contig/800000bp fixture不变，默认自训练15epochs、固定seed0。

6轮共12条trace：探测6个COMPLETED；消费者2个原生COMPLETED、3个CACHED、1个预期原生FAILED。等长同mtime的HMM描述文字变化使消费者重跑；损坏HMM头由真实hmmsearch拒绝；还原后精确复用原冷运行哈希。两次原生成功的bin DNA/成员和非空状态独立核对；没有宣称生物学聚类准确率。私有包32个非pycache文件结束时与原安装逐字节一致，未修改共享环境。两次启动前失败（驱动缺Biopython、复制源码匹配断言）单列保留。

本试验尚未接入生产：探测与消费者的Conda/容器、GPU及task.ext参数必须一致，可选预训练模型/GTDB读取集合尚未完成。8个隐式消费者仍全部待验收，不因试验通过减少未决数。Medaka2.2.2固定原脚本另确认默认模型选择依赖各样本reads及回退分支，需逐样本解析；ABRicate明确BLAST前缀/sidecar边界，Dorado仍须先固定实际版本。来源链接与限制记录在 `results/tool-audit/20261026-runtime-resources/readset-review.json`。

新增3个试验来源文件，四份顺序补丁对106个候选路径完成正向当前字节/反向HEAD核对；前一批103个候选来源未改动。正式718项接受清单与99/2/4结论保持不变。下一步把已验证的环境内探测机制与生产实际环境/选项一致地接线，再逐一验证其余隐式资源和显式可选读取集合；S2、P4、全平台/OCI和AWS仍在原计划中。


## SemiBin生产资源身份接线（未正式接受）

将上一轮环境内探测机制接入实际生产模块和MAG_HOST，新增查缓存前的运行上下文门禁，使用原生2.4.1参数/模型解析函数，校验后只执行同一份argv。当前默认15epoch完整原生、等长同mtime资源变化/还原、坏HMM、7种配置不一致拒绝、8个读取集合方法及18场景路由通过；GPU声明匹配仅作stub。详见 [契约](contracts/semibin-runtime-resources.md) 和 [候选证据](evidence/20261026-semibin-runtime.json)。

nf-test原生计算完整使用固定上游FASTA和3个BAM，449个contig形成70个bin；路径API断言失败保留，改用标准Path/独立FASTA读取后通过原覆盖及完整DNA检查。最终两例框架通过包含精确UUID缓存恢复，不将CACHED当新的神经执行。初始内存要求、缺失history、观察器参数解析及未采用的cache钩子实验分别保留。源码42条比较为41直接匹配、1个控制台计数标签桥接；五份顺序补丁对120个候选路径正向字节/权限、反向HEAD字节精确核对，740项当前快照与正式718清单分别保存。

当前41资源对中，SemiBin从待接线转为候选；其余7个隐式资源对仍待接线，SemiBin可选FragGeneScan等ORF依赖/完整模型与GTDB原生验证、when/部署/GPU/OCI/provider仍须补齐。半监督GTDB现须先准备固定资源，不允许科学任务内才出现未记录下载；默认自训练方法未换。正式99项有界验证、2项用户退役、4项未决不变，TA-091仍S0。S2来源、完整GTDB r232、真实shotgun P4、全平台/M0–M4和AWS范围继续保留。


## ISEScan生产资源身份接线（未正式接受）

按隐式资源计划完成ISEScan1.7.3+FragGeneScan1.32生产探测/执行前校验与缓存前上下文门禁，保留默认illumina_5/w0。实际SSW按加载符号定位，constants与FragGeneScan别名读取位置均按argv0验证。详见[契约](contracts/isescan-runtime-resources.md)与[候选证据](evidence/20261026-isescan-runtime.json)。

完整原始NC_012624 fixture原生12阶段共22条trace：16 COMPLETED（12探测、4科学成功）、5 CACHED、1预期坏HMM失败；2次上下文不匹配在消费者提交前拒绝。pHMM/FGS模型/实际加载SSW等长同mtime变异及还原通过，四次阳性均以原工具TSV和独立完整IS/ORF DNA核对，未宣称生物学准确率。独立always-copy83包环境、全部83归档SHA和30个观察文件还原已核对。6个读取边界单元方法与166任务主流程mock通过；报告收录资源receipt，外部科学工具/资源扫描明确observer。

最终17条执行源码全部直接匹配，六份顺序补丁覆盖130个候选路径并通过精确正向字节/权限、反向HEAD核对；当前748项快照与正式718项清单分别保存。失败及替代尝试保留，不重复累计。41资源对现35候选、6待接线；SemiBin可选FragGeneScan仅完成上游读取边界调查，其complete模型尚未接线。完整环境/OCI/provider/when、TA-016来源、S2、GTDB r232、真实shotgun P4、M0–M4和AWS仍待完成；正式99/2/4不变，TA-091仍S0。下一步继续剩余隐式消费者与SemiBin可选ORF依赖。


## SemiBin可选FragGeneScan资源补齐（未正式接受）

生产helper现按实际2.4.1分支条件记录FragGeneScan调用路径、二进制和完整17文件train，保留complete/w0及argv0定位；缺少9个必需模型文件则探测拒绝，默认fast-naive/外部蛋白覆盖不引入FGS依赖。详见[契约](contracts/semibin-runtime-resources.md)及[候选证据](evidence/20261026-semibin-fgs-runtime.json)。

完整原始40contig/800000bp+原BAM、默认15epochs/seed0的10阶段19条trace通过：13 COMPLETED（9探测+4科学成功）、5 CACHED、1预期缺模型探测FAILED，无消费者提交。选定complete/共享gene空白与二进制非分配.comment段等长同mtime变化触发重跑，还原复用原缓存；四次成功完整bin DNA/状态核对，原生适配器FAA/FFN/GFF与原二进制直接输出逐字节一致。18个私有文件全部还原；11个单元方法包含既有8个及新增3项FGS读取集合控制，不能当11个独立科学样本。首次缺Bio、临时文件错误断言及删除模型后的权限还原不全均保留为失败尝试。

9条执行源码比较直接匹配，七份补丁覆盖131个候选路径正向字节/权限与反向HEAD核对，749项当前快照不替换正式718项清单。资源对仍35候选/6待接线；SemiBin其他ORF/可执行文件读取集合（含Prodigal/hmmsearch）及完整环境/可选模型/GTDB/provider尚未完成。正式99/2/4不变，TA-091仍S0；继续6个隐式消费者及剩余读取边界，随后S2、完整GTDB r232、真实shotgun P4、全平台/M0–M4和AWS按原计划推进。


## ABRicate资源身份与新错误发现（候选，未正式接受）

完成原生1.0.1 Perl解析器/FindBin资源探测与生产接线，保留默认80/80和原始参数语义。身份覆盖选定目录、BLAST真实外部别名卷及有效输入；固定176包与完整发布归档/fixture/数据库来源已核对。详见[契约](contracts/abricate-runtime-resources.md)和[候选收据](evidence/20261026-abricate-runtime.json)。

完整原始2.5MB装配与5386参考的13阶段24条trace通过：18 COMPLETED（13探测+5科学成功）、5 CACHED、1真实BLAST失败；2次上下文拒绝无消费者提交。等长同mtime的真实.nhr产品注释变化使正常/外部别名消费者重跑、只改变预期PRODUCT，恢复缓存通过。实际可选PLASMID_DOWNSTREAM的报告事件/完整5行输出与空输入分支通过；7个读取集合方法另计，非独立生物学真值。17个私有文件字节/权限均还原。

新发现TA-092 S0：缺.nhr时真实BLAST报错，原ABRicate仍exit0/表头零命中。候选guard只加原pipeline的pipefail与close状态检查；真实坏卷现FAILED，两个明确晚退出7/9故障observer拒绝，合成合法零命中仍通过。已有完整正常5命中输出基线证明数值/方法未换；TA-092保持ready/未接受。开发中的Perl插值与slurp作用域失败均保留。

九份顺序补丁覆盖141个候选路径并正向字节/权限、反向HEAD精确核对，当前757项快照、16条执行源码直接匹配，正式718清单未变。41资源对现36候选/5待接线。正式99项接受修复与2项用户退役不变；新增TA-092使当前问题106项、未决5项（2S0+3S2）。下一步继续5个隐式消费者、完整读取/环境边界与TA-092独立复核，随后S2、GTDB r232、真实shotgun P4、全平台/M0–M4和AWS按原计划推进。


ABRicate后续完成元数据及vendored nf-test接口修复：原始完整Bacteroides压缩基因组（解压5.3MB）上的native/stub两例通过，原生报告原MD5未改；4条框架COMPLETED包含stub，不当4次科学计算。初始配置不一致被门禁拒绝的失败保留，修复共享测试配置后以完全相同来源的隔离副本运行，副本字节/权限另核对。原九补丁快照另存before-framework；新增第10补丁后145候选路径/759当前来源，22执行源码直接匹配。正式718清单、99接受修复/2用户退役/5未决不变。


## IntegronFinder资源与未知拓扑规则（联合候选，未接受）

接入固定2.0.5原生Config/功能库清单实际匹配文件及模型资源探测、入口解释器一致性与查缓存前上下文门禁；75原始包归档、全部23安装源码/模型文件与固定tag已核对。见[契约](contracts/integronfinder-runtime-resources.md)及[候选证据](evidence/20261026-integronfinder-runtime.json)。

新TA-093 S0：原程序对单个未标注replicon隐式circ，与现有已批准未知线性规则冲突。完整原始ACBA20301bp上原默认1complete，原显式--linear为1CALIN+1In0；候选生成逐序列确定性拓扑表落实规则，显式--circ保留原结果，不主张改变输入生物学真拓扑。最终12阶段22trace（16COMPLETED、5CACHED、1真实坏CM科学FAILED）、11单元、172任务mock、原始2nf-test例通过；native/ref/stub/observer分开。NFcore Ecoli原始软件片段49200bp完整使用，不称全基因组。Matplotlib警告误入版本字段已修正；原生报告commit来自cwd，不能当上游提交，TA-016仍开。

第11份联合候选补丁对157路径精确正向字节/权限、反向HEAD，768当前来源快照/26执行源码直接匹配；原10补丁与正式718清单不变。41资源对现37候选/4待办。正式99接受修复、2用户退役不变；新增TA-093后当前107项问题、6未决（3S0+3S2），新项ready待独立接受。继续4个隐式消费者、可选读取/环境边界，再按原计划处理S2、完整GTDB r232、真实shotgun P4、M0–M4/全平台和AWS。


清理增量：核对证据与后续依赖后移除ISEScan已被v6取代的v3/v4/v5私有环境，逻辑4.06GB、实测可用空间增加1,635,164,160字节；所有固定证据哈希保留/复核，原始包元数据、锁和完整删除清单可重建。见[清理台账](cleanup.md)及`results/tool-audit/20261026-cleanup-3/cleanup.json`。历史私有路径已不存在，不能称其当前可用。


## PlasmidFinder原生启动阻断与清理（候选，未正式接受）

资源调查实际复现两项独立S0：TA-094未约束Python使2.1.6真实求解到3.15并在distutils导入处失败；TA-095生产--legacy被真实2.1.6解析器拒绝。候选固定Python3.10、去除无效flag，科学脚本/默认9库/0.60覆盖/0.90身份/五输出保持。87原始归档哈希和固定源码仅打包路径差异已核对。见[契约](contracts/plasmidfinder-native.md)与[候选证据](evidence/20261026-plasmidfinder-startup.json)。

实际生产模块/共享配置5阶段5trace：3COMPLETED（2科学+1stub）、1CACHED、1预期旧CLI FAILED。完整原始569字节540bp软件阳性两次与上游golden TSV及两份全DNA精确一致；不称完整质粒或生物学正确性。172任务主流程mock通过，原vendored阴性nf-test和资源身份/变异控制仍待完成，不缩减原范围。首次mock重复-log启动失败及归档路径元数据错误检查均保留。

第12补丁覆盖162候选路径，精确正向字节/权限与反向HEAD；原11补丁/正式718清单不变。新增两项ready未接受，当前109问题、8未决（5S0+3S2），正式99局部接受修复/2用户退役不变。41资源对仍37候选/4待办，继续PlasmidFinder接线及原计划其余边界/平台工作。

按新增清理授权移除失效Python3.15安装，保存完整文件清单/84包元数据/重建锁和归档；逻辑1.28GB、实测可用空间增加502,448,128字节。可用Python3.10、完整数据库/fixture、所有证据保留；旧路径现不可用。见[清理台账](cleanup.md)。


## PlasmidFinder资源接线及用户禁止病毒元素（候选，未接受）

用户新增明确约束：不许使用病毒元素，见[user-constraints.md](user-constraints.md)。本轮原病毒fixture下载未成功、未运行，脚本及空目录已清理；vendored阴性测试改用固定提交的完整原始Bacteroides细菌gzip，保留原零命中TSV MD5及五输出语义，实际native/stub通过。不把细菌来源等同于已证明无任何病毒同源片段，也不允许后续因旧计划继续使用病毒输入/模型。

完成固定2.1.6原解析器/配置/分类选择、完整DB、entry/解释器、CGEcore、实际BLAST/KMA方法身份探测；生产cache:false/deep消费者、执行前核对、查缓存前上下文门禁、完整meta join和report事件接入。见[契约](contracts/plasmidfinder-native.md)和[候选证据](evidence/20261026-plasmidfinder-resources.json)。最终13阶段23trace：16COMPLETED（12probe+4科学）、5CACHED、2预期FAILED（缺FSA probe拒绝/坏FSA真实BLAST失败）；2上下文拒绝无消费者。等长同mtime注释/sidecar变化重跑，还原复用精确缓存；完整原540bp软件阳性golden TSV/全DNA核对，48私有DB文件还原。8单元、178mock、2细菌nf-test通过，角色分开，不宣称科学准确率。

13份顺序补丁对171候选路径精确正向字节/权限、反向HEAD；原12补丁与正式718清单不变。41资源对现38候选/3待办；109问题/8未决（5S0+3S2）、99正式接受局部修复/2用户退役不变。继续其余资源/完整环境/provider/可选分支与S2、GTDB、真实shotgun P4/M0–M4/平台范围，但执行必须遵守禁止病毒元素约束。


## MOB-suite读取边界调查与失败任务中间文件清理

固定MOB-suite3.1.9 tag→不可变提交eb860648，仅获取六份代码/配置和tag JSON，无任何DB、序列、taxonomy或模型下载。直接源码与不可变提交逐字节相同；浏览器缓存的不同渲染不用于实现。原AST解析器/路径分支19场景+未知参数拒绝通过：默认目录采用8逐项资源并verify_init，显式-d改用约定文件名并覆盖逐项参数，taxonomy/literature另算。详见[契约](contracts/mobsuite-runtime-readset.md)和[来源证据](evidence/20261026-mobsuite-readset.json)。

这是源码边界验证，不是原生MOB安装/科学计算/生产资源接线。默认缺status会自动调用DB/ETE3准备器，必须在真实任务前准备满足“不使用病毒元素”的资源；未审核默认数据库不能直接下载，原病毒fixture不得执行。生产仅纠正错误bundled DB注释，无运行时门禁冒充。MOB仍pending，41对38候选/3待办；109问题/8未决、99接受修复/2用户退役不变。14顺序补丁173候选路径正向当前字节/权限、反向HEAD，正式718清单不变。

清理已由成功v2替代的PlasMAAG超时失败任务6个BAM/BAI，逻辑1.78GB、实测可用空间增加550,785,024字节。2160份JSON证据引用及最新453固定产物删除前后核对；完整逐文件元数据/哈希、原始输入、软件、成功产物与所有日志/trace保留。删除BAM字节不保留，旧失败attempt不再可据此resume，见[清理台账](cleanup.md)。继续MOB原生准备/资源接线与其余消费者，但所有执行受禁止病毒元素约束。


## MOB-suite原生软件准备与独立只读门禁（未接受、未生产接线）

安装实际Conda3.1.9 build1/Python3.10.14，共180包原始归档SHA256全核对；显式skip-run-link-scripts/no-pyc，原包post-link确会运行mob_init，现已跳过。默认DB仅__init__.py，无status/序列/sketch/taxonomy。未另行下载生物库/模型/测试序列；软件自带10份FASTA示例/测试文件单列且未使用。OCI声明build0未运行，不能替代验收。实际CLI3.1.9；六份代码/配置与原包相同，五份与固定tag相同，但tag的version.py为3.1.8，版本来源分开记录。见[契约](contracts/mobsuite-native-preflight.md)及[证据](evidence/20261026-mobsuite-native.json)。

新增独立预检复用已安装真实parse_args/原路径分支，默认缺status拒绝且不调用初始化；SQLite用只读模式检查schema2/完整性/必要列，不触发ETE3创建/升级。2个真实子进程拒绝缺库，8单元结构控制通过；4实际CLI help/version通过。结构阳性用明确非生物学占位文件，只证明门禁结构，不是科学DB，不运行MOB分类。预检无execute且未接生产，fullDB/native/cache/可选filter/安装阶段部署门禁仍待完成。

第15顺序候选补丁177路径精确正向字节/权限、反向HEAD；当前783来源快照、原14补丁与正式718清单分别保留。41对仍38候选/3pending，109问题/8未决、99正式接受局部修复/2用户退役不变。继续按“不使用病毒元素”约束完成资源内容核对及安装阶段无隐式下载方案；软件准备成功不冒充MOB科学计算或资源缓存通过。


## MOB软件安装无隐式建库与新增Typer默认库待办（未接受）

两份生产Conda YAML改为原依赖范围+官方3.1.9固定SHA wheel，避免旧Bioconda post-link mob_init；16Python代码与原始包完全相同，179Conda依赖build/hash与前批一致。真实全新Nextflow26.10/Micromamba创建无全局skip-link选项、默认DB未初始化，pip check通过。recon/typer4trace：2COMPLETED版本检查、2CACHED，共用同一prefix；8唯一预检单元/2缺库拒绝在新环境通过，不当科学分类或完整资源缓存。见[契约](contracts/mobsuite-no-init.md)及[候选证据](evidence/20261026-mobsuite-no-init.json)。

新发现MOB_TYPER缺目录/7可选文件时回落环境库和taxonomy/literature，原显式目录candidate不能覆盖它。实际native parser+原5条路径AST语句/verify_init observer确认，未执行main/初始化。补记新隐式对，当前42对38candidate+4pending（Dorado、Medaka、Recon、Typer默认库），不因安装修复减少TA-091。完整DB非病毒范围/科学时初始化/资源身份及native缓存、Conda/Mamba CLI/OCI/provider仍未完成。109问题/8未决、99正式接受局部修复/2退役不变。

第16顺序候选补丁183路径、787当前来源快照，正向字节/权限及反向HEAD精确核对；原15补丁/正式718清单不变。首次沙箱元数据失败、日志stdout/stderr断言错误保留并修正，未降低创建/源码/trace断言。预检驱动只排除正常__pycache__，仍检查真正库内容为空。

清理已被新环境替代的旧MOB软件prefix，逻辑2.11GB、实测可用空间增加79,757,312字节；保存37,844文件/2,036链接/5,055目录清单、180包元数据/锁/原始归档，新prefix全部保留。2194JSON引用和55固定产物删除前后复核，历史旧命令路径现不可执行，见[清理台账](cleanup.md)。继续4个隐式资源对及原计划其余范围，始终遵守不使用病毒元素约束。


## MOB真实任务入口禁止初始化（候选，未接受）

Recon/Annotation/Typer3生产别名均显式stage同一helper，实际原parse_args/原5条资源路径选择，准备通过后调用原main与同一argv。真实verify_init点再检查状态，并禁止MOB初始化/ETE3升级；taxonomy连接和健康检查只读，资源丢失也不建库。可选native filter参数继续交给原算法，完整filter读写验证deferred，不静默删方法。科学源码/阈值不变，完整资源身份/probe仍未完成，见[契约](contracts/mobsuite-execution-guard.md)和[候选证据](evidence/20261026-mobsuite-execution-guard.json)。

最终9阶段9trace：6真实缺默认/显式库FAILED（exit2、科学main未调用、无输出），3独立stub COMPLETED；原540bp细菌软件fixture/DB状态不变。16唯一单元含明确合成SQLite/主函数observer，不作科学DB正例。178主流程mock、2实际nf-test stub（完整5.3MB细菌FASTA）、发布12trace及显式MOB目录4轮52stub/cache通过；原生完整参考科学案例保留prepared标签及全DNA/数值目标、尚未运行。病毒fixture已移除，旧snapshots仅历史，不自动重录。首次nf-test helper相对工作目录失败保留，改projectDir路径后通过。

发布回归保存task-evidence后清理两个私有work，最终副本hash仍可读；未测回收字节。第17顺序候选补丁192路径、791当前来源快照正向字节/权限与反向HEAD精确核对；原16补丁/正式718清单不变。42资源对仍38候选/4pending，109问题/8未决（99正式接受局部修复/2用户退役）不变。继续完整非病毒参考内容、科学阳性/阴性/错误传播、查缓存前资源身份与其余原计划范围。


## Medaka原生CPU准备与逐输入模型选择控制（候选，未接受）

固定2.2.2 tag提交293b33dbf168935aee4d5b2f3e1a92f4a54e409f，原Conda py312h3050eb1_0软件包CPU环境已安装、真实CLI版本通过。141原始归档/安装元数据SHA核对，五份关键代码与固定提交完全相同；mini_align仅绑定原包，不能声称tag字节相同。四份随包通用DNA模型实际字节/路径已记录，未另行下载模型或序列、未执行推理。见[契约](contracts/medaka-runtime-readset.md)及[候选证据](evidence/20261026-medaka-readset.json)。

18原生API控制+5精确原Bash脚本前段控制确认FASTQ/BAM元数据、前100条边界、显式model优先级及bacteria行为，HTTP模型请求一律记录并拒绝。发现识别到旧模型但下载失败也会回退默认模型，后续探测不能将该回退误当已准备。控制仅N/空BAM头部，不是科学样本；未进入比对/推理/stitch。第二轮模型stores前后全文件SHA不变，保留生成控制/脚本/shim；第一轮不重复计数。原病毒fixture未执行，禁止病毒元素约束持续适用。

第18顺序补丁新增2测试/锁路径，共194候选路径、793当前来源快照，正向当前字节/权限与反向HEAD精确核对；原17补丁/正式718清单不变。42资源对仍38候选+4pending，109问题/8未决、99正式接受局部修复/2用户退役不变。未修改生产Medaka或冒充资源接线完成，完整合规细菌ONT科学数据/真实抛光、逐样本模型身份、上下文/缓存及其余原计划范围继续待完成。当前环境/模型为下一阶段所需，不新增不实清理回收量；既有清理台账继续保留。


## Medaka逐样本模型选择候选、输入审查与清理（2026-10-27，未接受）

新增独立选择器，核对固定2.2.2源码后执行原CLI/原Bash前段，保留getopts/显式model/bacteria/科学flag，输出实际模型字节/路径/权限/输入/context。记录并拒绝下载，原脚本隐藏下载错误后exit0回退也不算成功；合法无元数据fallback保持。--expect比较完整身份，同大小同mtime模型变化拒绝，还原后通过；尚非完整格式/兼容性/执行资源验证或生产/cache门禁。见[契约](contracts/medaka-model-selection.md)和[候选证据](evidence/20261027-medaka-selection.json)。

最终9实际CLI（6exit0、3预期exit2）+1明确注入的父resolver空store晚期拒绝observer，N元数据控制不是科学样本；stores前后普通文件SHA不变，v1不重复计数。Medaka vendored病毒输入移除，native要求完整审查细菌ONT/assembly及独立全FASTA预期结果，旧native snapshot仅历史。nf-test0.9.5 dry-run发现2例，0真实testcase/0Nextflow任务，不能把dry-run控制台PASSED当框架通过。未修改生产MEDAKA命令、未抛光。

按官方目录线索下载固定提交完整候选FASTQ（10,258,859字节），核对blob/SHA并审查1000reads/33,343,943bases；名称494个NC-000913.3、506个NC-006347.1且comments全空，不是保留FDAARGOS_1225参考的已知匹配输入，也未证明真实ONT，拒绝作科学阳性，不另行抽取小子集来制造通过。清理这份未用候选和重复解压参考，逻辑15,573,586字节、实测可用delta0；2585递归JSON索引/74前批固定证据核对，原gzip、源码/模型、元数据和诊断保留，候选正文需按锁重新下载。见[清理台账](cleanup.md)。

第19顺序补丁197候选路径、795当前来源快照正向字节/权限与反向HEAD精确核对；原18补丁/正式718清单不变。42资源对仍38候选+4pending，109问题/8未决（99正式接受局部修复/2用户退役）不变。继续真正匹配细菌ONT及模型/生产/科学/cache验证、其他隐式消费者和原S2/GTDB/真实shotgun P4/M0-M4/平台/AWS范围，始终不使用病毒元素。


## Medaka真实ONT样本下载进行中及新增相邻索引待办（2026-10-27，未接受）

按ONT官方NO-MISS 2026细菌分离株数据选定发布顺序第一个完整分析样本sample_1_1；metamap确认barcode01/run_id与SUP5.2.0，完整已抛光同名两contig装配4,806,605bp已获取。约1.11GB完整已发布filtered FASTQ仍在下载，前100条真实测序标签匹配同一模型，只作临时元数据观察。它不是整flowcell/raw数据，装配也不是独立真值；未抛光、未声称错误率改善。详细[进行中记录](contracts/medaka-real-ont-progress.md)、source-review.json及实际session状态为准，不按partial文件声明完成。

新增两个未接受driver，完整下载/ETag校验后自动先核对全读段数，再执行原始Medaka CLI，成功后才运行实际native/stub nf-test；任何非零即停，不改变方法或取小子集过关。当前未产生科学/框架通过receipt，第20补丁尚未固定；原19补丁/116固定产物/795来源及正式718清单核对保持。下载session77923与控制session89079需工具实时重查，不把此文本或状态文件视为仍活跃的证明。

实际固定mini_align源码及2个原生index-only调用发现参考相邻.fai/.map-ont.mmi按存在性复用；完整有效索引创建通过，而明确损坏的非生物学索引仍被-X分支保留、exit0。没有据此声称可正确比对，后续必须做真实alignment错误/缓存/还原。第一次FAI大小任意阈值断言失败已保留，改用完整FAI记录长度及MMI格式标识。该额外资源族登记在清单增补，旧已固定主表42对不改写；有效总数现43=38candidate+5pending，TA-091及109问题/8未决不变。新资源与数据仍供后续核对，未做新的空间回收声明，始终禁止病毒元素。


Medaka下载期间补齐目标filtered文件官方per-file统计：392,014reads/1,384,109,852bases、1000–120531bp，与metamap392,181不同。保留两份原始来源，不推断167条差异具体原因；driver改用文件名匹配的四项独立数值精确核验，未放宽标准或重筛数据。原driver字节/hash与队列修订记录保留，旧等待控制器的源码guard将拒绝变更后源码，确认其终态后再布置新验证；下载进程未重启、完整计算尚未开始。另新增独立HDF五类概率/去重神经覆盖检查待实际产物后执行，不能以BAM覆盖或draft回填代替。见进行中契约及queue-revision.json。
