# tests 测试逻辑审查

用户于本轮明确将 tests 纳入同步审查。tests-inventory.tsv 登记 tests/ 下 Python、nf-test、Nextflow harness、config 和 shell 入口；词法 test/assert 数量不等于独立用例或覆盖率。未将 vendor 上游目录当作本地适配器审查完成。

TT-001：mock E2E 的所有 sample assemblies 使用同一 reference，mock CoverM 根据输出文件名选样本并生成数值。现有核验可验证调用次数、文件布局和一部分标签，不能证明 reads/index/reference 同源。TA-022 已给出同一运行器上的反例。应增加错配故障对照，验证交换参考确实被测试拒绝。

TT-002：Metabat2 的 then 仅验证 task 名；Recycler/SCAPP 的非空目录不保证其中为正确阳性重建，longread 的表头不证明 bridge 真阳性。Hifiasm 允许空图是明确标注的执行测试，不应把它当阳性 assembly 能力；这属于已声明范围，保留，不通过放宽或强加不适合该 fixture 的阳性断言修补。PLATON 阳性断言更强，但只覆盖 plain FASTA，未覆盖生产 gzip；COPLA parser 和 SCAPP ID 反例目前也没有进入生产测试。

TT-003：P4 ENA 的空质粒分支合法，注释也说明不保证 network 执行。缺项是独立非空 fixture，而不是删除空结果允许条件。DESeq2 文件存在不验证真正 count model 成功；diversity 的行数/sample/group 检查不拒绝数值 NA，正如已保留 TA-014 反例。FastSpar 专项目前仅检查前两行列数相等，并未实际证明矩阵行列维度和标签集合一致。

已有较强保护：merge Python 单元用例验证重复键与显式 sample ID；link_sequence_optional harness 直接导入生产 HOST_LINKING，并覆盖缺 MAG/缺 taxonomy/额外键/重复键/空 plasmid；catalog P3 验证独立 accession 和长度。这些局部保护应保留。sample-ID P0 明确要求诊断和零成功分析任务，仍需恢复运行器后当前复验。

下一批测试审查：r_mock 自研统计对照、prepare_data 下载/校验及恶意归档边界、所有 nf-test 数据锁与真实结果归属、测试配置覆盖是否隐藏生产失配、剩余 vendored/local harness。当前仅部分静态审查与已有单元复验，不给 tests 全量通过结论。

## 数据准备与统计 smoke 追加审查

prepare_data.py 的 GitHub 模式校验 size+Git blob SHA1，通用 URL 模式按锁文件 size 与 sha256/md5 检查；提取使用 tarfile data filter，拒绝已有 destination。现有 tests/test_prepare_test_data.py 在仓库 .venv Python 上复验 8/8 通过。默认 Python 和系统 Python 没有 pytest，首个尝试的失败日志已保留；没有安装新依赖，也没有把错误当测试失败。用例覆盖同尺寸/截断污染、通用 SHA、ENA MD5、目录与部分派生布局。内存 URL mock 的输入不是真实 FASTQ/数据库，不算工具可用性证明；其注释对此已有明确区分。

TT-004：download_databases.sh 仅 set -u。fetch 出错返回 1，但各调用不检查，末尾 echo ALL DONE 覆盖退出状态。离线提取原函数、对本地 checksum 错误资产复现，退出 0 且包含 CORRUPT/ALL DONE，见 results/tool-audit/20261020-test-logic/download-failure.json。没有触发下载。脚本另允许无 manifest 的已有非空文件成为新记录，属于首次采集来源而非独立真值，需与正式 lock 校验区分。

r_mock smoke 复验 54 passed/0 failed。DESeq2 case 自行生成 raw_count 表，没有通过生产 MERGE_ABUNDANCE，所以其成功不覆盖 TA-011。多数统计断言检查行数、标签或字段存在，未对 effect size/pvalue/alpha 指标做独立数值对照。report case 直接运行 R 脚本且预先建好发布目录，不能检验 REPORT 的 publishDir/文件依赖和 JSON 发布；其通过不否定 TA-015/017。脚本以 FAIL 计数作最终退出码，单个命令失败能被相邻 check 捕获，这一机制没有发现错误。临时目录退出即清理，若需要失败日志归档还需专门支持，不将 smoke 日志当完整生产运行证据。

