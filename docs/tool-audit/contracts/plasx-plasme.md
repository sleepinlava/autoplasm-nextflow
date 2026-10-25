# PlasX 与 PLASMe 输出语义

当前 PLASMe 状态以本文2026-10-23补验及对应receipt为准；下文20/21日的ready和环境未知为历史调查。PlasX生产者TA-025仍未决。

2026-10-20，基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。官方源码固定快照见 evidence/score-tools-upstream.json；实际安装/Conda 版本仍未知，不计真实工具通过。

PlasX 官方 [commit 5c9acfd00a597da27ef5261acf72dbaf2117b645](https://github.com/michaelkyu/PlasX/tree/5c9acfd00a597da27ef5261acf72dbaf2117b645)：plasx_script.py 定义 -a annotations、-g gene-calls、-m model；model.py 输出所有 contig 的 score。README 建议 >0.5 判断质粒，分数接近零表示非质粒。共识 generic parser 无 classification 列时直接 TRUE，与“仅报告阳性”的 Platon 不同。TA-023：人工真实 schema 的 1e-8/.99 两行均转 plasmid；隔离权重 genomad:0,plasx:1 时两序列都写入 FASTA。run.json、输入、预测和最终序列保存在 results/tool-audit/20261020-score-parsing。这不是 PlasX 算法运行，只验证当前消费者。

TA-025：Prodigal GFF 不是要求的 gene_callers_id→contig 表；源码 model.py 用该两列做 annotation merge。生产没有逐样本 gene family 注释链，-a 配置是全局 value；如果注释已有 contig 列，GFF 可能不被用于 merge，但也必须验证注释属于本样本，不能据此声称任意 GFF 合法。缺安装版本/依赖，当前为静态差异。

PLASMe 官方 [commit 4405d5aa82065cf23a9d78de8b70ba261342ad40](https://github.com/HubertTang/PLASMe/blob/4405d5aa82065cf23a9d78de8b70ba261342ad40/PLASMe.py)：plasme_output 将阳性 FASTA 写到 output_path 本身，报告为 output_path_report.csv，虽扩展名 csv，实际列用 TAB 分隔。当前包装的输出参数为 S.plasme，却不读取 S.plasme 或 S.plasme_report.csv。TA-024 用原生产模块、真实 Nextflow 26.10.0 和一个仅按官方格式写出的 CLI double 复现：阳性原文件/报告存在，但 S.plasme.tsv 只有表头，进程 COMPLETED/0。原命令、stdout/stderr、trace、.command.sh 与文件均在 results/tool-audit/20261020-plasme-wrapper。该 probe 无真正分类、无模型/数据库推理，不计 P3 生物学节点验证。

包装应明确区分无检出与文件缺失。不得通过保留当前吞缺文件 fallback 来处理合法阴性。分数阈值/实体解析改变影响 consensus strategy，需单独记录结果可比性。

测试逻辑：tests/test_plasmid_consensus.py 的负例使用 classification 列，positive-only 只测 Platon；没有 PlasX 低分/边界表，也没有 PLASMe 实际输出文件名适配。测试应使用固定上游格式 fixture，而非假设每工具共享同一个人工 schema。

## 2026-10-21：PlasX 消费者修复与 PLASMe 输入/输出适配

TA-023仅关闭共识消费者范围：固定官方5c9acfd的contig/score表含全部候选，按README严格score>0.5记阳性，=0.5为阴性；要求有限[0,1]，完整负分行保留，PlasX分数用17有效位输出以保持边界值可往返。原有投票算法、权重及其他工具分数格式不变。旧PlasX参与的共识结果需要从实际分数表重算，不能与新结果直接混合。TA-025的逐样本基因家族注释/安装环境仍未决，不能宣传整个PlasX节点已认证。

TA-024实现并标ready：PLASMe v1.1的第二个参数是阳性FASTA路径，报告为该路径_report.csv（实际TAB）。固定Git blob7f0718071849b73111a4e641b27e0f528d3356a2重新从GitHub核对，按原路径读取两文件并检查ID集合、长度、完整DNA；所有缺失/破损/不一致均在生成消费者表前失败。报告本身已筛为阳性，不重新按Transformer概率阈值过滤；BLASTn命中score=nan、或BLASTn支持但Transformer0.2的记录仍保留。规范化表带明确classification和source_score等来源字段；R预测中的1为调用指示值，原始报告及FASTA一起发布，不是概率校准。单独函数源码按moduleDir嵌入任务脚本，随脚本进入缓存身份。

新TA-053 S2：压缩assembly直接传给PLASMe，在官方输出函数SeqIO.index报普通gzip不可索引。已为.gz/.GZ解压并保持plain输入原样；坏gzip在调用工具前失败，标ready。TA-024/053尚缺固定完整PLASMe环境、模型/DB真实推理及平台P3/P2，不能因writer接口通过改为verified。

验证：PlasX新增5方法/14 CLI场景，前态12断言失败，后态全过；原28共识方法全过。正常/空结果与PlasX实际两列表通过原Nextflow共识/结构10成功任务，3错误输入仍正确拒绝且无发布产物。PLASMe helper7方法通过（缺文件、错表头、重复/空ID、错DNA/长度、格式空白）；原模块+实际固定源码的plasme_cmd/merge_ranges/plasme_output AST，受控candidate和BLAST命中，7场景16任务通过。前态plain阳性和缺报告均成功/3任务却丢失结果，另gzip前态在官方索引函数失败，均保留。完整检测子工作流3组合26任务observer回归通过，样本/输出/列身份不变；observer现使用官方PLASMe路径/报告及PlasX分数表。以上没有真正模型/BLAST推理，无nf-test loader、镜像或科学准确率认证。

保留新测试harness校准失败：最初include占位符替换误改process符号，7场景均0任务解析失败，修正为仅替换引号内路径；正确前/后态单独保存。辅助Python3.12.15/pandas2.2.3/Biopython1.85环境安装成功，41包explicit lock，只用于writer测试，不替代PLASMe部署。证据、输入、trace、命令、补丁前后hash及限制见results/tool-audit/20261021-detection-score-adapters/receipt.json。主入口未改，37个P0保持原main hash对应，不重复增加分母。

当前62问题：17verified、2用户退役、43未决（11S0/2S1/30S2）；新增TA-053并保留ready状态。全量审计未完成。

本批补充证据：PlasX前/后态各14条CLI保留完整FASTA、summary、score表、输出、stdout/stderr、命令及逐输入SHA256，重复重放不增加14场景分母。PLASMe最终7场景16任务另用包含空格/单引号的FASTA与数据库名通过，原module单引号参数编码与当前helper内容均核对；首次闭包调用未使用.call导致strict Nextflow零任务解析失败，已保存并修正。原共识模块对TaskPath本身自动进行shell转义，实际.command.sh已核对，不误报为新缺陷。主入口代码未改，额外一个原main拒绝场景检查新include可解析、仍精确拒绝且0任务，不计新增独立P0。

## 2026-10-23：完整 PLASMe 模型、环境与接口补验

TA-024/053及新增TA-069–073按局部范围verified。固定官方commit4405d5aa的全部9个Git blob逐项匹配；PLASMe.py为100644、无shebang，旧模块裸调用实际exit126。现在把官方源码目录作为第三个path输入，选用PLASMe时必须提供--plasme_dir，moduleDir解析精确Conda YAML；--plasme_container可覆盖本地构建镜像。6个新入口拒绝控制和原45场景均0任务/正确诊断，当前51场景不把重放累计为新增。

完整Zenodo8046934 DB.zip：13,632,339,031 bytes，MD5 b32263ad4fb20c04044700170b1609ef，SHA256 3375080dec8e6151566816824bd7c712ee36462a472516335cb5d5015a2f36f2。41个文件含36模型均CRC读取/逐SHA保存，嵌套完整33,125个核酸参考及3,681,948个蛋白用于实际建BLAST2.13.0和DIAMOND2.0.15索引；不是只读ZIP目录或抽取部分模型替代完整库。公共身份在tests/plasme-native.lock.json；完整准备receipt独立保留。

环境保留官方核心版本Python3.9.15/Torch1.11.0/Numpy1.23.4/Pandas1.5.2/Bio1.80/MKL2021.4.0/Prodigal2.6.3，99包明确URL/MD5。旧Torch库GNU_STACK flags7在本机导入失败；私有复制只清PF_X，原SHA03f6d083…到928c4d73…；仅LD_LIBRARY_PATH仍被Torch RPATH压过，真实Conda推理反例因此失败。修复为仅Python子进程预加载私有SONAME，并在调用实际源码前移除传递给外部程序的LD_PRELOAD；实际完整Transformer通过，清理私有目录，原Conda缓存SHA保持。模型和机器码均未改，镜像构建时清同一ELF标志。

官方内部shell调用缺乏路径引用，故source/DB/input/temp统一暂存固定ASCII名，plain与gzip/GZ保持完整DNA。仅对固定PLASMe.py及匹配bio_script SHA生成任务私有源码补丁：零BLAST查询先写合法空候选表；BLAST及4个helper subprocess使用check=True；取回每个Prodigal异步worker结果再合并。真实微型BLAST前态range(step0)红、后态合法空；真实坏DB非零传播；显式partial-output/exit7 worker前态假成功、后态正确失败。微型库及该worker只验证边界，不计模型效果。完整官方库另跑人工N-query无命中控制，并明确不把它当真实生物学阴性基准。

容器基于固定micromamba基础digest和99包锁；真实Nextflow运行暴露并修复UID映射、缺ps，以及copy2复制宿主security xattr的EACCES。使用宿主UID/keep-id、procps及只复制源码字节，未关闭指标收集。失败原始产物保留。实际本地镜像ID03ca182dfec80dc6e587c76143e04984df85c7b33b23f73c08a55cc40c939462，不冒充已发布registry manifest digest。

当前代码真实nf-test0.9.5两用例（plain/gzip）及Nextflow Conda(gzip)、Podman(GZ)共4次完整pUTI89 Transformer推理通过；同一114,230bp质粒NC_007941.1，不是4个独立生物样本。独立BioPython解析核对每条DNA/ID/长度及预测集合；分数按预定float32绝对容差2^-22比对，实际数值见oracles。原始FASTA/report与规范化表均一致，BLAST支持记录不会被再次按Transformer0.5重筛。20独立单元方法、5个边界控制、writer7场景16任务/检测3场景26任务分别记账；后两者分类器为明确observer。所选8个原生trace为5完成3保留失败，不能全部算阳性。

20来源增量补丁、204项当前source hash及完整命令/日志/JUnit/输入/运行库身份见results/tool-audit/20261023-plasme-native/receipt.json。3个检测选择组合仍验证样本连接，不冒充完整真实分类链；全量M0–M4、其他profile/平台、分类准确率、真实阴性基准及COPLA/TETRA阈值仍未完成。算法/模型/阈值不变；历史漏写的PLASMe阳性需重新检测并重算共识。
