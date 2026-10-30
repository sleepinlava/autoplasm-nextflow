# 工具接口审计进度（首轮）

2026-10-20，代码基线 `f57d0f91454ee0c99cf462ac9093bdf68349991a`。工作区原有 .gitignore 修改和 docs 未跟踪内容保留。本轮仅新增审计材料，未改生产代码。

全量文件盘点：101 个 .nf = 32 自定义模块 + 52 vendored 模块 + 16 子工作流 + main.nf。inventory.tsv 是词法盘点，登记定义、include/alias、直接调用者、环境声明、候选测试引用。它不是运行依赖图；启用条件、配置覆盖、完整命令契约和路径矩阵尚待解析，M0 未完成。

首批四对象：OPERA-MS 与 Recycler 已发现接口差异；Platon 与 PLASMID_DETECTION 仍 investigating。其余 97 个文件 not_started，不能称全量审计通过。findings.tsv 当前 2 个 S0、2 个 S2；其中 TA-004 为待证实的来源风险，其余为静态差异。所有修复 planned；当前真实验证为 0。

历史状态冲突：COVERAGE.md 的 Recycler done 指真实运行失败（缺 k）；REAL-NODES-RESULTS.md 报告随后修复通过。两者描述不同运行事件，不能统一成当前语义通过。Platon 的 COVERAGE new 与真实报告通过同样需要原始日志、代码/数据标识迁移；本轮未完成迁移。

验证阻塞：PATH 无 nextflow/nf-test；tests/nf-test/env.sh 指向的 results/nf-test/runtime 目录不存在，无法直接复用所声明运行器。当前磁盘可用约 122 GiB、内存 available 约 12 GiB；未启动数据库下载和大型任务。未执行真实 P3/P2/P4，无缓存命中或阳性分支认证。

下一步：补全 M0 的运行依赖/配置/支持矩阵；确认 Platon 固定版本来源（v1.7 下两个猜测源码路径 404，不代表仓库不可用）；验证可选 join 的多样本/空结果行为；随后逐项最小修复与真实回归。两个上游仓库均通过 GitHub 插件读取，未创建远程 issue/PR。

## 第二轮检测链审查

固定版本 Platon 源码入口已确认，新增 TA-005 压缩输入接口差异（S2）；SCAPP 重建环 ID 与 assembly ID 混用已最小复现，新增 TA-006（S0）。当前共 3 个 S0、3 个 S2，均未修复；TA-004 仍为 evidence_missing。原始上游证据保存于 evidence/detection-upstream.json。四个校准对象均有首轮契约文档，但尚无闭环通过项。

新增 history.tsv 从现存 JUnit 提取 Platon/Recycler 两条通过记录；未找到可认证当前代码的 SHA，保留历史状态。共识现有单元测试已启动，其结果另记；人工复现只证明 ID 接口错误。Nextflow 连接规则的运行验证仍未执行。

现有共识单元测试：`python3 -m unittest discover -s tests -p test_plasmid_consensus.py`，9 项通过（63.477 秒）。该测试集未覆盖 TA-006，不能抵消人工复现失败。台账 TSV 和上游 JSON 的结构检查通过。

## 第三轮入口、平台与 MAG 接线

新增 platform-matrix.tsv、support-matrix.md、可重复生成的 scan_wiring.py 及 include-edges/reachability/config-selectors 台账。101 个文件，162 导入符号，95 文件词法可达，0 未解析 include，130 配置声明；运行时分支和 selector 优先级尚未验证，M0 仍未完成。

新增 TA-007 图依赖工具无输入兼容校验（S2）、TA-008 CONCOCT/SemiBin 最终结果路由丢失（S0）、TA-009 ABRICATE 可选参数位置与 gate 不一致（S2）。当前累计 4 个 S0、5 个 S2；均未修复。MAG 子工作流已静态审查，实际 CLI/数据库/运行仍未验证。

当前 inventory 状态：8/101 个文件 investigating，93/101 not_started；没有 matched 或真实节点认证通过项。六个主入口未导入文件已登记，不自动视为应删除。新增五个平台接线矩阵，不改变计划中的支持分母。

## 第四轮跨样本实体、计数与缺失样本

新增 TA-010/012（S0）：局部 contig ID 跨样本身份错误、coverage 作为 DESeq2 count proxy；TA-011/013/014（S2）：空 raw_count 误判导致全零失败、metadata-only 样本静默消失、单 feature alpha 指标 NA。两个非空人工接口复现产物在 results/tool-audit/20261020-abundance 和 20261020-deseq。均为 native R，版本差异与适用边界见契约；不计真实生信节点通过。当前累计 6 个 S0、8 个 S2。科学计数/统一参考的修复必须单独评估可比性，尚未修改生产代码。

## 第五轮报告与宿主关联

新增 TA-015（S0）：报告扫描共享发布目录导致旧样本混入，且缺完整文件依赖；TA-016/017（S2）：固定方法描述声称未执行步骤，机器可读 report_data.json 未声明输出。人工 assembly 报告复现已保存，不算 Nextflow 发布竞态或 R Markdown 渲染复验。当前累计 7 个 S0、10 个 S2。宿主三种关联的本地数据流与过滤规则已静态审查，完整算法依据与科学性能仍未认证。

宿主关联现有脚本单元测试 22/22 通过（49.653 秒），日志与运行元数据已登记。此为局部人工测试，不能抵消上游 MAG/跨样本实体缺陷。新增 .gitignore 例外保留审计台账及脚本，使其能进入后续版本审查；原有忽略规则不删除。

## 第六轮可选包装器

新增 TA-018 PlasMAAG manifest 类型不符、TA-019 COPLA 参数/输出约定不符、TA-020 COPLA 将整样本视为单一质粒、TA-021 gplas2 格式/入口待固定版本确认。固定上游 parser 复现 COPLA argv 退出 2，位置参数对照成功；不是生物学工具执行。当前累计 8 个 S0、13 个 S2（其中 TA-004/021 evidence_missing）。其余已读包装器仍 investigating，未认证。

## 第七轮核心比对与 tests 逻辑

用户明确要求同步审查 tests。新增 TA-022 多 queue 输入按完成顺序混配（S0），及 TT-001/002/003 测试 oracle/阳性断言/P4 非空覆盖缺口（S2）。已恢复缓存 Nextflow JAR 26.10.0，在两个实际 task 上复现 A reads+B index。初次 JAR JVM opens 警告保留；补 opens 复验无 WARN/ERROR。tests-inventory 登记 63 个测试源码/配置/harness 文件，尚未完成全量逻辑审查。

## 第八轮测试前提、断言与配置

新增 TT-004 数据库准备失败仍成功退出，离线复现已保留。prepare_data 8/8 单元通过；r_mock 54/54 检查通过，但计数源和发布依赖不在其覆盖内。历史 source/report hash 归属已核验，default/test/podman/conda 当前配置解析成功。当前 9 个 S0、17 个 S2；tests 中 24/63 个文件 investigating，剩余继续审查。

## 第九轮检测解析与测试格式

新增 TA-023 PlasX 无分类列低分仍阳性（S0）、TA-024 PLASMe 阳性输出文件名未被识别而静默转空（S0）、TA-025 GFF/gene-call 注释契约不符（S2）。消费者和原 Nextflow wrapper 的人工格式复现均保留。当前 11 个 S0、18 个 S2；新检查不视为真实分类工具运行。

## 第十轮 nf-core 注释与 typing

新增 TA-026/027 核酸被当蛋白输入、TA-028 RGI local load/global main 数据库范围不一致、TA-029 MOB recon 输出未发布；新增 TT-005 vendored 测试辅助依赖缺失。固定版本依据保留 annotation-upstream.json。当前 12 个 S0、22 个 S2，含5个TT。未执行真实工具与数据库，不据此给默认注释路径完整放行。

## 第十一轮 MAG 文件/参数契约

新增 TA-030 DAS Tool 缺 --write_bins、TA-031 GTDBTk 默认扩展名排除当前 bins、TA-032 CONCOCT gzip 输入缺适配。固定源码和默认 parser/筛选对照保留；真实分类未运行。当前累计 13 个 S0、24 个 S2。

## 第十二轮 QC 与输入转换

新增 TA-033 长读长宿主去除消费错误 FASTQ 输出桶（S1），TT-006 对应 mock 分类错误/未覆盖宿主去除（S2）；TA-034 FASTP SE 文件与 emit glob 不匹配，已真实 Nextflow stub 对照复现（S2）。局部 sample-ID 验证 5 场景当前通过。当前累计 13 个 S0、1 个 S1、26 个 S2。

## 第十三轮比较分析与宿主 profile

本轮未新增确认缺陷。Catalog 单元7/7和原生产模块 Nextflow cache/stale/empty suite 当前通过；固定 MMseqs 18-8cc5c 参数定义明确 cov-mode1为target coverage。BLAST/MetaPhlAn/Kraken2本地调用类型与共享value检查已记录，完整工具与数据库行为继续 investigating。

## 第十四轮来源与环境台账

全部52个vendored main.nf已按固定commit比对：45一致、7本地差异，补丁单独保存。72份环境YAML和131项依赖规格入账。新增TA-035 SCAPP后端版本约束不一致（S2）。本机geNomad1.12 cleanup源码复核纠正配置注释线索，不将未经运行的目录缺失作为事实。当前13个S0、1个S1、27个S2。

2026-10-20 结构/统计批次：新增 TA-036（ITR 不足以推断环状）、TA-037（not_circular 子串误判），原生 R 人工反例保存；Welch 正常值与独立 SciPy 一致。四个剩余 .nf 完成首轮阅读，全部 101 个仅 investigating，未计作审计闭环。当前 43 问题，S0=14/S1=1/S2=28；生产修复未执行。

2026-10-20 网络边界：TA-038 原生 R 复现过滤后全零样本列保留；核对 FastSpar v1.0.0 绝对计数要求和独立 bootstrap 步骤，未把缺失 p-value 当作未声明功能的接口错误。当前 44 项：S0=14/S1=1/S2=29。

2026-10-20 tests 批次：22份此前未检查的测试/配置/harness 来源进入 investigating；merge unit 5/5 与实际 NXF host-routing adapter 通过。补充 TT-002 的重复 route、索引有效性、FASTQ完整性与 final assembly 身份等遗漏，不重复累计相同类别。生产未修改，真实 P3 环境仍待恢复。

2026-10-20 linking/tests：剩余12份来源首轮阅读完毕，63份全部 investigating，非闭环通过。实际 NXF merge→coabundance 局部回归通过；toy SAM有效性、周期序列oracle与前5contig伪质粒集合的证据边界写入 tests-review；问题44项不变。

2026-10-20 TETRA：固定pyani v0.2.12 数学函数与原R独立对照，新增TA-039（S0方法数值不一致、阈值两侧）和TA-040（S2跨MAG contig人工kmer）。原CLI确认关联输出；未修改科学方法。共46项：15S0/1S1/30S2。

2026-10-20 关联方法续审：SAM有效长度边界三组probe与共丰度独立Pearson/BH数值对照完成。区分consumer标记信任与真实aligner错误，未在证据不足时新增S0。累计46项不变，真实科学基准尚缺。

2026-10-20 主入口：原validate函数实际NXF四场景复现未知工具名不校验，新增TA-041(S2)。已知Platon缺DB和非法平台对照正常。47项=15S0/1S1/31S2；不声称全主入口P0完成。

2026-10-20 共识边界：原R六场景，新增TA-042(S2权重校验)、TA-043(S0样本名影响工具身份和最终FASTA)。累计49项=16S0/1S1/32S2；生产未修改。

2026-10-20 共识ID续审：四个原CLI边界，新TA-044(S2重复ID静默覆盖与记录数不一致)；未知预测ID归既有TA-006证据，不重复累计。50项=16S0/1S1/33S2。

2026-10-20 报告：新增TA-045(S0)，合法ID内含输出后缀导致样本合并及不同来源计数混合。原生R复现，与TA-015异步/陈旧文件独立。51项=17S0/1S1/33S2。

2026-10-20 可选宿主：新增TA-046(S2) HOTSPOT默认CRLF导致缺失Species被当宿主；原awk对照复现。PHF固定源码/模型仍证据不足，本次访问失败未泛化为不存在。52项=17S0/1S1/34S2。

2026-10-20 diversity：4场景原R+独立参考，新增TA-047(S2非法coverage文本静默0)，正常alpha/beta数值对照通过，负数失败如实区分。53项=17S0/1S1/35S2。

2026-10-20 DESeq：补齐固定1.42.0源码静态依据TA-011/012；新增TA-048(S0数字sample ID类型转换合并)。原CLI两场景，数值相同仅ID前缀不同，0行vs120行。54项=18S0/1S1/35S2。

2026-10-20 ID传播：8个原R运行扩展TA-048至三个额外consumer、literal NA与numeric positional indexing，已有单项更新而非累计新问题。54项不变。

2026-10-20 coverage/network：复核hybrid明确short统计来源，不新增无证据缺陷；实际NXF补TA-038过滤后全空矩阵仍被路由。489份当前tracked来源哈希归档，production/tests相对HEAD无diff。54项不变。

2026-10-20 MAG质量链：CheckM2固定1.1.0源码确认列表gzip/plain兼容，原分派两组probe通过，排除把GTDB目录扩展问题泛化给CheckM2的猜测。模型/DB未执行，不新增问题，54项不变。

2026-10-20 长读长/主入口：输入priority静态复核不新增缺陷；原main三项P0按预期拒绝且无任务，初次runner配置覆盖错误保留为非通过后修正。54项不变，未给P0全部/平台E2E放行。

2026-10-20 主入口P0续验：原main剩余8/8与先前3/3合计11/11当前测试对应场景；逐项stderr校验，均无任务。并非完整契约分母/成功E2E/nf-test框架认证。问题54项不变。

2026-10-20 SemiBin：固定2.4.1允许no-bin，原NXF module阳性/空输出对照新增TA-049(S2必需glob拒绝合法空结果)，stub四bins掩盖边界。55项=18S0/1S1/36S2。

2026-10-20 注释续审：新增TT-007(S2 IntegronFinder --gbk stub执行文件名)，原NXF正/反对照0/127。AMRFinder本地-n/显式DB静态匹配，未冒充真实工具运行。56项=18S0/1S1/37S2，TT7。

2026-10-20 sequence路由：原suite声称成功但duplicate负向oracle假通过，独立子case再跑workflow0/2任务完成；新增TT-008(S2)。正常可选输入routing局部通过，科学方法未认证。57项=18S0/1S1/38S2，TT8。

2026-10-20 负向oracle：5个expect_success=False调用点建立映射；原CRISPR suite5次观察，未将共享断言弱点泛化成全部实际假通过。main-disabled成功范围纠正为仅未触发CRISPR guard，实际平台检查失败。57项不变。

2026-10-20 真实节点：恢复一个已锁真实pUTI89输入（35KBgzip），原QUAST5.3.0模块plain/gzip均通过，独立基础指标一致。首次当前native真实P3局部证据归档，不再笼统称当前零真实节点；仍未全量P3/平台认证。57项不变。

2026-10-20 MultiQC：原模块native1.33汇总真实QUAST指标保持，发现测试锁1.33与模块1.35差异TT-009(S2)。未升级依赖/伪称1.35验证。58项=18S0/1S1/39S2，TT9。

2026-10-20 QUAST reference：首轮nonfatal降级被语义断言发现，ccache sandbox阻塞按权限流程make后修复，本地Minimap2构建receipt归档；新目录参考自比全部明确指标通过。58问题不变，不把初始环境降级报默认生产缺陷。

2026-10-20 按阶段D最小修复TA-043：新回归先红3subcase，最终11/11及原NFX包装器2/2通过；工具身份只按producer suffix，算法/权重不改。58台账中已验证修复1项，仍未决57项（17S0/1S1/39S2）；生产/测试现在有上述两文件变更，未提交。

2026-10-20 TA-045报告最小修复：仅最后producer suffix删除；旧版3测试2失败、补丁后3/3，原REPORT实际Rmd两样本行保持独立。新增测试来源64。累计58项中2项verified，余56（16S0/1S1/39S2）；acceptance旧阶段摘要归档，重写当前边界避免历史runtime描述混淆。

## 2026-10-20 TA-048 标识符适配修复验证

四个 R 消费者显式按字符读取样本/特征 ID，保留前导零及字面量 NA；数字组名001/1保持分离，非标识符缺失值策略不变。新增 tests/test_statistics_identity.py 共7项回归方法，修复前5项触发8个失败子场景、数字组名另触发2个失败子场景；最终7/7通过（53.586秒）。四个原 Nextflow 模块各执行两组对照，共8任务通过，样本重命名前后统计一致。DESeq2 特征重命名结果按预设数值容差比较。证据：results/tool-audit/20261020-statistics-identity-fix/receipt.json及nextflow/run.json。

TA-048关闭；TA-011/012/013/014/047及重复输入策略仍未闭环。原生DESeq2为1.52.0，不能替代声明1.42环境认证、FastSpar或完整跨样本/科学基准。历史受影响数据需重新生成下游统计；不改变模型、阈值或计数单位。

## 2026-10-20 TT-008 负向判定与重复键修复

run_nf 的 expect_success=False 现在必须取得非零退出；重复键场景必须匹配实际 Nextflow 的完整 duplicate emission 诊断，路径中出现 duplicate 不再足够。原序列套件加正确退出断言后实际退出1，暴露原workflow仍成功并发布两个S1结果。随后两个序列join启用failOnDuplicate，并对plasmid、MAG、taxonomy三路重复分别验证拒绝；保留原正常、缺MAG、缺taxonomy、空plasmid四场景。最终4项oracle单元、7场景原序列套件、5场景原CRISPR套件通过。

证据：results/tool-audit/20261020-negative-oracle-fix/receipt.json、各原始log及retained trace。此为人工路由fixture；重复检测按完整metadata键，不能推导全部host linking路径按sample_id唯一，也不提供异步失败前任务/发布的事务回滚。CRISPR disabled main仍因其他输入校验失败，不算成功E2E。TT-008关闭，其他主路径/科学契约仍未决。

## 2026-10-20 TA-037 表头解析修复

表头阳性限精确circular=true/topology=circular token或首个序列ID的_circular后缀；否定token和_not_circular ID后缀禁用header推断，冲突写warning。未修改DTR/ITR算法、低复杂度过滤或拓扑字段定义。新增5项回归方法，修复前5个失败子场景；最终5/5通过（9.894秒）。原PLASMID_STRUCTURE wrapper两任务均exit0，7条混合标记记录的ID/调用/方法匹配预期、空FASTA输出仅表头。证据：results/tool-audit/20261020-structure-header-fix/receipt.json及wrapper.json、原trace/work命令。

TA-037关闭；TA-036的ITR环状推断仍未决。fixture是人工解析/重复序列，不能替代已知生物学拓扑或容器环境认证。此前仅靠否定、部分或冲突header判阳性的结果可能改变，需重新生成结构和依赖报告；未判header阳性不能解释为确认线性。

## 2026-10-20 OPERA-MS 输出选择及PATH调用适配

重新从GitHub读取v0.8.3 OPERA-MS.pl，blob08c41900c791669dabd0755329d4fe615a7ca04a，默认POLISHING=0，write_final_assembly写out/contigs.fasta。保留固定版本摘录evidence/opera-ms-v0.8.3-output.json。发现新增TA-050：原perl OPERA-MS.pl在任务目录无法按PATH查找脚本；原Nextflow任务exit2，chmod可执行的PATH observer按bash -ue重放同样exit2。改perl -S后，原结果选择4场景3失败：选中GF3中间结果、接受仅中间文件、任意decoy。最小补丁仅接受非空最终contigs.fasta并显式诊断缺失/空产物。

最终5/5人工接口场景通过（16.301秒）；原P3增加output_dir/contigs.fasta与下游FASTA全文一致断言，但未执行。receipt和完整命令/trace/输入/产物哈希保存在results/tool-audit/20261020-opera-adapter-fix/。早期observer未chmod的探针和缺-ue的手动重放单独保留，不能作为生产语义证据。

TA-001、TA-050均ready但未关闭：本机无OPERA-MS可执行及完整依赖，未运行真实组装、真实P3、hybrid子工作流或平台验收。此处Perl替身只生成带独立标签的产物，不计真实工具通过。历史若使用中间assembly，下游检测、coverage、注释和统计都可能受影响，真实验证后需重生成受影响结果。

## 2026-10-20 TA-005 压缩FASTA输入适配

PLATON包装对.gz/.GZ先gzip -cd生成任务内plain FASTA，未压缩文件原样传入，不改变classifier参数/模型。使用锁定pUTI89真实序列（114230bp，来源commit618f1541382c4ad49eff566dadf13d5ccbd0ebb4，plain SHA256 f48980b3e15eb733333493755a432de7e2380b71abf8ac682d92e94353ad8431），由明确标注的ASCII输入observer记录内容与hash。基线原模块2方法均失败；补丁后2方法、4原Nextflow任务符合预期：plain/gzip/GZ三样本输入字节完全一致，损坏gzip任务exit1且observer未调用。原P3另增锁定上游gzip阳性场景，保留既有plain阳性；未运行nf-test。

证据：results/tool-audit/20261020-platon-input-fix/receipt.json及保留trace/work/输入输出。TA-005标ready，保持未决：本机native platon不在PATH且官方DB目录不存在，尚无实际分类器阳性/阴性plain/gzip一致性、版本/DB锁、容器或平台认证。真实序列来源不能把接口observer升级为真实Platon节点。

## 2026-10-20 TA-047 五入口数值边界补证

以同一120-feature/6-sample人工整数矩阵逐次只改变一个有效数值单元，对diversity、internal differential、network prepare、DESeq2及merge分别运行zero/text/NA/blank/Inf/negative，共30次原生CLI。每次保存输入、命令、stdout/stderr、输出hash。矩阵见numeric-input-matrix.tsv；完整证据results/tool-audit/20261020-numeric-input-matrix/run.json。

文本garbage在四个消费者都与真实0产生完全相同输出；diversity/internal differential/DESeq2的NA/blank也同0。network NA/blank会使用有效coverage，这是既有fallback，不能把它们误报为同0。network及DESeq2负raw_count同0；internal differential接受负coverage；merge把损坏/负/Inf coverage传下游。diversity Inf退出0，受影响样本所有beta距离被改0；network Inf退出0但对应count单元为空。其余Inf失败只说明下游拒绝，不能当作已建立统一入口校验。