历史 execution.json 可追溯到 dirty_worktree=true 的旧基线。historical-manifest-check.tsv 复核其 6 个 source hash，validation.nf.test 已不同、其余 5 个仍匹配；6 个 report 引用 hash 匹配（含重复引用同一 P1 JUnit）。这只能确认历史文件身份，不能认证当前生产代码或每个分支。

Nextflow 26.10.0 的 default/test/podman/conda 四套 config -flat 均当前解析成功，结果在 results/tool-audit/20261020-test-logic/config-*.txt。与先前词法扫描不同，这已验证配置语法/合并，但不证明 task-specific closure、样本关联或工具执行。其他 profile 仍待验证。

## 检测分数与真实输出 schema

TA-023/024 已分别以 PlasX 官方两列格式和原生产 PLASMe 模块复现。现有 consensus 单元的正负标签断言可保护显式 classification，但没有检验低分 PlasX 的含义；将 Platon positive-only 表的逻辑复用到 PlasX 会全部判阳性。现有测试未验证 PLASMe 工具输出路径到标准化文件的适配。应加入各工具固定格式正负/阈值/缺文件用例，保留现有标签错误测试。

## 注释/typing 测试输入与依赖

MacSyFinder/eggNOG 的已读上游用例输入蛋白，无法保护本地传核酸的接线。RGI 测试使用在线 latest CARD 且没有双数据库选择对照，不能证明 declared CARD 被实际使用。静态扫描全部 vendored suite 的 99 个字面 script 引用，14 个出现位置缺失（非 14 个不同模块）；TT-005 对应辅助依赖未落盘，不等于已配置四套 P1 的运行失败。

## MAG 参数差异与 stub 盲区

DAS Tool 的 upstream real tests 加 --write_bins --write_bin_evals，本地没有；stub 无条件造 bins，所以只跑 stub 会掩盖 TA-030。GTDBTk 上游测试显式 --extension fa，本地缺此选项且多来自 .fa.gz；不能转移 upstream pass 到本地 caller。CONCOCT gzip 缺适配需要在实际生产压缩输入上复验。当前 dedicated metabat2 P3 也没有检验下游聚合/质量/分类的完整链路。

## QC 输出桶与单端模块

TT-006 对应 samtools fastq double 未遵循 -0 分类，且 host removal 未进 fixture。FASTP 原模块实际 stub 复现 TA-034：SE 文件生成但 emit 不出现；paired 对照正常。现有 fastp 上游套件包含 SE/PE 用例，不能因局部 paired E2E 成功将 module 全部模式算通过。sample-ids 局部 Nextflow suite 当前 5 场景通过并保留原始日志/工件。

## 比较目录的当前正向证据

Catalog 单元 7/7 和真实 Nextflow catalog suite 均通过。suite 检验旧发布目录隔离、空输入和实际 resume/输入变化，是有意义的消费者依赖测试。它没有执行 MMseqs clustering，不能认证聚类与 abundance feature identity。MUMmer 自比用例需进一步区分 ID/长度文本出现和实际全长覆盖的断言；本轮不把弱于完整覆盖的断言改报成已失败测试。

结构 smoke 仅验证 DTR/普通线性两种输入，遗漏 ITR 拓扑解释和 not_circular 否定标记；实际原 R 脚本反例见 contracts/structure-statistics.md，归入 TT-002。Welch 正常数值与独立 SciPy 对照一致，仅为单 fixture。

FastSpar P3 的 square matrix 注释强于实际断言：仅首行宽度相等；缺所有行/标签/有限性/对称性与准备矩阵校验，归入 TT-002。TA-038 原生准备脚本反例见 structure-statistics contract。

## 运行入口与断言复核（2026-10-20）

