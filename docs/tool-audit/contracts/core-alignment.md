# 核心比对多样本接线

基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。BOWTIE2_ALIGN 接受 reads(meta)、index(meta2)、fasta(meta3) 三个输入；MINIMAP2_ALIGN 接受 reads(meta)、reference(meta2)。本地 caller 将每样本 queue 分别传入，没有先按 key 合并；process 内没有核对 meta 相等。独立 index task 的完成顺序不保证与 reads 顺序相同。

TA-022：results/tool-audit/20261020-pairing/pairing.nf 保留相同多 tuple 输入签名，用 val 载荷隔离路由；强制 reads A/B、indexes B/A、references A/B，在实际 Nextflow 26.10.0 build 14055（缓存 JAR）上输出 A-B-A、B-A-B。此为真实 Nextflow 语义复现，不是 Bowtie2/minimap2 生物学执行。trace 记录两个 task COMPLETED/0。[官方 multiple inputs 说明](https://docs.seqera.io/nextflow/process)亦说明多 queue 不会按 meta 自动关联。

已确认风险位置：CONTIG_COVERAGE、PLASMID_ABUNDANCE及Illumina/hybrid宿主去除的Bowtie2独立index队列。MINIMAP两个输入均由同一上游队列派生，其当前caller是否存在失配须单独实证，不能由签名探针直接断言。错配可能导致混样参考或错误 host removal，但具体每次生产运行是否触发取决于完成顺序。不得因为一个顺序恰好相同的运行通过就否定风险。

运行器恢复：本机 launcher 缺失，但 ~/.nextflow/framework/26.10.0/nextflow-26.10.0-one.jar 可用；Java21 运行。首次直接 jar 调用产生 cache serializer opens 警告；补 java.util/java.lang opens 的复验日志单独保留，未把首次警告当作无效运行。真实生信依赖及 nf-test launcher 仍需恢复。

修复应在 module 边界前把关联字段放在同一个 keyed tuple，或使用能够正确提供每样本 reference value 的子工作流策略；不要将整个多样本 reference channel .first() 作为通用修复。测试必须使用不同参考序列并强制乱序，检验每样本 BAM @SQ/序列身份。

2026-10-20续审：CONTIG_COVERAGE按样本join short/long再merge；PLASMID_ABUNDANCE两条量化链分别发射，hybrid明确将short_abundance用于跨样本统计，long链仅独立产出并进入done。该来源选择是已声明行为，未凭“没合并短长丰度”增加缺陷；已有多queue错配TA-022和统计实体/单位问题仍不受此静态检查消除。未运行真实aligner/CoverM。

## 2026-10-20 TA-022 固定版本真实比对补证

在results/tool-audit/runtime内恢复Bowtie2 2.5.4、SAMtools/htslib1.21、pigz2.8，版本与两个Bowtie2模块environment.yml完全匹配。官方conda-forge/bioconda38依赖显式URL+hash锁，下载计划92325363bytes，38个conda-meta版本/build/SHA均与解析计划一致，另记录实际可执行文件SHA；安装未替代其他模块1.24/1.23.1环境认证。

原BUILD/ALIGN模块实际调用原生工具，两样本不同12000bp随机参考，各20对100bp、无错误且有独立来源的reads。强制BUILD B先于A完成。旧三queue接线workflow和4任务均exit0，但A.bam的SQ为B_reference，B.bam为A_reference，各0 mapped；QNAME仍归本样本，说明文件名/RG不保证参考归属。候选reads.join(references).join(index)后再派生模块输入，在相同B先于A下4任务均成功、SQ/LN正确、每样本40 mapped。不是模拟BAM或按输出文件名生成期望量。

完整环境锁/输入hash/命令/trace/.command及BAM/SAM在results/tool-audit/20261020-bowtie2-native-pairing/run.json及environment.json。最初dotted withName配置语法错误的无任务校准保留config-calibration，排除真实8任务。此为修复前阶段记录；后续四个生产Bowtie2调用点已完成keyed修复与验证，详见2026-10-21更新。MINIMAP当前两输入来自同一producer，签名层反例不足以证明其当前caller确有失配，明确保留待验，不把Bowtie索引异步证据扩成所有long-read路径已实证失败。无CoverM、完整平台、容器或生物学性能通过结论。

## 2026-10-21 TA-022 已证实Bowtie2接线修复

CONTIG_COVERAGE、PLASMID_ABUNDANCE及Illumina/hybrid宿主去除四调用点，先按完整meta key合并reads/reference/index，再从同一matched tuple流派生模块输入；加入failOnDuplicate/failOnMismatch，保留nf-core输入签名、别名和参数。未改minimap2或算法/阈值。

恢复CoverM0.7.0/SAMtools1.24原生前缀，57个精确包身份核对并保存显式锁；仅新增下载23包约78.6MB，复用已缓存依赖。CoverM环境内minimap2依赖2.31未调用，不代表声明2.30/1.23.1长读环境已认证。实际BAM PG同时证明Bowtie2 2.5.4/sort1.21及merge1.24。

公开tests/run_native_alignment_pairing.py完整通过22真实任务：actual coverage/abundance14任务，原Illumina/hybrid host block各4任务；强制B索引先完成，全部SQ/LN/QNAME正确、每样本40 mapped，CoverM均值0.33755276与独立SAMtools depth和4000/(12000-150)一致；host准确去除20宿主对、逐字节保留5外源对，非header-only阳性。原四caller HEAD源叠加同一真实工具控制时，workflow照样exit0但SQ互换/0mapped，宿主过滤误保留全部25对，回归明确red。公开最终入口额外检查QNAME。

源码/原命令/输入/trace/.command/BAM/SAM/版本锁和校准过程在results/tool-audit/20261020-alignment-keyed-fix/receipt.json。初次配置在outdir前include发布规则导致null路径的运行单列publish-config-calibration并排除；最终配置顺序正确。TA-022仅按已证实Bowtie2问题关闭，未建立Minimap当前caller失败证据，更不认证完整FASTP/assembler/detector平台E2E或跨样本feature/count单位。TT-001原mock oracle仍未改；新原生独立真值回归不能替代修复旧mock本身。历史受错配影响的比对、去宿主、coverage及下游需重算。

## 2026-10-22 长读段宿主去除与管道失败（TA-033/057）

固定[SAMtools1.24 fastq手册](https://github.com/samtools/samtools/blob/1.24/doc/samtools-fasta.1)将 neither/both READ1/READ2 标记的记录归 category0；模块始终指定 -0，因此 stdout interleaving 不会接收未配对长读段。旧 ONT、HiFi、hybrid 消费 interleaved，真实原工具下两个宿主样本均输出空下游，尽管应分别保留3/4条reads；无宿主参考样本5条正常。三份修复前 host-removal caller 片段逐字冻结（只替换上游变量名），不是完整旧平台执行。

三个平台统一调用 LONG_READ_HOST_REMOVAL；仍用原 Minimap2 map-ont/map-hifi、SAMtools VIEW -f4。FASTQ调用false，消费other；保留meta/group和无参考旁路，临时preset移除。若 gzip 解压后无首字节，明确报“No non-host long reads remain for sample …”，拒绝空输入组装，hybrid不自动改为仅短读组装。报告保留原三个process的完成/输出记录。

TA-057：安装revision135d883a43b1a2324b4112cd270cf22e20835533的[nf-core mapper](https://github.com/nf-core/modules/blob/135d883a43b1a2324b4112cd270cf22e20835533/modules/nf-core/minimap2/align/main.nf)在默认bash -ue中没有pipefail。故意包装真实mapper，写完有效SAM再exit7，sort仍exit0；旧模块及workflow成功。现仅增加set -o pipefail，原失败码7阻止下游/发布；没有替换工具、预设或参数。上游blob e61e77eeaa0fd7af5d2de7718fd15cc5c49b8ce8与冻结before完全一致，当前差异另存local-patches/minimap2-align.diff，modules.json revision保留。

原生Minimap2 2.30/SAMtools1.23.1排序、SAMtools1.24过滤及FASTQ，独立人工20kb宿主A/B/非宿主P、正反向2kb reads、非恒定质量、gzip/含空格路径。最终8场景53条trace（before31/after22）符合独立ID/DNA/quality预期，全被过滤/故障无下游。故障为明确注入，不声称真实mapper自发崩溃。共享三模式55原生任务正例回归通过；均不代表湿实验宿主去除灵敏度/特异度。

TT-006修正显式未配对fixture的 -0 分类并拒绝未建模的配对BAM。新增TT-010：Bowtie2替身原把sample.fastq.gz错误写为sample.fastq.gz.1.gz，导致host样本未进入下游；真实固定2.5.4 wrapper512–535及3个原生命名场景说明应在末扩展名前插入.1/.2，%则替换，无扩展名则附加。修复后6单元方法全过，旧两类替身各3方法全红。短读宿主链仍明确全部传递的observer，无分类含义；宿主profile用逐记录短读来源验证，放弃仅凭clean后缀的错误断言。

真实main的ONT150/HiFi142/hybrid(OPERA)204及ONT无参考144任务经最终语义validator全部通过；其中仅三份host运行18个长读宿主工具任务为原生，其他CLI仍observer，实际R/Python另记。第二个hybrid assembler的额外尝试因缺SPAdes计划解析环境失败，不计通过。未进行完整真实组装/分类/平台、镜像、远端executor、nf-test或科学效果认证，TT-001覆盖度/计数filename oracle继续开放。历史受影响去宿主、组装、检测、定量需在新目录从去宿主步骤重跑。

证据：results/tool-audit/20261022-long-read-host/receipt.json；native-final/run.json、platforms.json、shared-regression/run.json、environment.json及bowtie-naming-native.json。保留initial/calibration和额外失败，最终台账仅引用明确验收记录。
