# 当前验收边界

全量审计未完成，不能给出支持路径放行结论。基线 f57d0f91454ee0c99cf462ac9093bdf68349991a；当前变更均未提交。生产/测试增量补丁及当前源码哈希见 patches/ 与 evidence/post-fix-source-state.json；原始来源共489个tracked对象：source-receipt.tsv冻结488个普通文件hash，另1个目录symlink身份补在source-receipt-symlinks.tsv；历史“489文件hash”措辞按此澄清，原表保持不变。旧验收摘要见 history/before-scapp-removal/acceptance.md，精确当前计数由 status.md 生成。

COPLA批次正在验证：TA-019/020/074为in_progress，完整9894参考原生双候选和实际nf-test仍在运行。当前工作代码尚未加入上一接受批次的204项来源清单，source mismatch表示这批待验变更。入口曾包含一个不必要的固定目录名限制，该约束及对应测试已撤回，61个有效拒绝场景已按当前main通过，全部0分析任务；不能把旧62/62或上一批51/51当作当前main验收。完整状态以status.md/current source hash与运行产物为准。

累计85项：62项已验证局部修复，2项按用户要求退役（TA-006/035，不计修复通过），21项未决（S0=3、S1=0、S2=18）。PLASMe的TA-024/053及新增TA-069–073已按完整库/真实模型与有界接口范围验证；Platon的TA-005、TETRA的TA-039仍为ready。单项修复或能力退役不代表所属路径放行。

