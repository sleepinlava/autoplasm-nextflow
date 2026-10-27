# PlasX 完整逐样本注释：本批有界验证

用户选择的完整逐样本自动注释已由原生两阶段、完整资源、真实nf-test及351+63包dependency-only Conda验证。TA-025/087/088按本契约的有界范围验收；最终结论和来源补丁链见results/tool-audit/20261024-plasx-native/receipt.json，不代表全量审计、科学准确率、OCI、完整真实平台或AWS通过。上一批Platon264项清单是历史基线。

## 固定方法与来源

- [PlasX 5c9acfd00a597da27ef5261acf72dbaf2117b645](https://github.com/michaelkyu/PlasX/tree/5c9acfd00a597da27ef5261acf72dbaf2117b645)：22 个 Git blob 已逐项核验。其 setup.py 没有启用版本字段，不能称为 Bioconda 的 plasx0.2。
- [anvi’o 7.1，258991a5bc0f483c958040a55d339e1f447429ac](https://github.com/merenlab/anvio/tree/258991a5bc0f483c958040a55d339e1f447429ac)：1,244 个 Git blob 已逐项核验，包括安全解析的仓库内部符号链接。运行包装另核验 bin/ 与 anvio/ 下 1,185 个来源项目的聚合摘要，排除字节码缓存。
- 使用完整 COG2014、Pfam32.0 和 [Zenodo 5819401](https://zenodo.org/records/5819401) 的官方完整 de novo profiles 与系数。COG20、新版 Pfam、仅 COG/Pfam 注释都不符合所选方法。
- MMseqs2 10.6d92c；完整搜索全部十组 identity：90、80、70、60、50、40、30、25、20、5。splits32 仅分割搜索资源，不删除家族或修改筛选阈值。COG 使用 DIAMOND2.0.14，Pfam 使用 HMMER3.3.2，Prodigal2.6.3。

原始下载、官方可用 MD5、逐文件 SHA256、完整原生数据库构建及失败日志位于 results/tool-audit/20261024-plasx-native/。Pfam32 三个原始文件按官方 MD5 核验；COG2014 目录无独立发布者校验清单，记录 HTTPS 来源、长度和本地 SHA256，不能称为已核验官方 COG SHA256。

## 逐样本生产接口

`PLASX_ANNOTATE` 接收该样本组装，规范化压缩 FASTA，建立带样本命名空间的内部 contig ID，并保存原 ID、长度及序列摘要。由原生 anvi’o 生成 contigs DB、导出基因表，依次运行 COG14、Pfam32 并导出函数表。校验数据库与 FASTA 的完整 DNA、基因坐标、方向、蛋白序列、注释基因和样本归属。

`PLASX` 接收同一上游 tuple 中的 FASTA、ID 映射、基因表和 COG/Pfam 表，自动搜索完整 de novo 家族，再把两个注释表同时传给官方 predict。输出恢复源 contig ID，保持官方概率文本；按每条源 contig 发布 scored、not_assessed_no_annotations 或 not_assessed_no_genes 状态。没有评分不能补零或自行生成截距预测。无基因组装的原生程序边界尚待验证，不能据此声称该路径已支持。

新增资源参数为 plasx_anvio_source、plasx_source、plasx_cog_db（包含 COG14/ 的基目录）、plasx_pfam_db、plasx_profiles 和 plasx_model。旧共享 plasx_annotations 选项明确拒绝。源码及参考目录同时作为目录和递归文件依赖进入任务；重复 basename 分别暂存，避免缓存漏检和名称冲突。显式 Conda 锁仅包含运行依赖，固定官方源码作为独立输入，不能宣称锁内含有已发布 PlasX 包。

## 已取得的证据及限制

- 固定原生 PlasX、完整原模型和官方预计算注释得到 39 条评分，与官方 scores 的最大绝对误差为 4.440892098500626e-16；checked 运行与原始原生评分输出字节相同。官方 FASTA 有 40 条 contig，不能将这条证据写成“全部 contig 均评分”。这不是从 FASTA 重建全部注释的验收。
- 当前 anvi’o7.1/Prodigal2.6.3 原生命令从同一 FASTA 得到 196 个基因，官方表为 195 个；原有 195 个坐标/方向/蛋白均一致，额外一条为 AST0002_000000008287:774–903，f。未通过删除额外基因或改参考评分来强求一致。完整包装将与同一固定环境的直接官方调用对照，示例差异另记。
- 完整 COG14/Pfam32 索引已由原生类构建；直接官方 COG 和 Pfam 注释已运行成功。Pfam 首次运行因沙箱禁止本机 multiprocessing IPC 失败；沙箱外重跑成功，原错误记录保留，没有跳过搜索。
- 当前 12 项新增输入/参考/状态/执行控制单元方法通过；原 main61 场景及新增14 个 PlasX 场景全部精确拒绝、0任务。检测选择3组合28任务通过，分类器及 PlasX 注释/校验全部为明确 transport observer，不能算原生推理。完整当前生产 Nextflow 两阶段冷运行已完成；真实nf-test1用例/2任务及351+63包dependency-only Conda均通过，最终来源闭合见本批receipt。

## 已发现的原生兼容问题

anvi’o7.1 的 COG 搜索已请求 DIAMOND blastp 直接输出 outfmt6 TSV，仍调用 view 转换不存在的 DAA；原生官方 COG 命令忽略 view 的 exit1 并继续使用已有 TSV。当前严格审计包装正确阻止该失败任务；仅在内存中删除 COGs.search_with_diamond 搜索后的 diamond.view()，跳过这一步冗余转换。原安装及源码文件未修改，实际执行函数有这项明确兼容修复，不得描述为完全未修改的执行代码。搜索参数、阈值、注释解析均不变；原/有效函数 SHA256 和一行 diff 写入运行记录。首次修复错误定位到未被该命令调用的 get_blast_results，重跑仍正确失败；该失败记录保留。当前196基因/388注释与同环境直接官方调用一致，故障控制已完成。

PlasX 的 search 包含 `mmseqs ... | tee ...`，默认 shell 缺 pipefail。checked 包装对实际 shell 调用使用 bash -o pipefail，并检查实际子进程退出，不变更搜索或预测代码。真实失败管道的单元控制已证明 exit7 原先被 tee 隐藏、现在保留；完整当前搜索成功，对其注释直接调用未修改原始 predict 与包装评分一致。早期原始完整搜索被中断，仅完成9/10组，不算完整搜索对照成功。

依赖解析曾选入不支持 Python3.7 的 Django4.0，实际 CLI 失败。已通过官方包元数据确定并安装 Django3.2.24，并补齐 Cython0.29.32、setuptools-scm6.4.2、tomli2.0.1；最终351个 Conda 包精确锁定，pip check通过。新 Conda 部署另发现原生 CLI 文档解析会在 PATH 查找自身脚本；包装加入已核验 source/bin，提取器恢复官方 Git100755 可执行位254项，内容字节不变。全新351包Conda原生COG/Pfam及63包Conda完整十组搜索/预测均通过；两个环境均未安装anvio/plasx包，使用独立固定源码。

TA-087：真实 HMMER 索引解析错误被原生 HMM worker 当成无命中/exit0。当前在每个 fork worker 内检查原生 run_command 退出值，写共享逐命令记录，非零经原有 Manager queue 向主进程传播。任务私有单模型经真实 hmmpress 构建，再在 h3m 附加非法记录；原始 CLI假成功/current CLIexit1，实际 hmmsearchexit1。前两次只改文本或h3f，完整h3m仍被读取，两个程序正确返回完整260命中；这些无效故障控制及其断言失败保留，不计错误复现。

同一固定环境直接官方 CLI 与生产包装的196基因集合及388条 COG/Pfam 注释完全一致。当前还增加了导出注释与样本 DB 的逐字段比对，以覆盖“不同样本恰有相同本地 gene_callers_id”的情况；该最新检查已在新 Conda 注释任务中通过。完整当前搜索已完成；完整Conda/nf-test及来源台账按本批receipt有界关闭TA-025，整仓目标仍开放。

## 完整当前搜索和独立评分核对

完整当前生产两阶段冷运行得到196基因、388条COG/Pfam、2,193条de novo注释、39条评分和1条未评估。十组identity和32splits保持；搜索峰值内存4.9GB。原trace的搜索耗时25分43秒与外层elapsed_seconds不一致，原记录均保留，不据此推算性能。workflow-native-current/execution.json记录七项执行来源及退出0。

同路径、同大小、同mtime的私有模型NaN修改使评分任务重新执行并在搜索前拒绝，注释仍缓存；恢复后两任务均缓存。COG隐藏.VERSION同大小/mtime私有修改同样被拒绝、无发布注释，恢复后缓存。原资源未修改。GZ注释冷任务生成的FASTA、映射、基因表和COG/Pfam表与普通输入字节一致；不据此声称第二次完整GZ模型搜索。

tests/run_plasx_native.py独立用标准库统计重复及!!!多家族的计数并计算logistic概率，39条评分最大绝对差2.22e-16，完整未评估状态域一致。相同当前注释直接运行未修改官方predict，与包装评分数值完全相同。5项oracle反例方法检查重复家族不能变成二元存在、外来contig、遗漏/添加评分、错误/非有限概率及空评分域。

与官方预计算示例相比，17条contig的家族计数改变，严格>0.5的阳性数19→20。跨越阈值的是AST0002_000000025164，0.46724720324976454→0.5968566710215314。不能将全部差异归因于额外第196个基因，也不能将自动结果当独立真值更新快照。逐家族差异见independent-current-scoring-final/annotation-differences.json。这是用户批准的自动注释方法变更，模型和阈值未改；旧共享注释结果需重算后比较，不作分类准确率证明。

完整资源已通过tests/prepare_plasx_resources.py从锁定公共输入重建。两份COG pickle字节不同但1,785,679项PID映射及空missing集合一致；Pfam h3i字节不同但实际hmmfetch返回同一模型，其余关键数据库字节一致。重复大文件随后按独立清理记录移除，主资源保留。准备receipt是历史成功证据，不能声称已删除路径当前可用。

## 原生无命中与无基因边界

实际完整COG/Pfam注释对子集AST0002_000000028801得到3基因、0注释，原生各阶段成功；1000个N的输入仍被Prodigal预测为1个基因，同样0注释，因此该文件虽曾命名zero-genes，不能作为0基因证据。60个N的短输入实际生成0基因，anvi-export-gene-calls明确报“does not seem to have any gene calls”，任务失败，未发布成功注释；此整个组装无基因的输入目前排除支持，不冒充已评估阴性或合法空预测。一个含基因的组装内单独无基因contig可按映射标记未评估。原生predict空注释表的header-only控制只验证评分边界，不证明整个0基因链路成功。见annotation-empty-boundaries/measured-results.json和short-no-genes/run.json。


## 2026-10-26 目录身份候选续接

两阶段的5个目录资源改为紧凑内容/布局身份值，保留原路径布局、完整数据库、十组搜索和原系数；不再依赖glob成员staging。完整NIO枚举发现原主归档的Git子模块未展开，3个UI链接断开；没有删除链接或放宽枚举。按原gitlink提交补齐全部13子模块，并保持原1185文件主源码摘要 `7956da22fe2d89cf113ab0416b9a98e96a6b85db32c36be543158d60ce033004`；新增2216个依赖文件另有摘要/归档锁。生产源码守卫分别验证主源码和全部子模块。

当前完整原生冷执行位于 `results/tool-audit/20261026-resource-consumers/plasx-native-v3/`：196基因、39个可评分contig，独立logistic与新的官方predict对照最大差2.220446049250313e-16。这里仍是原软件fixture，不能作独立科学准确率。原始断链失败和沙箱IPC拒绝失败均保留；经本地IPC执行授权后使用相同完整输入、参数和工具版本重试。冷会话不变/私有anvi’o源码等长同mtime损坏/还原对照通过（4CACHED、1预期FAILED）；其余4个资源未逐一做原生损坏控制，不能扩写该范围。

资源准备器已集成精确子模块获取/验证步骤，单独补齐入口为 `tests/prepare_anvio_submodules.py`。本轮只重复验证该准备步骤，未重复完整COG/Pfam/profile格式化。源码/缓存总契约见resource-directory-cache.md；整项TA-091继续开放。