当前merge单元测试主要核对ID、路径配对、重复键及空输入；新增identity回归也只针对重命名，不覆盖本数值契约。TA-047范围扩至五入口，保持planned/未决；具体校验边界及与TA-011/012的关系见contracts/numeric-input-policy.md。无科学模型/阈值/单位或生产代码变更，不新增通过计数。DESeq2原生1.52，不替代1.42认证；本次无Nextflow/P4。

## 2026-10-20 TA-047 数值校验修复完成

五个入口在输出/统计前校验实际使用的数值为有限非负值，缺列明确报错；无效单元给出来源/行/sample/feature/字段。merge保留合法coverage原字符串精度，网络保留缺raw_count时使用有效coverage策略；不再用0代替损坏文本、无穷、负数或缺少的有效测量。DESeq选中的缺raw_count现在提前失败，TA-011计数来源仍待解决；TA-012单位/rounding未修改。

新增6方法共35拒绝子场景通过；原5方法garbage基线5失败。原identity7/7、merge5/5通过。重跑30-case矩阵，五脚本合法zero输出与修复前逐字节一致；network原NA/blank fallback保持。原四模块8任务对照通过（早于最终network缺列guard）；最终7次原模块gate另核验当前五源码hash，包括五类坏输入任务明确失败且不发布TSV，以及network/merge正常输入成功。完整命令/输入/trace/.command及哈希在results/tool-audit/20261020-numeric-validation-fix/receipt.json。

TA-047关闭，增量patch以HEAD+TA-048为前态，已与原30-case源码hash核对。没有宣称完整CROSS_SAMPLE/P4、DESeq2声明1.42容器或科学基准通过；原生1.52。此前损坏数值不再被接受，应从已验证测量重新生成受影响统计。失败测试使用隔离新输出目录，不承诺清理旧结果目录。

## 2026-10-20 TA-044 共识输入完整性修复

assembly及SCAPP FASTA按现有规范化ID校验唯一性；generic/geNomad表按trim后的ID校验唯一性；同一工具不允许多份extra来源覆盖之前的calls。相同记录也拒绝，不隐式去重或聚合。诊断提供输入路径、重复ID、首个/再次出现的解析record序号，或先前工具来源路径；record序号不冒充多行FASTA/quoted TSV的物理行号。

修复前5方法触发6个失败子场景；修复后6方法7子场景全部通过（14.800秒），包含冲突行两种顺序及完全相同记录。原共识11/11通过（83.817秒）；原PLASMID_CONSENSUS wrapper五类重复任务全部明确失败且无发布产物，两个正常样本的调用及锁定pUTI89序列保持一致。证据：results/tool-audit/20261020-consensus-integrity-fix/receipt.json及positive/gates原trace、work和数据哈希。

TA-044关闭；增量补丁前态为HEAD+TA-043并已核对源码hash。未改变唯一输入的投票/权重/阈值，未认证实际分类器、生物学性能或完整检测E2E。TA-006等SCAPP重新映射、其他工具格式与权重边界仍未决；若某工具本来有多hit记录，应另建明确聚合适配，不能依赖最后一条覆盖。历史重复输入结果需从无歧义来源重生成。

## 2026-10-20 TA-042 共识权重配置修复

权重配置现在校验每项恰一个冒号、非空条目、已知且不重复的工具键及有限非负数字；weighted_vote实际参与工具总和必须有限且>0，检查提前到任何预测表/共识表/FASTA写出前。没有重新归一化权重；保留未提供工具权重1及空串全部默认1。非加权策略允许全零权重，但非法语法/数值仍拒绝。README已写明此边界。

修复前1方法4无效数值子场景失败；最终6方法20 CLI场景（15拒绝/5合法）通过43.946秒，覆盖多余/缺冒号、空条目、unknown/重复键、负/非有限数字、inactive正权重但active总和0、总和溢出、合法缩放/缺省、非加权零权重。原共识11/11通过82.449秒。原wrapper3类坏配置任务明确失败且无写出/发布任何结果；2正常样本调用及真实pUTI89字节保持，预测标签仍人工fixture。证据results/tool-audit/20261020-consensus-weight-fix/receipt.json，positive-final/gates与最终源码hash一致。

TA-042关闭，增量patch前态HEAD+TA-043+TA-044，README前态hash亦已核对。无阈值、投票或缺省科学规则变化；历史坏配置须更正并重跑。主入口工具列表校验TA-041、真实分类器及E2E仍未决；本检查在共识任务执行，不声称main启动前P0拒绝。

## 2026-10-20 TA-041 真实main输入形式补证

完整main运行25场景（非抽取helper）：13类列表各放一个未知名，全部越过选择校验并在故意缺sample_id的样本表处失败。空/null元素、嵌套列表、尾逗号空项也越过校验；map输入触发未处理的ConfigMap contains运行时错误，不能当作明确参数拒绝。JSON列表[" platon "]被静默忽略，而相同CLI逗号串" platon "触发缺Platon DB检查，确认规范化形式不一致。empty-list、mob_suite/mob_recon和声明optional ABRicate仅作名称控制；不据此宣称路由执行。全部trace0/.command.sh0；退出来自刻意坏样本表/DB防线或map运行时错误，均不能当作unknown-name拒绝通过。

13参数候选全集见tool-selection-registry.tsv，词法覆盖当前44个unique route pair，含已声明但尚未正确路由的optional ABRicate（TA-009），以及已知但显式拒绝的CRISPR；不删能力来制造校验通过。边界与测试要求见contracts/tool-selection-policy.md。原validation.nf.test的11场景不覆盖本契约。

首次父目录22个隔离配置校准漏assembler默认值，日志完整保留但不计本25场景，不把无关启动失败作为选择拒绝。最终原命令/参数/stdout/stderr/trace与hash见results/tool-audit/20261020-tool-selection-main/final/run.json。TA-041仍planned/未决；本轮无生产代码修改、新增认证或完整E2E结论。

## 2026-10-20 TA-041 注册表与消费者规范化修复

main在validateParams及任务提交前校验13类列表的已知名称/类型/空条目，保留mob_suite/mob_recon别名及所有声明能力。未删optional ABRicate或CRISPR以制造通过；TA-009与已知未实现CRISPR的启用拒绝仍独立。Nextflow复制module params，单改父params不会改变子级；初版赋值/replace及strict-syntax前置语句探针已保留，不能当最终证据。最终采用lib/tool_selection.nf纯函数，每个main/子工作流消费者规范化自己的raw值，无ParamsMap修改或内部API依赖。44个unique contains gate及MAG空列表gate均覆盖。新增utility后生产NF102、include170、词法可达96、未解析0。

最终25个真实main对照含19个准确选择拒绝、6个已知解析控制；原11 P0完整重放通过，全部目标错误均在stderr且0trace任务/0.command.sh。validation.nf.test新增19场景，当前30正式P0均有原main对照，但nf-test loader/JUnit尚未运行。三层父/子/孙在13组完整名称的字符串/列表及空值控制均一致；原宿主suite7场景通过，另2个trimmed真实子流程对照均正确调度两样本并保持有/无MAG分支，已纳入runner；MAG纯空白选择不提交索引任务。

TA-041关闭。证据results/tool-audit/20261020-tool-registry-fix/receipt.json、final/final-replay/consumer-probe/trimmed-routes/mag-disabled；P0映射已更新并归档旧11行。增量patch保留TT-008前态且核对hash。不是实际分类器、平台完整E2E、工具DB可用性或科学基准认证；主入口之外直接调用者仍负责名称/类型校验。未知/坏形式旧配置现在明确失败，合法别名和空列表含义保留。

## 2026-10-20 TA-009 可选ABRicate接线修复

ABRICATE选择条件现在接受annotation_tools或annotation_optional_tools，两个入口共用同一次process调用，不改变vendored模块、--db/线程/prefix配置或阈值。原PLASMID_DOWNSTREAM/ABRICATE模块6场景基线均workflow exit0，但optional及trimmed两场景未提交任务；修复后公开runner的abricate-routing套件6/6通过、启用4场景共8任务。每个样本独特序列，逐项核对S1.card.txt/S.2.card.txt、输入SHA、样本prefix及card参数；both只各执行一次，disabled/空通道0任务。

这是明确标注的Python CLI接口observer，不进行ABRicate/CARD检索；observer的1.0.1版本响应仅供模块eval，不认证真实工具版本。真实native abricate/blastn不在PATH。首次测试驱动重构误缩进observer导致fixture启动失败，after.log留存但排除；修正后公开suite通过，完整工件复制到results/tool-audit/20261020-abricate-selection-fix/retained/，receipt含hash。测试harness与observer suite已进入tests，统一runner新增abricate-routing并清楚打印无生物学搜索；共享oracle4/4保持。

TA-009只按选择/接线契约关闭，ABRicate模块inventory仍investigating，真实节点/数据库/容器/P3及平台完整E2E没有通过声明。当前normalized route unique pair由44增至45，原44条证据归档。此前被忽略的optional选择现在实际执行，需在真实环境验证后重新生成所需注释。

## 2026-10-20 TA-022 固定版本真实比对补证

在results/tool-audit/runtime内恢复Bowtie2 2.5.4、SAMtools/htslib1.21、pigz2.8，版本与两个Bowtie2模块environment.yml完全匹配。官方conda-forge/bioconda38依赖显式URL+hash锁，下载计划92325363bytes，38个conda-meta版本/build/SHA均与解析计划一致，另记录实际可执行文件SHA；安装未替代其他模块1.24/1.23.1环境认证。

原BUILD/ALIGN模块实际调用原生工具，两样本不同12000bp随机参考，各20对100bp、无错误且有独立来源的reads。强制BUILD B先于A完成。旧三queue接线workflow和4任务均exit0，但A.bam的SQ为B_reference，B.bam为A_reference，各0 mapped；QNAME仍归本样本，说明文件名/RG不保证参考归属。候选reads.join(references).join(index)后再派生模块输入，在相同B先于A下4任务均成功、SQ/LN正确、每样本40 mapped。不是模拟BAM或按输出文件名生成期望量。

完整环境锁/输入hash/命令/trace/.command及BAM/SAM在results/tool-audit/20261020-bowtie2-native-pairing/run.json及environment.json。最初dotted withName配置语法错误的无任务校准保留config-calibration，排除真实8任务。TA-022仍未决，未改生产caller。下一步将keyed方案应用各实际Bowtie2调用并回归host/coverage/abundance。MINIMAP当前两输入来自同一producer，签名层反例不足以证明其当前caller确有失配，明确保留待验，不把Bowtie索引异步证据扩成所有long-read路径已实证失败。无CoverM、完整平台、容器或生物学性能通过结论。

## 2026-10-21 TA-022 已证实Bowtie2接线修复

CONTIG_COVERAGE、PLASMID_ABUNDANCE及Illumina/hybrid宿主去除四调用点，先按完整meta key合并reads/reference/index，再从同一matched tuple流派生模块输入；加入failOnDuplicate/failOnMismatch，保留nf-core输入签名、别名和参数。未改minimap2或算法/阈值。

恢复CoverM0.7.0/SAMtools1.24原生前缀，57个精确包身份核对并保存显式锁；仅新增下载23包约78.6MB，复用已缓存依赖。CoverM环境内minimap2依赖2.31未调用，不代表声明2.30/1.23.1长读环境已认证。实际BAM PG同时证明Bowtie2 2.5.4/sort1.21及merge1.24。

公开tests/run_native_alignment_pairing.py完整通过22真实任务：actual coverage/abundance14任务，原Illumina/hybrid host block各4任务；强制B索引先完成，全部SQ/LN/QNAME正确、每样本40 mapped，CoverM均值0.33755276与独立SAMtools depth和4000/(12000-150)一致；host准确去除20宿主对、逐字节保留5外源对，非header-only阳性。原四caller HEAD源叠加同一真实工具控制时，workflow照样exit0但SQ互换/0mapped，宿主过滤误保留全部25对，回归明确red。公开最终入口额外检查QNAME。

源码/原命令/输入/trace/.command/BAM/SAM/版本锁和校准过程在results/tool-audit/20261020-alignment-keyed-fix/receipt.json。初次配置在outdir前include发布规则导致null路径的运行单列publish-config-calibration并排除；最终配置顺序正确。TA-022仅按已证实Bowtie2问题关闭，未建立Minimap当前caller失败证据，更不认证完整FASTP/assembler/detector平台E2E或跨样本feature/count单位。TT-001原mock oracle仍未改；新原生独立真值回归不能替代修复旧mock本身。历史受错配影响的比对、去宿主、coverage及下游需重算。

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

入口仅允许Illumina/metaspades或hybrid/hybridspades的Recycler组合；前者和后者分别接入原SPAdes元数据及组装short pairs。5个不兼容组合P0均精确报错且0任务/0.command.sh，2个支持组合的解析控制到预定样本表错误才停止。SCAPP/gplas2的其他平台/图资格仍属TA-007未决，不能因此关闭整条问题。

新增TA-051：原生实际SPAdes E.coli1K配对产生只有孤立节点的合法图，索引/参考/k均正确后原Recycler0.7因percentile([])崩溃。新driver只对经实际get_fastg_digraph证明0边的图明确写零环文件及skipped_no_graph_edges状态；不捕获工具异常转成功。新增TA-052：受控1000bp环的k33图曾因上游get_long_self_loops/get_spades_type_name及嵌套覆盖计算省略k、隐式默认55而静默漏检/错长度。固定版本driver验证三函数默认签名后统一实际k，通过runpy运行原CLI，明确记录max_k_default_adapter；不修改安装包或替换算法，显式参数仍优先。旧非55结果、旧contig-BAM输入结果需重算；这属于有结果影响的参数一致性修正，不能声称历史结果可比。

真实数据：下载既有real-nodes-datasets.lock中的minigut pair6.72MB，逐一核对size/Git blob/SHA。最终原始P3工作流原生4任务新workdir无缓存完成（SPAdes4.1.0 --meta，2CPU/2GB，约40s；完整原始pair，无裁剪），317正向节点/260图边，实际k55。完整字典/图/BAM/BAI哈希一致，得到1条1871bp序列，独立解析能对应原图唯一自环方向的去k序列；同输入直接原recycle.py的FASTA/path两个文件逐字节相同。证明输入/输出/调用一致，不等于该环具有独立生物学质粒真值或方法准确率。首次同数据在沙箱内因Python3.15 forkserver Unix socket PermissionError失败，保留minigut目录；允许该本地通信后minigut-native及最终pipefail源码minigut-final两次4任务成功，均保留原命令/trace/task脚本，不改成only-assembler规避失败。

其他证据：provenance单元8/8、正向参考/元数据单元10方法（含5类坏k子场景）通过；原PLASMID_DOWNSTREAM的实际SPAdes双样本k33/k55共8任务明确0边/0环；受控原模块k33/k55双样本6任务各输出独立真值1000bp环与正确header，修复前k33空、k55文件修复后不变；原RECYCLER模块四类负例（缺BAI、错图SHA、错参考、显式工具退出23）精确失败且无已发布环；mapper部分SAM后退出23反例只完成reference、align失败23、consumer不运行。ABRicate受影响的6路由/8observer任务重放通过，非真实CARD搜索。

源代码25文件的focused差异以此前baseline+audit patches重建，并逐个对照上一轮累计SHA/原489文件receipt验证，见patches/TA-002-TA-003-TA-004-TA-051-TA-052.diff与results/tool-audit/20261021-recycler-production-fix/source-state.json；不会把先前TA-041/009/022补丁混入本修复。README与tests说明同步当前契约，原Recycler nf-test移除目录存在/未使用helper断言，改为hash/k/state/准确产物名检查；nf-test loader/JUnit及容器未执行，不能把原生counterpart升级为框架或镜像认证。完整Illumina/hybrid QC→报告及科学基准仍未完成。

本轮收尾：最终pipefail源码的minigut-final再完成4原模块任务，无缓存；FASTA/path与同输入直接Recycler0.7 CLI逐字节相同。final-zero用最终源码重跑原SPADES/下游8任务通过。BWA mem显式partial-header/exit23 observer证明producer失败23且consumer未运行；原consumer四类拒绝/失败传播均通过。当前main的35个独立P0场景全部重放（19registry、原11、5新增Recycler资格），两个允许组合解析控制另计；首轮11误用minimal config导致错误提前，本轮保留失败并使用原combined config纠正，不放宽诊断。p0-main-cases.tsv已关联当前main哈希，status生成器改按unique case映射计算，避免重复运行加大分母；运行历史保留。完整证据receipt.json/source-state.json及环境锁、trace、任务脚本见results/tool-audit/20261021-recycler-production-fix/。审计台账现61问题/16已验证/45未决，S0/S1仍有未决，整体目标继续。

## 2026-10-21：按用户要求删除SCAPP，保留历史审计分母

用户在候选实体/投票方法澄清中明确回复“删掉SCAPP节点”。已删除检测、binning、环境、调用及4份nf-test来源，主入口不再接受两类SCAPP选择；共识不解析SCAPP或接收其权重，固定输出四个工具列。TA-006/035标记removed_by_user/retired，不计verified修复；TA-007的GPLAS2及TT-002的MAG/linking断言仍未决。历史103个生产对象保留2个退役项，测试85份来源保留4个退役项。

原共识脚本此前的SCAPP重建DNA传递实验已撤销；保留在results/tool-audit/20261021-scapp-consensus-sequences，不用于当前修复认证。该实验还显示不同候选实体直接投票会把未评估当阴性；本次按授权移除工具，无需继续该方法方案。保留通用一致性检查：所有预测ID必须在assembly中找到，空记录明确拒绝，真正空文件/空结果允许。

验证：原main37拒绝场景全部非零/精确诊断/0任务/0.command.sh；共识28方法、R smoke54检查（表头改为完整相等，防止substring接受旧scapp列）；原native共识/结构8成功任务和3拒绝任务，序列/ID/长度/GC/结构对应、拒绝后无发布产物。原检测subworkflow单参数、2样本全关/仅Platon/全开3场景26任务通过，分类器为显式CLI observers，R消费者真实运行；原downstream6场景8任务ABRicate observer通过。不是分类器/DB/模型、nf-test loader、镜像、科学准确性或全平台认证。

保留失败：新harness初始Channel.fromList收String[]导致解析失败、0任务；修为toList后全部4场景通过，失败产物留modules/，正确产物在modules-corrected/。补丁前态重建首次README哈希不符（此前文档未纳入聚焦代码补丁），断言停止；将README排除聚焦代码差异并另记当前hash，没有跳过生产/测试前态校验。旧R smoke54通过后加强完整表头断言，再次54通过。

补丁前态为前16项修复的累计状态，逐文件校验基线/累计hash后重建；删除源也留前态hash，SCAPP-retirement.diff仅包含本批代码/测试差异。SPAdes本地diff重新生成并核对上游blob，保留modules.json revision。receipt：results/tool-audit/20261021-scapp-removal/receipt.json。当前61问题=16 verified+2 retired+43 open（12S0/2S1/29S2）；全量审计继续，不作完成/发布结论。

## 2026-10-21：PlasX 消费者修复与 PLASMe 输入/输出适配

TA-023仅关闭共识消费者范围：固定官方5c9acfd的contig/score表含全部候选，按README严格score>0.5记阳性，=0.5为阴性；要求有限[0,1]，完整负分行保留，PlasX分数用17有效位输出以保持边界值可往返。原有投票算法、权重及其他工具分数格式不变。旧PlasX参与的共识结果需要从实际分数表重算，不能与新结果直接混合。TA-025的逐样本基因家族注释/安装环境仍未决，不能宣传整个PlasX节点已认证。

TA-024实现并标ready：PLASMe v1.1的第二个参数是阳性FASTA路径，报告为该路径_report.csv（实际TAB）。固定Git blob7f0718071849b73111a4e641b27e0f528d3356a2重新从GitHub核对，按原路径读取两文件并检查ID集合、长度、完整DNA；所有缺失/破损/不一致均在生成消费者表前失败。报告本身已筛为阳性，不重新按Transformer概率阈值过滤；BLASTn命中score=nan、或BLASTn支持但Transformer0.2的记录仍保留。规范化表带明确classification和source_score等来源字段；R预测中的1为调用指示值，原始报告及FASTA一起发布，不是概率校准。单独函数源码按moduleDir嵌入任务脚本，随脚本进入缓存身份。

新TA-053 S2：压缩assembly直接传给PLASMe，在官方输出函数SeqIO.index报普通gzip不可索引。已为.gz/.GZ解压并保持plain输入原样；坏gzip在调用工具前失败，标ready。TA-024/053尚缺固定完整PLASMe环境、模型/DB真实推理及平台P3/P2，不能因writer接口通过改为verified。

验证：PlasX新增5方法/14 CLI场景，前态12断言失败，后态全过；原28共识方法全过。正常/空结果与PlasX实际两列表通过原Nextflow共识/结构10成功任务，3错误输入仍正确拒绝且无发布产物。PLASMe helper7方法通过（缺文件、错表头、重复/空ID、错DNA/长度、格式空白）；原模块+实际固定源码的plasme_cmd/merge_ranges/plasme_output AST，受控candidate和BLAST命中，7场景16任务通过。前态plain阳性和缺报告均成功/3任务却丢失结果，另gzip前态在官方索引函数失败，均保留。完整检测子工作流3组合26任务observer回归通过，样本/输出/列身份不变；observer现使用官方PLASMe路径/报告及PlasX分数表。以上没有真正模型/BLAST推理，无nf-test loader、镜像或科学准确率认证。

保留新测试harness校准失败：最初include占位符替换误改process符号，7场景均0任务解析失败，修正为仅替换引号内路径；正确前/后态单独保存。辅助Python3.12.15/pandas2.2.3/Biopython1.85环境安装成功，41包explicit lock，只用于writer测试，不替代PLASMe部署。证据、输入、trace、命令、补丁前后hash及限制见results/tool-audit/20261021-detection-score-adapters/receipt.json。主入口未改，37个P0保持原main hash对应，不重复增加分母。

当前62问题：17verified、2用户退役、43未决（11S0/2S1/30S2）；新增TA-053并保留ready状态。全量审计未完成。

本批补充证据：PlasX前/后态各14条CLI保留完整FASTA、summary、score表、输出、stdout/stderr、命令及逐输入SHA256，重复重放不增加14场景分母。PLASMe最终7场景16任务另用包含空格/单引号的FASTA与数据库名通过，原module单引号参数编码与当前helper内容均核对；首次闭包调用未使用.call导致strict Nextflow零任务解析失败，已保存并修正。原共识模块对TaskPath本身自动进行shell转义，实际.command.sh已核对，不误报为新缺陷。主入口代码未改，额外一个原main拒绝场景检查新include可解析、仍精确拒绝且0任务，不计新增独立P0。