原 merge_abundance 单元 5/5 通过（5.666 s），含显式复杂 sample ID、0/1/3 表、ID 数量/空/重复拒绝、重复 sample-feature 不写文件、legacy 文件名回退。测试主要校验身份与拒绝行为，没有断言 coverage/RPKM/TPM 数值与原始列一一对应，不能替代 TA-010/011/012 的跨样本统计验证。未发现这些五项已声明局部目标运行失败。

实际 Nextflow host-routing suite 通过，日志 results/tool-audit/20261020-tests-routing/host-routing.log，工件 /tmp/autoplasm-module-regression-94u_yub1。该 harness 仅调用 HOST_PROFILE_READS adapter，两样本各输出2条 mate；没有真正调用 MetaPhlAn，也未执行完整 hybrid 主流程。suite 使用 set(routes) 比较，会吞掉重复 route；仅检查每行 reads.size，不能发现 R1/R2 或样本路径错配。将这项覆盖不足补充至 TT-002；本次原始输出恰为每样本一条，没有声称生产已出现重复。未匹配 selector 警告是局部 harness 导入范围所致，不直接报生产配置失效。

进一步逐文件核对：OPERA-MS 断言只有 FASTA header，无法区分 final/intermediate（TA-001）；Dorado 只查首条序列，没有完整 FASTQ 记录/质量长度与 read IDs；SCAPP_BIN 只查目录非空，无法保证含真实 bin/序列。SAMTOOLS_INDEX 检查 BAI 前3字节而注释为4字节 magic，也没有基于原 BAM 做区域读取验证；不把有 BAI 签名等同有效匹配索引。均属于已有 TT-002 断言语义范围。

Platon P3 有明确 NC_007941.1 阳性行断言，强于只查目录；其 plain FASTA 正常路径仍不覆盖生产 gzip（TA-005）。BLAST P3 自比对只查 accession 子串，未解析 query/subject/identity/alignment coverage；CLINKER 对真实 GenBank 改扩展名作 scaffolding，非实际 Bakta→CLINKER 集成，HTML 大小与关键字仅是输出 smoke。保持这两种证据范围，不计完整 comparative 生物学正确性。

env.sh 与 test-only config 已阅读：机器特定 runtime 路径只在目录存在时加入，NFT_BIN 不证明 launcher 存在；部分 test-only publish/容器覆盖不是 production 配置验证。未启动外部工具/镜像下载或 nf-test。上述文件均仅 investigating。

## 剩余来源首轮审阅与 linking 证据

本批读完此前剩余12份来源（coabundance/sequence/longread_source harness；ena/nextflow config；link_longread/metabat2/recycler/scapp_detect real harness；三份 linking Python 测试）。63份来源均进入 investigating，仍不等于63份审计通过；固定当前文件 SHA256 于 results/tool-audit/20261020-linking-review/test-source-receipt.json。

原 coabundance suite 在实际 Nextflow 26.10.0 和原生 R 下通过，保存 out/trace/.command.sh 于 /tmp/autoplasm-module-regression-agkcslcs；日志 results/tool-audit/20261020-linking-review/coabundance.log。它将输入顺序 A__B.v1/S.2/S.1 与30/20/10配对，检查合并覆盖度字典与相关系数1，比只检 sample ID 集合更强。不能据此排除跨独立组装 feature 实体不一致（TA-010），也未运行 MetaPhlAn。

coabundance 单元检查多列布局、species/strain去重、少于3共同样本、空 profile、无效数值和重复记录等；已存在局部拒绝断言。尚缺独立非平凡相关/BH 多比较数值真值。sequence 单元对无MAG/空/重复host ID/gzip/长度阈值有明确断言；同序列周期 ACGT 的 score=1 正例仅证明此构造，不足以验证 TETRA 对真实宿主的科学准确性或多样序列数值实现。

