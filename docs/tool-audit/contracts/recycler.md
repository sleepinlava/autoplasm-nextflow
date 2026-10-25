# Recycler 首轮契约核对

基线 f57d0f91454ee0c99cf462ac9093bdf68349991a；取证日期 2026-10-20。

官方固定版本：[v0.7 README](https://github.com/Shamir-Lab/Recycler/blob/v0.7/README.md)，blob SHA `ac861c943f41c3055f459315ec3e93734e15bb40`。定位：Detailed usage / Preparing the BAM input。输入要求为同一个组装图的 FASTG、图节点参考上的配对比对（最佳匹配，过滤 supplementary）、排序 BAM 及索引；k 为该组装使用的最大 k。不能用同一样本的任意 assembly BAM 代替图节点 BAM。

生产路径：ILLUMINA 将 SPADES.out.contigs 送入 CONTIG_COVERAGE，所得 BAM 通过 PLASMID_DOWNSTREAM 送 RECYCLER；图来自独立 SPADES.out.fastg。contig 与 graph node 不是同一参考契约。测试也用独立 minigut.fasta 建索引。TA-002 不因同样本或进程退出码为零而消失。

TA-003：RECYCLER 输入只有 graph/bam，无 bai；测试的 bai 未 emit，生产 SAMTOOLS_MERGE 请求空 index_format。是否在空结果时不触发索引访问需真实阳性节点复验，不能作为正常支持依据。

TA-004：硬编码 k=55 没有关联实际图构建参数；尚未证明默认 fixture k 与该值不符，保留 evidence_missing。

容器声明 recycler:0.7--py_3，Conda 为 recycler>=0.62；实际安装版本、镜像 digest 未验证，二者不能视作已锁定的同一环境。历史运行保留为历史执行证据；阳性语义与当前代码未认证。

## 2026-10-21 Recycler固定版本输入契约补证

读取固定v0.7树commit12ce4dbb71fded2006d0c36c8f78187b4500f490，真实入口在bin/而非猜测src/路径，官方脚本/README/test源码归档evidence/recycler-v0.7-node-contract.json。下载官方FASTG16.17MB、BAM98.5KB、BAI1KB并逐个核对Git blob；恢复原生Recycler0.7 py_3，46个精确依赖（Python2.7.15/NX2.2/numpy1.16.5/pysam0.20.0，新增下载35.3MB），官方频道显式锁和原包身份核对留存。安装utils.py与v0.7原blob完全相同。

实测官方extractor生成3331条节点，原FASTG含6662条双方向记录；官方测试BAM只含14个定向SQ，名字/长度都属于该图，但不是完整3331节点BAM。最初完整字典假设失败已归档，不拿此局部fixture认证完整输入；第一脚本inspect.py遮蔽stdlib也已归档并更名，非工具环境故障。

真正重要的三组native函数反例：官方有索引BAM能找到预期外部mate，官方test_is_good_cyc中的负路径返回False；同一BAM移除BAI后mate为空、负路径返回True；换成有有效BAI但参考为A_reference的无关BAM，同样为空/True。原因v0.7捕获fetch ValueError后直接继续，is_good_cyc对空集合通过。此为真实函数/官方负例，不冒称完整CLI必输出该路径或已经完成科学假阳性基准。

TA-003由S2升级S0，缺索引不只是运行失败，可能静默失去配对证据；TA-002仍S0且得到indexed错误参考反例。两项均未修复。生产需从同一FASTG提取参考、用原组装的pairs重新比对/过滤supplementary/排序/索引，再将BAM+BAI完整stage并检查引用身份。官方推荐BWA，Bowtie2兼容性未经上游测试；不能未经方法评估就假定contig BAM或默认端到端模式等价。TA-004真实k的来源仍未验证，FASTG头length等于序列长度（差值0），不可用该差值猜k。完整命令/原数据/原生环境及观察在results/tool-audit/20261021-recycler-contract/run.json。

## 2026-10-21 Recycler输入校验组件（未接线）

bin/validate_recycler_inputs.py实现Python2/3兼容的FASTG记录检查、完整正向图节点SQ集合/长度、coordinate元数据、相邻bam.bai存在性与indexed fetch可用性。通过后记录graph/BAM/BAI SHA；错误返回2、有输入上下文且不写JSON。没有为官方14-reference局部fixture放宽为subset通过；真实生产必须先生成完整graph-node BAM。

公开tests/run_recycler_input_validation.py在原生Recycler0.7 Python2.7/PySAM0.20与SAMtools1.21上10/10通过：合法完整输入及缺/坏index、错误SN/LN、缺图节点、排序元数据、非FASTG、重复节点和空序列。数据为人工paired SAM经真实SAMtools生成并索引，不是mapper或Recycler生物学阳性。结果results/tool-audit/20261021-recycler-input-guard/receipt.json；测试入口和边界已写tests/nf-test/README。

TA-002/003仅改in_progress，没有关闭；RECYCLER模块及其生产者尚未调用该guard。下一步须同图提取节点、用原组装pairs重新比对、过滤/排序/index并成对stage，再接入guard。仅SQ/LN相同不证明DNA来源，index可访问也不是来源密码学证明；k、图邻接完整性、mapper选择/模式及完整cycle正负回归仍未完成。不要将组件10/10推成生产修复/P3或完整E2E。

## 2026-10-21 完整图节点比对准备的兼容性反例

已按固定 nf-core/modules commit a064a845f0c2afec03e02ae7e8cfb832486a2ea1 的环境声明恢复 BWA0.7.19-r1273 / SAMtools1.22.1 / htslib1.22.1，27个包逐项核对，显式锁与可执行文件SHA留存在 results/tool-audit/runtime/bwa-explicit.lock 及 results/tool-audit/20261021-recycler-graph-mapping/environment.json。此为原生准备栈，不认证声明容器或当前生产流程。

真实运行 Recycler0.7 官方 extractor→BWA index/mem→过滤0x0800→sort/index→严格输入校验。输入为已校验官方完整FASTG与从其中一个节点生成的人工精确paired reads；不是原始完整组装reads。3331条提取参考中1687条保留先出现的反向名称（末尾单引号），与Recycler mate lookup去除末尾单引号后的fetch名称不一致。校验返回2，完整失败日志保留，未删除关键断言或将字典检查放宽。

现有输入guard十例仅覆盖正向先出现的人工图，不能证明官方extractor兼容性；需补反向先出现的测试，并由专用生产者明确输出正向规范节点序列、验证序列方向与名称。禁止直接复用官方extractor后宣称TA-002修复。TA-002/003保持in_progress，k来源TA-004仍未解决；本次未执行Recycler完整CLI，也不作阳性/科学性能结论。

## 2026-10-21 正向参考组件与受控完整CLI验证

新增bin/recycler_graph_reference.py，复用graph_sequences解析真实正向记录并按节点名排序输出，避免保留反向首记录或只改名字不改碱基。6个独立单元案例覆盖反向先出现时AACG而非CGTT、正向先出现、邻接头解析、缺正向、重复与空节点。guard原有长度API保持不变；原生Python2.7/PySAM0.20+SAMtools1.22.1的公开测试现为12/12，加入reverse-first合法输入及primed BAM错误参考拒绝。没有放宽完整字典要求。

完整官方图经新组件提取3331条参考，逐条碱基与独立解析的原图正向记录一致；选择此前反向命名的长节点构造精确pair，BWA0.7.19→过滤supplementary→sort/index→guard的7项检查全过，primary2条均映射到预期节点。命令及来源SHA见results/tool-audit/20261021-recycler-canonical-mapping/run.json。数据是完整真实图+人工reads，不是完整原始reads或生产平台回归。

另执行实际Recycler0.7完整CLI：人工已知55bp闭合重叠的自环得到1条1200bp序列，按独立core的旋转/反向互补匹配；无环有向图得到0条。首轮负例误留反向自环而失败，原失败与图保留父目录，修正后独立final目录通过，非工具缺陷。证据results/tool-audit/20261021-recycler-cli-controlled/final/run.json；自环不使用多节点配对判据，不能替代官方负路径mate函数证据或科学基准。

组件仍未接入RECYCLER及生产者，TA-002/003仍in_progress，TA-004的实际SPAdes k未解决；未增加已关闭计数。下一步从同一SPAdes运行产物建立k来源，并整体更新生产/测试输入元组与索引staging、原模块真实回归。原tests/nf-test Recycler仅目录/任务存在断言仍待修复，不能用新CLI组件证据自动认证旧测试。

## 2026-10-21 SPAdes4.1.0最大k来源静态核对

读取生产声明匹配的ablab/spades v4.1.0：spades_stage.py blob6a563c67b405ab10f9a97a335ffdf61e89501fea，spades_iteration_stage.py blob2b56dc654a51679fee597789ea3945d3dc14eb3d。generateK按模式、read length和显式参数决定并裁剪迭代k；SpadesStage将latest更新为最后一次K目录，SpadesCopyFileStage从latest/assembly_graph.fastg复制最终图。故固定55不是可普遍替代的来源。原模块只发布FASTG与log，没有发出图与最终K目录的关联元数据。下一步核验原生4.1.0生成的执行计划/日志以及可追溯的最终copy source，避免用最大目录名或命令初始-k列表猜实际图k。TA-004仍evidence_missing，源文件全文与blob留evidence/spades-4.1.0-k-provenance-source.json；Conda dry-run只查询匹配版本依赖与体积，不计安装或运行通过。

## 2026-10-21 实际SPAdes4.1.0最大k证据（更新TA-004）

恢复23个精确包，新增下载11.95MB；安装spades_stage.py的Git blob与官方v4.1.0完全相同。机器16CPU/可用内存约9GB/磁盘117GB；本次限制2线程/2GB，使用官方包自带E.coli1K pair，--meta --only-assembler -k21,33。原生组装退出0，最终FASTG非空。run_spades.yaml中唯一copy_files输入K33/assembly_graph.fastg→最终assembly_graph.fastg；K33/configs/config.info为K33/main_iteration true，输入输出SHA相同且日志显示K33/copy/pipeline全部finished。9/9检查见results/tool-audit/20261021-spades-k-provenance/run.json。最初直接调用shebang继承hostPython3.15，保留k33作校准；正式k33-fixed-runtime显式前置环境PATH，核对执行计划使用该prefix的Python3.15，并保留环境与数据哈希。

TA-004由evidence_missing改mismatch：已确认支持的显式SPAdes k参数可产生k33真实最终图，Recycler固定55并非普遍正确。尚未修改k消费者，fix仍planned、不增加关闭计数。不能把当前默认fixture实际k写成33，也不能用本次小组装认证真实平台或科学效果。可行的来源链为同次运行的最终copy source + 对应config + graph bytes + 成功结束证据；不得仅取最大目录名/初始-k/FASTG长度差。下一步实现图与k同元组的可追溯生产输出，修复Recycler的完整输入链。

## 2026-10-21 Recycler完整接口修复与当前证据

TA-002/003/004及本轮新增TA-051/052已完成本地接口修复与限定范围验证。SPADES4.1.0的同次成功输出新增recycler_graph元组(meta,FASTG,k_provenance.json)。collector在组装task内核对唯一最终copy_files计划、同目录K配置/main_iteration、图字节及成功标记，不取最大目录名或初始参数猜k；图SHA进入元数据。嵌入辅助脚本内容进入task脚本/缓存哈希，容器不依赖宿主仓库脚本路径。原vendored模块revision6d46786420b4d7bc88eba026eb389c0c5535d120保留modules.json，仅本地新增输出/取证适配。

PLASMID_DOWNSTREAM从同次图元数据与实际用于组装的短读配对（QC/去宿主之后）按完整meta键严格join；同一tuple逐级传递，专用RECYCLER_REFERENCE取真实正向节点，RECYCLER_ALIGN使用固定BWA0.7.19/SAMtools+htslib1.22.1建索引、比对、过滤0x0800、排序并同时发出BAM/BAI。管道明确pipefail，部分SAM后mapper报错也不能被排序掩盖。消费模块在recycle前验证完整SQ/LN、可用相邻BAI、图/元数据SHA和合法实际k，输出目录保留input_contract.json及graph_provenance.json。Recycler Conda从范围改为=0.7，与实际审查版本和现有容器声明一致；原生显式锁和镜像执行认证仍分开。

入口仅允许Illumina/metaspades或hybrid/hybridspades的Recycler组合；前者和后者分别接入原SPAdes元数据及组装short pairs。5个不兼容组合P0均精确报错且0任务/0.command.sh，2个支持组合的解析控制到预定样本表错误才停止。SCAPP后续已按用户要求删除；gplas2的其他平台/图资格仍属TA-007未决，不能因此关闭整条问题。

新增TA-051：原生实际SPAdes E.coli1K配对产生只有孤立节点的合法图，索引/参考/k均正确后原Recycler0.7因percentile([])崩溃。新driver只对经实际get_fastg_digraph证明0边的图明确写零环文件及skipped_no_graph_edges状态；不捕获工具异常转成功。新增TA-052：受控1000bp环的k33图曾因上游get_long_self_loops/get_spades_type_name及嵌套覆盖计算省略k、隐式默认55而静默漏检/错长度。固定版本driver验证三函数默认签名后统一实际k，通过runpy运行原CLI，明确记录max_k_default_adapter；不修改安装包或替换算法，显式参数仍优先。旧非55结果、旧contig-BAM输入结果需重算；这属于有结果影响的参数一致性修正，不能声称历史结果可比。

真实数据：下载既有real-nodes-datasets.lock中的minigut pair6.72MB，逐一核对size/Git blob/SHA。最终原始P3工作流原生4任务新workdir无缓存完成（SPAdes4.1.0 --meta，2CPU/2GB，约40s；完整原始pair，无裁剪），317正向节点/260图边，实际k55。完整字典/图/BAM/BAI哈希一致，得到1条1871bp序列，独立解析能对应原图唯一自环方向的去k序列；同输入直接原recycle.py的FASTA/path两个文件逐字节相同。证明输入/输出/调用一致，不等于该环具有独立生物学质粒真值或方法准确率。首次同数据在沙箱内因Python3.15 forkserver Unix socket PermissionError失败，保留minigut目录；允许该本地通信后minigut-native及最终pipefail源码minigut-final两次4任务成功，均保留原命令/trace/task脚本，不改成only-assembler规避失败。

其他证据：provenance单元8/8、正向参考/元数据单元10方法（含5类坏k子场景）通过；原PLASMID_DOWNSTREAM的实际SPAdes双样本k33/k55共8任务明确0边/0环；受控原模块k33/k55双样本6任务各输出独立真值1000bp环与正确header，修复前k33空、k55文件修复后不变；原RECYCLER模块四类负例（缺BAI、错图SHA、错参考、显式工具退出23）精确失败且无已发布环；mapper部分SAM后退出23反例只完成reference、align失败23、consumer不运行。ABRicate受影响的6路由/8observer任务重放通过，非真实CARD搜索。

源代码25文件的focused差异以此前baseline+audit patches重建，并逐个对照上一轮累计SHA/原489文件receipt验证，见patches/TA-002-TA-003-TA-004-TA-051-TA-052.diff与results/tool-audit/20261021-recycler-production-fix/source-state.json；不会把先前TA-041/009/022补丁混入本修复。README与tests说明同步当前契约，原Recycler nf-test移除目录存在/未使用helper断言，改为hash/k/state/准确产物名检查；nf-test loader/JUnit及容器未执行，不能把原生counterpart升级为框架或镜像认证。完整Illumina/hybrid QC→报告及科学基准仍未完成。

本轮收尾：最终pipefail源码的minigut-final再完成4原模块任务，无缓存；FASTA/path与同输入直接Recycler0.7 CLI逐字节相同。final-zero用最终源码重跑原SPADES/下游8任务通过。BWA mem显式partial-header/exit23 observer证明producer失败23且consumer未运行；原consumer四类拒绝/失败传播均通过。当前main的35个独立P0场景全部重放（19registry、原11、5新增Recycler资格），两个允许组合解析控制另计；首轮11误用minimal config导致错误提前，本轮保留失败并使用原combined config纠正，不放宽诊断。p0-main-cases.tsv已关联当前main哈希，status生成器改按unique case映射计算，避免重复运行加大分母；运行历史保留。完整证据receipt.json/source-state.json及环境锁、trace、任务脚本见results/tool-audit/20261021-recycler-production-fix/。审计台账现61问题/16已验证/45未决，S0/S1仍有未决，整体目标继续。
