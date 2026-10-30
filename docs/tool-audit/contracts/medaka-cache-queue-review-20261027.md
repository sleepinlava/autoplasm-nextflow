Takeaway: Medaka生产缓存验证队列cache-v2已真实终态，14阶段全部符合预期；source guard与原始资源在队列后复核不变，TA-091/TA-096仍不关闭。

本轮按 [生产进展](medaka-production-progress-20261027.md) 的既定下一步，对实际缓存队列session72092的终态做独立复核：会话已结束、无活跃后台任务，驱动返回0且pass_bounded_production_checks为true；复核不止读state.json，而是逐项核对14个phase的run.json/trace/nextflow.log，并在队列结束后重新计算11份源码guard与4份原始资源SHA256，全部匹配，无漂移。

## Scientific context and question

沿用NO-MISS sample_1_1完整filtered细菌读段、同样本已抛光draft与固定Medaka 2.2.2 CPU原生SUP5.2.0模型；没有新下载、下采样或更换模型/阈值，不涉及病毒元素。软件基线仍不是独立生物学真值，本复核不宣称错误率改善。

## Question, lifecycle, and endpoint

问题：生产接线的MEDAKA_RESOURCE_PROBE（声明cache false）+ MEDAKA消费者（深缓存）是否满足不变复用、有效内容变化重算、损坏在查缓存前拒绝、还原复用、运行上下文在查缓存前拒绝、plain/ordinary-gzip/BGZF一致。终点为14阶段队列真实终态加队列后source/原始资源复核。

## Key findings

- baseline：probe COMPLETED、consumer COMPLETED（hash 9a/2d5a60），完整FASTA头部/DNA与原生软件基线一致。
- unchanged：probe真实重跑COMPLETED（probe不缓存），consumer CACHED自baseline同hash；证明不变输入稳定复用。
- valid-model-content-change：模型归档仅gzip头mtime字节变化（同大小同mtime，解压内容不变但归档身份不同），consumer hash变为f4/c0d632并COMPLETED重算；restored阶段consumer回到9a/2d5a60并CACHED。
- bad-model-trailer：probe exit 1，完整模型流读取抛gzip.BadGzipFile "Incorrect length of data produced"；无consumer任务，拒绝发生在查缓存前。
- bad-mmi-magic / bad-fai：probe exit 1，"Adjacent Medaka index differs from native reference rebuild: .map-ont.mmi / .fai"；无consumer任务。
- runtime-mismatch：probe COMPLETED后consumer从未提交，ProcessUnrecoverableException "Medaka resource probe/consumer runtime mismatch before cache lookup" 在消费者script闭包抛出（lib/medaka_runtime.nf:14）；runtime-restored后consumer CACHED。
- ordinary-gzip / bgzf：probe+consumer均COMPLETED，完整FASTA与原生基线一致；连同baseline的plain输入，三种压缩形式结果一致。
- 队列后复核：11份guard源码与4份原始资源（模型归档、draft FASTA、FAI、MMI）SHA256与队列起始记录逐一匹配。

## Interpretation

结果支持TA-091资源身份/缓存控制与TA-096压缩接口的有界候选继续成立：缓存键绑定已校验资源内容身份，同大小同mtime的有效归档身份变化触发重算，损坏模型/索引在probe阶段（cache:false、必先执行）拒绝，运行上下文不匹配在消费者查缓存前拒绝，还原后复用基线结果。仍属候选，不按本复核关闭问题。

## Artifacts

根目录 results/tool-audit/20261027-medaka-production/cache-v2/：run.json、state.json、14个phase各自run.json/exit.json/trace.tsv/nextflow.log及共享work目录。固定复核数据见 [证据](../evidence/20261027-medaka-cache-queue-review.json)（含上述全部run.json SHA256）。

## Limitations and blockers

harness声明范围不含生物学基因组准确率、可选RLE/force/regions分支、重试行为、全环境/固定OCI/provider与完整主流程。ordinary-gzip验证输入为Flye正常无旁索引输出；带旁索引的歧义资源拒绝此前仅独立验证。99项正式有界verified、2退役与718接受来源清单不变。

## Recommended next step

补可选CLI参数读取集合（RLE/-x force/regions）与实际调用端/后端边界验证，再决定TA-091/TA-096有界接受；随后按原计划推进MOB Recon/Typer默认非病毒资源、Dorado隐式模型，并独立复核TA-092/093/094/095候选。
