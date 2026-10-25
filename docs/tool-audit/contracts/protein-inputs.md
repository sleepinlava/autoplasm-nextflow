# Prodigal → MacSyFinder / eggNOG 蛋白输入契约

2026-10-23。TA-026/027的蛋白输入修复及新发现TA-077/078按下述局部范围验证；完整模块、镜像、平台、全量数据库和科学准确率不因此通过。

## 固定来源

MacSyFinder 2.1.6 [固定输入文档](https://github.com/gem-pasteur/macsyfinder/blob/9caf84252b9cc89b9ef93173df250e764172b330/doc/source/user_guide/input.rst)要求蛋白；ordered_replicon表示一个复制子，多复制子使用gembase，蛋白ID为`复制子名_基因名`且按基因组位置连续排列。实际环境是MacSyFinder2.1.6、MacSyLib1.0.4、HMMER3.4、Prodigal2.6.3、pigz2.6、Python3.12.15。MacSyLib1.0.4 [数据库实现](https://github.com/gem-pasteur/macsylib/tree/1.0.4/src/macsylib)按最后一个下划线分组，拓扑文件按`复制子: circular`读取，**不是TSV**；原生运行已核实。

[CONJScan2.1.0](https://github.com/macsy-models/CONJScan/tree/898f8a1a3d9076855eb8f32be9f32d4e1b375c1f)共162个Git blob逐一验证。项目既有测试下载清单已经声明此release，本批锁定该版本及Plasmids子模型；不改profile/阈值。原来的`CONJ`包/模型名称不能找到这些定义，正确选择是`CONJScan/Plasmids all`，下载要求为`CONJScan==2.1.0`。该版本含官方MOBH阈值和MOBM模型变化，不能拿它与别的模型release直接比较；没有可认证的旧`CONJ`分析结果。两别名CONJSCAN/MACSYFINDER使用同一程序和模型，不是两份独立证据。

eggNOG-mapper2.1.13 [固定入口](https://github.com/eggnogdb/eggnog-mapper/blob/a82fac7f5534ee97fa0385718b0012c266fcf3e7/emapper.py)默认protein模式。实际声明构建`pyhdfd78af_2`要求Python<3.12，本批使用Python3.11.9、DIAMOND2.0.15、BioPython1.88；没有据失败的3.12解析判定软件不可安装。官方完整小型integration fixture数据库和配套DNA/蛋白/预期注释来自同一固定commit，228个blob（含3个安全目录内symlink）全部核对，190,298,604字节；这不是生产完整eggNOG库。

两套Conda环境分别79和70包的归档SHA256/MD5全部核对，包含重复依赖，不能相加称149个唯一包。安装后MacSyFinder9、MacSyLib27、eggnogmapper56个Python源码均与相应固定Git blob完全一致。CONJScan原生安装器会重写metadata并添加release版本：其余161文件hash及metadata剩余YAML字段分别核对，未改写共享Conda包。完整环境/来源证明在`results/tool-audit/20261023-protein-inputs/runtime-proof.json`，可携带锁在`tests/protein-input-native.lock.json`。

## 生产者、边界与拓扑

需要任一蛋白消费者或显式选择Prodigal注释时，原有Prodigal2.6.3 `-p meta`仅调用一次。保留其GFF、CDS、蛋白、partial及每条序列选择的翻译表；不强制统一genetic code、不重新预测或翻译。只选择Prodigal时仍走原注释路径，无额外适配任务。

新PROTEIN_INPUTS以严格重复/缺失键检查连接同一样本的DNA、GFF、AA、CDS。适配器先验证所有记录再写输出：唯一原contig ID、GFF序列元数据及长度、gene ID、坐标/链/属性、CDS与原DNA切片/反向互补一致、蛋白长度与CDS一致且无内部stop；蛋白按原contig顺序及起点排序，同一复制子连续分组。保留原蛋白ID、header、序列及终止符；输出plain蛋白、gene_map、拓扑文件和来源hash/state manifest。生产适配器不重新实现翻译；独立测试另用BioPython核对每条AA。

用户明确决定“未知按线性；仅明确闭环的序列按环状”。仅完整header token `topology=circular`/`circular=true`授予环状；`topology=linear`/`circular=false`/`not_circular`为线性，正负冲突失败；未标注保持`unknown_treated_as_linear`，不从终端重复或名字后缀猜测闭环。拓扑文件只列有蛋白的明确环状复制子，其他由`--replicon-topology linear`处理。显式环状ID若含冒号或以#起头，无法无损写入该版本拓扑语法，明确拒绝。gembase的最后下划线分隔允许contig本身含下划线。

零蛋白样本仍输出完整manifest和`no_predicted_proteins`状态，跳过蛋白工具；所有样本均无蛋白时也不下载模型。不把未评估当成阴性。工具关闭与空输入不生成分析任务。MacSyFinder tuple新增显式topology path，保持其与样本/蛋白同一tuple；原vendored三份nf-test输入已适配空topology，但未运行该套上游测试，不提升框架认证。

MacSyFinder命令增加pipefail。原包装器在真实ValueError后，tee和日志移动仍可成功，日志又满足宽泛results输出，因此任务错误地COMPLETED；当前同一坏拓扑输入明确FAILED。此为TA-077，独立于蛋白类型修复。模型名称/版本为TA-078，单独补丁记录。既有MacSyFinder发布glob保留`<sample>.<alias>/`目录；本批撤回了不必要的额外样本目录改动，未将其误报为覆盖缺陷。新适配器的固定文件名另按样本目录发布。

## 验证及限定

9个独立单元方法覆盖DNA/坐标/链/ID/排序、gzip、大小写、冲突拓扑、缺失/重复记录、错误CDS、零蛋白及只含ACG字母的合法短蛋白；不以字母猜测蛋白类型。原下游实际原生运行6种输入/选择场景及1次指定运行名的恢复检查，共32trace：19COMPLETED、13CACHED。三个受控样本分别含真实pUTI89+官方ychF DNA、同一ychF DNA、后者30bp短片段；这是接口构造，副本/片段/改变header不计独立生物重复。三个样本Prodigal各调用一次，适配后132/1/0蛋白分别归属；所有有蛋白记录逐条独立翻译、坐标及元数据核对。pUTI89的实际F型接合系统、ychF实际功能注释、单ychF无MacSy系统、零蛋白、eggNOG单开、原Prodigal单开、全关闭、空输入及恢复均通过。

模型获取在该回归中由明确记录的transport adapter把生产`CONJScan==2.1.0`替换为已验证同版本归档，再执行**未改写的原生msf_data安装器**；不伪造任何模型/基因/检出/注释。生产在线获取未认证，不能称完整联网部署通过。全部分类和注释为真实工具；eggNOG只使用官方小库，不能外推全量注释性能。

错误对照另2个Nextflow trace：旧wrapper伪成功1、修复后预期失败1。直接CLI确认旧DNA超过HMMER100K蛋白长度上限，旧`CONJ`定义被拒，eggNOG旧DNA触发DIAMOND明确蛋白类型错误。MacSyLib的HMMER错误处理会kill整个进程组；首次直接调用导致审计进程退出137，保留原始诊断，随后用独立进程组重放并正常保存错误退出码，不宣称空结果。连同下游共34trace=20完成（含1旧错误反例）、13缓存、1预期失败；不是34份生物学样本或成功模型。

原生eggNOG官方两蛋白阳性的query、seed ortholog及全部功能注释字段与固定上游预期一致；不同DIAMOND下的E-value/bit score原样保留，不认证数值相同。最初拓扑TSV尝试、错用另一genepred fixture小库、错误发布路径oracle、并行时无指定目标的resume及重复log参数等失败/被替代尝试全部留存，不能算正式通过或增加独立分母。指定resume运行名后13项均确实缓存。

12个既有profile按当前配置重放，确认gembase、默认线性、适配器selector及原GTDB标准参数；0分析任务，不新增场景分母。固定基线、3份依赖补丁、当前来源hash、失败与正式运行索引见该批receipt。完整M0–M4、TT剩余测试审查、TETRA未通过的科学阈值、GTDB完整分类及AWS实际验证仍未完成。