## 2026-10-21 TA-028：真实RGI本地/全局CARD选择修复

上一目标轮完成PlasX/PLASMe适配与测试修正，本轮为继续推进，未重定义审计范围。TA-028已用真实固定版本工具/完整数据库复核并修复：RGI6.0.8原代码与GitHub固定tag的RGI.py/settings.py/Database.py/load.py/ORF.py/Filter.py匹配；native环境另含KMA1.6.11（仅version eval）、DIAMOND2.2.8、BLAST2.16.0、Prodigal2.6.3，Python3.11.17，256包explicit lock。Conda环境文件和nf-core revision0a93f68a28f5e07bb7ae82aeb005720faf8a3b35保持不变；原始blob a11398832cbd7675cd4fe28a34fe637ae903cd1c与GitHub重新获取结果一致，本地差异单独登记。

两份完整[官方CARD归档](https://card.mcmaster.ca/download)为3.3.0、3.2.8（非裁剪/虚构版本），下载包和解出JSON逐一锁hash；测试的全局路径由DB_PATH/DATA_PATH指向审计目录，未使用或覆盖系统库。上游6.0.8锁定的真实NC_020818.1质粒、NDM-1蛋白和CARD3.3.0的VIM-77真实参考序列用于限定sanity；独立预期VIM-77 model6038在3.2.8不存在、在3.3.0唯一，NDM-1/mphE/msrE参考断言来自固定上游tests/test_1.py。随机DNA为明确人工阴性，不是科学效果基准。

原模块在load本地3.3.0后仍用global3.2.8运行main，3任务全部COMPLETED/0，DB_VERSION甚至显示3.3.0，却把VIM-77记录报为VIM-2 model391/Strict99.62。原始全局库的独立protein CLI能Perfect100命中NDM-1，说明不是故意损坏global造成的失败。修复为main显式--local，与既有load --local一致；DB_VERSION来自card.json，不再任意ls/SED匹配文件名。加载前检查对应canonical/all注释文件；加载后确认localDB/card.json逐字节SHA256及loaded_databases.json版本与输入一致，避免load失败/陈旧库继续查询。验证器嵌入实际任务脚本并参与缓存身份，未改变模型、阈值、Prodigal模式或其余生产默认参数。

验证闭环：validator6方法全过；当前模块四个独立场景共6任务（global存在3、global为空1、版本/文件不符1预期失败、上游参数oracle1）全部符合独立预期。原PLASMID_DOWNSTREAM+真实RGI启用/关闭两场景，启用2样本2任务正确命中VIM-77及真实质粒参考，禁用0任务；逐样本加载CARD JSON hash一致，最终JSON/TSV样本名/数目正确，全局CARD保持原hash。合计8个当前任务脚本均含完整当前验证器两次；这是一个RGI工具节点的多个case，不是8个独立工具。actual main原有unknown optional tool拒绝场景也在新include下精确失败且0任务/0.command.sh，不增加37个P0分母。

保留全部校准失败：初始dry-run误用KMA1.4.14，明确中断且未安装；依据真实environment.yml更正1.6.11后256包安装成功。新测试最初把上游NDM-1断言套在生产默认Prodigal参数上；读固定上游才确认其使用low_quality/include_loose/include_nudge/clean/debug，默认本地和全局库均能找到mphE/msrE而未必找到NDM-1。生产算法未改，默认模式的原生检查与完整上游参数NDM-1/Perfect100检查分别保留并通过，不能把模式差异误归数据库补丁或盲目删断言。测试还出现fixture/case目录重名，以及上游专用配置选择器语法错误（0任务），均保留；只纠正并重跑受影响上游参数控制，未抹去final-native中失败记录。最终receipt聚合三个有效原场景和修正后的一个oracle，明确引用各自原始记录。

TA-028现在fixed/verified，仅限实际数据库选择/版本元数据及受影响注释子工作流；inventory整体仍investigating。镜像、nf-test框架/JUnit、wildcard分支、完整平台/P4及临床AMR检出性能尚未认证。旧RGI输出若不能证明查询库与配置一致，应在新输出目录重算。证据与8源增量补丁：results/tool-audit/20261021-rgi-database-scope/receipt.json，patches/TA-028.diff，local-patches/rgi-main.diff。当前62问题=18verified+2按用户要求退役+42未决（10S0/2S1/30S2），全量审计未完成。

本批测试可复现入口另已放入tests：rgi-database-scope.lock.json锁定两份完整归档和上游质粒SHA256，prepare_rgi_scope.py只读本地数据、拒绝覆盖准备目录并调用实际固定RGI；完整运行成功，生成的10项关键输入与本批原始fixture逐字节一致，旧global真实查询仍为VIM-2 Strict。原生运行说明已加入tests/nf-test/README.md，明确独立native测试不冒充nf-test执行。增量补丁最终共11源（含测试数据锁/准备器和说明），来源台账94份中当前90、用户退役4；manifest不充当测试用例计数。成功任务stderr已逐项复核，无隐藏ERROR/Exception。

## 2026-10-21 MAG最终结果政策、路由与DAS FASTA导出

用户明确选择“必须同时选择 DAS Tool 汇总；单分箱器直接进入下游（推荐）”。main与直接MAG_HOST共用依赖校验；多分箱器未显式选择DAS、无分箱器却选择汇总/质量/分类，均在分析前拒绝。单独CONCOCT/SemiBin现在进入最终bins；三个分箱器都能转表汇总，按样本收齐可用预测；必须的assembly/BAM/coverage连接检查重复及不匹配，SemiBin独立运行不再索引未用BAM。生产DAS参数启用--write_bins，未改算法/阈值/环境或vendored版本。

原模块受控前态：CONCOCT与SemiBin两场景20任务都成功，却无最终bins/消费者输入，新增成员/DNA/数量断言正确变红。修复后原MAG_HOST及原HOST_LINKING，13场景201任务通过，覆盖三种单分箱器、各两两与全部组合、显式单分箱器DAS、重复选择、MetaBAT2可选无bin、部分分箱器无bin和工具失败。按双样本不同ID/分组、逆序BAM检查每个最终bin的文件名、成员和DNA、CheckM2/GTDB实际暂存与真实R关联输出；DAS输入转表辅助程序为实际固定上游脚本。分箱器/质量/分类与该组DAS为明确CLI observer，BAM/DB为假输入，不是分类/质量或真实binning认证。GTDB只核验暂存，真实扩展名问题TA-031仍在。

真实DAS Tool1.1.7/R4.4.3/DIAMOND2.2.8/Prodigal2.6.3及141包显式锁隔离恢复；主R/bash源码Git blob与固定primary逐字节一致。完整33.45MB官方gut assembly与4组预测、上游Run1成员和汇总表均固定Git blob/SHA256。旧生产配置真实运行成功且15个已知bin的成员/长度吻合，但没有FASTA；新配置真实导出15个bin，全部独立成员、数量、长度和逐条DNA吻合。最终阳性无测试ext.args覆盖、不加labels、不改score0.5，直接消费当前生产配置。真实低分bin配明确测试阈值0.9必须保留上游停止/失败，并确认无部分发布文件；不是成功无bin。原生DAS与observer路由分别记录，不混计为真实binner/CheckM2/GTDB或多种独立工具。

测试逻辑校正也完整保留：首个R关联测试阈值-1无效；改用合法测试阈值0及受控重复motif，不改生产R。plain fixture名与CUTUPFASTA输出prefix冲突，改fixture basename而非删除上游guard。初始native negative错误预期exit0，实际固定cherry_pick使用type=stop；原das-native/run.json保留pass=false，测试改为检查失败/诊断/无部分发布，并实际重跑通过。阳性原始精确15-bin断言没有放宽。较早native示例添加labels，最终阳性直接验证生产参数；版本/源码变更前快照和校准记录均保留。

所有原37个main拒绝场景重放通过，新增8个MAG场景构成当前45个独立场景；另8个直接include guard不增加main分母。全部0分析任务/0.command.sh。7份新测试来源加到台账，共101（当前97+退役4），不把文件数当用例数。锁验证器还确认篡改独立预期汇总表必须失败；当前7个正版固定文件验证通过。202次成功任务执行的stderr复核无隐藏错误（包含重复DAS对照，不增加独立工具/用例数）。

TA-008/030现fixed/verified，仅限用户政策、局部路由和真实DAS导出；TA-031/032/049、原MetaBAT2 P3仅任务名断言及其他TT问题仍未决。新增TA-054：module可选非空数据库参数拼成--db_directory，而实际1.1.7只接受--dbDirectory；原生命令证明前者CLI解析失败、后者进入故意缺失输入表校验。默认生产传[]不受影响，自定义完整DB阳性仍待修复验证，不能用选项识别冒充DB有效。

本批14源增量patch：patches/TA-008-030.diff；当前源码与前态5源/9新源已核对原receipt及累计manifest。真实/observer/校准/原始失败分开保存在results/tool-audit/20261021-mag-final-bins/receipt.json及各run.json。当前63项=20verified+2用户退役+41未决（8S0/2S1/31S2）；没有提交、推送或远程写入。旧CONCOCT/SemiBin/DAS静默缺失输出不能用来评价修复后结果，应在新目录重算；多个binner此前隐式MetaBAT2而今显式DAS的结果政策变化来自用户决定，结果不可直接视作原策略重现。全量M0/P1/P2/P3/P4、镜像/nf-test/五平台及科学准确率仍未认证。

## 2026-10-21 CONCOCT压缩输入、BED步长、空提取修复

新增TA-055(S2)和TA-056(S0)，连同既有TA-032实际复核并修复。固定1.1.0两个helper源码与primary Git blob一致。生产保持chunk1999/overlap1900；原helper切片按99bp步长，BED却按1999bp步长，2400bp输入25个切片中24条区间越界。适配器仅对已审查source的唯一BED表达式修正实际步长，未知source失败；没有改为官方另一种10kb非重叠策略。两个包装器将.gz/.GZ解压到任务内.fna，原文件与ID/DNA保持不变。真实extract对空成员表成功且无FASTA，原wrapper随后通配符失败；现nullglob/optional允许成功空提取，但所有真实错误继续失败。

原wrapper四个反例保留：gzip cut、gzip extract、空提取都失败，default cut成功却坐标错误。最终17原生叶场景通过，含真实官方DNA、空格路径、压缩大小写、默认重叠/非重叠末段合并、无BED、source拒绝、损坏gzip/未知contig/错表头；诊断来自实际任务stderr，避免从显示命令文本里命中关键字而假通过。固定官方composition.fa350条真实DNA及明确构造的合法映射BAM进入原MAG_HOST，2样本各六原生节点共12任务，通过逐条BED/原DNA、成员/DNA、无重复和plain/gzip一致性检查，每样本122 bins。保持default clusters400/seed1/iterations500。初次计数断言误写14，工具/语义都成功但checker失败，原mag-native记录保留false；改为12及命名节点各样本一次后真实重新运行通过。

原路由13场景使用真正的CONCOCT cut/merge/extract与native Python后重放；另增empty-concoct，共14场景217任务。受控empty成员经真实merge/extract后跳过该样本质量/分类、原R关联为空。核心分箱/coverage/质量/分类/DAS的observer范围与完整native分支明确分开。238次成功任务stderr无隐藏错误。不是实际测序、aligner、独立分箱准确率或质量/分类模型认证。

可复现入口run_concoct_io.py/run_concoct_mag.py及两个Nextflow harness、concoct-sample.lock.json和说明已加入tests；旧入口run_mag_routing.py新增--concoct-prefix，不用假helper绕过生产source校验。12源增量patches/TA-032-055-056.diff，local-patches中的两个模块差异保留原revision。native环境63包显式锁在runtime/concoct-explicit.lock；source/data/native/原始失败与完整receipt在results/tool-audit/20261021-concoct-gzip/。

当前65项=23verified+2按用户要求退役+40未决(8S0/2S1/30S2)。测试来源105份含当前101与退役4，不是用例分母；生产NF/导入图未增加。main未改，只重放一项既有拒绝检查，45个独立P0分母不变。TA-031/049/054和其他生产/TT问题继续未决；M0动态配置/channel、五平台P4、镜像/nf-test与科学基准未完成。旧默认重叠路径coverage/bins可能受错误坐标影响，应在新目录重算；未提交、推送或远程写入。

## 2026-10-21 DAS可选数据库实际修复（TA-054）

原module非空DB参数--db_directory在真实1.1.7 CLI解析失败。改为--dbDirectory且统一暂存名dastool_db；这是必要的路径适配，因为上游bash/R命令会拆分空格路径，而参数恰等于db又触发内置DB默认值。查询前校验六个非空reference/lookup文件，非目录/缺文件/空文件明确失败，避免上游自动解压替换用户DB；原MAG_HOST仍传[]且算法/score0.5/导出选项/环境/上游revision不变。

8原生场景/8任务全部符合预期：原错误反例；含空格完整DB、目录名db完整DB和[]默认三正例，各自全部15个固定独立预期bin的成员/大小/DNA相符；三种预检错误在查询前失败；另一个保留完整真实reference FASTA、刻意换成不匹配lookup ID的负例（源目录仍名db）触发原生No single copy genes predicted。该负例检验实际读入指定DB：忽略DB或回退内置会错误产生15 bins，而非仅凭命令字串通过。它是明确输入依赖对照，不是生物学阴性/性能基准；三个正例均为完整正版六文件，85,354,910字节，包/文件SHA256与实际缓存归档及完整包清单一致。R/bash Git blob再次对照固定primary。

全部custom/bundled DB和真实生成蛋白的前后hash不变；失败无部分发布。原MAG三个binner+DAS的32任务回归与native R断言通过，model/core/quality observers和真实DAS范围分开；35次成功任务stderr无隐藏错误。main未改，原拒绝用例重放0任务，不增加45独立P0分母。测试数据锁在准备断言加入期间单独再次核对实际记录的完整DB/package SHA后验收，生产代码在native开始后没有变化。

公开入口tests/run_dastool_custom_db.py、新harness及dastool-db.lock.json/说明已加入；五源增量patches/TA-054.diff、local-patches/dastool-dastool.diff及source/完整运行记录见results/tool-audit/20261021-dastool-custom-db/receipt.json。原revision保留、整个模块inventory仍investigating。当前65项=24verified+2用户退役+39未决(8S0/2S1/29S2)；测试来源107份含当前103与退役4，不作用例分母。TA-031/049及其他生产/TT问题、M0动态配置/channel、五平台/P4、镜像/nf-test与科学基准仍未完成。无提交、推送或远程写入。

## 2026-10-21 ITR与拓扑分离（TA-036）

真实SCP1完整固定参考及独立实验研究支持线性，旧原生脚本却报true/itr1000。现在保留重复证据并输出unknown，不将ITR反推线性；header/DTR仍是环状候选，原八列后追加三个字段，报告明确候选与未知语义。13结构/3报告单元、54 R smoke、原结构5任务+REPORT1及原检测三路由26任务通过；后者分类器observer和真实R分开。报告在结构完成后显式准备新目录，不能据此关闭TA-015。原生参考/命令/trace/前后表与源码SHA见20261021-structure-topology/receipt.json，增量patch TA-036.diff。无图/reads闭环、镜像/nf-test/全平台或拓扑灵敏度认证。累计65项=25verified+2用户退役+38未决（7S0/2S1/29S2）；tests来源109份含当前105与退役4，main45分母不变，NF仅注释修改。

用户最新明确选择统一核酸参考目录并重映射；TA-010/012仍未关闭，下一批将建立共享序列身份、映射/多重比对与计数单位、hybrid及空结果契约并独立验证。没有提交或远程写入。

## 2026-10-21 共享核酸参考与计数（TA-010/011/012）

用户明确选择统一参考目录并重映射。新目录按完整DNA/反向互补去重，以全长SHA256标识并保留来源；所有样本组装序列竞争映射，质粒子集为来源候选并集，hybrid统计只用短读。原CROSS_SAMPLE和coabundance改用共享表，本地MAG/局部链接覆盖度保留。计数为CoverM实际primary read alignment，双端mate分开，拒绝coverage取整；mean/TPM/RPKM/count在同一过滤BAM/end0上生成，预期样本/特征必须完整，空目录另有明确状态。

最初MAPQ>=1被明确等价双参考击穿：Bowtie2 ties=1/AS=XS并任意分配22/18 reads。改为>=10并排除未知255/非主要比对，保留失败和最终独立歧义对照。55真实固定版本节点/实际R消费者任务，29边界任务（含1个预期缺样本失败），37单元方法及54 smoke通过；真实参考DNA+明确源坐标模拟reads和控制hostprofile，非湿实验/科学准确率。四平台和空质粒5个实际main/Python/R连接场景725任务均通过，外部分类器/mapper为明确observer，不计真实模型认证。修正旧mock期待无分箱器BAM索引及不认识显式Perl调用的错误假设，但TT-001文件名计数oracle仍未关闭。最终四正例保存启动前与运行后源码hash；源码输出hash改为分块计算避免大目录全量读入内存后，全部native/edge与平台重验通过。

TA-010/012局部verified；TA-011计数生产者/解析和缺失拒绝已ready，但部署DESeq2 1.42完整正/零模型仍缺（本机1.52的identity/smoke另记），不关闭。TA-013生产路径部分保护，其他metadata/eligibility未完成；TA-014/015/038、TETRA及完整环境/平台/科学基准继续开放。增量30源补丁TA-010-011-012.diff，完整code/data/env/失败历史见results/tool-audit/20261021-shared-catalogue/receipt.json。当前65项=27verified+2用户退役+36未决（5S0/2S1/29S2）；新增3生产NF共107台账（当前105），tests新增7来源共116（当前112），不是覆盖率分母；main未改、45独立P0分母不增。历史489源receipt保持。无提交、推送或远程写入。

## 2026-10-22 报告本轮输入与完成链（TA-015/017，TA-016 ready）

再现旧R报告exit0纳入OLD_SAMPLE、空annotation目录显示完成、assembly虚构读段QC。现在REPORTING汇集所有已调用分支的named outputs事件，仅必需检测文件stage为path，其他大BAM/DB只记完成/版本证据；样本表、R脚本和模板均path声明。报告按本轮样本/角色/表内ID/特征集合严格验证，移除--outdir扫描；原8列结构和4列样本摘要保持各自语义。JSON数据和输入清单随Markdown/HTML/methods五份产品显式发布，板块为观察输出/提供输入/未观察，不当作启用或生物学阴性。

5原生REPORT/RMarkdown场景8条trace：4完成、3缓存、1预期失败；延迟writer不发布仍等待/记录，旧样本/空目录无效，不变resume缓存、同名数据改变重算、可选失败无REPORT。13原生R方法保留原合法后缀ID/零调用并补失配/损坏/manifest拒绝；R smoke54通过，结构fixture纠正为生产的质粒子集，真实HTML表与JSON/Markdown逐样本一致。共享原生55、结构6和MAG32受影响回归通过（MAG模型/core observer和真实CONCOCT I/O/native R分开）。5平台正例+空结果6场景788任务实际main/R/Python连接回归，外部CLI是明确替身，含assembly无QC/覆盖度输出不虚构方法、注入旧样本/空network和trace producer覆盖；不是完整真实平台/模型或科学性能认证。

严格DSL最初拒绝dynamic spread、ChannelOut参数自动展开、heredoc缩进均保留失败证据，修复后专用suite通过。本机javap确认named outputs API，未用最新版文档代替固定运行器。TA-015/017局部verified；TA-016删除虚构默认叙述后ready，完整实际CLI/数据库/模型等仍缺，版本声明明确可能静态；不得宣称完整复现方法或原始数据自包含归档。30源增量patch TA-015-016-017.diff及source/data/env/trace/失败限制见results/tool-audit/20261021-report-inputs/receipt.json。

累计65项=29verified+2用户SCAPP退役+34未决（4S0/2S1/28S2）；NF108台账含当前106/退役2，tests118来源含当前114/退役4，不是用例覆盖分母。212导入、99文件词法可达、0缺失include、145配置声明；main未改45独立P0分母不增，旧489基线receipt保留。全量M0–M4、其余生产/测试契约与真实环境/平台/科学基准继续未完，无提交/推送或远程写入。

### 2026-10-22 长读段宿主去除、失败传播和测试替身（TA-033/057、TT-006/010）

宿主关联续审时先处理更上游的长读段丢失。SAMtools1.24固定手册和真实工具证明 neither-READ1/READ2 属category0；三份旧caller均误消费stdout interleaved。统一helper消费other gzip并保留meta/旁路，预设/过滤不变；全被过滤明确QC失败，hybrid不自动改短读单独组装。固定上游mapper在默认bash -ue下没有pipefail，新发现TA-057：故意包装真实mapper写完有效SAM再exit7，sort0掩盖错误；仅增加pipefail，原错误7无下游/发布。上游revision/blob与before完全相同，当前local diff保留。

native-final8场景53trace=修复前31+修复后22：三旧caller反例、ONT/HiFi保留3/4/5条独立受控reads、正反向DNA/非恒定质量、含空格/gzip、meta/bypass、全过滤/故障。真实Minimap2 2.30、sort1.23.1、VIEW/FASTQ1.24使用既有精确锁，无新安装。共享三模式55原生任务回归通过。stderr748文件逐份读取，CoverM全零样本的无主要比对提示及Pandoc弃用警告符合已有边界，不当作新的成功指标。

TT-006替身限定显式未配对记录并正确 -0，未建模paired拒绝。真实hybrid新fixture暴露TT-010：Bowtie2 double错误将.1.gz附到完整.gz路径，2样本丢失后生产目录正确报missing sample；固定安装wrapper命名规则和3真实CLI场景证明期望。修正最后扩展名前插入、%替换/无扩展名；6单元方法旧源各3全红、当前6全绿。旧宿主profile只认clean文件后缀的断言改为实际暂存短读逐记录来源，避免正确host后文件被误判。短读host仍全传递observer，不声称宿主分类有效。

ONT150/HiFi142/hybrid(OPERA)204与ONT无参考144共640完成任务，经最终read-only语义validator重新核对保留work，并非重跑新任务；三host场景中18个长读宿主工具任务原生，其他CLI observer、真实R/Python。混合FASTQ/BAM/POD5支持按平台fixture测试，BAM/POD5输入仍JSONdouble。HybridSPAdes额外运行缺SPAdes计划解析环境失败，保留且排除通过；不是完整真实组装/分类/平台/镜像/远端executor/nf-test或科学灵敏度/特异度认证。TT-001继续开放。

验收证据results/tool-audit/20261022-long-read-host/receipt.json，15源增量patches/TA-033-057-TT-006-010.diff，before与上一轮changed-source清单或未变HEAD逐项核对，reverse apply/whitespace及源码hash通过。主main未改，一条原拒绝场景重放0任务/0命令，不增加45个独立P0分母。保留initial/calibration、Hybrid缺样本/旧validator失败、最终validator局部NameError修复、P0错误诊断字符串校准和HybridSPAdes环境失败，不当作阳性。

累计67问题，33已验证局部修复、2用户退役、32未决（4S0/1S1/27S2）。生产107当前+2退役=109、测试118当前+4退役=122；210导入、100词法可达、0missing、145配置声明。原489基线来源不覆盖，所有变更未提交。历史受影响host去除及下游应在新目录重跑。全量审查继续，M0–M4尚未完成。

基线计数复核：历史489指tracked来源对象，冻结source-receipt.tsv实际488条普通文件hash（489物理行含表头）；另一个是tests/nf-test/workflows/bin目录symlink，不能由is_file扫描计作普通文件。原表hash未变，新增source-receipt-symlinks.tsv记录git120000/blob/target及hash，详见evidence/source-receipt-count-clarification.json。较早“489份hash”表述按此澄清，不覆盖原始证据或改变当前生产/测试分母。

### 2026-10-22 用户授权的TETRA方法修正与分类输入保护

上一goal turn为progress：实际完成长读宿主输出/失败传播与替身修复、原生和平台证据闭环；本轮继续高风险宿主关联审查。用户明确选择标准TETRA修正并另行校准阈值。原论文双链256维框架与固定pyani0.2.12源码分开看：后者尾部计数/稀疏默认不能当作全部合法窗口的独立真值。当前tetra_markov256_v1逐记录、逐链汇总di/tri/tetra计数，再计算Markov期望/方差，全256槽Pearson；回文每链一次、歧义断点/尾部窗口正确，未定义/恒定完整profile弃权。TA-040跨MAG记录虚构窗口局部verified；TA-039数值修复ready，真实宿主阈值验收未完成，不能关闭S0。

8独立逐窗口/标量数学方法、11CLI接口、7阈值工具及4测试退出oracle方法和54Rsmoke通过。旧周期性ACGT人为“阳性”改为事先定义非周期自匹配，并增加周期/低复杂度在零阈值也不可伪造关联。公开native runner使用锁定pUTI89/SCP1真实DNA作明确self/fragment/unrelated控制，两份原LINK_SEQUENCE任务24配对分数与Python独立参考一致，非已知宿主标签；人工旧反例0.9588941484、当前标量及实际CLI0.4549428621跨过0.7（不是较早pyani尾部实现0.4314798081）。17位分数和method/uncalibrated标签、all-pairs评分表及profile JSON均发布。

输入hash不变检查暴露新S0 TA-058：原分类输入名taxonomy.tsv，合并输出也taxonomy.tsv，head读取前重定向截断暂存symlink指向的源表；原任务0且分类NA。第一次native-current保留为失败证据（两份fixture被改0字节）；后续公开runner用准确冻结旧module+R再1任务复现，当前分类输入改放host_taxonomy??/*，单表及两域同名表2任务原字节与分类marker准确。最初只检查配对分数不会发现分类丢失，现同时检查标签和源hash。旧真实来源若经碰撞路径需核查并从可靠上游重建；测试仅损坏独立临时fixture。

实际HOST_LINKING原可选路径/重复键10场景11任务另验；最初trace聚合误把内部.command.trace当工作流trace，已纠正并重跑最终11任务，不计219等虚假数。原生接受trace共16条=评分2+taxonomy3(旧1/新2)+可选11，全部stderr逐份读取无异常；不是16个科学样本。既有main拒绝场景重放0任务/命令，独立P0分母仍45。

独立bin/calibrate_sequence_threshold.py需要有label_evidence的明确0/1标签、sample-local身份及质粒组/宿主组均隔离的calibration/holdout；未知缺失不当负例，分数方法/空值/重复/泄漏明确拒绝；只在calibration选阈值，报告holdout及不可评分数量，不自动改默认。7方法/3CLI验证估计、泄漏拒绝和无可行阈值，人工控制的0.8不是科学阈值；故意差的holdout也原样保留。未取得独立整理/锁定且可证明endpoint的真实宿主标签数据，0.7仍显式未校准。原论文搜索得主方法，随后PMC直开botcheck、BMC/EuropePMC及新数据检索transport失败均如实记，不把网络失败升级永久不可用或完成科学校准。

增量14源patches/TA-039-040-058.diff；before逐项对照前一接受manifest或未变HEAD，源码hash/reverse apply/whitespace/Python编译通过。原nf-test no-MAG测试仍仅空结果，native harness不等框架或镜像认证；本机R4.6.1/Biostrings2.80.2/jsonlite2.0.0实际版本有sessionInfo，无完整部署镜像/远端executor/全部平台/宿主效果放行。

累计68问题=35局部verified+2用户退役+31未决（4S0/1S1/26S2）；TA-039科学阈值继续open。生产109台账=当前107+退役2，tests127来源=当前123+退役4；210导入/100词法可达/0missing/145配置声明；原基线488普通hash+1目录symlink身份保持。全量审计M0–M4继续未完成，未提交/推送或远程写入。

### 2026-10-22 统计资格、零结果及源代码缓存修复

本轮继续原计划结果语义与tests审查，非另起新任务。TA-013/014/038及新TA-059/060局部verified：生产携带全样本定量state，预检单一共享contig/plasmid/state产物、metadata样本数/唯一ID、完整矩阵、计数总和及质粒精确子集；缺失/重复不得补零或静默求交，明确全局空/真实零保留cohort。SQLite落盘索引与流式hash的百万行规模控制峰值25100KiB，不以额外全量Python对象扩大内存。

单特征vegan旧代码不仅丢名字，还将样本池化；最初只给scalar命名的候选被独立公式测试击红（0.59827而期望0），现逐样本算Shannon/Simpson，7个独立alpha/Bray方法含0/1/多特征与raw/TSS。alpha零值及零/零Bray兼容0明确输出status，不冒充生态相似性科学结论。

FastSpar原生固定1.0.0（18锁包）确认最少4components；旧过滤后零矩阵实际exit0却无输出，原CROSS_SAMPLE任务因missing产品失败。最初>=3假设被官方源码及真实执行修正。prevalence仍一次性按初始非零cohort分母，随后移除新零列，不迭代改阈值；最终不足4特征或样本数不足只发状态，不生成eligible供推断。8feature20sample正例保留上游默认参数、矩阵有限/对称/ID完整且与直接CLI一致；官方exclusion早停提示保留，不给科学相关边放行。新TA-060复现旧as.integer将2^31+123计数变空白，现文本精确保留并拒绝超2^53-1，不声称引擎内部任意大数精度。

新TA-059是前一已接受共享计数实现的缓存遗漏：绝对路径Python不作为输入，私有副本改program仍CACHED旧method，直接CLI可见新marker。当前显式path输入使不变缓存/改变重算。Python6trace=3完成3缓存；R6trace=4完成2缓存，后者将本轮新helper故意换成私有公式作回归，不能当HEAD已有helper缺陷。初稿在script中本地读hash的comment及printf都未触发重算，已弃用；不声称Nextflow“去注释”机制。七custom任务显式声明程序/helper，包括shared catalogue与collector。

最终57单元方法及54Rsmoke通过；原CROSS_SAMPLE13场景37trace（34完成3预期失败）、真实DNA/明确模拟reads的共享比对/计数三模式58trace、上述缓存12trace、原P3网络wrapper2trace，共109=101完成5缓存3预期失败。全部关联stderr读取/hash留档：FastSpar官方早停、Pandoc弃用、明确零Bray策略、无比对D及CoverM可选cache的12条mv无匹配诊断均保留，独立计数/矩阵断言通过，不隐瞒为“无警告”。最初接口arity controller失败、错Python路径direct控制失败、旧源指纹尝试及早期native前驱日志保留，不计最终通过。

六个平台/空结果最终793任务=Illumina160+ONT141+HiFi134+hybrid(OPERA)191+空104+assembly63；外部CLI observer，R/Python实际执行，非完整真实工具/镜像/nf-test/P4认证。45main原独立拒绝场景按当前SHA重放+8直接MAG检查，仍45分母，不把53称新的独立P0。TT-003有限/完整cohort/实际分支断言加强ready，但框架及完整真实非空P4未验，仍open。DESeq2固定1.42/R4.3的185包原生环境身份已恢复，完整正/零模型TA-011尚未验；另列静态TA-061：min_group_replicates未传入而脚本写死3，后续模型批次修复并保持默认3。

38源增量patches/TA-013-014-038-059-060.diff，29before逐项对应前一157hash清单或未变HEAD（assembly快照未改不在patch）。当前175hash=前一157+8首次变更HEAD源+10新源；patch reverse-apply、whitespace、Python3.12编译及接受harness源码身份通过。原始488普通hash+1目录symlink、2SCAPP退役身份及历史分母保持不变。证据results/tool-audit/20261022-statistics-eligibility/receipt.json。

累计71问题=40局部verified+2用户退役+29未决（4S0/1S1/24S2）；生产110台账=108当前+2退役，tests134来源=130当前+4退役；211include/101词法可达/0missing/145配置声明。M0–M4全量审查继续，TA-039真实宿主阈值、模型/数据库/其他未决不被本批认证。未提交/推送或远程写入。

### 2026-10-23 固定DESeq2模型、参数与统计文件源保护

上一goal阶段为progress：已完成统计资格/零结果/缓存修复与证据闭环。本轮开始于10-22，最终验收10-23；沿原计划继续部署1.42正例与tests审查，没有缩小M0–M4目标。185锁包/R4.3.3实际加载DESeq2=1.42.0。初始正例和zero-sample报assays不平行，全零在DDS构造直接拒绝；旧two-replicates配置2仍输出空表。不能用本机1.52单元正例代替目标版本。

TA-062独立原生类型对照：未subset的xtabs及as.matrix(xtabs)均能拟合；按生产重排后只剩table类，table及as.matrix(table)均失败并丢dim/dimnames；同值/同顺序/同dimnames普通matrix成功。现在完整唯一矩阵检查后构造普通整数矩阵。TA-011真实计数生产者及部署正/零局部验证完成；没有恢复覆盖度取整、伪造counts或升级包。保留全设计一次DESeq拟合、原>=10/最小实际组大小预过滤、ratio默认、独立过滤/BH，未加lfcShrink。

新增deseq2_status.tsv给全输入cohort、设计/拟合标记、原始/过滤后文库及特征、实际参数/已加载版本和contrast失败数。0特征/全零/过滤无特征/组或重复数不足明确not_run；无残差自由度、过滤后零文库及ratio无正几何均值not_estimable，不删样本或补大小因子。过滤后才出现零文库的新增单元控制保留输入5/model0/in_designTRUE。显式CLI poscounts另与同版本官方API对照100features，默认ratio同一稀疏数据弃权而官方ratio报已知错误，不自动切换。其他模型错误仍失败阻止报告；contrast原NA策略现在显式completed_with_contrast_failures，不能当完整成功。

TA-061默认3保持，但配置2/4和无效0现在真正在原节点生效；resume未变缓存、提高阈值重算模型和报告。TA-063冻结旧内部效应量R接受1.5/0/-1并输出比较，现两入口正整数检查不截断。TA-066旧network_min_samples显式0因Elvis被改回20，原生对照确认status20；现仅null取默认20，显式0交R至少2校验后失败，输入源不变。执行阈值不代表统计功效保证。

TA-064四统计wrapper的平面暂存会在输入名等于输出时写穿symlink，原生四个旧任务完成但私有原计数表被改为结果。旧DESeq对照用旧Conda允许的1.52/R4.6.1，默认1.42类型失败会遮住写入；不冒充默认镜像通过。现在四节点abundance/*与cohort/*分别暂存，计数/metadata同名和与结果同名都保留源SHA；默认CROSS_SAMPLE规范文件名原本未碰撞。11场景11trace含四旧写穿、五当前保护、旧0门槛忽略/新0拒绝；仅独立临时fixture有意损坏。原P3网络wrapper另验[]可选metadata与新namespace，真实R/FastSpar2任务通过。

TA-065有效带引号/制表符/换行分组输入，旧DESeq/internal100行被独立CSV读成200，旧alpha24行读成36。单修输出不足：fread元数据保留双写引号，本地与read.delim对照已记录；三消费者统一标准TSV解码及double/auto转义，现100/100/24且标签逐字一致。新status初稿escape格式也被击红修正，属候选回归而不是额外历史缺陷。怀疑NA分组变假组的前后实际都空表，没有伪造新问题；仅补显式guard和回归。

固定1.42原DESEQ2/CROSS_SAMPLE23场景32trace：22完成5缓存5预期失败，正例、三组联合模型、复杂标签、2/3/4门槛、零/空/缺测拒绝及report依赖；宽矩阵官方API程序独立于生产导入/状态实现，逐键/数值及受控F3–F7方向/q值核对。两统计同时启用另4原生任务，报告按真实completion evidence路径/hash检查；初稿误以为统计文件也暂存到REPORT，已按实际设计修正，不改生产凑断言。既有资格13场景37trace、真实DNA/明确模拟reads共享三模式58trace、可选metadata2，连同11文件/参数trace共144=130完成5缓存9预期失败。数值/文件/分组证明不是生物学准确率或FDR/功效基准。

56单元方法后加过滤产生零文库场景，18状态方法全部重新执行；两组重叠17，去重57，不报74。Rsmoke54检查通过。五读平台/空结果当前730任务+未受影响assembly63=793；每个实际执行的alpha/内部R副本hash与当前源码相同。外部CLI仍observer，TT-001未关闭；TT-003状态/有限数值/真实拟合分支断言补强ready但nf-test框架/完整真实非空P4未执行。未将旧工具成功、合法gated或空结果冒充阳性模型。

144关联stderr完整读取/hash留档。预期9失败类型明确；成功记录保留DESeq非标准因子名提示、100行官方FastSparexclusion早停、32条Pandoc弃用、两个零/零Bray兼容提示、12可选cache mv无匹配及3个故意未比对D警告。计数/矩阵/直接CLI对照通过，不写“无警告”。初稿PATH配置GString、恢复会话选错、诊断漏路径、转义/导入不足、源变化guard拒绝及有意中断后的不完整manifest均保留，不当最终通过。句柄缺失后核对仅101/88/71任务、无报告的中断平台，才新目录重跑；没有凭等待超时重启。

增量17源patches/TA-011-061-062-063-064-065-066.diff，13before快照逐项对照前一175来源清单；helper/网络R未改不进patch。当前181hash=前175+6新tests来源。reverse apply/whitespace/Python3.12编译及所有当前接受harness源码hash通过。main未变，原45独立P0及其当前SHA分母保持，不新增入口用例。冻结488普通来源hash+1目录symlink、SCAPP用户退役及DAS/统一参考/TETRA决定未改变。状态生成器改为当前台账/最近接受receipt/未决清单，旧历史数值保留在journal/history，避免旧ready句误导当前状态。

累计76问题=47局部verified+2用户退役+27未决（4S0/1S1/22S2）；生产110台账=当前108+退役2，tests140=当前136+退役4；211include/101词法可达/0missing/145配置声明。TA-039真实宿主阈值、剩余工具/DB/model/profile与真实阳性平台/科学验收继续open。未提交/推送或远程写入；全量审计不宣称完成。

### 2026-10-23 下载前提、FASTP输出和IntegronFinder测试分支

继续原审计目标，本轮关闭TT-004/TA-034/TT-007的局部问题。TT-004原先只验证fetch函数，现隔离目录运行完整旧脚本，仅替换OUT赋值，用明确curl失败observer证明损坏既有资产加九项失败仍exit0/ALL DONE。当前完整脚本聚合失败返回1，继续成功项，临时文件通过非空/摘要/归档检查后发布；未锁定的现存文件不自动记为成功，损坏文件不删除，旧锁不能静默重写。首次本地hash仍不是独立上游来源，TA-016继续open。

20个独立unittest方法测试真实curl和本机HTTP/file、tar/unzip，覆盖混合404、截断Content-Length、空200、坏归档/摘要、现存损坏/未锁部分文件、旧part、锁冲突/精确名称、非法/重复/空清单和路径。默认十项失败与manifest写故障使用明确observer。沙箱首次禁止监听导致0用例错误，获自动审核允许后在本机回环运行；Python3.15和支持的3.12各20全过，按同一test ID只计20。未执行默认多GB下载。脚本新增清单/输出路径参数用于可复现整脚本回归，默认十项URL不变。

fastp环境保持声明1.3.6（h43da1c4_0），官方v1.3.6固定23d6211d4f05d61f561899f1b7702435a4b5d408，8包显式URL+MD5锁、包SHA256和二进制hash保存。锁经离线dry-run重放确认8包。初次micromamba list输出只有URLs不含EXPLICIT标记，未冒充可重放锁，随后从实际conda-meta生成有效显式锁。TA-034旧单端/交错真实处理正确但optional reads通道为空；脚本与stub统一clean后缀，双端名保持。原模块前后SE/PE/交错各三真实任务及各三stub，核对明确构造12单端/12对读的ID/DNA/质量/JSON计数与输出事件，关闭相应过滤/修剪以固定独立预期；不是生物学QC效果或整个流程单端支持。

TT-007原--gbk stub把文件路径当命令导致127，默认通过；仅加touch后两分支通过，要求输出时GBK通道有sampleID及文件，默认明确为空。integron_finder版本命令为显式observer，没有原生注释。合计16原生Nextflow trace=15完成+1旧预期失败，真实fastp6、fastp stub6、IntegronFinder stub4。全部stderr读取/hash保存，成功fastp的reads failed 0是正常统计；未出现额外失败。nf-test框架及vendored快照依赖TT-005仍未执行认证。

COPLA继续只读核对官方完整安装：固定spec为graph-tool2.35/Python3.9，不只是README的>=2.33。仓库相对helper/DB、copla.ini、绝对参考FASTA列表及独立Python2 MacSyFinder环境必须一起处理；不能只换CLI就称修好。保存6份固定上游源，官方latest数据库HEAD在开放网络仍连接超时，没拿到大小/版本；不推断全球或永久失效。TA-019/020保持planned/open，整体样本多FASTA当单一质粒的S0仍未解决。

7来源增量patches/TA-034-TT-004-TT-007.diff，4before快照分别对应前一181hash或未变HEAD；README before由精确逆替换恢复并通过前一接受SHA核实。新增3tests来源，当前187hash=前181+3首次修改HEAD源+3新源。reverse-apply/whitespace/bash语法/Python3.12编译通过。接受脚本初稿把findings字段acceptance误写decision，CSV写入途中失败；立即从未修改的本批before快照恢复，改成字段预检与临时文件原子替换后重做，全76行及其他台账一致，未计任何草稿通过。当前状态生成器按receipt实际存在的检查项显示，避免给非R批次硬套R smoke/平台计数。

累计76=50局部verified+2用户退役+24未决（4S0/1S1/19S2），tests143=139当前+4退役，运行记录167。生产110台账及45独立main P0分母未变。完整平台未重跑，历史证据不自动变为当前全平台认证；所有用户方法决定保持，TETRA真实阈值仍未校准。M0–M4原目标继续，未提交/推送/远程写入。

### 2026-10-23 OPERA-MS真实默认节点、gzip与隐藏子进程崩溃

上一goal turn关闭下载/QC三项，为实质progress；本轮继续最高严重度。核对官方v0.8.3 commit a55285272ea5efb17b79f0b51800776b1a3cb4d3，209MB源码/二进制/测试数据归档逐项验证469 Git blobs。原make因系统ccache只读失败，使用原Makefile的CC=/usr/bin/g++编译三组件成功，无上游源码改动。最初Conda无法解析perl-switch，其他110包（Perl5.32.1/R4.4.3/MUMmer3.23等）锁定安装；Switch2.17从官方CPAN取得，独立CHECKSUMS SHA核对后安装到前缀，590个依赖自测通过但不计流水线方法。内置SAMtools的ncurses5另锁1包，全部help检查通过，仍未据此宣称分析成功。

实际默认参考文件17290589=2,934,421,515bytes MD5 3d979db1bd72d2c0dff33cdfdec8ff89；配套17290511=42,858,600bytes MD5 67abfbd6ea87f99faca9ebc742204d60。完整下载/核对/解压5242参考文件9,770,538,818bytes及各SHA。未关闭默认reference/strain/gap filling，未替换截断数据库。metadata另核对PLASMe DB.zip实际13,632,339,031bytes/md5 b32263ad4fb20c04044700170b1609ef，本轮没有下载/运行PLASMe，不关闭TA-024/053。

新增TA-067：真实原OPERA module在check_data拒绝当前hybrid与原P3使用的.gz长读；先前observer没有表达该限制。私有解压.gz/.GZ、坏gzip先于tool失败，源SHA不变。固定真实minigut三输入逐Git blob和SHA验证，原生解压后SHA另由Python gzip流核对完整字节。Perl observer新增GZ/损坏/参数含空格控制但只认包装边界，不冒充上游所有内部路径空格支持。

第一次完整真实节点输出57contigs/1,776,306bp，文件/stats表面一致；安装nf-test0.9.5并核对release SHA后，原P3却在setup GString提前解释root而MissingPropertyException，0分析任务（TT-011）。仅转义内层root后原P3真实运行green。随后按计划审读全部内部日志，发现两次“完成”都有SAMtools0.1.19 compressBound断言崩溃；立即撤销正例验收，两份原始pass记录保留并显式列为degraded/rejected，不能用于工具通过。

新增S0 TA-068：宿主系统zlib-ng1.3.1的compressBound(65280)=69373，破坏SAMtools0.1.19要求<65536；锁定前缀zlib1.3.2为65311。依赖help检查不能发现该运行错误，父OPERA-MS仍exit0/最终文件存在。修正审计任务库绑定，生产module在发布前要求覆盖度日志并扫描已识别致命子进程诊断。helper完整源码内嵌进入Nextflow缓存身份，不依赖未声明全局bin内容。真实故意坏ABI重跑生成原始最终FASTA但helper使节点失败且不发布FASTA/目录；这不是科学阴性或阳性。helper是有界防线，不保证捕获每种无日志的外部错误。P3也加入覆盖度诊断完整性断言。

正确ABI环境下原模块和原nf-test P3各真实完成；前者57contigs/1,776,306bp/N50 846278，后者56contigs/1,791,905bp/N50 863997，最长均874908bp。分别用独立BioPython1.85解析和各自assembly.stats交叉核对，完整解压DNA/质量流SHA相符。两个固定输入重放产物不完全相同，本轮未归因，不声称字节复现/准确率或把一次57硬编码为所有运行真值。独立验收脚本初稿误把两个重放都写57导致红，改为各自统计与产物一致；不是改生产凑数字。

17独立方法=9原module/Perl observer+8helper方法通过，Switch590不计。选定16trace=8COMPLETED+8预期FAILED，其中9为CLI observer，另含两个不验收的退化COMPLETED；不把8个完成都算真实阳性。当前原P3 JUnit1个唯一case实际通过，rootsetup失败/dry-run/旧green反例分别保留。nf-test全仓库扫描仍提示其他vendored缺依赖，TT-005及其他P3/P4未关闭。最初nf-test --version参数无效、version缺Nextflow PATH、mock跑错有双-log包装器、负环境字符串替换初稿不精确而0任务失败都保留，不计最终通过。

最终hybrid201连接任务通过，宿主过滤为真实Minimap2/SAMtools，逐六个组装器入参核对ID/DNA/质量；其他外部工具仍observer。mock显式拒绝压缩OPERA入参并写明模拟诊断，当前六OPERA任务内嵌helper逐字验证（heredoc额外一个已知换行）；全部201 stderr及五组各30内部日志已读/hash，正常xargs和Pandoc弃用提示保留。验收脚本初稿错假设mock有独立mock_tool.py文件，实际每个CLI复制脚本正文并重写shebang；按真实已执行正文比对，不靠猜文件名。

10来源增量patches/TA-001-050-067-068-TT-011.diff，五before均对照前一187清单，新五源使当前192hash；新增四tests来源含公共native runtime锁，tests147=143当前+4退役。compile/reverse apply/whitespace及独立oracles通过。source/runtime/DB自测和全部接受范围见results/tool-audit/20261023-opera-native/receipt.json。生产110台账、211 include/101词法可达/0missing/145配置和原45独立main P0未变，不把重放加成新场景。

累计79=55局部verified+2用户退役+22未决（3S0/0S1/19S2）。TA-001/050/067/068及TT-011仅按本批范围关闭，完整真实hybrid/镜像/替代参数/科学基准仍未认证；COPLA实体/部署、PLASMe完整推理与TETRA真实宿主阈值仍open。用户三项方法决定及SCAPP退役保持。原M0–M4全量目标继续，未提交/推送/远程写入。


## 2026-10-23 PLASMe 完整模型与运行契约批次

按用户已确认的SCAPP退役、DAS多分箱器必选、统一参考重映射、标准TETRA及另行校准阈值决定继续；不恢复SCAPP，不把TETRA真实阈值任务标完成。固定PLASMe1.1官方9 Git blobs与实际只读源；完整Zenodo8046934归档校验并提取36模型/完整DNA蛋白，完整建索引。下载约79分钟，沿同一进程正常完成，未重启/裁剪以求通过，.part成功后重命名DB.zip。锁定99包及实际Conda cache和本地镜像。

发现并修复TA-069部署/裸入口/显式源码、TA-070内部shell路径、TA-071零BLAST查询崩溃、TA-072外部失败被忽略、TA-073旧Torch可执行栈兼容。新增局部源码补丁只修空/错误边界，实际模型与阈值不改。旧裸入口126、原Torch导入错误、LD_LIBRARY_PATH私有库仍被RPATH压过、容器UID/缺ps/copy2 security xattr失败全部保留，不作阳性。最后定位xattr并只复制源码内容；未关闭指标收集/忽略失败。真实Conda私有预加载后原缓存保持，外部child不继承预加载。

最终当前source的native原nf-test2用例、Conda与Podman4次全库模型推理完整pUTI89阳性；plain/gzip/GZ的ID/DNA/分数由独立BioPython核对，不将同一样本编码/后端重放当科学重复。人工N-query的全库无命中为边界，另5控制只含真实微型BLAST和显式失败Prodigal；不是分类准确率/真实阴性基准。20去重单元方法，writer7场景16任务、检测3场景26任务中的分类器observer明确标注；原51入口P0正确诊断/零任务，包括45重放及6新增source预检。原P3框架其他vendored依赖警告仍归TT-005。

验收oracles初稿把writer的单个module SHA字符串误当source映射，红后按真实receipt schema并核对8个实际producer任务嵌入的当前helper；生产结果与断言语义未改。台账脚本初稿误把测试README也加入测试来源分母，保护断言中止；修正为7个程序/配置/锁来源新增，README仅列源码补丁，不作测试用例或来源分母。中间失败记录保留，没有因此放宽生产验证。

20来源增量patch，当前204 hash；生产台账110/108当前、211导入/101词法可达/0missing/146配置声明；tests154=150当前+4退役，运行记录193。当前累计84=62局部verified+2用户退役+20未决（2S0/0S1/18S2）。TA-024/053/069–073只按receipt有界关闭；COPLA实体、TETRA真实校准及全部剩余M0–M4/profile/平台/科学基准继续open。未提交、推送或远程写入。


## 2026-10-23 COPLA 批次进行中（未接受模型验收）

本轮是实质进展：完整官方源30 Git blobs核对；原站超时后从上游issue指向的历史官方URL快照恢复357,242,880字节RS84全库，SHA1与独立CDX索引一致，完整10228文件/9894参考及图/注释资源逐SHA。188个主环境包和98个Python2环境包归档校验，graph-tool2.35真实加载9894节点/89591边，MacSyFinder1.0.5原源码103+1自测。libcrypt.so.1从锁定镜像私有提取并与官方Debian包字节复核，不改共享环境；运行锁已保存，不等于模型分类通过。

已实现COPLA逐候选调用、位置参数/精确PTU产物、原始记录/DNA/长度校验、错误传播与原子汇总；原始图/MCMC/ANI阈值及窗口不变。未知拓扑线性，显式环状才环状。真实边界9控制和16方法、原downstream5场景（分类器为DNA驱动observer）通过，包含同contig ID不同样本DNA、缺产物、第二候选失败不发布部分汇总。

审查纠错保留：固定位置截断在未使用FastANI函数，实际ANI解析本来正确；已撤回多余改动且不登记该缺陷。边界初稿还误把缺参考文件当作被吞掉的子错误，实际该读文件错误本会失败；改用真实有效DNA和缺BLAST环境才复现Ruby子退出被Perl忽略。原生ANI同输入补丁前后数值逐字相同；29个短参考的无窗口情况明确不可评估。新增TA-074只登记真实HMMER/Ruby失败被当作负值/漏关系的风险，不将前述错误假设计缺陷。

一次旧实验因撤回多余FastANI改动，核对唯一PID后显式SIGTERM；随后两个正确源码的全库实验在会话中断后句柄失效、宿主ps也无对应进程，分别仅完成6496/6143参考，没有最终预测或退出码，不计阳性/阴性。保存全部部分产物，未以观察超时断言终止或重复启动。继续复核又去掉了不必要的Copla_RS84目录名限制，使用声明内安全参考链接，支持自定义目录及空格/单引号；旧额外P0目录名约束随之撤回并保留历史，61个实际错误场景重放中。

当前全库验证由可追踪PID/状态/退出码的监督进程管理：full-native-generic与nf-test-generic，配置及日志在results/tool-audit/20261023-copla-entities。仍用全部9894参考、原图和官方真实质粒；其中一个参考路径改为自定义含空格/引号目录的字节相同副本，以验证路径而非缩库。尚未接受实际模型/P3结果。现85问题/62 verified/2用户退役/21未决，新增8测试来源使台账162（158当前+4退役）。原204接受来源hash保持不变，WIP另存working-source-state.json，完整M0–M4与TETRA真实阈值等仍未完成。

COPLA通用参考路径版本补验：撤回额外目录名约束后，16方法/9真实边界/原downstream5场景及61当前main独立拒绝场景全部通过。61/61已更新canonical P0，原62记录和错误目录名用例保留在本批历史。16来源WIP增量补丁反向应用检查通过，working-source-state.json仅标accepted=false，不覆盖204接受来源清单。完整native/nf-test监督进程实际PID匹配并存活；旧中断运行不重标为通过。共享下游真实RGI两场景回归已启动，完整模型和最终来源验收仍待完成。


## 2026-10-23 M0 配置展开补证

用实际Nextflow26.10.0 build14055的config -o json和-C仅加载工作区配置，默认、conda、mamba、docker、podman、singularity、test及test与五后端组合共12场景通过。9份配置前后SHA一致，保留全部JSON/诊断/完整命令，results/tool-audit/20261023-profile-resolution/run.json。默认66、test67个选择器声明可序列化；test中的geNomad禁神经分类、小库与资源上限明确，不宣称科学准确率。没有启动分析任务；模块内指令、closure与实际任务选择器优先级、CLI平台参数及工具部署仍需动态验证，M0未完成。

共享downstream真实RGI开启/关闭两场景完成：开启2个当前真实RGI任务，关闭0任务，精确VIM77/mphE、所声明CARD的实际加载/本地隔离及发布名称通过。未扩大为全部downstream或COPLA模型证明。COPLA两个完整模型监督进程仍匹配并存活；原生第一候选已完成全部9894参考ANI，尚待PTU及第二候选。运行台账193增加这两条独立证据为195，未将计算中任务计通过。


TETRA真实标签准备：先于任何TETRA评分，以固定SHA排序冻结20个旧header属各3来源共60候选，来源完整官方OPERA参考归档DNA/hash均核对。实际NCBI nuccore/taxonomy原始元数据验证同一非空BioSample、accession/version、长度、chromosome/plasmid类型、完整性和source taxid，55/60符合，5排除及原因逐条保留；当前taxonomy属数26，说明不能直接用旧文件夹命名分组。results/tool-audit/20261023-tetra-calibration/metadata-readiness.json只证明标签准备，不证明实验宿主范围；仍未聚类近缘质粒/分组留出/评分/校准，未更改0.7默认且TA-039保持open。


## 2026-10-23 COPLA与QC有界验收

COPLA两个监督任务均完整完成且exit0，未重启当前任务或裁剪参考：原生双候选约75分钟，真实nf-test单压缩Lab26约44分钟。原生NZ_CP028167.1/PTU-X4和NZ_CP028329.1/PTU-Lab26各自正确，均score1.0000，BioPython独立DNA/ID/长度一致；真实nf-test同Lab26重复不增加生物样本数。三候选执行各9894评估，短窗口不可评估单列而非阴性；原始30Git blobs与20122数据文件、路径别名DNA终验不变，发布无整库外链。旧中断、错误FastANI初判和控制失败全部保留。TA-019/020/074按固定legacy/native范围verified，其他后端/科学性能/完整平台仍未验。

等待模型时完成QC版本与逻辑复核：原环境1.33与生产1.35不一致，实际旧版本被新guard拒绝；同步pyproject/uv.lock，只更新MultiQC和必需Polars族，实际93包/844MultiQC文件校验。官方FastQC0.13.0 ZIP与GitHub asset SHA一致。真实当前版本原8报告汇总成6；同16真实报告的默认调用变10，A.clean.B/C混为A，新增TA-075。生产两个MULTIQC别名保留完整名称。测试trace原缺workdir会回退仓库且硬编码目录/弱子串断言；新增TT-012，修复为当前work根/精确表和逐来源计数。首次修目录后仍缺workdir而红；修trace后手写fastpJSON缺command被目标正确拒绝；改真实1.3.6生产200readJSON，不为通过降低断言。初稿补丁匹配错误、保存GitHub文本多一个尾换行的来源校验红也保留/明确纠正。

最终QC5场景24trace(19完成5缓存)，8标准/16扩展报告含真实不同.clean ID逐读数对应，fastp-only与MultiQC禁用、原输入resume通过；另1真实ONT别名用同16FastQC报告，不能认证NanoPlot语义。8去重oracle方法含4原退出状态方法。12唯一配置组合因生产QC参数改变必要重放，保留前12历史不增加唯一case分母；仍非完整动态profile工具证明。

两份增量补丁分别16COPLA和7QC来源，14个before对照前204清单或HEAD，9新文件；当前219hash全部匹配，反向应用检查通过。测试新增登记原已存在环境TOML/lock两份来源，共164(160当前4退役)，不是两个新用例。生产110台账/108当前、211include/101词法可达/0missing/148配置声明；61当前main P0、冻结488普通文件hash+1symlink以及SCAPP7退役身份保持。当前87=68局部verified+2用户退役+17未决(1S0/0S1/16S2)，运行记录212；当前receipt仅选定29真实trace=24完成5缓存，5路由observer另列2完成3预期失败。完整M0–M4与TETRA阈值继续open，未提交/推送/远程写入。


### 2026-10-23 TETRA冻结真实来源基准与AWS只读准备

上一goal turn有实质progress：完整COPLA/QC节点与6项局部修复证据闭环。本轮继续全量M0–M4，完成TETRA真实来源标签/分组/评分/阈值分析；不缩小目标，不用数值通过替代科学验收。

既有60候选在任何TETRA评分前冻结；实际NCBI metadata符合55份，BioSample、accession/version、长度、类型和source taxid独立核对，5排除不补选。实际全对BLASTn2.10.1按>=95%identity、query/subject覆盖并集均>=80%得到54质粒簇，近缘边仅NC_003922.1/NC_020797.1。宿主按当前属/旧header属/BioSample保守合并，联合质粒近缘形成20来源分量；SHA分配27calibration/28holdout、各10分量。准备脚本、原始元数据、protocol/panel锁均先于评分，500bp短查询明确排除、不补阴性。715查询/55代表染色体及15130标签对通过独立BioPython1.78 SeqIO与primary元数据检查；第一次用测试venv探测BioPython不可用的记录保留，未为此另装库。

原生产R4.6.1/Biostrings2.80.2实际30250对，29700完整profile、550不可评分；独立C++滚动双链计数先经7逐窗口边界控制，再由Python标量公式及fsum Pearson逐对核对，最大绝对差3.33e-16。165个500bp哨兵均不比较；ID、方法、0.7选择、不可评分标签逐项验证。实际校准CLI/独立全候选选择一致，仅训练完整质粒选择0.9534655970247977，训练TP1/FP0/FN26。留出完整质粒TP4/FP3/FN24，precision57.1%、sensitivity14.3%、仅4父质粒预测；1/5/10kb无预测，违反预定precision>=.9/recall>=.5/至少10父质粒等规则。历史0.7完整质粒留出precision28.6%、sensitivity78.6%。全部结果保留，未重新拟合、未改阈值、未改标签或放宽接受标准。

1000次固定seed查询分量cluster bootstrap仅针对固定宿主目录；选定阈值完整质粒precision879次有定义、121次无预测，后者单列。初次分析报告省略全未定义precision键，仅修复报告键及加独立连通分量检查后重放冻结数据；初稿analysis-initial-missing-undefined-CI.json和日志保留，分数/阈值/混淆矩阵/科学失败结论完全一致。不计新独立样本。终点为recorded_assembly_host，其他来源chromosome是来源decoy，不是实验不许可宿主；不能外推宿主范围。TA-039 S0/ready/open，数字修复通过不等于通用科学阈值可用，详见contracts/tetra-source-benchmark.md和evidence/tetra-source-benchmark.json。

用户追加审查修复后用computer-use在AWS创建并真实验证流程的完整目标。通过CUA打开AWS登录页，用户自行登录；当前us-east-1、抵扣金120美元已用0，100美元免费套餐产品列表含Omics/S3/ECR/EC2，免费计划约6天后结束与抵扣金2027到期分开记录。Budgets首次页面，无已有预算；HealthOmics私有工作流列表明确无工作流。不推断其他区/服务为空，不把余额当获准花费上限。仅只读，未创建资源/改IAM/上传/开始运行。官方HealthOmics最高Nextflow26.04.0、默认23.10.0，与本地主要26.10.0证据不同，云端必须固定并独立重验，容器/输出/模型/费用和最小权限内容后续准备，见aws-validation-readiness.md。

生产/测试源码219项接受清单未变，无新测试来源，无生产阈值修改；新增3种分开的科学输入/分组/实际基准记录，当前215。问题仍87=68局部verified+2用户退役+17未决(1S0/16S2)，测试164来源(160当前4退役)，NF110台账(108当前2退役)、211include/101词法可达/0missing/148配置声明、61当前main P0分母保持。支持矩阵同步已接受PLASMe/MAG/COPLA事实及TETRA失败，旧历史不重写。未提交、推送或远程写入；后续继续剩余GTDB/其他工具和测试逻辑审查。


### 2026-10-23 GTDB2.7.2真实输入边界、标准ANI方法决定

继续处理TA-031，固定官方2.7.2 tag到f17decef1f9d9cf5b4d31fd21f5c9d32d813abdc，302tree条目；工作区隔离Conda57包全锁，57归档SHA256/MD5匹配，70安装Python Git blobs精确一致。首次受限网络解析DNS失败保留，授权官方Conda索引/26.5MB新增下载后同版本显式安装，未清缓存或改共享hardlink。Conda解析NumPy2.5.4/DendroPy5.1.1与setup.py约束差异明确保留；只作该原生边界，不推断pip/完整模型兼容。

新normalize_gtdb_bins适配所有已声明plain/gzip fa/fna/fasta到任务私有同stem.fna，保留原FASTA字节及ID；重复stem/非法ID/坏gzip/空/未知/目录先失败，精确重试幂等、错误残留拒绝、输入不可被输出覆盖。新manifest记录输入/目标/hash，不把它当分类证据。模块内嵌已读helper文本便于任务来源关联，固定extension=fna；最终bin通道/CheckM/宿主输入仍原文件。9单元方法通过。

首次原模块回归尚未到文件选择就失败：原ext.args的--skip_ani_screen已被实际2.7.2 CLI删除，新增TA-076(S2)。直接真实入口也exit2报unknown-option；用户明确选择官方标准含ANI预筛选，独立TA-076配置补丁清空该参数，不用--genes/降级/改上游绕过ANI。标准真实CLI通过解析到达GTDBTK_DATA_PATH缺真DB保护exit1，不算分类成功。方法变化单列、旧跳过ANI结果需重算/记录不可比。

旧输入问题用显式有效CLI控制继续复现：混合3bin仅.fna一个被完整原生_genomes_to_process选中，成功但漏2；全.fa/.gz则原生选择0失败。当前正式配置10唯一场景12trace=5完成(含1旧漏读反例)+2cache+5预期failed，所有当前ID、字节、DNA、前置拒绝、原生函数/工具失败、不发布部分结果及空样本0任务通过；先前有效CLI重放保留不增独立场景。真实DNA取已锁OPERA NC_013656.1/NC_019427.1，人工file/sample副本不是新生物重复。原生OptionsParser构造器绕过、fake参考名册和summary标记清楚，不运行真实taxonomy模型。

MAG旧oracle按private fna改名，成员DNA真值不变，CheckM/最终bin/宿主ID仍原名；7代表场景93trace=91完成2预期失败通过，仍合成binner/quality/taxonomy observer、真实CONCOCT/DAS I/O助手与native R，不是全真实MAG。首次runner因PATH缺nextflow在0分析前停止，日志保留；提供已锁runtime后全7重放。当前9配置12profile补证通过且GTDB空ext.args，0分析任务，12唯一分母未增加。

TA-076按废弃CLI修复有界verified；TA-031改为ready而不关，因为固定r232约100GB参考库大于本地约66GB空间，尚无真实marker/ANI/placement/taxonomy IDs和模型结果；不裁剪/伪造DB求通过。官方module原revision保留、vendored diff单列。两份增量patch9源，3before对照前219清单或原HEAD；新增7唯一source，现226hash。新5测试来源使169=165当前+4退役；88问题=69局部verified+2用户退役+17未决(1S0/16S2)，运行221，生产108当前/2退役、211include/101词法可达/0missing/148config不变，61当前main P0未新增。冻结488普通hash+1symlink/SCAPP7退役保持。完整M0–M4、TETRA失败的科学阈值及AWS创建/真实执行仍未完成；无提交、推送或云端资源写入。

## 2026-10-23 蛋白输入、复制子拓扑和错误传播

用户选择未知拓扑按线性，仅明确闭环按环状。完成TA-026/027共同蛋白桥接及新增TA-077错误吞没/TA-078模型身份局部修复：原Prodigal仅一次，保留原基因ID/坐标/CDS/蛋白与源DNA，按原复制子分组排序，gene_map/state/hash明确；未重预测/统一翻译表或调阈值。真实MacSy2.1.6/MacSyLib1.0.4/HMMER3.4/完整CONJScan2.1.0检出pUTI89 F型系统，真实eggNOG2.1.13在官方小fixture库注释ychF及两个官方预期蛋白；不外推科学性能或完整生产eggNOG库。

9单元；下游6场景+指定恢复1检查32trace，错误对照2trace，总34=20COMPLETED（1旧原生错误伪成功）/13CACHED/1预期FAILED。前期拓扑TSV格式错误、发布路径oracle错误、不同genepred fixture不配当前注释库、误选polB DNA key、并行无指定resume目标、重复log参数及原生HMMER杀进程组退出137全部保存并纠正，不删关键断言或把失败算新通过；原publish glob本已保留sample前缀，撤回不必要目录改动。原生本地归档安装仅替代模型网络获取，完整推理未伪造。

两个环境79/70归档hash、安装后9/27/56源码blob、CONJScan162及eggNOG228 Git blob含3symlink核对；源锁/原始运行/失败/正式选择/3补丁顺序与回滚往返均可追溯。13来源5before、11新唯一源，当前237hash；111生产台账/175测试来源/229运行记录。90问题=73局部verified+2用户退役+15未决(1S0/14S2)。12profile按新配置重放，main61拒绝场景未新增。见contracts/protein-inputs.md和results/tool-audit/20261023-protein-inputs/receipt.json。完整审计、剩余tests逻辑、TETRA阈值未通过、GTDB全分类及AWS创建/真实验证继续开放；无云资源创建或远程写入。

## 2026-10-23 SemiBin默认原生状态与检查点

TA-049及新增TA-079局部verified：固定2.4.1官方169blob/128包/32安装源码与内置模型blob匹配；默认CPU自监督15epochs，原完整官方fixture40contig800kb，seed0固定。不变算法而修正合法零bin输出契约、显式最终summary/file状态和真实.pt检查点。原零bin正常退出0被wrapper判失败，原阳性真实.pt未emit，两个反例和修复后原生状态/检查点加载/有限参数、独立DNA/成员/N50/L50都通过。4单元，7native trace=4完成(含1stub)+1缓存+2预期失败；MAG11cases126trace124完成2预期失败，明确inference observers与实际I/O/R区分。首次测试prefix写错的失败/脚本保留，不弱化断言；原伪阳性stub和空model快照改成语义断言，框架/GPU未运行。

2增量补丁11源6before、9新唯一源，当前246hash；生产111/当前109、测试179/当前175、运行237；问题91=75局部verified+2用户退役+14未决(1S0/13S2)。配置未改，当前12profile和61main证据未新增/未假称重跑。HOTSPOT固定14blob仅下一任务准备，尚未修TA-046/运行权重。全量M0–M4和AWS目标继续开放。见contracts/semibin-states.md与results/tool-audit/20261023-optional-boundaries/receipt.json。

## 2026-10-24 HOTSPOT原生增量

TA-046/080/081局部verified：固定0e3e3013完整14源码blob、17数据库/19模型文件和102包；真实原程序正常CPU推理，严格CRLF转换、gzip/样本归属、私有ELF兼容、显式deep资源缓存和新建锁定Conda环境。13单元，选定trace9条 {'COMPLETED': 4, 'CACHED': 3, 'FAILED': 1, 'ABORTED': 1}；原模型内容损坏仍缓存与当前真实错误传播均保留。首次测试遗漏唯一子分类继承的失败及原脚本未删除。不是独立宿主准确率/科学阈值、GPU/镜像/nf-test/AWS或完整平台认证。当前接受来源256项；问题93=78局部verified+2用户退役+13未决。配置未变，未假称重放61main/12profile。用户已决定TETRA保留分数、停用未校准链接，随后按独立方法批次实施。全量M0–M4与AWS目标继续开放。见contracts/hotspot-native.md和results/tool-audit/20261023-hotspot/receipt.json。

## 2026-10-24 TETRA按用户决定仅保留分数

55来源的阈值科学验收仍为失败，不安装0.9534655970247977也不沿用0.7判宿主。按用户明确选择，标准256维数值公式逐字不变，所有比较和不可评分状态保留，taxonomy移至分数表；删除阈值通过标签，旧cutoff兼容但忽略，链接表仅表头、HOST_LINKING统一链接通道不发TETRA链接，另发composition scores。报告同步说明。TA-039只关闭未校准分数被当宿主的S0风险，不代表科学阈值通过。39单元；原生R/NF {'COMPLETED': 16}，另MAG真实I/O/R加显式分类器observer {'COMPLETED': 58}，不同层次不混算。源码257hash匹配；当前93问题=79局部verified+2用户退役+12未决。配置及main未改，沿用61入口拒绝和12profile证据，不假称重放。全量M0–M4及AWS目标继续开放；见contracts/tetra-score-only.md与results/tool-audit/20261024-tetra-scores-only/receipt.json。

2026-10-24 TETRA/HOTSPOT组合追加复核：同一官方序列与人工自匹配MAG同时进入两个真实节点，TETRA分数接近1而无链接，统一通道只发原生HOTSPOT的Escherichia链接；另发组成分数。2任务均完成，合并本批原生R/NF为18完成，MAG观察替身58任务另列。首次生成harness因闭包meta重名而编译失败、0分析任务，原脚本/诊断保留，修正测试变量后通过，生产源码不变。当前257唯一运行记录，39单元/55smoke及257当前源码hash不变。不是独立宿主真值或科学校准通过。

## 2026-10-24 Platon完整库与真实节点增量

TA-005及新增TA-082–086局部verified：固定1.7完整79blob/安装7Python文件、完整31文件2.899GB官方库、85包；真实默认accuracy+meta原CLI/当前包装的阳性与无检出结果保持，4处日志只在内存修复。实际HMM失败/未读取Future、同大小mtime目录缓存、全部长度过滤无文件及依赖下限均有原生反例。8单元、2原生传输方法、2原nf-test P3以native overlay通过；24选定trace={'COMPLETED': 12, 'CACHED': 4, 'FAILED': 6, 'ABORTED': 2}，含5旧反例/观察（1旧伪成功与1旧过期缓存），非24有效科学样本；当前任务取消另列。DETECTION3场景26任务显式分类器/auditor观察替身。源码264hash匹配；问题98=85局部verified+2退役+11未决（全S2）；测试来源190、运行272。当前main/配置未改，沿用61入口/12profile已有证据，不假称重放。全量审计、剩余测试、科学/OCI/完整平台与AWS仍开放；见contracts/platon-native.md与本批receipt。

## 2026-10-24 PlasX完整自动注释、测试来源及MOB发布增量

TA-025/087/088、TT-001和TA-029局部verified；100问题=90局部verified+2退役+8未决。完整PlasX两阶段及1个真实nf-test/2任务、351+63包dependency-only Conda通过；39评分独立算术最大差2.22e-16，当前注释直接原始predict相同。自动注释相对官方预计算17contig家族计数不同、严格0.5阳性19→20，单列批准的方法变化；无独立准确率声明。整组装0基因明确失败、排除支持。32单元方法；平台5场景652当前trace含缓存，只有6长读宿主任务原生；DETECTION28任务及MOB发布12条trace为明确替身。MOB默认copy的分样本/阶段副本在私有work清理后保持。已纳入来源285项；运行293；测试来源202。原main75控制有效，后续MOB发布配置未重放全部75或旧12profile，不外推。全量M0-M4、其他测试和AWS实际运行继续开放。详见本批receipt与三个contracts。

## 2026-10-24 可选图分箱与缓存输入：进行中

用户已批准继续 PlasMAAG 项目隔离环境修复；pyrodigal3.6.3、官方 CPU Torch2.13.0及固定源码构建可加载，pip check无破损。未再请求同一安装授权，未创建收费 AWS 资源。完整源/数据库及 geNomad 模型资产已核对。内部 Conda 网络/校验和失败均保留；163个已缓存原包逐项 SHA256 验证后通过 Snakemake 平台 pin 文件离线创建，未跳过校验。

新增 TA-089 S0：真实恢复运行复用旧辅助脚本，18process/16module改为显式深度文件输入。当前 gplas 六任务完整原生分支、双样本模块和真实 nf-test、CONCOCT四原生场景、Illumina/hybridspades observer端到端及main75重放通过。不同范围分别记录，不汇总成“全量测试通过”。旧模块对照的输入数量与私有 harness 路径一并修复。原历史receipt不变，当前来源尚未统一接受。

新增 TA-090 S0：原生 PlasMAAG 丢弃 Snakemake 非零状态；新守卫已通过真实 CLI 的原始0/子进程2反例，当前守卫1/子进程2。完整官方两样本 fixture 首次遇到隔离 Conda 的 shell 激活解释器错误，按失败保留；修正隔离入口解释器后继续原生运行。守卫尚未接入生产 cohort 适配，不能关闭 TA-018/TA-090。

详见 contracts/gplas-native.md、contracts/helper-cache-inputs.md 和 results/tool-audit/20261024-optional-binning-native/；尚未生成本批接受receipt。既有来源清单与当前工作区不匹配属正在实施的修复，status如实显示，不以旧历史证明当前全仓库通过。

本批后续局部进展：官方PlasMAAG两样本完整原生执行在允许IPC后成功，实际VAMB200epoch及四个剩余Snakemake规则完成。独立核对123质粒成员/111bins、原生200kb门槛后的14基因组bins/3102成员、147病毒成员/79bins；五个实际产品/源码反例通过。仅完成环境恢复与独立CLI验证，生产完整cohort接线尚未修改，不关闭TA-018/TA-090。新增environment-recovery-checkpoint而非接受receipt。移除已不再使用的第一份geNomad1.11.1隔离环境，记录全部文件/元数据并保留可重建材料，实际观察可用字节增加661626880。

## 2026-10-25 PlasMAAG生产接线与当前回归（工作批次未接受）

完整cohort/源DNA/原meta接口已进入生产；SPAdes实际同任务三件套独立检查、原生生产双样本、真实nf-test0.9.5及contigs模式均通过各自记录的源码版本。声明核心环境重新从固定Git构建且pip check通过；嵌套环境仍需单独证明可移植部署。原生Node2Vec默认8workers已用实际源码证实，生产至少8CPU保护及前命令拒绝对照通过；之前2CPU记录不覆盖上游8worker实际资源。

独立原始组装核对：生产112质粒bins/129成员，框架126/140，contigs模式123/139；默认随机图嵌入导致的差异不通过更新快照掩盖，不视为准确率真值。当前helper再次改为私有兼容geNomad YAML并附163官方远程URL/hash锁，另启动nf-test-v4；实际已发生pin失败并回退YAML，待最终状态，不能把v3通过算新源码通过。源归档85文件不变。

测试修复 Map.get 默认值插入导致的共享ConfigMap并发问题；gplas重复输入可先报left/right，精确key诊断与无原生分箱要求同时保留，三场景重跑通过。当前main旧75拒绝全部重放，台账更新当前SHA。词法图112文件/223导入/105可达/0missing/155配置，生产台账114=112当前+2退役；tests台账补齐46份可见源码/锁/参考/历史说明至248=244当前+4退役，只是来源盘点而非用例/审计通过率。现309条分层运行记录；102问题90局部verified+2退役+10未决保持，未伪造批次最终receipt。

AWS会话只读复核：us-east-1无私有工作流/运行；预计抵扣金116.19美元，最终未更新汇总120美元；本月3.81美元现有成本未归到本任务。免费计划显示约4天，无预算；未创建资源或授权、未上传或开始运行。旧独立原生intermediate清理有完整manifest，物理空闲实测增加981,241,856字节，最终产物与正在测试资源保留。

随后PlasMAAG当前部署补验完成：v4在线失败192.4秒、真实子程序1传播，保留；新缓存首次离线失败也保存，原因是Conda自动索引无SHA256字段，精确MatchSpec无法匹配。只在独立缓存补充已重新计算/核对的163个原始归档SHA，未改共享元数据/源归档或锁；新的同远程URL/hash锁离线前缀安装成功。当前v5实际nf-test一例368.7秒通过，10捕获源前后不变，新建并实际使用geNomad599bf...环境，163包remote URL/SHA及6模型匹配，无YAML回退；独立最终85质粒bins/90成员、14基因组bins/2933写出成员、95病毒bins/147成员和原始样本ID/DNA/meta均通过。默认随机图结果不固定快照。当前守卫另3个默认help/校验恢复/私有依赖篡改拒绝对照通过。运行记录现在314，S0/批次仍待统一接受。

按计划从GitHub继续TT005固定来源核对：通用6d467...中UNTAR/GUNZIP存在，但HiFi下载helper404；查实际consumer的modules.json revision9cc9ac...后helper存在，故不能将错误revision404判为永久缺失。两次响应都保存，尚未安装或认证。依赖恢复须逐消费模块revision核对，而不是统一拿一个常见SHA。安装-only probe前缀另清理，实测释放658,415,616字节；本节两次清理实测总计1,639,657,472字节。当前681个可见来源全部逐hash匹配并保存独立副本，`production-routing-checkpoint.json`明确为未接受工作检查点；旧接受285来源清单和receipt不变，不伪造全量通过。

## 2026-10-25 TT005固定测试前置模块（ready、未接受）

恢复10个vendored suite的14处缺失依赖，按9个实际consumer revision取12组helper/source；45个官方GitHub响应、24个实际main/env/meta Gitblob及9份相同MIT许可都核对。8类测试专用helper放tests/nf-test/prerequisites，五组字节一致UNTAR合并留全来源；只换14处setup路径，未改断言/fixture/快照/生产版本/modules.json。常见6d467下HiFi404在实际9cc9ac下存在的反例保留。

独立静态99literal/0missing、14setup/24文件/consumer版本/许可全部通过。实际nf-test0.9.5 dry discovery10suite/33定义当前警告14→0、0命令；工具自己将dryRun标PASSED不计已执行用例，历史源副本45条other警告保留。真实tar1.34/gzip1.13/pigz2.8四原始helper任务逐字节保留846字节固定上游FASTA和meta，CRC坏gzip唯一任务FAILED且不发成功输出；收紧精确版本/任务身份/原输入不变断言后重放通过，不增加独立场景分母。14包工具环境六上游固定版本及所有原归档SHA核对，新增下载约5.62MB；pigz既有prefix复用。其余DB/模型/完整P1/镜像未验，HiFi master数据库仍需实际数据锁。

41源增量patch（10suite+测试README、30新增测试/metadata/许可/审计来源）反向check通过；还原替换后10suite逐字节等于before，11before SHA对应上一未接受681源捕获。当前41源副本、partial-source状态/checkpoint均明确未接受，未改旧正式receipt/接受285清单。TT005从planned到ready，未提前verified。tests台账新增29份至277=273当前+4退役，仍非用例数；生产112当前+2退役、99literal依赖清单更新、main75当前SHA保持。当前319分层运行记录，问题102=90局部verified+2退役+10未决不变。完整M0-M4、其余TT/GTDB全库及AWS仍在继续。


## 2026-10-25 当前来源补验与 ENA 实验类型

最新接受receipt保持285来源冻结；恢复全部55个最初变动文件的精确接受前字节，随后COPLA测试修正一项仅适用于旧heredoc的额外换行预期，未改PTU/DNA/分数断言。TA-089已有接受CONCOCT真实缓存反例和当前显式输入八阶段对照；当前完整PlasX/独立公式/官方predict、PLASMe Transformer与DNA通过，仍有剩余节点待补验。TT-013新增：ENA PRJNA848809是16S PCR数据，原始XML及论文方法优先于矛盾WGS标签；仅修正历史套件范围/标签，原when/then断言、文件与组别不变。TT-003真实非空shotgun P4保持未决。所有新证据尚未纳入统一源代码接受。


当前节点补验全部结束：新增28条真实原生COMPLETED（完整PlasX2、PLASMe1、COPLA1、Platon1、SemiBin1、蛋白桥接13、HOTSPOT1、RGI3、OPERA1、Recycler链4）；GTDB8场景10trace=4完成2缓存4预期失败，分类模型为明确observer。18迁移process的真实staging/精确helper字节及命令/导入依赖矩阵通过；TA-089/090改ready未verified。现有GTDB全r232分类边界不变。候选712来源捕获、143文件混合参考patch反向check0：57份精确此前接受preimage，24份边界外Git基线及62份新文件；不冒充143份均来自285接受清单。TT-013单独5源patch反向check0；TT-005原41源checkpoint继续历史冻结，README后叠加TT-013已说明。旧接受receipt/285来源未改。清理完成OPERA工作/发布副本526个中间文件（保留最终组装及诊断、完整hashmanifest），本次文件系统实际空闲增加16920576字节；不拿逻辑大小当物理回收。


2026-10-25 P3语义批：TT-002/014候选修复ready未verified。新增实际三套5例12原生COMPLETED，mapper状态注入对照2完成1预期FAILED；6 R单元、12实际产品反事实(3合法/9拒绝)通过。MetaBAT固定35原始包归档核验，源码归档SHA对应2.17；htslib1.21原为repodata合法放宽，后仅固定1.20兼容原配方。原始源码的内部簇号/文件序号区别纠正了首个oracle假设，错误实现和失败保留。13源增量patch(6精确此前712前像+7新增)反向check0。旧285接受manifest/receipt和前143文件候选保持冻结；本批实际来源另存，不自动升级全流程/OCI/科学/AWS状态。


P3收尾：当前718来源全部匹配；新版混合参考候选154文件反向check0，保留上一712来源/143文件候选，不覆写。原285接受manifest仍冻结。当前104问题、283测试来源行(非用例数)；TT002/014均ready未verified。三套5例/12原生任务完成；mapper对照2完成1预期失败另列。清理失败启动配置v2中的8个BAM/SAM中间文件，保留原始数据、当前成功产物、日志/命令/XML和清理前完整SHA清单；本次测得文件系统空闲差值0，不把逻辑字节当物理释放空间。尚未给整体放行或AWS执行结论。


2026-10-25 统一复核接受九项有界修复：TA-007/018/021/089/090和TT-002/005/013/014。154文件混合参考patch实际前向/反向及全部来源核对通过；718身份接受清单取代当前指针，旧285原字节归档，旧receipt不改。232处当前来源证据比对和18process实际helper字节匹配。两份gplas历史测试来源已更新，当前入口按原UUID6CACHED恢复及当前独立oracle通过，不计新原生次数；ENA旧README仅插入P3说明。104问题=99局部verified+2退役+3未决S2，完整M0/平台/科学/AWS继续开放。见 results/tool-audit/20261025-consolidated-acceptance/receipt.json。


2026-10-25 当前配置补验：Nextflow26.10隔离-C展开相同12场景均通过，捕获11份当前配置SHA前后不变，gplas图节点选择器、PlasMAAG的SPAdes选择器/原生参数默认及已有引擎/资源/GTDB/蛋白/测试小库声明通过。0分析任务，不证明closure实际求值、全部selector优先级或工具/数据库/镜像就绪，不增加旧12的独立场景分母。上一profile证据指针另存，见results/tool-audit/20261025-profile-resolution-current/run.json。接受的718生产/测试来源未改变，九项局部接受receipt不改。


2026-10-25 报告来源第一增量：两个R生产者输出实际完整引擎脚本/原生R版本/原任务SHA，报告显式文件输入及deep缓存校验，保留原样本与图节点ID，JSON/方法/两种HTML均有来源信息。17报告单元、当前6原生任务和17缓存/1预期校验失败、旧5场景8trace及共识10完成3预期失败通过；当前gplas两个R重跑四缓存，原图/成员DNA不变。首版FASTA单行oracle和漏PATH启动错误保留，不算新增仓库缺陷。九源增量7精确718前像+2新增，实际正反应用逐字节通过；720当前身份仅候选，旧718接受清单/receipt冻结。TA-016改in_progress、继续开放；99verified/2退役/3未决不变，完整生产者/资源/环境来源未完成。


## 2026-10-26 TA-091续接：NIO枚举、目录身份边界与COPLA现场

按工作总结先处理S0，保留此前报告/缓存候选。COPLA原任务源码/包装器、输入和部分产物SHA已保存：候选1产出PTU-X4，候选2留2091/9894 ANI状态，无最终trace/exit；不能算通过，不能从当前隔离进程表推测外部后代状态。1800秒不足以覆盖已观察到的两候选工作量；重试保留2候选和全9894参考，须新目录、至少7200秒预算和进度监测，本轮未重复启动该长任务。

紧凑指纹当前调用方改NIO FOLLOW_LINKS完整遍历；v2纳入相对路径/类型、目录存在、成员链接原始目标及POSIX权限，在文件读取前后核验size/mtime/fileKey。合法UTF-8特殊文件名不经glob，断链/循环/FIFO等明确失败；资源须全程不可变，非事务快照、不外推非POSIX/provider支持。22独立Python属性场景及16轮真实Nextflow26.10缓存控制（9完成7缓存）通过，reader脚本SHA不变；v1和20场景中间控制按自己的来源SHA保留。

当前完整模型geNomad1.12/fullDB1.9和PLASMe1.1各4轮：1完成、2缓存、1预期失败；私有资源等长同mtime损坏正确失效，恢复复用原有效结果，共享资源未改。原检测子工作流3场景28完成，显式classifier observers与真实R消费者区分；初始PATH无Nextflow未启动，补固定runtime/bin后在新目录通过，未删除失败现场。源码锁和结果校验见results/tool-audit/20261026-resource-identity/receipt.json及docs/tool-audit/evidence/20261026-resource-identity.json。

新增39条消费者—资源对清单，包含其他glob、裸目录、可选/上游模型、隐式环境/容器资源，均按机制列出剩余动作，不能当39个已过工具。TA-091仍S0 in_progress，99有界verified/2退役/4未决及718正式来源保持；新增6条运行/检查记录，不提升为正式接受批次。未创建收费云资源，未提交或推送当前增量；全流程、其他S2、OCI/AWS继续待验收。


## 2026-10-26 显式资源消费者候选归档

按S0优先级继续TA-091，完成当前显式消费者身份接线及选定原生回归。COPLA完整两个候选/9894参考冷运行、PlasX完整两阶段、PlasMAAG两样本200epochs和各自私有变异/还原对照完成；anvi’o13个固定子模块补齐并锁定，不改原始主源码/科学参数。24份证据、119条源码比较无差异，102个候选源码路径由两份补丁正反精确还原。TA-016报告候选仅保留，不算新增验收。见 `evidence/20261026-resource-consumers.json`。

显式stub缓存控制、MAG/检测路由observer、mock illumina、GTDB接口与原生推理分别记账；失败尝试原样保留。发现3个未改动vendored模块既有比较链哈希失配，另记待复核。75个main旧场景重放不增加分母。当前41资源对中8个隐式环境对仍待审；可选读取集合、根定位及provider边界未全覆盖。正式718清单不改、99项有界验证/2项退役/4项未决不改，TA-091保持S0。未提交、推送或执行AWS。


## 2026-10-26 字面资源根路径边界

冻结上批消费者证据后，真实引擎复现默认glob定位拒绝含`[]`/`*`/`?`的实际根目录。共享入口添加glob:false，7个真实入口控制和13个既有observer任务精确缓存重放通过；三份顺序候选补丁覆盖103路径，正反逐字节核对。上一receipt保留为历史快照，明确共享入口随后被替代，未把旧哈希称为当前。见 `evidence/20261026-resource-root.json`。8个隐式资源入口静态复核完成但未修复/运行验收；实际安装SemiBin源码区分默认自训练、marker.hmm与可选预训练分支，未改科学方法。TA091及其余3个S2仍开放，未变更正式来源接受或AWS。


## 2026-10-26 环境内资源探测原生试验

默认SemiBin资源从固定原生环境解析，cache:false探测先于复制消费者查缓存；6轮真实引擎/默认15epoch原生验证产生6探测完成、2消费者完成、3缓存、1预期坏HMM原生失败。私有HMM等长同mtime变化/还原，结束32个包文件字节复原；原共享安装未改。source-chain四补丁106路径精确正反核对，原103候选文件未改变。见 `evidence/20261026-runtime-resource-pilot.json`。这验证机制，尚无生产环境/参数一致性接线；8隐式资源对和TA091仍开放。两次启动前失败单列。另查固定Medaka2.2.2自动选模/回退依赖reads，下一步需逐样本探测；未以文档或pilot冒充完整原生/科学/OCI/AWS验收。


## 2026-10-26 SemiBin生产环境资源候选

实际模块+MAG_HOST接入cache:false资源探测及查缓存前上下文门禁，固定原生解析器决定读取集合，验证后exec同一argv。当前默认原生/变化/损坏/还原、7个上下文不一致控制、8个读取集合方法、18路由场景及两例nf-test通过（完整冷计算与精确UUID恢复分开）。449contig/3BAM软件fixture的70bin完整DNA核对不代表生物学准确率或真实P4。失败/被替代尝试、恢复前复制cache/history、控制台计数标签源码桥接均保留；未采用未验证的task.cache钩子。

来源42比较（41直接、1展示标签桥接）、120候选路径五补丁正反核对。SemiBin已接线但可选ORF/模型/GTDB/GPU/OCI/provider/when未齐，其余7隐式消费者待接线；原718清单及99/2/4不改，TA091仍S0。未提交/推送/执行AWS。见 `evidence/20261026-semibin-runtime.json`、`contracts/semibin-runtime-resources.md`。


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


2026-10-26：PlasmidFinder调查新TA-094/095启动候选；实际模块5phase/5trace、172mock和87archives/固定源码核对，12patches162paths；仍ready/unaccepted，资源接线未完成。清理失效Python3.15安装，逻辑1.28GB/观测502448128bytes，完整清单/84包锁与原始归档保留。详见work-summary、契约和新候选receipt。


2026-10-26：用户明确禁止病毒元素；本轮病毒fixture未下载/未运行，未执行下载器与空目录已删，旧病毒阴性用完整固定细菌Bacteroides替换并保留原TSV MD5。PlasmidFinder资源候选13phases23trace/8unit/178mock/2细菌nf-test，48私有DB文件还原；13patches171paths，41pairs38candidate+3pending。正式清单与问题接受边界不变。


2026-10-26：MOB3.1.9 immutable eb860648源码/选择边界19场景+未知参数拒绝；默认verify_init可触发准备，科学前需非病毒资源门禁，尚无原生安装/DB/科学执行，MOB pending不减。14patch173paths，正式718不变。清理旧失败PlasMAAG6生成BAM/BAI，逻辑1779612564bytes/实测550785024bytes，2160JSON引用/453固定证据复核，输入/成功v2/日志/trace保留。


2026-10-26：MOB软件环境180包/归档核对，跳过确会mob_init的post-link；实际CLI3.1.9、tag3.1.8版本差异记录。独立只读预检2拒绝/8结构单元/4CLI通过，无科学分类/DB准备/生产接线；软件包附带10FASTA未使用，非另行数据下载。15patches177paths/783snapshot，正式718及99/2/8和41pairs38+3不变。


2026-10-26：MOB两YAML改官方固定SHA wheel+同179Conda依赖，16源码raw-package exact；真实Nextflow软件4trace2COMP2CACHED/no skip-link/DB未初始化，非科学任务。补记Typer默认环境DB隐式对42=38candidate+4pending；16patch183paths/787snapshot，正式718/99/2/8不变。旧独立MOBprefix清理，逻辑2112274204bytes/实测79757312bytes，完整清单/180锁元数据归档/55固定证据保留，新最终prefix保留。


2026-10-26：MOB3别名执行guard显式输入接线，固定native parse/path/main argv保留，真实准备点禁init/ETE3升级、taxonomy ro；6实际准备FAILED+3stub，16唯一边界/结构单元，178mock/2nf-test stub/12发布trace/52显式目录stub-cache通过。完整prepared科学案例未执行，资源身份pending4。17patch192paths/791snapshot，正式718与99/2/8不变。publication私有work按驱动清理，最终副本hash复核，无空间虚报。


2026-10-27：Medaka cache-v2队列终态独立复核：14阶段真实完成/返回0，probe逐次重跑、不变与三处还原consumer CACHED同hash 9a/2d5a60，有效同大小同mtime模型归档身份变化consumer重算（f4/c0d632），坏模型trailer/坏MMI/坏FAI在probe exit1拒绝、运行上下文不匹配在消费者script闭包查缓存前拒绝，plain/ordinary-gzip/BGZF完整FASTA均对应原生基线；队列后11源码guard+4原始资源SHA256复核不变。TA-091/096仍in_progress不关闭，正式99/2/718不变。见[复核](contracts/medaka-cache-queue-review-20261027.md)与[证据](evidence/20261027-medaka-cache-queue-review.json)。


2026-10-27：Medaka可选分支探测级验证通过：-x下损坏相邻FAI/MMI被跳过（force_indexes=true/source_indexes=null，对应固定脚本170-172行mini_align -f），同fixture默认分支rc1拒绝；-B单区间BED内容身份入receipt（原生186-204行仅传medaka inference）；RLE检测三方等价（原生CLI/helper/receipt均false），包内无已准备RLE模型，变换分支仅源码级依据；调用端共享选择器与符号链接解析边界复核健全。原始资源不变，TA-091仍in_progress。见[契约](contracts/medaka-optional-branches-20261027.md)与[证据](evidence/20261027-medaka-optional-branches.json)。


2026-10-27：Medaka -x/-B完整真实推理验证通过：原生-x共识=默认native-v1，生产-x输出/gaps BED一致、receipt force_indexes=true；原生-B仍输出全部contig、contig_1由draft回填（gaps BED contig_1 0 4724790），生产-B与原生基线逐字节一致。新原生行为记录：-B只限推理区间不限输出contig；已抛光fixture下序列oracle弱，判别靠gaps BED。v1误设断言失败目录保留。TA-091仍in_progress（RLE真实执行缺），正式99/2/718不变。见[契约](contracts/medaka-optional-exec-20261027.md)与[证据](evidence/20261027-medaka-optional-exec.json)。


2026-10-27：TA-095独立复核通过：固定2.1.6原生parser在钉住py310环境对--legacy仍exit2 "unrecognized arguments"（完整原569B/540bp fixture作-i），同env --help exit0（旁证TA-094启动修复）；当前config无--legacy、mock断言在位、environment.yml钉python=3.10，历史py310-legacy/run.json完整。建议下一合并批接受；台账与718清单不变。见[证据](evidence/20261027-ta095-review.json)。


2026-10-27：TA-094独立复核通过：钉住py310环境实际Python3.10.22，按历史同命令真实重跑完整540bp阳性exit0，results_tab.tsv与两份FSA逐字节等同2026-10-26基线，data.json仅run_info日期/时间不同（其余22键一致）；3.15.1失败环境已按台账清理、历史失败证据保留不重解。建议下一合并批接受；台账/718不变。见[证据](evidence/20261027-ta094-review.json)。


2026-10-27：TA-093独立复核通过：evidence钉住的20项artifact全部重哈希匹配；完整原ACBA fixture（SHA不变）在固定2.0.5环境真实重跑三模式——默认隐式circ得1complete、--linear得1CALIN+1In0、--circ保留原1complete，与topology-before-after.json逐项一致；候选拓扑表helper仍在模块两调用点。建议下一合并批接受；台账/718不变。见[证据](evidence/20261027-ta093-review.json)。


2026-10-27：TA-092独立复核通过：22项钉住artifact全部匹配；钉住驱动/tests/run_abricate_errors.py（SHA一致）真实重跑三例——converter/blast晚失败下原1.0.1仍exit0且带5真实命中，守卫exit1；合法零结果两者均exit0零命中，无误伤；fixture/源码SHA全不变。四项ready S0候选（TA-092/093/094/095）独立复核均完成并建议接受，待合并批次。台账/718不变。见[证据](evidence/20261027-ta092-review.json)。


2026-10-27：合并接受批次20261027-consolidated-acceptance完成：TA-092/093/094/095经独立复核转为bounded verified，台账110项=103verified+2退役+5未决（S0 TA-091/096；S2 TA-016/031、TT-003），findings.tsv与acceptance.md已更新；四项候选补丁层9/11/12/13所涉文件与HEAD一致，进行中Medaka接线不在本批；正式718清单不变。见[receipt](../../results/tool-audit/20261027-consolidated-acceptance/receipt.json)与[复核](../../results/tool-audit/20261027-consolidated-acceptance/review.md)。


2026-10-27：TA-091/096首个OCI后端边界通过：rootless Podman拉取钉住镜像quay.io/biocontainers/medaka:2.2.2--py312h3050eb1_0（digest sha256:18d5d73a…），未修改生产probe+consumer在容器内均COMPLETED，helper全部钉住校验（2.2.2源码/medaka_consensus/mini_align/模型选择加载）对镜像内安装成立，完整FASTA与conda native-v1基线逐字节一致，原始资源不变。仅单镜像单后端、plain draft；Docker/Singularity/远程/AWS与-x/-B/RLE容器内分支未覆盖，TA-091/096仍in_progress。驱动tests/run_medaka_podman_exec.py，见[证据](evidence/20261027-medaka-podman.json)。


2026-10-27：对当前工作区（含未提交TA-091/096 Medaka接线）全量重放P0 main拒绝注册表：83/83通过（75注册main拒绝含8 MAG依赖矩阵+8 direct MAG_HOST），每例精确诊断、0分析任务、0 .command.sh；main.nf SHA仍绑定39f4d062（Medaka接线未改main），重放不增分母、非端到端/框架认证。磁盘余量8.2G，未启动大下载。见[证据](evidence/20261027-main-p0-replay.json)。


2026-10-27：磁盘97%满（余8.2G）阻碍MOB/GTDB资源准备；完成清理候选审查（只出计划未删除）：Medaka已完成阶段的中间BAM/HDF/任务私有副本合计约13.7G逻辑字节可清（cache-v2/work、production work、framework-gzip-v1、optional-exec v1失败轮与v2、podman-v1），各阶段receipt/trace/log/最终FASTA与钉住哈希保留；plasmaag-remote-url-pkg-cache6.7G须先核对归档留存。明确非候选：plasmaag-native-env-v4（在57保留prefix清单）、PlasX主库、HOTSPOT assets、medaka-nomiss完整样本、runtime环境。删除需用户授权，见results/tool-audit/20261027-cleanup-candidates/medaka-intermediates-plan.json。


## 2026-10-27重试与TA-096有界接受

实际早期版本检查注入失败后Nextflow两attempt不同workdir，第二次完整原生推理及全序列复核通过；首attempt无成功产品。补实际原模块ordinarygzip冷失败，重核14阶段guard与10完整FASTA后TA-096有界verified，TA-091保持开放。既有TA-092～095状态字段与生成器/registry同步，未增加这四项范围。当前110=104verified+2退役+4未决；13测试来源补登记不增加用例分母。冻结718来源当前123差异已列出，原清单不替换。详见contracts/medaka-retry-and-acceptance-20261027.md。


2026-10-27：718清单对账独立复核：重哈希全部718项，0缺失、123不匹配、0不可归因——与既有evidence/20261027-accepted-manifest-drift.json的123计数一致；本复核补充归因明细：122项最后提交均不早于2026-10-25（各候选/接受增量层），唯一例外modules/nf-core/medaka/main.nf（末次提交10-16）差异来自已知未提交TA-091 Medaka接线。718清单字节不变。另见并发完成的TA-096有界接受（104verified+2退役+4未决）。见[补充证据](evidence/20261027-manifest-reconciliation.json)。


2026-10-27：TA-096接受独立复核通过：5项钉住哈希全匹配；retry-v2 trace两attempt不同workdir、attempt1磁盘上确无test.fa.gz/consensus_probs.hdf、attempt2完整FASTA对应原生基线；修复前原模块冷失败任务日志含真实samtools "Cannot index files compressed with gzip"。接受范围回读无越界，TA-091保持唯一开放S0。见[复核证据](evidence/20261027-ta096-independent-review.json)。


2026-10-27：MOB默认库归档取得并核验：Zenodo10304948 data.tar.gz 472,851,578字节，MD5与官方元数据一致，SHA256 531f2124…；内容9数据文件（rep/mob/mpf/orit/repetitive/ncbi_plasmid_full_seqs等），文件名与全部31,888条FASTA头部筛查0病毒/噬菌体命中（头部级，不排除质粒内病毒同源片段）。未解包建库、未跑mob_init（其禁TLS校验且自动初始化taxonomy）、无科学运行。归档保留于results/tool-audit/20261027-mobsuite-db/。见[证据](evidence/20261027-mobsuite-db-archive.json)。


2026-10-27：MOB受控建库完成（不用mob_init）：按固定3.1.9 wheel环境的原生makeblastdb/mash调用精确复制mob_init步骤2-5，29文件2.2G，逐文件SHA256清单已存；status.txt带诚实的受控构建来源说明。生产preflight复核mob_recon/mob_typer均仅缺ETE3DBTAXAFILE，其余必需路径全部就绪。未跑科学用例；磁盘余6.2G。下一步受控ETE3 taxa.sqlite准备后跑阳性/阴性对照。见[证据](evidence/20261027-mobsuite-db-build.json)。


2026-10-27：用户授权清理执行（cleanup-9两批）：Medaka已完成阶段中间产物逻辑13.17G/实测+12.26G；冗余pkg-cache（158/158与保留缓存SHA256一致）+uv-cache逻辑9.11G/实测+1.28G（硬链接差异如实记录）。可用空间6.2G→20G。全部证据/receipt/主库/环境/当前样本保留，详见cleanup.md与results/tool-audit/20261027-cleanup-9/。


2026-10-27：MOB默认库准备闭合：NCBI taxdump经TLS校验下载（79,933,488字节，SHA256 6056adf8…，NCBI无官方校验值，记录观测值），以ete3显式taxdump_file路径受控构建taxa.sqlite（777MB，无隐式下载）。生产preflight现对mob_recon（11路径）/mob_typer（10路径）全部通过，taxonomy schema DB_VERSION=2。31文件清单SHA256 5977aa77…。无科学运行；磁盘余19G。下一步MOB科学阳性/阴性对照。见[证据](evidence/20261027-mobsuite-taxonomy.json)。


2026-10-27：MOB首个科学对照通过：经生产preflight guard（固定3.1.9源码/资源路径/ETE3只读schema核对后调原main）跑mob_typer——pUTI89完整质粒阳性得IncFIA+IncFIB、MOBF+MOBP、MPF_F（符合IncF预期），4.7Mbp无质粒染色体阴性全'-'且non-mobilizable，均exit0。首次PATH缺blast系工具的exit255为harness错误已记录。mob_recon与缓存身份接线未覆盖。见[证据](evidence/20261027-mobsuite-science-controls.json)。


2026-10-27：mob_recon对照经生产guard完成：阳性（pUTI89+无质粒染色体69contig）中pUTI89独立重建为plasmid AA337并正确分型IncFIA+IncFIB/MOBF+MOBP/MPF_F，染色体contig保持chromosome；阴性中2条小contig（4965+1683bp）被判plasmid AF232——边界观察：仅mash最近邻CP034740@0.0593（恰低于原生默认阈值）而零biomarker，属原生默认行为非管道缺陷，下游不应把小contig无biomarker的plasmid标签当强证据。两例exit0。见[证据](evidence/20261027-mobsuite-recon-controls.json)。


2026-10-27：MOB生产模块集成通过：真实Nextflow26.10+micromamba复用钉住环境，MOBSUITE_TYPER输出与直接guard CLI阳性逐字段一致（仅前缀不同），MOBSUITE_RECON的plasmid_AA337与直接CLI逐字节一致。v1/v2/v3失败尝试（占位符/conda缺失/-log重复）保留。明确TA-091边界：RECON的DB经ext.args传递、不在deep缓存键内，TYPER显式携带；MOB对缓存身份接线仍开放。harness为tests/nextflow/mobsuite_prepared.nf。见[证据](evidence/20261027-mobsuite-prepared-modules.json)。


2026-10-27：Dorado隐式模型合约级审查（TA-091最后pending资源对）：确认三重隐式——'hac'浮动模型名自动下载最新版、模型搜索路径隐式（模块三处都不用，落CWD不入缓存键）、无容器钉住（:latest浮动）+PATH软件无版本断言；官方文档依据已引，本机无dorado未执行。建议门禁设计记录于契约，不构成接受、无下载无科学运行。见[契约](contracts/dorado-implicit-model.md)。


2026-10-27：TA-091候选补丁TA-091-mobsuite-recon-db-input.diff（SHA 0bc678a3…）：MOBSUITE_RECON新增显式tuple path(db),val(db_identity)输入入deep缓存键，两个生产调用端与TYPER同样经resourceInput(params.mob_suite_db)接线，缺省为显式absent身份、保留原生默认目录分支。集成v5真实通过（.command.sh含--database_directory 'db'，AA337与直接CLI/旧轮逐字节一致）；stub nf-test2/2通过，三次harness失败（PATH/-log/eval）保留。候选未接受，TA-091仍in_progress；recon的native prepared nf-test例未跑。见[证据](evidence/20261027-mobsuite-recon-db-input.json)。


2026-10-27：MOB native prepared nf-test首次真实运行2/2通过：recon对单contig 5,150,703bp B.fragilis完整染色体（自保留genome.fna提取的完整复制子，非下采样）输出chromosome==输入DNA、无质粒、版本3.1.9；typer报告断言通过。发现并修复测试接口缺陷：nf-test0.9.5的then上下文取不到nextflow params（null路径撞上仓库根null/目录），改用MOBSUITE_BACTERIAL_FASTA环境变量；params{}块不受0.9.5支持，失败尝试保留。候选补丁更新为5文件SHA 72c47151…。TA-091仍in_progress（候选未接受）。见[证据](evidence/20261027-mobsuite-recon-db-input.json)。


2026-10-27：删除游离null/目录（约88K，未跟踪未引用）——某运行params.outdir未设置时Groovy把null插值为字面目录名；它正是此前nf-test "null（是一个目录）"失败的环境陷阱。清单管道写入失败（xargs空输入），仅记录文件名清单并如实标注未捕获哈希；不影响任何证据链。


2026-10-27：refresh_status.py重生成status.md并核对一致：110项=104verified+2退役+4未决（S0仅TA-091；S2 TA-016/031、TT-003），最近接受批次TA-096；718清单当前工作区匹配=False如实显示（123差异已另列归因）。TT-003核查：legacy ENA 16S数据与integration测试数据均已被此前清理删除，重跑需重下载（6样本约250MB）+podman长运行；完整shotgun P4仍需适当非空shotgun队列。


2026-10-27：TT-003基础准备：legacy ENA 16S六样本按锁重下载并逐文件SHA256核验（238MB，12/12），geNomad子集库按git blob sha1核验（避开real-nodes锁中sarscov2病毒文件，仅取非病毒必需项）；legacy ENA nf-test以podman后端启动（长运行，结果下轮核对）。完整非空shotgun P4仍需适当shotgun队列，本运行仅覆盖更新后断言的真实框架执行部分。


2026-10-28：TT-003框架部分通过：legacy ENA 16S六样本nf-test在podman后端真实执行SUCCESS 1/1（1825s，100任务全成功0失败），更新后Groovy断言（含独立alpha公式复核与低重复门控）真实执行。环境修复：pullPolicy=missing覆盖层（wave注册表瞬时失败）、本地构建autoplasm-r-analysis（5.05GB）、python:3.12-slim缺procps致ps失败→本地覆盖镜像（上游digest已记录，模块未改）；v3一次bowtie2 flaky挂起撞1h时限如实记录。数据：ENA按锁SHA256核验12/12，geNomad子集按git blob sha1核验，real-nodes锁中sarscov2病毒文件未下载。TT-003仍开放：16S非shotgun，需适当非空shotgun队列P4。见[证据](evidence/20261027-ena-legacy-framework.json)。


2026-10-28：TT-003 shotgun队列选定并锁定：用户明确PRJDB5375海洋宏基因组可接受（本底噬菌体不算病毒专用元素，约束针对病毒专用fixture/库）。按ENA portal实测library_strategy=WGS、天然采样点分组选定2×3队列：sendai_bay(DRR083116/167/184) vs aline(DRR083096/252/153)，12个PE文件共1.73GB，锁tests/nf-test/shotgun-multisample.lock.json含MD5/大小/设计说明；下载+MD5核验进行中。Zymo（大体积无分组）、唾液（单条件）候选排除理由保留于contracts/tt003-shotgun-cohort-candidates.md。


2026-10-28：TT-003 shotgun P4测试已写就：tests/nf-test/nodes-cross-sample-shotgun.nf.test（镜像legacy ENA契约：独立alpha公式、deseq2状态两分支、网络资格两分支、报告断言；config用integration.config即生产QUAST阈值，16S的min-contig200覆盖不适用）；samplesheet 2×3（sendai_bay vs aline）已建。队列下载进行中（193MB/1.73GB）。


2026-10-28：TA-016范围核查（只读）：当前仅consensus/structure两个R生产者有task_provenance，其余生产者为静态版本声明；报告bin/generate_report.R:278已诚实区分"static, not runtime probes"。扩展接入是系统性实现工作，需在无并行长任务窗口进行。shotgun队列下载642MB/1.73GB继续中。


2026-10-28：shotgun队列下载发现真实上游缺文件：DRR083167_2.fastq.gz在ENA API列出但FTP上不存在（301到目录索引，780B HTML），重试7次一致；按预定规则换成同组次小run DRR083259（两mate均HTTP200），锁与samplesheet同步更新并在锁内记录替换原因；测试样本列表同步。已下载7/12文件MD5全通过，剩余5+2续传中。


2026-10-28：shotgun队列12/12文件下载+MD5核验全通过（DRR083252_2一次SSL重试成功）；TT-003 P4真实测试nodes-cross-sample-shotgun.nf.test以podman后端启动运行（20261028-shotgun-p4-v1）。


2026-10-28：shotgun P4运行中磁盘一度降至3.3G：清理ena-legacy失败轮work、podman悬空镜像（4个none层，实回收约1.6G）及v5通过轮任务work（1,947文件SHA清单保存于20261027-ena-legacy-v5/task-work-manifest.txt，最终产物与junit保留）。回到5.1G后运行稳定。逻辑删除量与实测差异受硬链接影响，不虚构。


2026-10-28：TT-003首个真实shotgun P4执行通过但质粒特征为零：3 Sendai-Bay vs 3 Aline（PRJDB5375，含换人DRR083259）nf-test SUCCESS 1/1、100任务全成功；contig丰度391,344行、diversity 24行非空且独立alpha公式通过；geNomad测试子集库零质粒→DESeq2零特征合法no-fit、FastSpar insufficient_features正确跳过，两分支均以明确机器可读原因执行——空路径静默许可的缺陷类已覆盖。但严格"非空质粒统计"未满足，TT-003保持开放，需富质粒（肠道/粪便）队列让fitted/eligible分支也在真实数据上执行。见[证据](evidence/20261028-shotgun-p4.json)。


2026-10-28：决定性灵敏度检查：测试子集geNomad（--disable-nn-classification）在已知质粒阳性B.fragilis完整基因组上也零质粒调用（47kb质粒contig未被调用；另正确报出染色体内44kb原噬菌体，非我方引入的病毒fixture）。结论：非空质粒统计分支在钉住测试库下不可达，与队列无关——需要完整geNomad库+NN（即TT-003要求的部署级P4）。见[证据](evidence/20261028-genomad-sensitivity.json)。


2026-10-28：完整geNomad DB v1.9取得：NERSC官方portal下载842,023,773字节（与content-length一致；两次504+一次SSL重试成功），SHA256 47a54faa…，解包1.4G、version.txt=1.9。部署级shotgun P4启动（20261028-shotgun-p4-deployment-v2）：完整库+NN启用（去掉测试only的--disable-nn-classification），同一PRJDB5375契约。磁盘应急修剪：P4 v1通过轮任务work（6.4G，1,886文件SHA清单保留）与medaka-retry-v2 work已清，最终产物/junit/断言输出保留。


2026-10-28：真实系统状态变化记录：SELinux于当日10:07–12:02间从可用状态转为Enforcing（非本审计操作所致），致绑定挂载Permission denied、部署P4 v2/v3失败。诊断链：probe逐级定位MCS类别不匹配；chcon一次性误带--reference=/dev/null被其自身参数冲突校验拒绝、未发生任何重标记（已核实抽查）；正确chcon -R -t container_file_t -l s0整树重标记完成（69s，0错误），podman读挂载探针恢复。部署P4 v4重跑中。v3失败为重复挂载destination（runOptions与Nextflow自身挂载冲突）。


2026-10-28：部署P4 v4核实未生效：configFile附加的params.genomad_db与GENOMAD ext.args被测试config链（integration.config→test.config）覆盖，实际仍跑子集库+disable-nn（.command.sh实证）；v2/v3另受SELinux影响。v5改用AUTOPLASM_TEST_DATA指向完整库目录重跑；NN仍被harness钉为disabled，属测试范围限制如实记录。另v1通过轮output已带清单删除（456文件SHA），v5 legacy output亦同法处置；磁盘回到4G量级。


2026-10-28：TT-003完整geNomad库部署运行v5失败于真实资源约束：mmseqs prefilter对228k profile完整库需临时空间"最多22G"，本机当时仅4G（含应急修剪后）。另确认v5的GENOMAD仍带harness钉住的--disable-nn-classification（ext.args来自test.config链，configFile不覆盖）。海洋队列装配/前段任务在完整库staging前正常。状态：测试配置P4已通过（v1）；完整库部署P4受磁盘容量阻塞，需用户决策退役可重建主资源（如PlasMe 19G/PlasX 17G库）或外部存储。mmseqs splits等降峰值参数受harness钉住的ext.args阻挡，需先解除该覆盖链。


2026-10-28：TA-016扩展候选：QUAST接入task_provenance（首个非R生产者），真实podman quast5.3.0/pUTI89验证COMPLETED，命令文件SHA256与实发一致；补丁TA-016-quast-provenance.diff已存。候选未接受；其余生产者未接线，报告端到端未重跑。磁盘应急：medaka-nomiss四轮BAM/HDF中间产物带清单删除（证据哈希在案），v1通过轮output亦带清单处置。


2026-10-28：TA-016 QUAST候选报告层复核：现有17/17报告单元全过；runtime_command通用校验（字节保留/校验不符拒绝/缺失拒绝/重复拒绝）覆盖QUAST形态记录，无需新增用例。报告端到端重跑仍未做。


2026-10-28：TA-016 FLYE接入候选：真实podman flye2.9.5在2万条接口控制读段（明确技术控制非科学样本）COMPLETED，provenance SHA与实际命令文件一致。修复两个作用域问题（def prefix对output不可见/stub重复声明，失败轮保留）。补丁TA-016-flye-provenance.diff已存，候选未接受。


2026-10-28：TA-016 FASTP接入候选：3脚本分支+stub均接provenance；真实podman fastp1.3.6 PE分支在锁定ENA读段对上COMPLETED，SHA与实际命令文件一致。v1参数个数/v2 Groovy转义两轮失败保留。补丁TA-016-fastp-provenance.diff已存；interleaved/SE分支同改未单独执行。


2026-10-28：TA-016 FASTQC接入候选：真实podman fastqc0.13.0/锁定ENA PE对COMPLETED，SHA一致。补丁TA-016-fastqc-provenance.diff已存。已接入6生产者：consensus/structure/QUAST/FLYE/FASTP/FASTQC。


2026-10-28：TA-016 NANOPLOT接入候选：模块声明的1.47.0镜像拉取并在接口控制读段（2万条ONT，技术控制）上COMPLETED，SHA一致；注意本地旧1.46.2镜像存在但按声明用1.47.0。补丁TA-016-nanoplot-provenance.diff已存。已接入7生产者。


2026-10-28：TA-016 FILTLONG接入候选：真实podman filtlong0.2.1接口控制COMPLETED、SHA一致。补丁TA-016-filtlong-provenance.diff已存。已接入8生产者：consensus/structure/QUAST/FLYE/FASTP/FASTQC/NANOPLOT/FILTLONG。


2026-10-28：TA-016 MEGAHIT接入候选：真实podman megahit_pigz在锁定ENA PE读段上COMPLETED，SHA一致。补丁TA-016-megahit-provenance.diff已存。已接入9生产者。


2026-10-28：磁盘清理（20261028-cleanup-10，用户授权）：删除v4已通过轮内层work、5份plasmaag intermidiate_files、mamba repodata缓存，以及5个逐成员核对解包的下载归档和1,945份Conda包归档；逻辑35,118,985,374字节，可用空间4,597,522,432→29,386,518,528（约+23.09GiB）。逐文件SHA/大小/模式/mtime清单、归档SHA与provenance在results/tool-audit/20261028-cleanup-10/；解包主库、全部安装环境、最终产物、receipt与锁保留，归档重建须按锁/URL重下；genomad（TF 2.21.0）与plasmaag（torch 2.13.0+cpu）冒烟通过。


2026-10-28：新发现TA-097（S1）：SPAdes图来源守卫的完成标记过严——只认"finished."精确文本，真实metagenome（DRR083096）与minigut运行均以"finished WITH WARNINGS!"结束（常规估值警告），守卫拒绝全部真实非完美组装，Recycler路径在真实数据上无法运行。候选修复：接受两种完成形态并在provenance JSON记录警告存在/数量，不改算法。注意守卫为2026-10-26 9d36a98用户侧提交所加，尚无真实运行通过过该严格标记；接受前需复核。TA-016 SPADES provenance验证被此守卫阻挡而非模式本身问题；findings.tsv已登记（111项）。


2026-10-28：TA-097候选修复+TA-016 SPADES接入验证通过：守卫接受"finished."/"finished WITH WARNINGS!"两形态并记录completed_with_warnings/warnings_count（4）；真实podman SPAdes4.1.0 minigut COMPLETED，provenance SHA一致，图来源JSON含max_k=55/K55 copy_source/完整哈希链。两补丁已存；候选均未接受，警告内容审查政策未定义（候选仅记录）。已接入9生产者+SPADES待TA-097复核。


2026-10-28：TA-016 HIFIASM_META接入候选：新建micromamba环境（envs/assembly_hifi.yml；ha 0.13-r308/hamt 0.3-r079），原生真实运行在ONT接口控制读段COMPLETED（明确：hifiasm_meta是HiFi组装器，ONT输入不是其合法科学输入，仅验证接口/provenance路径，不评价组装质量），SHA一致。补丁TA-016-hifiasm-meta-provenance.diff已存。已接入10生产者。


2026-10-28：TA-016 MULTIQC接入候选：真实podman multiqc1.35消费fastp真实json产出COMPLETED，报告html生成，任务命令文件在位（sha a08ee7e0…）；v1失败为stage了work目录而非json产物（No analysis results）。补丁TA-016-multiqc-provenance.diff已存。已接入11生产者。


2026-10-28：TA-016 GENOMAD接入候选：真实podman genomad1.12.0+子集库/pUTI89 COMPLETED，SHA一致；v1失败为进程名实为GENOMAD_ENDTOEND（调用端别名GENOMAD）。补丁TA-016-genomad-provenance.diff已存。已接入12生产者。


2026-10-28：TA-016 PLATON接入候选：原生platon-1.7环境+保留DB在pUTI89上COMPLETED，探针改为platon --version（platon_checked.py无--version），SHA一致。补丁TA-016-platon-provenance.diff已存。已接入13生产者。


2026-10-28：TA-016 PLASME接入候选：原生plasme-1.1环境+保留模型库+PLASMe源码在pUTI89上COMPLETED，探针为plasme_runtime.py -h（无--version），SHA一致；v1失败为DB需指向DB/子目录。补丁TA-016-plasme-provenance.diff已存。已接入14生产者。


2026-10-28：TA-016 PLASX两进程接入候选：复用保留的S.1注释产物与profiles/模型/源码，真实原生运行COMPLETED，SHA一致，产出真实de_novo+预测分数。探针为checked wrapper -h。补丁TA-016-plasx-provenance.diff已存。已接入15生产者（含PLASX_ANNOTATE）。磁盘由外部释放回到27G。


2026-10-28：TA-016 ABRICATE+PLASMIDFINDER接入候选：ABRICATE经原生probe+consumer在2.5MB原fixture/私有alias库COMPLETED（真实BlaI命中），PLASMIDFINDER经py310环境probe+consumer在540bp阳性fixture COMPLETED，两者provenance SHA均与任务命令文件一致。v1失败为alias私有库路径；两模块def prefix作用域修正。合并补丁TA-016-abricate-plasmidfinder-provenance.diff已存。已接入16生产者。


2026-10-28：TA-016 MOB_TYPER+MOB_RECON接入候选：受控库下两模块均COMPLETED，命令文件SHA固定（f0752fa6/722453d3）。v1编译失败（def prefix作用域）已修正保留。补丁TA-016-mobsuite-provenance.diff已存。已接入18生产者。


2026-10-28：TA-016队列级生产者设计契约：cross_sample各模块无逐样本meta，需cohort扩展（任务内从暂存元数据实际读取样本域、cohort:true记录、R端校验cohort_samples⊆期望域）。记录在contracts/ta016-cohort-provenance-design.md，未实施。


2026-10-28：TA-016队列级provenance实现候选：reportEvidence新增cohort_provenance分支（cohort:true+样本列表），generate_report.R新增cohort域校验（非空且全部∈期望域），DIVERSITY接入（eval从暂存cohort元数据实际读样本域，cut -f1）。单元20/20（含3新cohort用例）；真实podman运行COMPLETED，cohort=s1,s2,s3正确。v1缺契约R文件、v2 awk分隔符转义问题均保留。补丁TA-016-cohort-provenance.diff已存。


2026-10-29：TA-016队列provenance批量接入：reportEvidence/R校验/DIVERSITY沿用前轮，新接入DESEQ2/DIFFERENTIAL_ABUNDANCE/NETWORK_PREPARE/STATISTICS_INPUTS/FASTSPAR/MERGE_ABUNDANCE/SHARED_ABUNDANCE_TABLES/SHARED_CATALOGUE；探针按工具实际（Rscript/fastspar/python helper -h带analysis_code/暂存路径）。9模块联合编译通过，单元20/20，DIVERSITY/NETWORK_PREPARE/SHARED_CATALOGUE真实运行COMPLETED且cohort域正确。v1-v3失败（缺R source、awk转义、目录vs文件列表、探针路径）保留。补丁TA-016-cohort-provenance.diff已存。REPORT与剩余单样本生产者未接线；报告端到端未重跑。


2026-10-29：TA-016覆盖/比对组接入候选：BOWTIE2_ALIGN/COVERM_CONTIG/SAMTOOLS_FASTQ/MERGE/SORT/VIEW/MINIMAP2_ALIGN七模块；7模块联合编译通过；BOWTIE2_ALIGN+COVERM_CONTIG真实链（锁定ENA PE vs pUTI89，本地镜像建索引）COMPLETED、SHA一致；其余5个仅编译级。首批批量打补丁误在闭合引号后插入被回滚重打，记录保留。补丁TA-016-coverage-provenance.diff已存。已接入24生产者。


2026-10-29：TA-016 INTEGRONFINDER接入候选：原生integronfinder-2.0.5环境+官方仓库fixture（acba.007.p01.13.fst）probe+consumer均COMPLETED；探针身份JSON固定2.0.5及模型/可执行/包SHA；provenance命令文件SHA c617b3ce…（运行后重算一致）。stub内def prefix改共享prefix作用域修正。补丁TA-016-integronfinder-provenance.diff已存。已接入25生产者。typing/host批其余8模块仍仅编译级。


2026-10-29：TA-016 ISESCAN+RGI_MAIN接入候选：ISESCAN原生isescan-1.7.3-modern+锁定fixture NC_012624.fna probe+consumer COMPLETED，真实IS5命中，provenance SHA 50e835f2…；RGI_MAIN原生rgi-6.0.8+保留CARD 3.2.8夹具真实rgi load --local COMPLETED，DB_VERSION=3.2.8捕获正确，pUTI89零AMR命中（科学空结果），provenance SHA 8d57cabd…。发现并修复批量插入错误：RGI_MAIN的cp曾被插进load_wildcard赋值字符串（wildcard存在时会把cp参数并入rgi load命令行），已移至script块顶部；全库扫描确认无其它同类错位。合并补丁TA-016-isescan-rgi-provenance.diff已存。已接入27生产者。


2026-10-29：TA-016 MACSYFINDER_SEARCH接入候选：原生macsyfinder-2.1.6+保留CONJScan-2.1.0模型+gembase蛋白fixture真实CONJSCAN(boundary) COMPLETED，真实all_systems输出，provenance SHA 0c2b5782…。补丁TA-016-macsyfinder-search-provenance.diff已存。已接入28生产者。MACSYFINDER_DOWNLOAD（需联网macsydata）仍仅编译级。


2026-10-29：TA-016 REPORT自身来源接入候选：REPORT无meta且为终端消费者，不套用task_provenance事件流；改为新增输出REPORT.task_command.sh（cp BASH_SOURCE[0]）随publishDir发布到report/。原生R 4.6.1+既有fixtures真实report_runtime链6任务全COMPLETED，发布文件与.command.sh逐字节一致（SHA c8af4f9f…）。v1失败（bin/不在PATH，plasmid_consensus.R未找到）保留。补丁TA-016-report-self-provenance.diff已存。


2026-10-29：TA-016 OPERA_MS接入候选：opera-native-env.sh固定环境（perl5.32.1+Switch.pm+ncurses5）真实OPERA-MS v0.8.3 minigut_hybrid COMPLETED，57条contig共1.78MB，provenance SHA 4724c37e…；探针为perl -S OPERA-MS.pl --help（无独立--version，--help首行含版本）。无stub块故仅script插cp。补丁TA-016-opera-ms-provenance.diff已存。已接入29生产者（REPORT自身另计）。


2026-10-29：TA-016比对组接入候选：BLAST_BLASTN/MUMMER/CLINKER/MMSEQS_EASYCLUSTER四模块task_provenance+cp；PLASMID_CATALOG_PREPARE无meta且无样本域输入，按REPORT式自来源发布PLASMID_CATALOG_PREPARE.task_command.sh。五模块经新harness tests/nextflow/comparative_compile_check.nf真实Nextflow 26.10编译通过，补丁反向apply校验通过；首版补丁误混入git status行已重打（保留记录）。真实运行待做（BLAST需DB、CLINKER需Bakta gbff）。已接入/自来源34模块。


2026-10-29：TA-016 MAG/host/linking/basecalling批量接入候选：带守卫补丁器（results/tool-audit/20261029-mag-linking-patch/apply_provenance.py）接线23模块（首轮22后追加EGGNOGMAPPER）——22个meta级task_provenance（SAMTOOLS_INDEX、METABAT2×2、CONCOCT×4、DASTOOL_DASTOOL、SEMIBIN、GTDBTK、KRAKEN2、METAPHLAN、PRODIGAL、HIFIADAPTERFILT、RECYCLER、PLASMAAG、PROTEIN_INPUTS、DORADO、LINK_SEQUENCE/HOTSPOT/LONGREAD）+1个cohort级LINK_COABUNDANCE（样本域取host_sample_ids输入）。探针复用各模块既有version惯用法或暂存helper -h。22模块联合编译通过，补丁反向apply校验通过。事故保留：补丁器v1漏拼接插入点后尾部导致22文件截断，git checkout全量恢复后修正重打；v1编译DAS_TOOL命名错误（实名DASTOOL_DASTOOL）已修。LINK_CRISPR为永久exit-2占位不接线。全部仅编译级，真实运行待做。补丁TA-016-mag-linking-provenance.diff已存。
（接上条）补丁再生含EGGNOGMAPPER共29模块（再追加CONCOCT_EXTRACTFASTABINS）（含BOWTIE2_BUILD、DASTOOL_FASTATOCONTIG2BIN、CHECKM2_PREDICT、GPLAS2三进程），SHA abdeaf41…，编译复检通过。


2026-10-29：TA-016 typing/host遗留批补丁固化：BAKTA/AMRFINDERPLUS/PLASMIDHOSTFINDER/MACSYFINDER_DOWNLOAD四模块（早前已接线并过typing_compile_check），补丁TA-016-typing-host-provenance.diff反向apply校验通过。前三者无原生环境/本地镜像、DOWNLOAD需联网macsydata，保持编译级并如实记录。COPLA真实运行仍在进行。


2026-10-29：TA-016 SEMIBIN_SINGLEEASYBIN真实验证：原生semibin-2.4.1+官方single_sample_data fixture，probe+consumer COMPLETED，真实分箱产物（model.pt/output_bins/binning_status.json），provenance SHA 99937f1d…。探针身份JSON固定SemiBin 2.4.1。补丁含于TA-016-mag-linking-provenance.diff。


2026-10-29：TA-016 CONCOCT MAG链真实验证：原生concoct-1.1.0（含samtools）环境+既有official composition/controlled.bam fixtures跑MAG_HOST(mag_tools=[concoct])，SAMTOOLS_INDEX/CONCOCT_CUTUPFASTA/CONCOCTCOVERAGETABLE/CONCOCT/MERGECUTUPCLUSTERING ×2样本共12任务全COMPLETED，10个provenance命令文件SHA逐一记录（evidence 20261029-ta016-concoct-chain.json）。发现CONCOCT_EXTRACTFASTABINS（reportEvidence标签CONCOCT）此前漏接，已补接线并编译通过，补丁更新SHA abdeaf41…。


2026-10-29：TA-016 RECYCLER真实验证：recycler_real.nf（minigut reads+SPADES 4.1.0 beforeScript固定）4任务全COMPLETED，recycler_out含真实input_contract.json，RECYCLER provenance SHA c38cd252…（SPADES dc4f1f1a…顺带）。v1因real-data夹具目录已退役启动前停掉，v2指向20261023-opera-native/real-data。报告R单元20/20通过（REPORT自来源改动无回归）。


2026-10-29：TA-016 COPLA真实验证：原生copla-1.0+保留RS84库+copla-macsyfinder-1.0.5，two_plasmids对照真实运行约80分钟COMPLETED，真实PTU分类（PTU-X4/PTU-Lab26 score 1.0），provenance SHA c18c4521…。会话退出致后台包装失联，但trace与.exitcode=0直接核实任务完成。补丁TA-016-copla-provenance.diff已存。


2026-10-29：TA-016 METABAT2路由真实验证：原生metabat2-2.17+concoct-1.1.0(samtools)环境，MAG_HOST(mag_tools=[metabat2])三任务COMPLETED。v1失败（metabat2环境无samtools，SAMTOOLS_INDEX失败）保留于20261029-metabat2-chain-v1。SCAFFOLDS2BIN_METABAT2未触发（链尾条件）。


2026-10-29：TA-016 BLAST_BLASTN真实验证：blastn_real.nf改原生（podman关闭+abricate-1.0.1环境BLAST 2.16.0+），makeblastdb建pUTI89迷你库后BLAST_BLASTN(pUTI89) COMPLETED，真实命中输出，provenance SHA 98598c84…。BLAST BLASTN/CLINKER容器镜像本地缺失且当前无外网，原生路径代替。


2026-10-29：TA-016 MUMMER真实验证：platon-1.7环境nucmer/show-coords，pUTI89 vs two_plasmids.fna真实比对COMPLETED，provenance SHA 071daefe…。v1失败（query与reference同名文件staging冲突）保留；新harness tests/nextflow/mummer_native.nf。

2026-10-29：接续来源候选进行实际集成复核，确认并修复cohort命名空间校验路径、cohort校验/输出成员丢失、FastSpar stderr版本、共享参考伪样本身份、全局空参考cohort丢失五类问题。保留真实失败后，嵌套别名、20样本生产统计链、4样本真实共享参考链及3样本空参考链均到报告终点；28来源记录逐字节/SHA/探针/样本域与原任务核对。23报告单元+15共享单元通过；三份共享量化/状态表与既有控制逐字节一致。缓存/原生执行分列，首次harness编译失败单列。静态发现比较基因组plasmid_catalog身份仍需动态检验；TA-016保持in_progress，正式接受边界不变。刷新后确认111项/5未决：旧摘要遗漏已在20261028登记的TA-097，已纠正当前计数。详见contracts/ta016-integration-review-20261029.md及evidence/20261029-ta016-integration-review.json。

2026-10-30：TA-097独立复核完成并有界接受：固定4.1.0上游正常/带警告/异常终态区分，当前真实minigut原生模块完成；旧冻结helper拒绝同产物，保留真实干净K33通过，10CLI控制、14来源单元、10Recycler单元通过。修复旧成功掩盖新异常及警告重复计数，原文保留；原生2warning事件（旧候选4含横幅/摘要）不等于质量通过。首次沙箱socket失败与经批准的重跑分列。详见contracts/spades-completion-review-20261030.md及receipt。当前111项=105局部verified+2退役+4未决；正式718清单不变。

2026-10-30：TA-016比较分支实际复现：目录/MMseqs2完成而REPORT因plasmid_catalog伪样本失败。现从目录解析产物生成实际样本清单、两个生产者队列来源进入报告，empty样本1保留；脚本显式path/deep缓存，所有当前调用及nf-test已更新。三任务native成功、10R方法、nf-test1/1及冷/缓存/同大小mtime改字节重跑/恢复缓存四阶段通过；目录DNA及1簇2成员与前态一致，实际报告2来源记录原件/SHA/域核对。只用通用MMseqs18.8cc5c，无geNomad/病毒模型执行。TA-016仍in_progress。详见contracts/comparative-provenance-review-20261030.md及机器证据。
