# 当前验收边界

全量审计未完成，不能给出支持路径放行结论。基线 f57d0f91454ee0c99cf462ac9093bdf68349991a；当前变更均未提交。生产/测试增量补丁及当前源码哈希见 patches/ 与 evidence/post-fix-source-state.json；原始489文件盘点 source-receipt.tsv 保持历史基线。旧验收摘要见 history/before-scapp-removal/acceptance.md，精确当前计数由 status.md 生成。

累计63项：20项已验证修复，2项按用户要求退役（TA-006/035，不计修复通过），41项未决（S0=8、S1=2、S2=31）。OPERA-MS的TA-001/050、Platon的TA-005补丁仍为ready，缺真实节点及受影响平台验证。单项修复或能力退役不代表所属路径放行。

| 验收对象 | 当前证据与限制 |
| --- | --- |
| 源码盘点 | 当前102个生产.nf，另保留2个SCAPP退役对象，共104台账；173导入符号、96文件主入口词法可达、0缺失include；仍需完整动态配置/channel审查 |
| 测试审查 | 当前97份来源，另保留4份退役SCAPP来源，共101；包括harness/config，不是用例分母，剩余TT断言/fixture问题仍未决 |
| SCAPP退役 | 用户明确要求“删掉SCAPP节点”；删除检测/binning节点、环境和4份测试，调用端与工具选择已清理。旧选择、权重、FASTA输入明确失败，输出表仅4个工具列；历史证据及对象保留，见retirements.tsv |
| 当前入口P0 | 当前main45个独立拒绝场景全部正确诊断且0分析任务/0.command.sh；本批重放37个并新增8个MAG依赖场景，含原2个SCAPP旧开关；p0-main-cases.tsv按当前main哈希映射。不是nf-test框架/JUnit认证，也非完整平台能力矩阵 |
| 当前共识与结构 | 共识33测试方法（原28+PlasX5）、PLASMe适配7方法通过；R smoke上一批54断言通过；原模块4场景：5样本10任务阳性/阴性/空结果/PlasX低高分及3个失败任务正确拒绝旧SCAPP输入、未知ID、空记录，未发布部分产物。DNA、ID、长度/GC与结构对应通过；不是分类器效果验证 |
| 当前检测连接 | 原PLASMID_DETECTION单输入调用，2样本可选工具全关/仅Platon/全开3场景26任务通过；分类器为明确CLI observer、下游为真实原生R。证明tuple/样本连接，不能认证PLASMe/PlasX真实输出格式、模型或DB |
| PlasX消费者 | TA-023已验证：原生R及原wrapper验证官方两列表、严格>0.5、负分保留与17位精度；TA-025注释/模型生产者仍未决，不是完整PlasX或科学效果认证 |
| PLASMe适配待验证 | TA-024/053 ready：固定上游输出writer AST（受控candidate/BLAST hit）+原module/R消费者7场景16任务通过，原始FASTA/report校验与发布、gzip/GZ、缺文件/错误传播已检查。完整分类器/模型/DB/P3及平台仍未执行，不计verified |
| 当前downstream连接 | 删除SCAPP后ABRicate路由6场景8任务observer回归通过；不是真实CARD搜索或完整平台认证 |
| 已验证局部修复 | TA-043/045/048/037/047/044/042/041/009/022/023/028/008/030、TT-008及Recycler TA-002/003/004/051/052；各批receipt保留代码/输入/环境和限制，不扩大验证范围 |
| Recycler | 真实锁定minigut原P3工作流原生4任务通过：同图317参考、k55、1条1871bp图自环序列；k33/k55受控阳性、0边显式状态、BAM/BAI/hash拒绝和失败传播通过。SCAPP移除后只改变SPAdes注释并保留上游SHA/差异；完整Illumina/hybrid/镜像/框架与科学准确率仍未认证 |
| RGI数据库修复 | TA-028 verified：RGI6.0.8实际完整CARD3.3.0/3.2.8，原成功错用global导致VIM-77报VIM-2；改为同任务local且JSON/loaded hash/版本一致。6原生叶任务（含1预期失败）和2实际downstream任务、6方法通过；默认真实质粒与独立上游参数oracle分开。非镜像/nf-test/完整平台/临床准确率认证 |
| 其他真实节点 | QUAST5.3.0 native对锁定pUTI89 plain/gzip指标和同序列reference通过；Bowtie2固定版本四个调用点22原生任务符合独立受控真值；不是完整平台或minimap2认证 |
| MAG路由与DAS导出 | TA-008/030仅局部verified：用户明确多分箱器必须显式DAS，单分箱器直连；13 observer场景201任务/native R检查样本/分组/成员/序列/数量，真实DAS1.1.7官方完整gut样本导出15个独立预期bin且逐条DNA一致。最终阳性直接使用生产参数；真实无达标bin依上游主动失败并无部分发布。45 main+8直接include拒绝检查通过。TA-031/032/049和新增TA-054自定义DB选项仍未决；不是完整MAG/质量/分类/平台认证 |
| 五个平台/科学结果 | Illumina/ONT/HiFi/hybrid/assembly无当前完整成功E2E认证；跨样本实体、计数单位、TETRA、报告屏障等问题仍需修复验证；P1/P2/P3/P4完整工具/环境/DB与科学基准待完成 |

SCAPP退役前的重建序列接入实验已撤销；候选实体不同导致的投票方法问题保留在历史调查中，不再作为当前待实施方案。结果兼容性：删除共识表scapp列；曾选择SCAPP的调用必须移除该项并在新输出目录重跑，不与旧SCAPP共识结果直接混合。

M0动态配置/完整channel图/历史证据归属及默认真实基线尚未闭环；M1首批、M2核心、M3扩展与M4平台验收继续按原计划进行。退役有明确用户授权，并保留历史分母和失败证据。
