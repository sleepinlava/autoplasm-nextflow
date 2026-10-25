# 报告输入、发布与方法契约

2026-10-20；基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

TA-015：CROSS_SAMPLE 用 collect 收集部分平台输出后传 REPORT，但 REPORT 仅接 val trigger，脚本忽略其内容，直接扫描 params.outdir。ILLUMINA.done 等未包含全部 typing/annotation/binning/MAG/linking/comparative/MultiQC 输出；即便都收集，publishDir 也不是文件依赖。[Nextflow 官方 publishDir 说明](https://docs.seqera.io/nextflow/reference/process/directives/publish-dir)明确发布是异步的，下游应访问声明的 process outputs。该说明为当前官方参考；项目声称运行器 26.10.0 尚未本机复验，未以最新版文档冒充固定运行器源码。

直接复现保存于 results/tool-audit/20261020-report：发布根目录放 OLD_SAMPLE 的历史 consensus、当前样本清单为 CURRENT_SAMPLE，另建空 08_annotation 目录；generate_report.R 正常退出，report.md/JSON 将 OLD_SAMPLE 记为当前唯一样本，annotation 显示 present=true。脚本不读取样本清单，人工 manifest 仅用于定义预期，不是已支持参数。此复现证明旧目录没有运行隔离；未声称动态复现 Nextflow 复制竞态。

REPORT 不通过 path 输入声明报告数据，还影响容器 mount 与 resume 的缓存依赖；具体后端缺挂载未复验，不额外计为已确认运行失败。修复应传入本次需要的文件及 stage status，不能靠延时或目录存在判断“完成”。

TA-016：同一 assembly 复现没有读段分析，methods.md 却宣称 performed read QC / typing / annotation / CoverM，且泛列所有工具。方法应由实际运行记录生成，包含版本和参数；没有检出与禁用不可混写成执行过。

TA-017：脚本生成 report_data.json（模板也会消费），REPORT output 只有 report.md、report.html、methods.md。未声明文件不属于该 process 的发布输出，机器可读数据层留在 work。修复后应核验三种报告的同一运行样本/数值一致。

本轮未运行 R Markdown 模板（复现省略 --template，使用脚本明确支持的简单 HTML），未验证浏览器渲染；这些仍是验收缺项。

## TA-045：合法样本名含输出后缀

2026-10-20 原生R报告探针：两样本S与S.plasmid_contigs.fasta，均符合生产ID正则，标准输出文件均存在，前者1条plasmid/1条circular，后者2条plasmid/2条circular。generate_report.R在FASTA basename上执行 sub("\\.plasmid_contigs\\.fasta.*$", "", fasta)，删除第一个匹配及其后内容，而非最后的固定suffix。因此第二样本被解析为S，samples[[sid]]覆盖第一条；计数从第二个FASTA取2，但consensus/structure按误解析的S读取第一样本文件，circular为1。最终JSON只有S一个样本、count2、circular1，exit0，Markdown/HTML同源。

这与TA-015的共享publish目录异步/陈旧文件不同：本fixture只有当前两个样本、所有文件完整，没有异步任务和旧结果，也会出现样本混合。修复必须保留完整sample_id及显式文件关联，不能限制目前合法ID或只修正报告标题。catalog已有后缀文本sample ID测试，但报告没有继承其断言。

命令、退出码、输入和JSON：results/tool-audit/20261020-report-identity/run.json。仅人工文件原生报告，不是主流程或科学基准。额外确认read.delim读取当前小写true/false保持字符串，未发现因此将所有circular计为0的问题，不新增该猜测。

## TA-045最小修复与验收

现仅删除文件名最后的固定.plasmid_contigs.fasta后缀，保留sample ID内完整相同文本。生产变更一行，不改计数/方法定义或发布触发器。新test_generate_report.py在旧版3项中2项失败（普通ID对照通过）；修复后3/3（1.794s）。覆盖S与含一次/非终端后缀的3样本独立计数/工具、零调用样本完整ID、普通样本兼容；逐项核对JSON、Markdown和fallback HTML。

原REPORT模块实际Nextflow/R Markdown验证，使用先前完整人工published fixture，两合法样本S与S.plasmid_contigs.fasta分别得到1/1和2/2计数，实际HTML表格解析得到正确独立行，Markdown样本数2。harness按原projectDir约定提供原assets目录symlink，模板文件哈希未变；没有修改wrapper或模板。JSON仍未声明发布，测试从工作目录/原CLI产物读取不能当TA-017已修。

改动patches/TA-045.diff；完整red/green及wrapper receipt在results/tool-audit/20261020-report-identity-fix/。TA-045标fixed/verified，TA-015/016/017等仍未决，不将完整静态fixture等同异步端到端验证。

## 2026-10-22 TA-015/017 显式本轮输入与发布修复

当前基线之前态冻结在 results/tool-audit/20261021-report-inputs/before/，旧脚本本轮再次运行：期望样本S.1/001，发布根仅有OLD_SAMPLE及空08_annotation时，exit0仍纳入旧样本、annotation present=true，assembly还虚称读段QC。这是实际前态反例，不将目录污染当作动态复制竞态已复现。

新REPORTING收集本轮的类型化事件，每个样本的plasmid_fasta/consensus/structure均作为REPORT的path输入；样本清单、R脚本、Rmd模板也显式暂存。输入路径用编号子目录隔离同名文件，事件按内容排序保证稳定缓存键。各平台和子工作流从实际已调用process的命名outputs建立完成/版本记录，包括可选typing/annotation/binning、MAG、linking、comparative和MultiQC。其他大BAM/DB仅记录输出证据，不复制其数据到报告。没有发布目录扫描、延时轮询或以空目录判断完成。

R严格按样本清单匹配三类输入及表内sample_id、FASTA/质粒共识/结构ID集合；缺失、重复、不一致、破损表头和非法调用/环状值明确失败，不能回退成0。0候选仍保留样本。旧--outdir CLI被移除；独立使用需manifest(schema_version=1,settings,records)+samplesheet。原四列表样本摘要兼容，sections新增observed_outputs/provided_input/not_observed状态；未观察到输出不等于禁用或阴性。报告从验证后的本轮输入生成，REPORT现在声明并发布report_data.json及report_inputs.json，和Markdown/HTML/methods一起共五份。输入清单是工作路径/依赖证据，不是自包含原始数据归档；清理work后路径可能不可直接重放。

原生Nextflow26.10实际REPORT/RMarkdown测试5场景、8个trace条目（4 completed、3 cached、1 expected failure）：可选任务延迟且禁用发布，报告仍等待并识别它；旧样本/空目录被忽略；无可选任务不误报板块；resume不变正确缓存，修改同名实际输入正确重算且其他任务缓存；可选任务失败时REPORT不运行且无新报告发布。Markdown/HTML表格/JSON样本ID及计数相同，五份产物均实际发布。13原生R单元方法保留原3个合法复杂ID/零值回归，并增加失配/破损/清单规则；R smoke54检查包含真实Rmd与fallback，结构fixture修正为生产使用的筛选后质粒FASTA，而非整份组装。

受影响回归：原结构/报告6任务（锁定SCP1/pUTI89及规则对照）、共享定量/CROSS_SAMPLE/coabundance55原生任务、MAG全binner32任务（核心/模型为observer、真实CONCOCT I/O和R分开）。五平台及空质粒共6个实际main/R/Python场景788任务，外部工具明确替身，不是生物学/模型真实性能。新增assembly场景核对无QC/覆盖度输出时不声称执行；各场景注入旧样本和空network目录，并核对实际trace producer被记录、JSON/HTML/Markdown一致。不是镜像、远端executor、nf-test框架或完整真实平台认证。完整源hash/命令/trace/失败尝试见本批receipt。

TA-015与TA-017局部verified。TA-016虚构默认方法文字已删除，改为观察producer、process报告的版本（明确可能是静态声明）、请求设置（明确不是执行证据）及缺失说明；所有CLI/数据库/模型/代码与数据身份仍未完整记录，保持ready而非verified。版本topic的声明不自动升级为实际运行版本证据。实际运行器ChannelOut可迭代named outputs已用本机javap及实际harness核对；严格DSL不支持动态spread，helper改为逐stream合并，ChannelOut需封在Map中防止函数参数自动展开。上述修复无生物学算法/阈值变化。