| 验收对象 | 当前证据与限制 |
| --- | --- |
| 源码盘点 | 当前108个生产.nf，另保留2个SCAPP退役对象，共110台账；211导入符号、101文件主入口词法可达、0缺失include；仍需完整动态配置/channel审查 |
| M0 配置展开补证 | 实际Nextflow26.10.0隔离-C序列化默认/五后端/test/五test组合，12场景引擎开关、资源和显式小库方法一致，9配置SHA前后不变。0分析任务；未证明模块指令、closure、实际选择器优先级、其他平台或执行就绪。见evidence/profile-resolution.json；M0仍未闭环 |
| 测试审查 | 当前158份来源，另保留4份退役SCAPP来源，共162；包括harness/config/数据锁，不是用例分母，剩余TT断言/fixture问题仍未决 |
| OPERA-MS真实默认节点 | 固定v0.8.3全部469 Git blobs核对、完整官方2.93GB归档/43MB sketch及5242参考文件、111包及41包Python前缀+Switch2.17锁。gzip私有解压、最终产物身份、内部崩溃阻止发布通过真实原模块/原nf-test0.9.5 P3与故意坏ABI反例；17方法、16选定trace=8完成8预期失败（含9 observer和2个明确不验收的退化完成）。当前hybrid201连接任务包括真实宿主过滤及全read ID/DNA/质量核对，其他CLI仍observer。两个成功重放各57/56contigs，分别与自身stats/最终产物一致；不认证字节级复现/差异原因/组装准确率/完整真实hybrid。10源补丁、当前192hash，见results/tool-audit/20261023-opera-native/receipt.json |
| 下载与QC局部修复 | TT-004完整下载脚本20个独立方法，真实本机HTTP/file与curl/归档；重复Python3.12/3.15不增分母，默认十项失败及manifest写失败为明确observer，不下载生产DB。TA-034固定fastp1.3.6原生SE/PE/交错核对ID/DNA/质量/计数与reads通道；TT-007仅修复--gbk stub创建文件。新旧16trace=15完成+1旧预期失败，其中6真实fastp、6fastp stub、4IntegronFinder stub。7来源增量patch，当前187来源hash。完整镜像/框架/平台/生物学性能不由本批认证，见results/tool-audit/20261023-prerequisites/receipt.json |
| SCAPP退役 | 用户明确要求“删掉SCAPP节点”；删除检测/binning节点、环境和4份测试，调用端与工具选择已清理。旧选择、权重、FASTA输入明确失败，输出表仅4个工具列；历史证据及对象保留，见retirements.tsv |
| 当前入口P0 | 当前main61个独立拒绝场景全部正确诊断且0分析任务/0.command.sh；包括上一批51场景与10个有效COPLA依赖场景，含原2个SCAPP旧开关；p0-main-cases.tsv按当前main哈希映射。固定参考目录名的额外限制和对应测试已撤回，旧62记录不计当前分母。不是nf-test框架/JUnit认证，也非完整平台能力矩阵 |
| 当前共识与结构 | 共识33测试方法（原28+PlasX5）、PLASMe适配7方法通过；R smoke上一批54断言通过；原模块4场景：5样本10任务阳性/阴性/空结果/PlasX低高分及3个失败任务正确拒绝旧SCAPP输入、未知ID、空记录，未发布部分产物。DNA、ID、长度/GC与结构对应通过；不是分类器效果验证 |
| 当前检测连接 | 原PLASMID_DETECTION单输入调用，2样本可选工具全关/仅Platon/全开3场景26任务通过；分类器为明确CLI observer、下游为真实原生R。证明tuple/样本连接，不能认证PLASMe/PlasX真实输出格式、模型或DB |
| PlasX消费者 | TA-023已验证：原生R及原wrapper验证官方两列表、严格>0.5、负分保留与17位精度；TA-025注释/模型生产者仍未决，不是完整PlasX或科学效果认证 |
| PLASMe真实模型及部署 | TA-024/053/069–073有界verified：固定官方1.1全部9 Git blobs、完整Zenodo8046934归档13,632,339,031字节/36模型、完整DNA/蛋白与BLAST/DIAMOND索引，99包CPU环境。当前代码原nf-test2用例/native与Conda、Podman共4次真实Transformer阳性，均完整pUTI89同一样本，plain/gzip/GZ的ID、完整DNA与分数核对；真实完整库的人工N-query无命中、微型BLAST/显式失败worker5控制、20方法、writer7场景16任务/检测3场景26任务（分类器observer）通过。入口/显式source channel/零命中/外部失败/私有ELF预加载/容器用户及xattr边界均保留前态失败。20源增量补丁，当前204源hash，见results/tool-audit/20261023-plasme-native/receipt.json。不代表独立生物重复、分类准确率、完整真实平台、Docker/Singularity或远端executor认证 |
| 当前downstream连接 | 删除SCAPP后ABRicate路由6场景8任务observer回归通过；不是真实CARD搜索或完整平台认证 |
| 已验证局部修复 | TA-043/045/048/037/047/044/042/041/009/022/023/028/008/030/032/055/056/054、TT-008及Recycler TA-002/003/004/051/052；各批receipt保留代码/输入/环境和限制，不扩大验证范围 |
| Recycler | 真实锁定minigut原P3工作流原生4任务通过：同图317参考、k55、1条1871bp图自环序列；k33/k55受控阳性、0边显式状态、BAM/BAI/hash拒绝和失败传播通过。SCAPP移除后只改变SPAdes注释并保留上游SHA/差异；完整Illumina/hybrid/镜像/框架与科学准确率仍未认证 |
| RGI数据库修复 | TA-028 verified：RGI6.0.8实际完整CARD3.3.0/3.2.8，原成功错用global导致VIM-77报VIM-2；改为同任务local且JSON/loaded hash/版本一致。6原生叶任务（含1预期失败）和2实际downstream任务、6方法通过；默认真实质粒与独立上游参数oracle分开。非镜像/nf-test/完整平台/临床准确率认证 |
| 其他真实节点 | QUAST5.3.0 native对锁定pUTI89 plain/gzip指标和同序列reference通过；Bowtie2固定版本四个调用点22原生任务符合独立受控真值；不是完整平台或minimap2认证 |
| MAG路由与DAS导出 | TA-008/030仅局部verified：用户明确多分箱器必须显式DAS，单分箱器直连；13 observer场景201任务/native R检查样本/分组/成员/序列/数量，真实DAS1.1.7官方完整gut样本导出15个独立预期bin且逐条DNA一致。最终阳性直接使用生产参数；真实无达标bin依上游主动失败并无部分发布。45 main+8直接include拒绝检查通过。TA-031/049仍未决；不是完整MAG/质量/分类/平台认证 |
| CONCOCT输入/坐标/空提取 | TA-032/055/056局部verified：真实1.1.0切片/extract的17场景通过；原默认重叠BED越界已改为实际步长，DNA切片及参数不变。固定真实DNA与明确构造合法BAM，原MAG分支2样本12真实节点、各122 bins成员/原DNA对应且plain/gzip一致。路由使用真实cut/merge/extract与原生R，13旧场景+1空CONCOCT共217任务通过；核心/质量/分类observer与真实分箱分开。不等于生物学分箱准确率/镜像/nf-test/完整平台认证 |
| DAS可选数据库 | TA-054局部verified：--dbDirectory正确拼写、固定暂存名避免空格拆分及db保留名回退，六个非空文件预检。8真实任务：含空格/名为db/默认DB三正例全部15 bins独立成员/大小/DNA吻合；三类预检错误在查询前失败；不匹配lookup的明确负例证明实际读取指定DB，均无部分发布且输入不变。32任务MAG/R回归通过；不认证任意自定义DB生物学有效性/镜像/nf-test/完整平台 |
| 结构拓扑TA-036 | 固定真实SCP1独立线性拓扑反例：旧true/itr1000，现false/unknown并保留ITR；pUTI89原FASTA保持unknown、显式metadata header为候选。13结构/3报告方法、54 smoke、5原结构+1原REPORT及检测26任务通过；该结构fixture的报告输入显式隔离；TA-015由报告专用批次补验，图/reads/镜像/nf-test/完整平台/科学性能仍未验证 |
| 共享参考/真实计数TA-010/012 | 用户选择已实现；完整DNA/RC精确去重，全组装竞争映射，hybrid短读。真实固定DNA+明确模拟reads，三模式55原生任务和歧义/全局空/缺样本29任务通过；原CROSS_SAMPLE和coabundance实际R核对独立数值。四平台+空结果725连接任务用明确CLI observers，非完整真实平台。37单元方法和54 smoke通过；MAPQ≥10排除Bowtie2 ties=1，count为read比对数、mate分开；覆盖度不再取整。本段为共享参考初验scope；TA-011/013/014/038现由后续统计批次局部verified，TT-001继续open |
| 本轮报告TA-015/017 | 显式本轮FASTA/共识/结构、样本表、R脚本与模板path输入；各已调用分支输出作为完成证据，旧样本/空目录不能影响结果；五份产品含JSON数据/输入清单均发布。原生5场景8 trace（4完成3缓存1预期失败）验证延迟无发布、resume不变/改变及失败阻止报告，13R方法/54smoke、共享55/结构6/MAG32和6平台场景788 observer任务回归通过。TA-016完整CLI/数据库/模型身份仍ready；非镜像/远端executor/nf-test/完整真实平台或科学效果认证 |
| 长读宿主TA-033/057与TT-006/010 | other类别输出修复、全过滤明确QC失败、Minimap2管道失败传播；8原生对照场景53trace(旧31/新22)，6单元方法/旧6红，Bowtie命名3原生场景，shared55原生任务通过；ONT150/HiFi142/hybrid(OPERA)204/ONT无参考144共640任务最终逐记录验证，仅其中18宿主长读任务原生。HybridSPAdes额外环境失败排除；其他CLI observer/实际R/Python，不是全平台/镜像/nf-test/科学效果认证 |
| TETRA与分类输入TA-039/040/058 | 用户授权标准256双链修正；跨记录虚构窗口TA-040、taxonomy.tsv源表截断TA-058局部verified。8数学/11接口/7校准工具/4退出oracle方法、54smoke、真实2节点24配对/分类输入3节点/可选路由11任务通过。TA-039仍ready/open：0.7未校准，尚缺独立真实宿主标签/组隔离留出基准；人工0.8不写默认；自匹配DNA非已知宿主真值 |
| 统计样本/零结果/网络TA-013/014/038/059/060 | 五项局部verified；完整cohort/state/矩阵/质粒子集校验，真实零值保留而缺测失败，逐样本alpha避免单列池化，过滤后去新零列并按FastSpar1.0.0至少4特征/最终样本门控。大整数文本不经int32；七custom程序/helper显式path输入。57单元方法/54smoke、109native trace=101完成5缓存3预期失败；真实共享58包含其中，6平台793任务外部CLI仍observer。百万行25100KiB。Python前一接受wrapper缓存缺陷直接复现；新Rhelper缓存控制不冒充基线缺陷。TT-003/P4框架仍open，TA-011/061模型/配置由2026-10-23批次补验。见results/tool-audit/20261022-statistics-eligibility/receipt.json |
| 固定模型/阈值/输入保护/标签TA-011/061/062/063/064/065/066 | 七项局部verified；普通整数矩阵修正固定1.42 table/S4失败；完整模型/逐对数值与独立宽矩阵官方API一致，零/空/过滤后零文库明确状态。每组正整数门槛默认3，网络默认20且显式0拒绝；四节点分别暂存计数/metadata，同名输入不改源；三消费者标准TSV分组解码/转义。144原生trace=130完成5缓存9预期失败（含旧错误对照）；57去重单元方法/54smoke，真实共享58已包含在144内；5读平台/空结果730新任务+未受影响assembly63共793，外部CLI仍observer。旧输入改写对照明确1.52非默认1.42；不认证镜像/框架/真实非空P4/生物学功效。见results/tool-audit/20261022-deseq-model/receipt.json |
| 五个平台/科学结果 | Illumina/ONT/HiFi/hybrid/assembly无当前完整成功E2E认证；共享参考/计数局部契约已有验证；完整真实部署/镜像/框架、TETRA真实阈值、完整报告方法溯源等仍需验证；P1/P2/P3/P4完整工具/环境/DB与科学基准待完成 |