longread 单元的 reference LN=4/FASTA4bp，但记录 POS=1、CIGAR=100M、100bp SEQ；这是超出参考末端的简化 fixture。它检查 flags、唯一read计数、阈值与坏字段，不是生物学有效的分段比对，不得计入真实BAM正确性；尚缺相对 query 区间、参考边界与真实主/补充关系对照。此限制补入现有 TT-002，不把专门 parser toy fixture 本身等同生产缺陷。real longread harness 用前5个真实 assembly contig 作“plasmid”集合，明确是执行输入选择，非已知质粒/宿主真值。

real Recycler harness 的独立 assembly BAM 与本次 SPAdes graph 不同（TA-002），并且生成 .bai 却未在 process output 中传递（TA-003）；执行历史不能解决契约差异。SCAPP detect/bin harness 都是单样本 combine，当前不会证明多样本 keyed pairing。METABAT2 harness 使用固定真实 gzip assembly/BAM/BAI，能覆盖节点格式但未覆盖 production final-bin 路由。ENA 降低 QUAST min-contig 是测试专用覆盖，不能当成默认生产参数执行证明。

TETRA 独立非周期序列对照复现 TA-039：0.9589 vs 固定pyani0.4315，默认0.7阈值两侧；原同周期score1无法检出。MAG跨record人工kmer问题TA-040也未被同序列单record测试覆盖。方法真值与生物学真值区别见 contracts/tetra-method.md。

补测longread SAM长度/参考边界一致的disjoint/overlap/低MAPQ三组；原script未验证query区间，overlap作为刻意标记矛盾的鲁棒性探针，不报真实aligner已失败。共丰度3假设Pearson与BH独立SciPy对照通过，包含过滤掉的低相关假设；见host-linking contract。

入口P0遗漏未知工具名（TA-041），已有trace.succeeded为空不能单独证明未提交任何analysis任务；局部validator四场景实际NXF结果见entry-validation contract，非完整P0/nf-test运行。

共识新增原CLI反例：TA-042非法权重文本静默fallback，TA-043合法sample ID中的工具名误识别producer并翻转最终调用。现有token/ensemble测试未覆盖；不变性应比较重命名前后call与FASTA内容。见consensus-boundaries contract。

TA-044共识重复FASTA/同工具冲突预测原CLI复现：表/FASTA记录数和长度不一致、交换行序翻转调用；现有共识测试未覆盖。catalog已有独立重复ID拒绝测试，不把局部有防护误述为整个链已防护。unknown summary ID人工反例补充TA-006引用完整性边界。

报告TA-045：S与S.plasmid_contigs.fasta两个合法样本被合并，且FASTA/structure来自不同样本；原报告smoke仅S1，遗漏suffix-containing ID不变性。catalog相关测试不能替代report测试。

HOTSPOT无当前真实P3；原awk CRLF/LF对照复现TA-046，缺失Species会成为host_id而非回退Genus。应增加跨行尾和各rank缺失的格式语义测试，不能只查links.tsv存在。PlasmidHostFinder历史环境阻塞不等于当前固定CLI验证。

多样性正常3样本2feature独立公式/SciPy全值对照通过；garbage和真0输出逐字相同、exit0复现TA-047，negative control exit1。现有smoke名称/行数断言不足以识别此输入损坏；不将正常对照外推单feature或跨组装实体正确性。

TA-048：DESeq numeric IDs001/1被类型推断合并，3+3输入变少复制数后空表exit0；同矩阵S前缀control120条。正式测试应覆盖纯数字ID不变性、matrix/metadata唯一性及全部样本计数，而不只检查结果文件存在。固定1.42源码依据已补齐，当前成功模型control仍是native1.52。

TA-048扩展至diversity/network/internal differential：6→5样本、重复元数据行当重复、原p值改变；另有字面NA丢失与数字10-60位置索引失败。此前sample-ids suite只验证入口语法，不能覆盖各R消费者身份不变性。

网络门控补证：原preparation后0feature×20sample仍进入原FASTSPAR process；实际NXF局部harness+明确CLI observer，归TA-038，不计真实FastSpar成功。正式网络断言应核对预处理后维度和eligibility，而非只看原表行数。

