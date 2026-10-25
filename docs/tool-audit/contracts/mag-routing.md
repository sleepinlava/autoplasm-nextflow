# MAG 结果路由审查

2026-10-20；基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。范围为本地接线；尚未声称第三方 CLI/算法正确。

MAG_HOST 输出 ch_final_bins 只来自 METABAT2.out.fasta，或启用 das_tool 时改成 DAS_TOOL.out.bins。CONCOCT.out.fasta 赋给 ch_concoct_bins，仅参与 DAS Tool；SemiBin 调用没有把 output_fasta 接入任何下游。实际 vendored SemiBin 的 output_fasta 在 modules/nf-core/semibin/singleeasybin/main.nf:26，生产流程没有引用。故单独选 concoct/semibin 不会形成最终 mag_bins，checkm2/gtdbtk 可启用但无输入。宿主 sequence linking 接收空 bins，可能输出无关联而掩盖上游路由丢失。记为 TA-008（静默丢弃分析结果 S0）。

启用 das_tool 但无 binner 也没有入口依赖验证。多 binner 最终使用何者/合并方式需明确，不能直接 mix 后制造相同 meta 的重复 join 键。SemiBin gzip bins 与 DAS Tool extension、CheckM2/GTDBTK 的格式兼容还需另行对应版本验证。

所需验收：逐一选 metabat2、concoct、semibin；分别与 checkm2/gtdbtk/sequence linking 组合；验证每样本 bins 的来源、数量、ID、序列与下游输入相符。组合模式需明确代表同一套最终 bins 的政策和去重键。当前无运行证据。

## 版本化文件契约追加

官方固定源码原始记录见 evidence/mag-upstream.json。

