# 丰度与跨样本统计契约审查

2026-10-20，基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。本轮不修改科学方法。

生产链：每样本 plasmid FASTA → 该样本 reads 比对 → CoverM mean/tpm/rpkm → MERGE_ABUNDANCE → DESeq2/network。contig coverage 也是每样本独立 assembly 比对 → merge → diversity/internal differential。COMPARATIVE 单独构建带 sample|id 的 catalog，但 catalog cluster/representative 没有回接统计计数。丰度合并正确传递显式 sample IDs、拒绝重复 sample/feature；这些局部保护不构成跨样本 feature identity。

TA-010：以本地 contig 名作跨样本实体，独立组装不保证同名同序列，亦不保证同序列同名。results/tool-audit/20261020-abundance 保存人工两样本 FASTA（同 NODE ID，不同序列）、CoverM 格式输入、完整命令和结果。merge 后合成一个 feature；diversity TSS beta 距离为 0。独立参考是两个不同 feature 的比例向量 (1,0)、(0,1)，Bray-Curtis = (1+1)/(1+1)=1。修复需要统一参考和全样本重新量化，属于科学结果兼容性变更，不能靠给行加样本名前缀就宣称解决。

TA-011：即使 CoverM 输入有 Count 列，merge 也不解析，raw_count 永远空。read.delim 将其转 NA，而 nzchar(NA) 返回 TRUE；脚本因此误选 raw_count，NA 转零。results/tool-audit/20261020-deseq：6 样本、两组各 3 重复、4 feature、coverage 均 >=20、raw_count 空，退出 1，DESeqDataSetFromMatrix 报所有计数均为零。运行环境为 native DESeq2 1.52.0，非声明容器 1.42.0；R 空值判断与本地代码的数据流已直接证实，部署版本复验仍待做。