CheckM2固定1.1.0原输入分派代码单gzip/混合列表两组通过，模型被观察器替换，仅证明文件准备。生产DAS Tool emit是*.fa文件列表，未将目录默认extension规则错误归因给该路径；真实质量/DB认证仍缺。

原main实际P0三情景（duplicate/invalid/missing-read2）按预期拒绝，trace0任务且.command.sh0；证据在20261020-main-p0，不是nf-test/JUnit完整套件。首轮配置组合错误提前缺DB失败已保留并剔出通过计数；修正只改变audit runner的include顺序。

当前validation.nf.test实际有11个执行场景（5显式+6表驱动，词法test调用数不是用例数）。原main对应11/11诊断在stderr、exit1、trace/command0；映射p0-main-cases.tsv。nf-test框架/插件本身未运行，且这些case不覆盖TA-007/041缺口。

TA-049 SemiBin输出必需glob在合法no-bin场景失败；原模块stub总生成四bins，不能证明no-bin兼容。实际NXF synthetic writer正/空两场景已对照，均taskexit0而workflow分别0/1；真实模型回归尚缺。

TT-007：IntegronFinder --gbk stub把文件名当命令执行，原NXF任务exit127；默认stub对照0。vendored testcase无此选项，且当前p1-suites四套不含该module，故未泛化为既有P1全部失败或真实分析失败。

TT-008已实际证实：sequence-optional负向duplicate case workflowexit0、两个同名S1任务完成，但测试因work-duplicate-keys路径含keyword判通过。直接独立重复该case确认exit0；普通sequence/default/缺MAG/缺taxonomy/空plasmid routing局部对照通过。修复需要非零状态和精确诊断，不是改路径或刷新快照。

## expect_success=False调用点复核

共5处：sequence-optional重复键1处、CRISPR guard4处；run_nf关闭subprocess check但未断言失败是共享弱点。TT-008的重复键已真实假通过，其余CRISPR情形本次未观察到相同假通过，不能把“断言不足”说成“当前所有负向场景错误”。详见negative-oracles.tsv。

原CRISPR suite由不改结果的observer记录5次run_nf：subworkflow开启exit1/无任务/正确诊断；关闭exit0/无任务；direct module workflowexit1，LINK_CRISPR task FAILED/exit2（本身仅echo未实现后退出，没有生信分析）；main开启exit1/无任务/正确诊断；main关闭exit1/无任务但报非法platform。最后一个只证明没触发CRISPR guard，不证明合法平台/输入下其他分支可成功运行，runner总结“leaves other branches available”不能扩写成完整成功基线。

原suite代码/生产未修改。首次audit observer误取位置参数导致TypeError已保留initial-observer文件，修正索引后5项观察完成；该错误是审计探针错误，不新增生产/测试缺陷。真实日志/trace和run.json在results/tool-audit/20261020-crispr-oracles/，工件/tmp/autoplasm-module-regression-ozj_x848。

QUAST补真实P3局部证据：锁定pUTI89 gzip核对size/gitblob，原module/plain+gzip实际QUAST5.3.0均通过，独立计数/长度/N50/GC一致。不是stub/synthetic，但仅基础统计、未reference alignment或平台E2E。见quast-real contract/native-real-nodes.tsv。

TT-009确认MultiQC native测试环境锁1.33，模块声明1.35，runner只查程序存在。真实QUAST报告汇总在1.33通过且数值保持；该兼容性不能认证1.35。正式测试应记录并约束目标版本，不能只检查Nextflow版本。

真实QUAST reference首轮exit0但Minimap2编译失败、无比对指标；已修复本地ccache编译权限并以新work重跑，自比100%/0错组装/0错配/0indel/NGA114230全部通过。初始降级不能凭成功状态计参考分析通过；也不应影响本来未请求reference的basic路径结论。

TA-043进入修复：新增2个真实CLI测试方法，4producer sample-token不变性与CSV/gzip/raw cycles兼容；旧实现先复现3个subcase失败，补丁后共识11/11。原NFX wrapper2样本调用/序列不变性也通过。未刷新快照或放宽原断言。