TA-030：[DAS Tool 1.1.7](https://github.com/cmks/DAS_Tool/blob/1.1.7/src/DAS_Tool.R) 的 FASTA bin 导出在 if(arguments$write_bins) 内。本地没有传 --write_bins，DAS_TOOL.out.bins 又是 optional 并被设为最终 bins；因此修好 TA-008 的单 binner 路由仍不能修复 DAS 聚合路径。上游 module real tests 显式传 --write_bins --write_bin_evals；stub 却总建 bins，不能作为此生产选项的依据。

TA-031：[GTDBTk 2.7.2 cli.py](https://github.com/Ecogenomics/GTDBTk/blob/2.7.2/gtdbtk/cli.py) default extension=fna，[main.py](https://github.com/Ecogenomics/GTDBTk/blob/2.7.2/gtdbtk/main.py) 以 endswith(extension) 筛选 genome_dir。METABAT2 输出 .fa.gz、DAS Tool 输出 .fa，而本地只传 --skip_ani_screen。results/tool-audit/20261020-mag-contract/gtdb-extension.json 运行固定 argparse helper 并投影该筛选谓词：默认选择零输入，显式 gz/fa 分别选择相应文件。未做 taxonomy/数据库运行；不能据此声称已有实际分类错误率。

TA-032：固定 CONCOCT 1.1.0 [cut_up_fasta.py](https://github.com/BinPro/CONCOCT/blob/1.1.0/scripts/cut_up_fasta.py) 与 [extract_fasta_bins.py](https://github.com/BinPro/CONCOCT/blob/1.1.0/scripts/extract_fasta_bins.py) 直接用 SeqIO.parse(filename, fasta)，不做 gzip 解压。本地两个包装器亦无解压，而 production assembly 是 .fa.gz；只用 plain upstream fixture 的测试无法覆盖该路径。当前为静态差异，真实节点复验仍缺。

其余边界：depth join/CONCOCT coverage tuple 在当前源码的字段顺序匹配；Fasta_to_Contig2Bin 本地补丁已对列表里的 gzip 解压后再用 extension=fa，不重复报其 gzip 输入问题。CheckM2 接受列表形态，不能把 GTDBTk 的目录扩展名约束套到它；但 CHECKM2DB 应是实际数据库文件，README 所指下载路径还需单独核验。MetaBAT2 optional 无 bins 与缺失输出应明确区分。

所有质量/分类与聚合路径仍需有独立正负 fixture，不能只统计进程成功数。

## CheckM2 1.1.0输入准备确认

2026-10-20：固定官方 [CheckM2 1.1.0 README](https://github.com/chklovski/CheckM2/blob/1.1.0/README.md) 明确支持单文件/文件列表以及gzip/plain混合列表，不要求列表输入声明extension。固定main.py（blob3eb2dbe654d1fcfe790c54ce77ce918562799bef）在一个目录参数时保留extension，而在文件列表分支把文件复制/解压成临时*.fna。

生产METABAT2 emit是bin FASTA path/list；DAS Tool emit也是*_DASTool_bins/*.fa的文件path/list，并非目录。因此没有证据说CheckM2会像GTDB-Tk那样因DAS .fa后缀漏选文件；先前这一候选已排除，不新增缺陷。CheckM2单gzip与混合gzip/plain两组原分派块探针（只将model Predictor换成文件观察器）都保留预期bin ID与全部序列，输出*.fna。源行号/哈希见evidence/checkm2-1.1.0.json；原分派块、fixture和run receipt在results/tool-audit/20261020-checkm2-contract/。初次提取块缩进不适合顶层exec，修正dedent后运行；这属于probe提取错误，不是upstream失败。

验证仅覆盖准备代码，没有运行CheckM2可执行程序、Prodigal、DIAMOND或质量模型，不能计真实P3通过。单文件、嵌套目录、空bin及database兼容/校验依然需真实节点；当前CHECKM2DB变量应指向.dmnd文件而不是目录，固定README与main help有此说明。采用env变量不经过显式--database_path路径的checksum验证，使用裁剪DB不能冒充完整DB质量认证。

原MAG_HOST仍有TA-008/030/031/032；当前文件列表契约局部正确不能消除最终bins路由/导出问题。SAMTOOLS_INDEX在mag_tools非空时运行，即使只选质量工具且无binner也可能无有效final bins，此依赖矩阵仍属TA-007能力校验范围。

## TA-049：SemiBin无bin合法结果

固定[SemiBin v2.4.1 utils.write_bins](https://github.com/BigDataBiology/SemiBin/blob/v2.4.1/SemiBin/utils.py)只对whole_bin_bp>=minfasta写FASTA，默认200000bp；候选都不足阈值或label=-1可返回空bins信息表且不写FASTA。固定cluster.py将信息表继续写出。main.py默认compression=gz，与本地glob后缀相符，因此没有把默认压缩格式误报为缺陷。源/blob/行号见evidence/semibin-2.4.1-empty-bins.json。

本地output_fasta的prefix/output_bins/*.fa.gz没有optional:true；stub却每次生成四个bins。实际Nextflow26.10原module使用明确synthetic SemiBin2 writer：正例写csv/tsv和1个gzip FASTA，workflow exit0；无bin例写csv/tsv和空output_bins，writer task.exitcode0但workflow exit1，诊断Missing output file。全部脚本/trace/.command.sh/exit文件保留results/tool-audit/20261020-semibin-empty/。版本eval用了显式观察器，无真实SemiBin/torch训练；BAM是明确假输入，不计P3或生物学结果。

此项与TA-008不同：即使final-bin路由修好，当前module仍会把合法no-bin当失败。需要明确no-bin状态并保留表/日志，不能单靠删除glob掩盖命令失败，亦不能伪造空bin文件。真实工具的无bin与阳性用例、下游CheckM2/GTDB/linking跳过语义仍待验证。首次获取single_easy_bin.py路径404后已从main.py定位实际single_easy_binning函数，不声称上游缺少实现。

## 2026-10-21：最终 bins 政策与修复范围

用户明确选择“必须同时选择 DAS Tool 汇总；单分箱器直接进入下游”。入口和直接 MAG_HOST 调用都检查：多分箱器必须显式选择 das_tool；DAS Tool、CheckM2、GTDB-Tk 没有分箱器时拒绝。单个 MetaBAT2/CONCOCT/SemiBin 的输出进入最终通道；显式选择 DAS Tool 时，三个分箱器各自转表，按样本分组汇总，生产配置要求 --write_bins。BAM/coverage/assembly 必需连接检查重复键和不匹配，SemiBin 单开不再调用未使用的 BAM 索引。

MetaBAT2 optional 无 bins 的受控情形保留其他分箱器可用预测；全无最终 bins 的样本不给质量/分类制造空 FASTA，宿主关联按既有缺省语义产出空表。SemiBin 自身合法无 bins 仍受 TA-049 影响，本批不借修改 observer 隐藏它。TA-031 的真实 GTDB 扩展名筛选和 TA-032 的 CONCOCT gzip 输入也没有由接线修复消除。

原流程 CONCOCT/SemiBin 单开可以成功但无最终 bins；真实 DAS1.1.7 官方 gut 样本前态也成功且有15个成员集合，却无 FASTA。新接线用显式 CLI observer 检查每样本ID/分组、全部可用预测、数量和DNA，并用真实 R 宿主关联检查实际暂存与输出；CheckM2/GTDB observer 只认证接线/暂存，不认证质量模型/真实文件筛选。真实 DAS 使用完整33.45MB官方 assembly、4组预测与固定上游成员/汇总表验证导出，数据与预期结果均有 Git blob/SHA256 锁。真实版本源与primary逐字节一致，原生环境141包显式锁另存。最终是否 verified 以当前findings、receipt和原始run记录为准，不以本文描述代替运行证据。

新增 TA-054：DAS Tool module 的可选自定义数据库拼成 --db_directory，而固定1.1.7 docopt 定义 --dbDirectory。实际原生命令在前者 CLI 解析阶段报错，改成官方拼写可以进入刻意缺失输入表的检查；这只证明选项错误，不证明自定义DB有效。当前 MAG_HOST 传 [] 使用内置DB，默认路径不受此项影响。保留未决，之后必须用完整自定义DB进行原module阳性/阴性运行。

### 最终验收补充

TA-008/030仅局部fixed/verified，正式receipt见results/tool-audit/20261021-mag-final-bins/receipt.json。真实DAS无达标bin并非成功空输出：固定cherry_pick在分数不足时明确write.log(type=stop)，原生低分bin/测试阈值0.9确实退出1。初始错误exit0断言保留失败，已按固定源码修正为失败传播、正确诊断、无部分发布，并原生复跑；没有修改生产失败语义。只有上游成功且optional bin输出缺省的情形，才按既有无bins通道语义跳过消费者。

实际生产参数最终阳性导出15个固定预期bin，成员/长度/DNA逐一一致；observer路由13场景201任务/native R关联通过。45个main独立拒绝场景与8个直接include guard正确0任务；重放不增分母。TA-031/032/049/054及完整MAG平台模型仍未决，不能据局部修复认证完整分析链。

## 2026-10-21 CONCOCT后续实际验证

TA-032及新TA-055/056现局部fixed/verified：压缩输入、默认重叠BED坐标步长和成功空提取已通过实际固定1.1.0验证。17叶场景、原MAG两样本12真实节点、14受影响路由场景217任务，边界与失败证据见contracts/concoct-io.md及results/tool-audit/20261021-concoct-gzip/receipt.json。路由的core/model observers与真实CONCOCT分支分开；无独立生物学分箱准确率结论。仍未决TA-031/049/054及完整MAG/平台模型问题；前文原状态作为对应日期历史记录保留。

## 2026-10-21 DAS可选DB后续验收

TA-054现局部fixed/verified，完整契约和边界见contracts/dastool-database.md。8原生任务对完整DB正例、默认分支、预检错误及实际读入负例通过，32任务MAG/R回归保留[]默认分支；没有修改生产MAG选择政策或默认评分。TA-031/049仍未决，整体MAG/完整平台模型尚未认证，前文各日期状态作为历史保留。