TA-012：缺少 raw_count 列时的 coverage rounding 也不是合格计数来源。[Bioconductor 官方 vignette](https://www.bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html) Input data 要求未归一化 read/fragment counts 或 estimated counts。另核对了本机包版本 1.52.0 的同节；固定声明 1.42.0 源码仍需取证。真实计数来源、pair/fragment 单位、多重比对、统一 feature 长度/索引和分母均须定义；不要只修 NA 判断后继续把 coverage 当 count。

TA-013：输入样本 C 在 metadata 存在、但没有 abundance 表时，diversity 静默只报告 A/B。生产流程明确过滤无质粒样本，但没有随结果携带 expected sample IDs 和零检出状态；这会与意外丢样混淆。应保留生物学零值与意外无结果的区别，不能一律补零或一律丢弃。

TA-014：同一人工单 feature 输入，Shannon/Simpson 为 NA。独立计算一个阳性 feature 的比例为 1，故 -1*log(1)=0、1-1^2=0。native vegan 2.7.6 对一列矩阵的返回形状不符合脚本的按样本名索引假设；声明环境版本未锁定，需覆盖其版本。

上述均非真实生信工具或科学性能验证。空表历史通过不能覆盖这些非空输入。DESeq2/native 版本差异已显式保留，未将 native 复现计为部署真实节点通过。

## 多样性独立真值与非法数字边界

2026-10-20：TA-047，diversity将as.numeric转换warning抑制，再把is.na值置0。3样本/2共同feature人工输入S1=[1,3]、S2=[2,2]、S3=[4,0]，原native R的richness/Shannon/Simpson/Pielou与独立Python数学公式一致，beta与SciPy Bray–Curtis在六位输出精度内一致。此fixture特意有两个feature，不能覆盖/消除既有单feature命名缺陷TA-014。

将S1第一项替换为garbage后原script仍exit0，stderr空，metrics/beta与该项真实0的control逐字一致；这把损坏字段变成有效无检出。merge_abundance对指标列采用character并未先验证，因此这一输入保护缺口不能假定被上游拦住。differential也有相同静态转换逻辑，但本次动态反例仅运行diversity，不泛称所有统计消费者都已复现。若明确允许NA缺失，应有区别于0的状态/排除规则，不应把garbage纳入该规则。

负数-1对照exit1，没有说负数也成功；部分alpha输出可能在beta阶段前产生，是否需原子输出另行评估。原脚本对all-zero NaN Bray转换0有明确历史兼容注释与warning，本批没有将既有有意兼容选择重复报新缺陷。

完整命令、退出码、输入、stderr和独立数值真值：results/tool-audit/20261020-diversity-validation/run.json及probe.py。人工shared-reference coverage，非真实分类/跨独立组装feature对齐认证。现有smoke核对richness及指标名，但没有非法数字拒绝与完整浮点真值；本次probe补证据，生产修复/正式回归仍未完成。

## DESeq2固定版本依据与数字ID

已通过GitHub提交历史定位 [17a39b5296cb3d897f1e2a9aa4bebbdefb13b46a](https://github.com/thelovelab/DESeq2/commit/17a39b5296cb3d897f1e2a9aa4bebbdefb13b46a)，DESCRIPTION确为Version1.42.0。固定AllClasses.R保留全零counts拒绝，固定vignette要求未标准化counts/estimated counts。提取行号/blob哈希在evidence/deseq2-1.42.0.json，补强TA-011/012对应版本静态依据；最初尝试RELEASE_3_18 ref返回404，随后实际commit成功，不把ref失败当仓库缺失。尚未执行1.42容器/包，也不将1.52数值结果伪称1.42结果。

TA-048：read.delim两表均未指定ID为character。当sample_id列全部像数字时，001和1都转换为integer1；counts xtabs合并两样本，metadata再按sample_id去重。人工120feature整数raw_count矩阵（无缺失、没有coverage fallback），6个合法ID001/1/2/3/4/5，group A前3/B后3：原CLIexit0，输出只有表头；因A变成2个样本触发min3 guard。在不改变数值与分组的情况下将ID加S前缀，原CLIexit0输出120结果。独立reader类型检查确认只有5个unique IDs。

这是样本身份错误，不是“低重复应空结果”规则本身有错。数字case在library(DESeq2)前退出，不依赖1.42/1.52模型差异；成功control用当前native1.52，因此仅证明本地端到端对照。真实样本ID模式允许以数字开头并含纯数字，不能通过收紧合法ID掩盖损失。feature ID也必须同样按string保留，当前本次未动态量化feature numeric collision，不把它算已复现。

全部脚本、输入、命令、退出码和stderr在 results/tool-audit/20261020-deseq-identities/run.json。原smoke自造S1等ID绕过该边界；merge/sample ID局部测试能保留复杂ID，不代表DESeq消费者仍保持字符串身份。生产未修改。

### TA-048影响范围扩展（不重复计数）

在相同120feature/6样本raw-count fixture上调用原diversity、differential、network_prepare，数字001/1/2/3/4/5与字母前缀对照共6次运行：diversity和network输出从6个样本变成5个（1/2/3/4/5），均exit0。network是已声明raw_count，因此不涉及coverage proxy。fread后元数据A有3行但只有2个不同ID；differential按元数据行拼s1且按list重复采样1两次，仍输出120个检验。p0的pvalue从改名前缀control0.677466变为0.214506，log2fc从-0.208814变-0.569696，不能用“结果行数相同”判通过。

另一个6样本rename仅将S001改为合法NA，原DESeq exit0空表；默认read.delim将NA作为missing，样本从xtabs中丢失，正例control此前120条。此时仅指定colClasses可能还不够，标识列必须同时有明确的na.strings策略。真实缺失与字面ID NA不可混淆。

数字sample IDs10/20/30/40/50/60不碰撞，但diversity将numeric samples用于mat列下标而非名字，原script因subscript out of bounds失败；不能只修leading-zero重复而不固定ID字符串。完整runs：results/tool-audit/20261020-r-id-consumers/run.json、literal-NA/run.json、numeric-position/run.json；实际R原脚本，非真实工具/科学基准。所有这些由tabular ID读取根因归TA-048，问题总数不变。

## 2026-10-20 TA-048 标识符适配修复验证

四个 R 消费者显式按字符读取样本/特征 ID，保留前导零及字面量 NA；数字组名001/1保持分离，非标识符缺失值策略不变。新增 tests/test_statistics_identity.py 共7项回归方法，修复前5项触发8个失败子场景、数字组名另触发2个失败子场景；最终7/7通过（53.586秒）。四个原 Nextflow 模块各执行两组对照，共8任务通过，样本重命名前后统计一致。DESeq2 特征重命名结果按预设数值容差比较。证据：results/tool-audit/20261020-statistics-identity-fix/receipt.json及nextflow/run.json。

TA-048关闭；TA-011/012/013/014/047及重复输入策略仍未闭环。原生DESeq2为1.52.0，不能替代声明1.42环境认证、FastSpar或完整跨样本/科学基准。历史受影响数据需重新生成下游统计；不改变模型、阈值或计数单位。

## 2026-10-20 TA-047 五入口数值边界补证

以同一120-feature/6-sample人工整数矩阵逐次只改变一个有效数值单元，对diversity、internal differential、network prepare、DESeq2及merge分别运行zero/text/NA/blank/Inf/negative，共30次原生CLI。每次保存输入、命令、stdout/stderr、输出hash。矩阵见numeric-input-matrix.tsv；完整证据results/tool-audit/20261020-numeric-input-matrix/run.json。

文本garbage在四个消费者都与真实0产生完全相同输出；diversity/internal differential/DESeq2的NA/blank也同0。network NA/blank会使用有效coverage，这是既有fallback，不能把它们误报为同0。network及DESeq2负raw_count同0；internal differential接受负coverage；merge把损坏/负/Inf coverage传下游。diversity Inf退出0，受影响样本所有beta距离被改0；network Inf退出0但对应count单元为空。其余Inf失败只说明下游拒绝，不能当作已建立统一入口校验。

当前merge单元测试主要核对ID、路径配对、重复键及空输入；新增identity回归也只针对重命名，不覆盖本数值契约。TA-047范围扩至五入口，保持planned/未决；具体校验边界及与TA-011/012的关系见contracts/numeric-input-policy.md。无科学模型/阈值/单位或生产代码变更，不新增通过计数。DESeq2原生1.52，不替代1.42认证；本次无Nextflow/P4。

## 2026-10-20 TA-047 数值校验修复完成

五个入口在输出/统计前校验实际使用的数值为有限非负值，缺列明确报错；无效单元给出来源/行/sample/feature/字段。merge保留合法coverage原字符串精度，网络保留缺raw_count时使用有效coverage策略；不再用0代替损坏文本、无穷、负数或缺少的有效测量。DESeq选中的缺raw_count现在提前失败，TA-011计数来源仍待解决；TA-012单位/rounding未修改。

新增6方法共35拒绝子场景通过；原5方法garbage基线5失败。原identity7/7、merge5/5通过。重跑30-case矩阵，五脚本合法zero输出与修复前逐字节一致；network原NA/blank fallback保持。原四模块8任务对照通过（早于最终network缺列guard）；最终7次原模块gate另核验当前五源码hash，包括五类坏输入任务明确失败且不发布TSV，以及network/merge正常输入成功。完整命令/输入/trace/.command及哈希在results/tool-audit/20261020-numeric-validation-fix/receipt.json。

TA-047关闭，增量patch以HEAD+TA-048为前态，已与原30-case源码hash核对。没有宣称完整CROSS_SAMPLE/P4、DESeq2声明1.42容器或科学基准通过；原生1.52。此前损坏数值不再被接受，应从已验证测量重新生成受影响统计。失败测试使用隔离新输出目录，不承诺清理旧结果目录。

## 2026-10-21 用户确认的跨样本修复方向

用户明确选择“统一参考目录并重映射（推荐）”：跨样本定量必须先建立共享核酸参考目录，再把所有样本读段重映射到同一目录。该选择允许改变原来各样本本地ID的统计特征定义和计算量；不以简单前缀改名或继续拼合各自参考表冒充修复。目录实体定义、映射/多重比对和计数单位、hybrid策略、空结果及独立真值仍需实现验证。TA-010/012尚未因这项方法选择而关闭；当前结构TA-036修复独立进行。

## 2026-10-21 用户授权的共享参考实现与验证

SHARED_QUANTIFICATION 新路径将所有组装序列组成一个竞争参考，以 uppercase 完整IUPAC DNA和反向互补字典序较小者的SHA256生成seq_特征ID。SQLite落盘去重，排序稳定，来源sample/contig/orientation和逐来源质粒判定保留。候选必须确实存在于同样本组装且DNA相同；参考质粒子集是至少一个来源被判为候选的序列并集。不同片段、近似序列及环状旋转起点不自动合并，目录不是质粒家族或完整分子身份。

四个reads平台向共享流程提供原始全部候选（包括空FASTA），预期样本数来自原始输入channel count；缺组装、候选样本、重复键/元数据错配和缺测量失败。共享参考建索引一次，对所有样本重映射；hybrid只选短读段进入跨样本，不混合长度不同的计数。共同过滤未比对/secondary/supplementary/未知MAPQ255和MAPQ<10。原始计数为CoverM count的primary read alignment，两mate分别计数，不叫fragment。mean/TPM/RPKM/count从同一过滤BAM产生，end exclusion=0；TPM/RPKM分母是这一共同参考上的可用比对，非全部原始测序reads。

初始MAPQ>=1曾被明确近似双参考反例击穿：Bowtie22.5.4将等价最佳配对报MAPQ1且AS=XS=0，任意分配后得到22/18 reads。新阈值>=10对照保留原始失败证据后复验，所有共享区域计数为0；该置信阈值不保证唯一生物学来源，会低估共享区域，不能用measured_zero宣称真实生物学缺失。固定官方手册Git blobs见evidence/shared-quantification-primary.json；实际CoverM0.7 count输出Read Count语义亦已核对。原生工具环境锁沿用Bowtie2/CoverM并新增minimap2-2.30/SAMtools1.23.1，Python3.12，R4.6.1/native包另记。

两份已锁定真实参考pUTI89/SCP1，明确模拟reads按源DNA唯一性预选坐标（不以mapper输出反推真值），A/B同NODE_1但DNA不同，C改名+RC且无自己的候选，D空组装但有明确未比对reads。原共享节点、CROSS_SAMPLE的diversity/internal低重复guard/REPORT和HOST_LINKING原coabundance消费者，三模式19+18+18任务核对全部样本×特征、BAM reference/QNAME/flags/MAPQ、40双端read/20longread的独立计数、mean、A/C相同而B不同的独立Bray-Curtis及控制hostprofile r=1。报告发布仍是TA-015开放问题。三边界另验：近似同源双参考歧义15任务、全局空目录2任务和少一个样本12任务正确拒绝且无最终表；不把这些人工/模拟数据当生物学丰度准确率。

DESeq2/network严格要求raw_count非负整数，删除coverage取整回退；merge独立入口可解析Count/Read Count并在存在时校验，缺Count的旧独立coverage用途可输出空字段，但计数消费者拒绝。保留数值/ID保护和统计模型/阈值；部署DESeq2 1.42完整模型正例/零例仍未执行，TA-011保持ready而非verified。TA-013生产路径已部分保护，但其他standalone metadata/drop/intersect及网络最终eligibility未全审，不提前关闭TA-013/038。

旧统计特征、回贴竞争与count单位均变化，应从reads在新目录重算，勿混合旧表。来源映射见10_abundance/shared_reference/catalogue/sources.tsv，量化状态/单位见tables/sample_states.tsv和method.json；coabundance使用全局seq_ IDs，其他局部证据仍保留原ID。MMseqs2比较目录与该全长DNA目录不同，不用于替代核酸计数。真实完整平台、FastSpar/DESeq部署模型、镜像和nf-test框架/科学性能仍待验收。
