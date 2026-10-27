# SemiBin 环境资源身份候选契约

TA-091仍为S0未决；本页仅记录工作区候选，不改变正式718项来源清单或99/2/4结论。汇总见 [证据](../evidence/20261026-semibin-runtime.json)，完整运行在 `results/tool-audit/20261026-semibin-runtime/`。

## 实际接线

生产模块新增 `SEMIBIN_RESOURCE_PROBE`，在所声明的同一Conda/容器目录中每次执行，`cache false`；按样本暂存FASTA/BAM。它使用固定2.4.1原生参数解析器、训练模式选择函数及环境模型路径函数，读取实际展开后的参数。身份包含默认marker、包内Python源码、已选预训练模型、显式核酸/BAM/覆盖/蛋白/分类表覆盖输入，以及半监督所需已准备GTDB目录的所有sidecar。目录递归记录字节/权限/成员链接，断链、循环或特殊文件失败。

`MAG_HOST`按完整样本meta关联新身份及receipt，再调用消费者。消费者脚本闭包在缓存查找前比较实际Conda、容器、引擎、accelerator、beforeScript、环境module、containerOptions及ext.args/args2/prefix；不同的按名字覆盖会明确拒绝，不借用另一个环境的探测结果。自定义配置应对 `SEMIBIN|SEMIBIN_RESOURCE_PROBE` 使用一致选择器。探测的`cache false`是部署不变量；复制模块的task.cache实验未验证成功，没有将该实验钩子放入生产。

消费者校验当前资源和解析参数后，以同一份argv直接exec `SemiBin2`，避免再经一次shell展开。科学算法、原生默认自训练15epochs及工具模型选择保留。CPU数已出现在科学脚本缓存键中，因此探测解析值不以CPU配额作为资源变化；相关实际参数仍由工具接收。资源须在探测至任务结束期间不可变；本实现不提供跨文件事务快照或跨主机部署一致性证明。

半监督模式若需要GTDB，须先在相应环境准备选中的原始参考（`SemiBin2 download_GTDB --reference-db PATH`）；缺少时在缓存查找前拒绝，不能让未记录数据库在科学任务执行中才下载出现。这是资源准备契约变化，不是另选数据库或改训练方法。

## 已取得证据

- 当前模块8阶段14条trace：探测8个COMPLETED，科学消费者2个原生COMPLETED、3个CACHED、1个坏HMM预期FAILED；两次参数/容器不一致控制只完成探测，消费者未提交。
- 另6个运行上下文控制：Conda、beforeScript、环境module、容器选项和accelerator分别不一致均在查缓存前拒绝；匹配GPU声明的控制仅运行stub，不代表GPU环境启动或推理。
- 当前状态回归6场景10条trace，含冻结原模块、当前原生正例/有效零bin、缓存、stub、原生解析器错误；checkpoint可安全加载且参数有限，bin完整DNA/成员/指标独立核对。原驱动的控制台计数标签已修正，单行展示变化的执行源码/当前源码桥接另存，未为文字变更重算神经模型。
- 8个原生参数/读取集合单元方法通过；预训练路径调用原解析函数并散列真实模型，但没有据此声称预训练推理或假GTDB分类通过。隐藏换行sidecar等长同mtime变化、缺失GTDB、符号链接/特殊成员和外部蛋白覆盖另列控制。
- 生产MAG/宿主路由18场景通过：270个COMPLETED、2个预期FAILED，分箱/质量/分类及资源扫描是明确observer，R/转换器真实；不当作MAG模型推理。
- nf-test两例最终通过。原固定nf-core提交的数据含449个被特征化contig及3个BAM，原生15epochs完整计算得到70个bin。早先Path.name/Path.fasta断言API失败保留；修复为标准Path和独立FASTA读取器并加强完整DNA核对。最终框架运行复制完整冷cache/history、按精确UUID恢复，同一科学任务哈希和原workdir被复用；探测仍实际完成。不能把这次CACHED计成新的神经执行；stub另记。

数据取自固定提交 `618f1541382c4ad49eff566dadf13d5ccbd0ebb4` 的原文件，4份原始输入的URL/字节/SHA保存在 `framework-data/download.json`，未缩短或替换fixture。它们是软件契约数据，不是3个独立生物重复、真实shotgun P4或准确率真值。所有失败、初始64GB资源限制、未拷贝history的恢复失败及观察器参数解析失败都保留。

