Takeaway: Medaka生产资源探测已接线；完整普通gzip真实推理及框架2/2通过，不变计算缓存命中，变异与还原队列仍在验证。

本轮继续解决Medaka资源身份和Flye压缩装配接口问题，仍使用完整细菌ONT样本及原始模型。生产代码增加每样本不使用缓存的资源探测，在消费者查缓存前核对运行上下文，并在计算前后核对资源身份。完整普通gzip输入已在真实生产探测和计算中成功，全部头部及DNA对应原始CLI软件基线，两条contig神经概率位置覆盖均为100%。普通gzip的实际nf-test原生与stub两例通过，新缓存队列也已完成基线和不变计算缓存命中。有效归档字节变化、损坏、还原与其他压缩形式的后续生产验证尚未完成，不能将正在运行的计划计作通过。下一步是核对真实队列终态和逐项trace，并继续补齐可选参数及完整执行环境边界。

## Scientific context and question

沿用NO-MISS sample_1_1完整已发布filtered细菌来源读段及同样本已抛光draft；其软件基线不是独立生物学真值。没有新下载、下采样、更换模型/阈值或引入病毒元素，不宣称完整细菌基因组无任何病毒同源片段。BioNeMo没有执行GPU替代计算；Rosalind与NGS Workbench技能的证据范围和生命周期规则继续用于结果复核。

## Question, lifecycle, and endpoint

MEDAKA_RESOURCE_PROBE声明cache false；消费者MEDAKA深缓存并接收显式身份val、receipt及四个helper path。ONT调用端已接入逐样本join与报告事件，共享配置使probe/consumer获得相同prefix。独立tests/nextflow/medaka_runtime_resources.nf使用原生产两个process，未复制工具实现。bin/medaka_runtime_resources.py使用此前验证的原生选择器、完整模型加载、兼容性及默认索引校验，计算使用完整任务私有draft及已选模型副本；原始资源不被原生索引写入。消费者实际运行未修改的原medaka_consensus，最后显式-m绑定同一已选模型；保留其他原生参数。默认non-RLE/非-x验证原相邻索引后重建私有索引；RLE和-x保持原生变换/强制重建分支，不读取原本不应读取的外部索引。可选分支实现存在不代表已逐分支验收。

## Key findings

- ordinary-gzip-v1：实际Nextflow26.10原生产probe和consumer两任务COMPLETED/0；完整普通gzip来自原Flye同一gzip -c编码契约，全部解压字节保持。完整native HDF重读和FASTA对应见该目录review.json，两条神经major位置覆盖各1.0，概率有限/五类归一化通过。这个输入不是本轮实际Flye重新组装的产物；证明压缩接口修复，不等于完整真实ONT平台。
- framework-gzip-v1：实际nf-test0.9.5 CI native/stub2/2通过，完整FASTA逐头部和全DNA比较，snapshot未更新。前置还真实执行一个probe以生成同运行上下文receipt。之后仅修正测试harness的字符串false判断；生产模块、四helper及nf-test来源与通过记录一致，frame来源差异单列在framework-source-review.json，不宣称整份旧来源表仍逐字节对应当前。
- cache-v1：测试harness把CLI字符串false当真，实际只有probe/0。驱动正确拒绝缺失consumer并退出1；不算缓存通过，也不是原生计算错误。当前harness显式解析字符串true，旧失败目录保留。
- cache-v2：baseline实际probe/consumer均COMPLETED，完整输出对应原软件基线；unchanged实际probe重新COMPLETED、consumer CACHED，完整结果仍对应。其他phase是否完成须读各phase的run.json及当前真实session，不从state文件推断运行或通过。
- main-p0-polishing：当前主入口导入解析后，原polishing_tools-unknown拒绝正确，0分析任务/0.command.sh；只是一个既有场景重放，不声称75全部重跑或成功主流程。

## Interpretation

真实普通gzip推理成功与全序列/神经覆盖复核，支持TA-096压缩输入接口的有界候选修复。不变缓存命中同时probe真实重跑，证明初步稳定身份；尚不能代替后续同大小同mtime变化/损坏与还原控制。将模型和draft复制到任务私有目录可避免原生写原输入旁索引，也使实际计算绑定已校验内容。上下文不同在消费者script闭包内拒绝，旨在发生于缓存查询前，仍以实际负例验证为准。结果不支持生物学错误率改善或整个工具/平台放行。

## Artifacts

根目录results/tool-audit/20261027-medaka-production/。

- Results：ordinary-gzip-v1/review.json及其trace对应work目录test.fa.gz/consensus_probs.hdf，cache-v2各已完成phase的run.json与work产品；不能列未生成阶段为结果。
- QC and visual reports：framework-gzip-v1/junit.xml，ordinary-gzip-v1/review.json中的完整概率覆盖；没有独立基因组质量图。
- Provenance：framework-gzip-v1/run.json、framework-source-review.json、cache-v1/baseline/exit.json、cache-v2/baseline/run.json、cache-v2/unchanged/run.json、main-p0-polishing/run.json，以及各命令/日志/trace。
- Model synthesis：本文件；先前独立门禁17CLI与坏MMI反例继续保留在medaka-resource-gates-20261027.md和medaka-real-ont-review-20261027.md。

## Limitations and blockers

实际缓存队列工具session72092，必须轮询工具确认实况；state.json仅为索引。源码在队列中被guard冻结，不在进行中修改生产模块/helper/harness来让验证漂移。当前TA-091与TA-096仍in_progress，99项正式有界verified及718接受来源清单不变。全环境/固定OCI/provider、RLE/force/regions及重试行为、其他隐式资源、完整主流程与独立科学准确率仍未由此认证。普通gzip带已有旁索引会明确拒绝歧义资源，现验证输入为Flye正常的无旁索引输出；BGZF/其他索引边界以对应实测为准。此前已经有采样/阈值/工具方法决定保持。

## Recommended next step

先轮询session72092，不重启活跃任务；观察phase终态并核对source guard、逐项trace、全部序列及错误阻断。依次证明有效模型归档同大小同mtime变化重算、坏模型/MMI/FAI查缓存前拒绝、恢复复用、运行上下文拒绝和plain/ordinarygzip/BGZF一致性。随后补可选CLI读取集合和实际调用端/后端边界，再决定有界接受；不能以本文件或排队驱动存在关闭问题。
