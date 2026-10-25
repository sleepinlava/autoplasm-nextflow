# 注释与 typing 本地适配审查

2026-10-20；基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。所有结果基于当前源码与固定版本契约；本轮未运行真实模型/数据库。

TA-026：PLASMID_DOWNSTREAM 将核酸质粒 FASTA 直接传给 CONJSCAN/MACSYFINDER（MACSYFINDER_SEARCH 的 proteins 输入），配置 ordered_replicon。官方 [MacSyFinder 2.1.6 Input](https://macsyfinder.readthedocs.io/en/stable/user_guide/input.html) 要求蛋白序列，且该 mode 对应单个有序 replicon。需要先做 ORF/protein 预测并保留 contig/gene 顺序与边界，不能把多质粒 proteins 拼为一个复制子。upstream search test 使用 proteome.fasta 且 db-type unordered，与本地输入不同。

TA-027：EGGNOG_MAPPER 同样收到核酸 contigs，没有 ext.args 选择输入类型；固定 [eggNOG-mapper 2.1.13 emapper.py](https://github.com/eggnogdb/eggnog-mapper/blob/2.1.13/emapper.py) 默认 ITYPE_PROTS。可由蛋白链提供输入，或明确选择 genome/metagenome 的基因预测模式；这是方法选择，修复应记录可比性。上游用例均以 proteome 为当前已读对照，不覆盖本地核酸链。

TA-028：RGI module 的 load --local 与 main 没有 --local 不一致，本地 ext.args2 未补此参数。[RGI 6.0.8 app/RGI.py](https://github.com/arpcard/rgi/blob/6.0.8/app/RGI.py) 默认 local_database=False，只有 True 才转 LOCAL_DATABASE；[固定版本 docs/rgi_main.rst](https://github.com/arpcard/rgi/blob/6.0.8/docs/rgi_main.rst) 展示本地 load/main 联用。若全局库存在，可能成功却用不同 CARD；若不存在则失败。当前未用真实数据库复验，静态差异已确认。版本变量标注的本地库不等于实际查询库，需要区分两个库的对照。

TA-029：MOB_RECON 与 MOB_SUITE_ANNOT 既无发布又不在 subworkflow emit，结果仅留 work，配置注释将之列为故意限制。计划要求最终发布完整性，此限制仍需登记并修复或明确排除支持；不能以注释代替最终交付。

本轮同时核对 BAKTA、MOB_TYPER、PLASMIDFINDER、AMRFINDERPLUS、INTEGRONFINDER：当前调用 arity 与本地 module 声明一致。Bakta 正常接核酸，MOB_TYPER --multi 与 per-contig mode 显式配置，PlasmidFinder/IntegronFinder 有 gzip 适配，AMRFinder 默认 nucleotide。未发现的本地 arity 差异不等于工具 matched；数据库版本、阳性/阴性输出与部署锁仍需逐项证据。

TT-005：上游测试入口的辅助依赖未完整 vendored，见 vendored-test-dependencies.tsv。当前明确配置的 P1 清单仅四套，不能推导其余套件可直接执行。保留上游未修改测试有来源价值，但不是可运行或语义正确的证据。

## IntegronFinder stub 与 AMRFinder 输入续审

2026-10-20：TT-007，vendored INTEGRONFINDER.stub 的gbk_create值为Results_Integron_Finder_S/S.gbk，当args含--gbk时将这个路径直接插入独立shell行，没有touch。原module实际Nextflow -stub-run：default task/workflow退出0；--gbk task退出127，.command.err指出该文件路径不存在。tool只以显式observer提供版本，未执行真实IntegronFinder。完整harness/config/trace/命令与错误在results/tool-audit/20261020-integron-stub/run.json。

该代码与登记upstream revision f3cdfac60a5c7e23f72c5b211c50218277073c8b一致（vendored来源比对已有记录），不是本次修改引入。现有vendored两项test含real/default-stub，但没有--gbk覆盖。配置p1-suites.txt当前只有fastp/fastqc/samtools-sort/megahit，不含IntegronFinder，因此不声称当前四套P1入口已因此失败。stub创建文件成功也不是GBK内容或真实注释认证。

AMRFINDERPLUS生产别名对应amrfinderplus/run，meta没有is_proteins时明确-n核酸输入；并未把plasmid FASTA当默认蛋白，与EGGNOG/MacSyFinder输入差异不同。module会显式--database amrfinderdb，同一个staged DB也用于version查询，未发现RGI式local/global不一致。此为本地代码静态确认，尚未完成固定4.2.7工具/数据库实际回归；不声称抗性检出或数据库兼容已通过。

IntegronFinder真实script对gz解压后传FASTA，production consensus本身是plain。real输出gbk为optional，integrons/summary/out必需；真实无integron时是否均有带表头产物仍待固定工具或真实节点，未凭stub结果推断。

## 2026-10-20 TA-009 可选ABRicate接线修复

ABRICATE选择条件现在接受annotation_tools或annotation_optional_tools，两个入口共用同一次process调用，不改变vendored模块、--db/线程/prefix配置或阈值。原PLASMID_DOWNSTREAM/ABRICATE模块6场景基线均workflow exit0，但optional及trimmed两场景未提交任务；修复后公开runner的abricate-routing套件6/6通过、启用4场景共8任务。每个样本独特序列，逐项核对S1.card.txt/S.2.card.txt、输入SHA、样本prefix及card参数；both只各执行一次，disabled/空通道0任务。

这是明确标注的Python CLI接口observer，不进行ABRicate/CARD检索；observer的1.0.1版本响应仅供模块eval，不认证真实工具版本。真实native abricate/blastn不在PATH。首次测试驱动重构误缩进observer导致fixture启动失败，after.log留存但排除；修正后公开suite通过，完整工件复制到results/tool-audit/20261020-abricate-selection-fix/retained/，receipt含hash。测试harness与observer suite已进入tests，统一runner新增abricate-routing并清楚打印无生物学搜索；共享oracle4/4保持。

TA-009只按选择/接线契约关闭，ABRicate模块inventory仍investigating，真实节点/数据库/容器/P3及平台完整E2E没有通过声明。当前normalized route unique pair由44增至45，原44条证据归档。此前被忽略的optional选择现在实际执行，需在真实环境验证后重新生成所需注释。

## 2026-10-21 TA-028：真实RGI本地/全局CARD选择修复

上一目标轮完成PlasX/PLASMe适配与测试修正，本轮为继续推进，未重定义审计范围。TA-028已用真实固定版本工具/完整数据库复核并修复：RGI6.0.8原代码与GitHub固定tag的RGI.py/settings.py/Database.py/load.py/ORF.py/Filter.py匹配；native环境另含KMA1.6.11（仅version eval）、DIAMOND2.2.8、BLAST2.16.0、Prodigal2.6.3，Python3.11.17，256包explicit lock。Conda环境文件和nf-core revision0a93f68a28f5e07bb7ae82aeb005720faf8a3b35保持不变；原始blob a11398832cbd7675cd4fe28a34fe637ae903cd1c与GitHub重新获取结果一致，本地差异单独登记。

两份完整[官方CARD归档](https://card.mcmaster.ca/download)为3.3.0、3.2.8（非裁剪/虚构版本），下载包和解出JSON逐一锁hash；测试的全局路径由DB_PATH/DATA_PATH指向审计目录，未使用或覆盖系统库。上游6.0.8锁定的真实NC_020818.1质粒、NDM-1蛋白和CARD3.3.0的VIM-77真实参考序列用于限定sanity；独立预期VIM-77 model6038在3.2.8不存在、在3.3.0唯一，NDM-1/mphE/msrE参考断言来自固定上游tests/test_1.py。随机DNA为明确人工阴性，不是科学效果基准。

原模块在load本地3.3.0后仍用global3.2.8运行main，3任务全部COMPLETED/0，DB_VERSION甚至显示3.3.0，却把VIM-77记录报为VIM-2 model391/Strict99.62。原始全局库的独立protein CLI能Perfect100命中NDM-1，说明不是故意损坏global造成的失败。修复为main显式--local，与既有load --local一致；DB_VERSION来自card.json，不再任意ls/SED匹配文件名。加载前检查对应canonical/all注释文件；加载后确认localDB/card.json逐字节SHA256及loaded_databases.json版本与输入一致，避免load失败/陈旧库继续查询。验证器嵌入实际任务脚本并参与缓存身份，未改变模型、阈值、Prodigal模式或其余生产默认参数。

验证闭环：validator6方法全过；当前模块四个独立场景共6任务（global存在3、global为空1、版本/文件不符1预期失败、上游参数oracle1）全部符合独立预期。原PLASMID_DOWNSTREAM+真实RGI启用/关闭两场景，启用2样本2任务正确命中VIM-77及真实质粒参考，禁用0任务；逐样本加载CARD JSON hash一致，最终JSON/TSV样本名/数目正确，全局CARD保持原hash。合计8个当前任务脚本均含完整当前验证器两次；这是一个RGI工具节点的多个case，不是8个独立工具。actual main原有unknown optional tool拒绝场景也在新include下精确失败且0任务/0.command.sh，不增加37个P0分母。

保留全部校准失败：初始dry-run误用KMA1.4.14，明确中断且未安装；依据真实environment.yml更正1.6.11后256包安装成功。新测试最初把上游NDM-1断言套在生产默认Prodigal参数上；读固定上游才确认其使用low_quality/include_loose/include_nudge/clean/debug，默认本地和全局库均能找到mphE/msrE而未必找到NDM-1。生产算法未改，默认模式的原生检查与完整上游参数NDM-1/Perfect100检查分别保留并通过，不能把模式差异误归数据库补丁或盲目删断言。测试还出现fixture/case目录重名，以及上游专用配置选择器语法错误（0任务），均保留；只纠正并重跑受影响上游参数控制，未抹去final-native中失败记录。最终receipt聚合三个有效原场景和修正后的一个oracle，明确引用各自原始记录。

TA-028现在fixed/verified，仅限实际数据库选择/版本元数据及受影响注释子工作流；inventory整体仍investigating。镜像、nf-test框架/JUnit、wildcard分支、完整平台/P4及临床AMR检出性能尚未认证。旧RGI输出若不能证明查询库与配置一致，应在新输出目录重算。证据与8源增量补丁：results/tool-audit/20261021-rgi-database-scope/receipt.json，patches/TA-028.diff，local-patches/rgi-main.diff。当前62问题=18verified+2按用户要求退役+42未决（10S0/2S1/30S2），全量审计未完成。