## 尚未完成

其余6个隐式环境消费者尚待接线。SemiBin的FragGeneScan1.32可选分支现有下述限定验证；其他ORF/可执行文件读取集合（含Prodigal/hmmsearch）、完整环境、可选模型/GTDB原生验证、when和自定义部署配置、GPU/OCI/多主机/provider仍未完成；工作目录receipt也未形成完整最终报告来源（TA-016）。固定数据上的模块/路由/框架通过不能替代默认真实基线、完整MAG队列、全平台、真实shotgun P4或AWS验收。


## 可选FragGeneScan实际资源补齐（第七份候选）

最新[候选证据](../evidence/20261026-semibin-fgs-runtime.json)与原批收据分别冻结保存。固定2.4.1的orffinding.py直接通过shutil.which调用FragGeneScan二进制，参数-w0/-tcomplete，并不调用Perl wrapper。1.32的C源码按调用argv0截去FragGeneScan名字后定位train/，读取gene、rgene、noncoding、start、stop、stop1、start1、pwm与complete。新身份仅在--orf-finder fraggenescan且无外部蛋白覆盖时加入：实际调用路径、二进制内容、完整17文件train目录、固定模型complete/w0；不先resolve符号链接。缺少二进制或任一9个必需训练文件，在探测阶段拒绝。默认fast-naive和外部蛋白覆盖不新增FGS依赖，也未换成ISEScan的illumina_5。其他FGS版本的读取布局未据此认证。

本次从已核实归档SHA的FragGeneScan1.32安装复制独立二进制和17文件train；17个训练文件与固定原始源码归档逐字节相同。上游C/Python源码、包URL/hash及来源锁见results/tool-audit/20261026-semibin-fgs-runtime/readset-source.json，归档锁沿用tests/isescan-native.lock.json，不重复下载。生产运行仍使用实际SemiBin2.4.1解释器/PATH；驱动的独立FASTA解析使用已有含Bio的ISEScan解释器，不将其当SemiBin依赖环境。

最终10阶段19条trace：13 COMPLETED（9探测+4科学消费者）、5 CACHED、1缺少complete模型的预期探测FAILED（无消费者提交）。完整原始40contig/800000bp+原BAM不裁剪，默认自训练15epochs、seed0、CPU；保留用户可选FGS模型complete/w0。complete及共享gene训练文件的空白字符等长同mtime变化保留全部数值token，二进制仅变更非分配.comment段；均导致消费者重跑，还原精确复用原冷任务哈希。四个原生阳性检查完整bin DNA/非重复成员/状态及checkpoint，原生run_fraggenescan适配器完整输入FAA/FFN/GFF与固定原始二进制直接输出逐字节相同。它们是软件契约对照，不是准确率真值。18个私有文件最终与原安装逐字节还原，原安装未修改。另用真实二进制与生产resolver验证含空格的调用别名路径：目标原目录有train也不能替代别名目录train；缺少时两者均拒绝，加入明确train链接后两者通过，完整FAA/FFN/GFF与原输出一致。四个直接调用控制单列，不加入Nextflow19条trace。

11个当前单元方法包括前8个方法及新增3项FGS读取集合方法；FGS布局为明确observer，只检查条件/别名/缺失/等长mtime身份，不冒充模型计算。9条执行源码比较均直接匹配；七份顺序补丁对131个候选路径精确正向字节/权限、反向HEAD字节核对，当前749项快照与正式718项清单分离。未再次执行无改动的路由/框架/ISEScan批次，也不将旧批测试计作新执行。

首次驱动两次缺Bio在Nextflow启动前失败；修正解释器后原生15epochs完成，但驱动错误假定临时markers.hmmout会保留。该失败及旧驱动保存于attempts.json/before-assertion-fix；改为checkpoint与独立原生ORF输出对照后新批完整通过。随后缺模型测试重建文件未还原775权限，变为644；身份正确导致重跑，驱动缓存预期失败。修复为同时还原字节/权限/mtime后native-v3全组验证；18个私有文件的权限也逐一核对。未把失败批的冷计算累加进最终4次阳性。

TA-091仍S0未决；外部Prodigal/hmmsearch及完整Python/系统共享库身份、完整可选模型/GTDB推理、GPU/OCI/provider/when/部署、最终报告完整来源仍待完成。本批不改变正式99/2/4，无提交/推送/AWS资源/上传/收费。