SCAPP退役前的重建序列接入实验已撤销；候选实体不同导致的投票方法问题保留在历史调查中，不再作为当前待实施方案。结果兼容性：删除共识表scapp列；曾选择SCAPP的调用必须移除该项并在新输出目录重跑，不与旧SCAPP共识结果直接混合。

M0动态配置/完整channel图/历史证据归属及默认真实基线尚未闭环；M1首批、M2核心、M3扩展与M4平台验收继续按原计划进行。退役有明确用户授权，并保留历史分母和失败证据。

2026-10-22统计批次补验覆盖旧段落的TA-013/014/038未决范围；其当前状态已为bounded verified。175份当前生产/测试源码hash与38源增量补丁留档。TA-059源自前一已接受共享计数实现，不能追溯为HEAD即有问题；新helper仅为本轮候选回归。DESeq2固定1.42的185包环境恢复后，于2026-10-23完成本地模型/零计数与原wrapper验证；镜像与真实P4仍未验。

2026-10-23固定模型批次17源增量/181项来源hash留档；56方法与18状态方法重叠17，去重57而非74。缺失NA分组前后同样不生成比较，仅作回归，不计新缺陷。旧段落的TA-011/061未决均对应历史scope。原生工具版本、环境、数据、源码、旧错误和预期失败按receipt分别审查；M0–M4全量审计继续。
