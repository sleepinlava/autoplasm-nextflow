# QC 与长读长输入输出

2026-10-20；基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

TA-033：宿主去除后的长读长 BAM 经 SAMTOOLS_FASTQ_HOST(interleave=true)。模块始终设置 -0 prefix_other.fastq.gz，stdout 重定向 interleaved.fastq。固定 [samtools 1.24 bam_fastq.c](https://github.com/samtools/samtools/blob/1.24/bam_fastq.c) 的 which_readpart 用 READ1/READ2 flags 分桶；长读长两位均未设置，属于 category 0。-0 指定其输出文件。ONT/HiFi/hybrid caller 却 mix .out.interleaved。相同模块在初始 BAM 输入分支已正确消费 .other，宿主去除分支没有沿用。当前没有真实 samtools 二进制，保留静态确认差异，不声称真实节点复现或已量化损失比例。

TT-006：mock_tool.py fastq 以有无 -1 选择流，而不是 READ1/READ2 flags。interleave 时 stdout 始终写全部 reads，违背显式 -0 的真实行为；默认 mock 样本也没有 host_reference，所以仅运行现有无宿主去除 E2E 无法覆盖此链。应有真实 samtools 的输入记录分类和留存 ID 对照。

TA-034：FASTP 本地 paired 重命名补丁将 emit glob 收紧为 clean.fastq.gz，但 single-end/script 和 stub 的命名仍为 fastp.fastq.gz。results/tool-audit/20261020-fastp 使用原模块、实际 Nextflow 26.10.0、stub-run 及仅返回版本字符串的 fastp double；SE 文件存在但 reads emit 为 ABSENT，PE 正常 emit 两文件。此为模块输出契约测试，非真实 fastp 执行。当前主流程 short reads 只接 PE，因此该项影响模块声称的 SE/interleaved 与 vendored P1，不能说默认 PE 链已因此失败。

本轮还阅读 FASTQC 后缀/alias、FILTLong 参数/输入、NanoPlot plain/gzip 支持、HiFiAdapterFilt 本地包装和 Flye/Medaka 接线；MEDAKA 用单个 keyed join tuple，未重复报 TA-022。未进行相关真实阳性/空读段/样本乱序验证，均保持 investigating。

SHORT_READ_MULTIQC_INPUTS 的 JSON/ZIP 收集与 SAMPLE_ID_VALIDATION 的全表先校验后 flatMap 已检查。实际 sample-ids suite 5 场景（合法、重复、空、空格、路径分隔）通过；这是导入生产 validation workflow 的局部回归，不是完整主入口 P0。日志 results/tool-audit/20261020-qc-input/sample-ids.log，--keep-temp 保留全部 harness/trace。仅检查 Nextflow 主版本并不能单独证明每个测试都启用特定语法 parser。

2026-10-20 长读长输入选择续审：ONT/hybrid原branch顺序pod5→bam→fastq，HiFi为bam→fastq。多个字段同时非空时选第一匹配，未发现显式互斥检查或合并输入；这里保留为实际声明/文档澄清边界，不未经需求依据将优先级本身当确定性缺陷。初始BAM消费者取SAMTOOLS_FASTQ.other，与宿主去除错误桶TA-033不同。Dorado/hifiasm-meta当前无全后端容器认证，不能由原生P3历史推导docker/singularity支持；本次未basecall/assembly。