TA-045新增test_generate_report.py 3项（旧版2失败、修复后3/3），原REPORT与真实Rmd模板独立样本行验证通过；test来源清单增至64。计数和工具不同的fixture可捕获混合来源，零调用保留完整ID；其他报告问题仍未关闭。

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

### 2026-10-22 长读段宿主输入与替身真值

TT-006固定：旧samtools替身无视显式 -0 并把未配对reads送stdout；3个针对输出分类/空配对文件/未建模配对拒绝的方法在旧源全红、新源全绿。平台fixture现在两样本不同宿主参考、四旁路，真实长读宿主工具三步覆盖。精确QNAME/DNA/quality与预先指定参考来源比较；全被去宿主是明确QC失败，不能以空组装或丢样本算过。

TT-010新增并固定：真实hybrid测试揭露Bowtie2 double的--un-conc-gz命名错误，生产模块optional fastq无输出，最终统一目录正确报样本缺失。修正末扩展名前插入、%替换及无扩展名三种命名；固定2.5.4原生工具3场景/4CLI调用及旧替身3红、新3绿。宿主profile原clean文件名断言不适用host过滤后输入，改为实际暂存短读逐记录来源；测试不会因重命名而误判，也不再仅凭名称确认输入类型。

最终native-host8场景53trace，P2 ONT/HiFi/hybrid(OPERA)+无参考共640trace（前3共18真实长读宿主工具任务，其余CLI observer/实际R/Python）。最终validator只读取保留work/output，不重跑任务，之前失败validation记录保留。native共享55任务另验。HybridSPAdes额外失败因observer缺SPAdes计划解析运行时，不能纳入通过。新runner逐场景保存进度时只有8场景齐全才pass，避免中断的部分记录误算全绿。TT-001等未决测试问题仍以findings为准；无完整框架/JUnit/镜像/科学性能认证。

### 2026-10-24 正在实施的辅助输入及图节点测试修订

显式 helper 输入会改变 process ABI；11份nf-test的25个文件表达式已迁移。五个历史模块对照入口通过共用 materializer 保留原ABI并固定私有生成脚本的辅助路径；不能将错误“参数个数/找不到helper”当作旧生信缺陷复现成功。当前真实 gplas nf-test一例通过，更多调用源与历史对照仍需纳入批次验收。独立 gplas 检查器增加原始图与规范化图的完整 DNA/节点域/边核对，避免直接按原始DP-first标签拼原生KC-first标题而误判。图身份的首次重复诊断断言文字不匹配按失败保留，修订为实际精确诊断后三个原生工作流拒绝对照通过。

mock hybridspades 旧伪FASTG不具真实SPAdes执行计划，实际来源检查拒绝；此端到端observer现明确不提供图，完整真实图分支另有证据。不得用这种mock认证SPAdes图来源或Recycler/gplas。首次Nextflow包装器双-log启动失败保留，后续用nf-test兼容启动入口重跑通过。

### 2026-10-25 PlasMAAG完整cohort与当前测试语义

新生产cohort及 SPAdes三件套已接线，实际 nf-test0.9.5完整双样本一例通过，并用独立原始组装逐条验证最终成员、DNA、分数、长度门槛和恢复meta；不是空结果或只看退出码。核心环境由当前声明的固定Git源码新建，嵌套环境复用/本机pin的限制明确单列。另一contigs模式原生任务及独立样本导出检查通过，输入原为SPAdes，仅认证MEGAHIT兼容FASTA接口。test-only VAMB与splits16不改变生产默认。

两个 harness 的 Map.get(key,default) 实际会修改 ConfigMap，造成并发共享记录失败；现复制普通Map并使用getOrDefault。首次实际框架失败保留。下一次64GB资源请求超本机限制也保留；8CPU/6GB选择器才通过。新增有效cohort的不足8CPU拒绝检查，确认原生Node2Vec固定8workers不会被低CPU声明掩盖。

