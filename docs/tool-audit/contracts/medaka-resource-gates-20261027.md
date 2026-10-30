Takeaway: Medaka模型与索引独立门禁通过17个实际CLI控制；发现Flye普通gzip到Medaka索引接口阻断，生产缓存接线仍待完成。

本轮继续审查完整细菌ONT样本所用Medaka资源，目标是阻止损坏模型或索引被作为有效科学输入复用。已运行固定原生工具的索引重建比较、完整模型加载及数据兼容性检查。索引门禁13个实际CLI场景与模型门禁4个场景通过，原始参考、索引及模型字节保持不变。检查还确认，开启Medaka时的Flye普通gzip装配不能直接供固定原生工具建索引，而完整同序列的已发布BGZF可以。独立门禁尚未接入生产任务和查缓存前流程，不能据此关闭资源缓存问题或宣称平台通过。下一步需同时接入资源身份与私有draft准备，并在完整输入上验证生产缓存和压缩输入连接。

## Scientific context and question

延续TA-091，输入保持既有完整NO-MISS sample_1_1细菌来源读段与同样本已抛光draft，模型保持原SUP5.2.0。没有下载或引入新序列、数据库、模型或病毒元素；细菌来源不代表已证明无病毒同源片段。此次参考只是软件输入与比较基线，不是独立生物学真值。Rosalind/NGS Workbench技能的证据解释原则继续适用；BioNeMo没有执行GPU任务或替换科学工具。

## Question, lifecycle, and endpoint

独立候选bin/medaka_index_resources.py和bin/medaka_model_resources.py均已真实运行，测试驱动分别为tests/run_medaka_index_resources.py与tests/run_medaka_model_resources.py。两组实际控制均已终态退出0，完整生产模型推理未因本轮门禁重新执行。没有Workbench注册run或云资源启动。此前原生推理及framework-v3的2/2通过仍是前一批有界证据，未扩大为资源门禁生产通过。

## Key findings

- 索引候选在私有目录执行固定Medaka2.2.2原mini_align -X，用其原始默认minimap2参数及samtools构建完整参考索引；将待复用相邻FAI/MMI及存在时的GZI逐字节SHA256比较，包含工具二进制身份及参考内容身份，不写原目录。
- controls-v2共13实际CLI：基线、不变、MMI魔数/内部字节、FAI ID、参考明确A/C/G/T碱基替换四类同大小同mtime变异及各次还原、无索引、断链、最终还原。四类变异与断链正确拒绝；不变及还原与原receipt一致；无索引正确记为缺失且原目录仅保留输入。
- 第一轮controls-v1原参考XOR控制把T改成U，参考内容哈希确实改变而原生重建索引相同；驱动误把它当应改变索引DNA的控制而失败。完整日志及observer-review.json保留；修正为明确A/C/G/T替换后重新运行13场景，不删除失败历史。首次直接运行未将原生prefix加入PATH，正确拒绝缺少samtools；该准备失败不计通过。
- 模型候选使用原始CLI选择器，拒绝自动下载，完整读取压缩流，调用原生check_compatible及原生完整权重加载；实际CPU模型18个状态张量均有限，并再次核对选择/来源/模型身份。models、datastore等包内35份Python及候选本身共36份加载来源身份记录在receipt。
- model-controls-v1共4实际CLI：私有完整原模型基线、不变、同大小同mtime坏gzip尾、还原；原生兼容性及权重加载通过，损坏尾明确拒绝且无成功receipt，恢复后完整身份一致。使用完整原读段与draft，没有下采样或伪造读段标签。
- 新TA-096：modules/nf-core/flye/main.nf实际使用gzip -c生成普通gzip，subworkflows/ont.nf在启用medaka时直接join至MEDAKA，MEDAKA不解压而将同路径传给-d。完整draft按同一gzip -c命令压缩后，固定mini_align -X退出1，samtools明确要求bgzip；原完整发布BGZF则退出0、生成FAI/MMI/GZI，候选捕获通过。此处不是实际Flye组装或完整原生gzip抛光。默认polishing_tools为空，故失败范围为显式开启Medaka的路径。

## Interpretation

索引重建比较能阻止已确认的坏MMI被误当FASTX并返回exit0/空BAM的资源风险；它也能识别仍具MMI格式但参考DNA不一致的索引。不能仅凭文件头或samtools quickcheck认定科学参考有效。模型哈希之外的完整加载与原生兼容性是独立读取验证，不等于模型推理准确率证据。普通gzip接口阻断解释了为何plain/BGZF本机成功不能外推到Flye压缩生产连接；必须修复该连接再作验收。

## Artifacts

根目录results/tool-audit/20261027-medaka-index-gate/。

- Results：original.json、controls-v2/run.json、model-full-v1.json、model-controls-v1/run.json；都是资源验证产物，不是新的抛光序列或生物学结果。
- QC and visual reports：上述控制的逐次stdout/stderr及gzip-flye-contract-v1/stderr；没有产生独立基因组质量图。
- Provenance：controls-v1/observer-review.json、gzip-original-v1/run.json、gzip-flye-contract-v1/run.json、bgzip-capture-v1.json。固定来源及证据哈希为docs/tool-audit/evidence/20261027-medaka-resource-gates.json。
- Model synthesis：本文件；先前完整推理复核见medaka-real-ont-review-20261027.md。

## Limitations and blockers

两个新helper明确标记production_gate=false、formal_acceptance=false；尚未修改MEDAKA生产接口。索引候选只覆盖原默认non-RLE、非强制-x的相邻索引，不可直接用于所有原生可选参数；GZI已以完整发布BGZF实际验证，但GZI同大小变异及其他压缩格式边界未单列测试。模型候选不是外部依赖/全部环境或provider证明。没有实际查缓存前runtime/context guard、消费者执行前核对、生产不变CACHED/变异重算/损坏失败/还原CACHED证据，TA-091仍open。TA-096单独保持in_progress，不将独立索引拒绝当作生产gzip修复。全台账110项，99项有界verified、2项退役、9项未决（6S0+3S2）；正式718接受来源清单未改。

## Recommended next step

按原生模型实际选择和CLI状态设计cache:false逐样本资源probe，与消费者共享运行上下文、选择后的模型、原始/有效draft及索引身份；同时修复普通gzip的任务私有解压，并保持完整DNA。逐项覆盖RLE/force及实际读取集合，不为使门禁通过而删除原参数支持。随后执行完整真实模型与原生产模块plain/ordinarygzip/BGZF结果核对，查缓存前上下文、同大小同mtime变异重算、坏资源拒绝及还原复用。TA-091、TA-096未完成前不进入平台放行，也不重复下载完整样本或清理仍需资源。
