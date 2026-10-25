# QUAST真实节点局部验证

2026-10-20；生产基线f57d0f91454ee0c99cf462ac9093bdf68349991a，原modules/nf-core/quast/main.nf未修改。实际Nextflow26.10.0调用已安装QUAST5.3.0（c3eb988a），与模块声明版本5.3.0一致，native依赖环境与容器build不作等价认证。

数据来自锁文件plasmid-datasets.lock.json：nf-core/test-datasets commit618f1541382c4ad49eff566dadf13d5ccbd0ebb4，data/genomics/prokaryotes/plasmids/pUTI89/pUTI89.fna.gz。GitHub connector按固定revision读取base64，落地后核对35478bytes与Git blob6fffe679b2177ba7d9d22783c8571800bb70caa6完全一致；gzip/plain SHA256、原NC_007941.1 header和独立序列指标见data-receipt.json。未使用mock数据，也未生成/剪裁新的“生物学真值”。

两次原模块真实执行：plain FASTA与原gzip，各workflow/task exit0、各一个COMPLETED任务，未命中旧缓存。未提供reference/GFF，与生产QUAST调用形状相同。

| 指标 | 独立序列计算 | QUAST两次输出 |
| --- | --- | --- |
| contigs | 1 | 1 |
| total length | 114230 | 114230 |
| largest contig | 114230 | 114230 |
| N50（单contig） | 114230 | 114230 |
| GC | 按原序列逐碱基计数 | 51.03%，与独立值四舍五入一致 |

完整命令、config、trace、.command.sh、原报告及receipt在results/tool-audit/20261020-quast-real/run.json与gzip/run.json。资源限制每task1CPU/2GB，执行前磁盘可用119G，无数据库/模型下载。报告参数仅做基础统计，未做reference alignment、misassembly或真实组装效果基准；不是五个平台E2E，也不证明其他版本/容器/profile通过。

这是一项真实P3级节点基础统计证据，与先前synthetic CLI/stub探针区别记录；不能把同一tool的两种格式计成两个工具。该模块整体仍investigating：多FASTA、短/空assembly、reference/GFF、生产发布与其他后端边界尚待验收。

## 参考分支与非致命降级

2026-10-20：同一锁定pUTI89，gzip组装与plain参考逐字等同（解压SHA一致），原QUAST模块增加真实reference输入。首轮workflow/task仍exit0，但日志non-fatal ERROR报告Minimap2编译失败，只做basic stats，Genome fraction/misassemblies/NGA等字段缺失。这不是“参考比对通过”。make.err根因为ccache只读文件系统；已保留初始报告、日志和错误。

按sandbox指令通过require_escalated编译QUAST自带Minimap2，make exit0，编译器/二进制SHA和版本2.28-r1209记录build-receipt.json，无网络下载，未改生产/测试源码。完整build stdout只存在工具会话，receipt明确这一证据限制。

随后新work目录重跑，原module/相同输入真正完成reference alignment：Genome fraction100.000%、misassemblies0、mismatches0/100kb、indels0/100kb、NGA50和Largest alignment均114230bp，均与自比的独立预期一致；非致命ERROR0。输出misassemblies/unaligned等可选路径状态也记录。完整两个状态的命令/config/trace/报告见results/tool-audit/20261020-quast-reference/run.json。

因此当前QUAST局部证据包含basic plain/gzip与reference自比，仍是一个工具、一个真实plasmid sanity fixture。无法外推复杂错组装检测、参考差异/负例、基因feature或其他平台/后端。提供reference的验收不能只检查exit0或report.tsv存在，必须检查所需比对指标及错误日志；未把原无reference基础统计路径因此认定为失败。