gplas当前图身份重放揭示此前断言误指定right：两个输入都有重复，Nextflow可能先报left。首次失败保存；当前正则仅接受明确left/right重复诊断且key=A.1，另要求无原生GPLAS2分箱任务和无最终bins，三种拒绝重跑通过。没有把非确定性到达顺序当生产缺陷，也未删关键拒绝断言。

当前main的既有75个独立拒绝场景重放全部通过，当前台账更新指向这次运行与main SHA；不增加用例分母。新增PlasMAAG/gplas入口对照另列，不混作完整P4。新的远程依赖锁和私有兼容YAML正在单独重放，旧通过记录不自动认证新守卫。

当前部署补验更新：v4保留在线依赖失败；v5实际完整nf-test成功，使用同一精确远程URL/SHA锁从已核验原始归档离线新建geNomad环境，原始strobe/node2vec复用，无YAML回退。163包及6模型核对，独立最终85质粒bins/90成员和两个原meta通过；不是网络可用性或全部环境冷部署证明。当前守卫的默认无splits help、校验私有源码后恢复、等长保留mtime的私有依赖篡改拒绝3场景也通过。来源捕获/独立副本保持，最终批次未接受。

TT005补充primary GitHub探查提醒：modules.json不同消费者的revision不同。HiFi下载helper在常见6d467...返回404，在实际9cc9ac...存在；两次证据保留，未安装/未认证，不将错误revision选择变成上游永久不可用结论。

### 2026-10-25 TT005测试前置恢复完成，等待统一源码链接受

10suite的14处setup script引用已指向固定来源测试helper，24个main/env/meta文件Gitblob/SHA与各consumer revision一致，原MIT许可保留；无生产模块版本、断言、快照或fixture修改。99个literal引用现在0missing，独立source/revision/许可检查通过。实际nf-test dry discovery33个case定义当前缺失警告14→0，但没有执行case/命令；dryRun打印PASSED不能进入已执行分母。

真实四个归档helper保留完整原FASTA字节和meta，CRC损坏的gzip由真正1.13报错、唯一任务FAILED且不发成功输出；精确版本、实际任务集合、原文件不变断言重放通过。新14包工具环境与各原始归档hash及上游声明版本匹配，pigz2.8既有prefix复用。其余完整P1/模型/数据库/镜像均未认证；原HiFi下载master数据库须另锁。41源patch的before来自上一明确未接受681源工作状态，反向check及before内容验证通过，当前ready而非伪造最终接受；见contracts/vendored-prerequisites.md。


2026-10-25：TT-013 原始实验类型复核发现 PRJNA848809 为16S PCR数据，ENA结构化WGS字段与其设计/论文冲突。旧套件保留参数和全部断言，改为legacy-16s-execution，不认证shotgun P4；十二MD5与官方表一致。QUAST短contig不再解释为低生物量；TT-003必须用适用的真实非空shotgun数据补验。来源与边界见 contracts/ena-assay-scope.md。TA-089另完成已接受CONCOCT八阶段原生缓存反例、当前18process/36call/23snippet词法检查、完整PlasX原生两阶段和独立打分、PLASMe真实Transformer/DNA；词法/原生/独立公式分开记账，统一接受仍未完成。


TT-002现ready：实际原生nf-test0.9.5三套5例/12任务通过，覆盖MetaBAT默认合法空结果/固定上游参数非空DNA与完整分区，长读长独立SAM计数与预构造2读段阳性，当前Recycler原P3。6项R单元修合法参考长度；12实际产物副本对照通过。TT-014新增并ready：旧测试脚手架掩盖真实mapper最终退出29，pipefail后拒绝且R不运行。两次长读长启动配置失败和Recycler64GB资源拒绝保留，不计工具/框架通过。MetaBAT内部簇号与文件编号不同由固定源码证明，比较完整分区而非删成员断言。生产科学方法不变；合成fixture/宽松设置不是生物学真值。完整记录见 contracts/p3-semantic-oracles.md。
