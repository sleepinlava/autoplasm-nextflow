# GTDB-Tk 2.7.2 输入适配及标准流程调用

2026-10-23。TA-031的文件选择修复为ready，完整真实数据库分类未验收；新增TA-076只按已移除CLI参数的有界修复verified，不能据此放行整个分类节点。

## 固定依据与两项差异

目标为模块声明的GTDB-Tk2.7.2，官方tag指向提交 `f17decef1f9d9cf5b4d31fd21f5c9d32d813abdc`。实际Bioconda环境57包全部锁定并核对压缩包SHA256/MD5；安装后70个Python文件与官方Git blob完全一致。环境和两条真实来源染色体锁见 `tests/gtdb-input-native.lock.json`。Conda解析出的NumPy2.5.4/DendroPy5.1.1与上游setup.py约束不同，单独记录；本批只验实际Conda的输入边界，不外推pip栈或完整模型兼容性。

官方 [cli.py](https://github.com/Ecogenomics/GTDBTk/blob/f17decef1f9d9cf5b4d31fd21f5c9d32d813abdc/gtdbtk/cli.py) 默认extension=fna；[main.py](https://github.com/Ecogenomics/GTDBTk/blob/f17decef1f9d9cf5b4d31fd21f5c9d32d813abdc/gtdbtk/main.py) 的 `_genomes_to_process` 按后缀选择文件并据此生成genome ID。上游分箱器的`.fa.gz`、`.fa`不会自动进入默认集合，混入`.fna`时还能成功但只分析部分bin（TA-031）。

本地配置另传`--skip_ani_screen`，而固定2.7.2实际CLI不再接受它；真实入口退出2，报unrecognized arguments，先于读取输入（TA-076）。用户明确选择2.7.2官方标准流程，包含ANI预筛选，因此单独删除该过期参数；未用`--genes`伪装核酸输入、降级版本或改写上游程序来跳过ANI。标准CLI现在通过参数解析，实际入口到达未配置真实DB的保护并退出1；这不算成功分类。固定上游控制流在普通核酸、无既有完成阶段时运行ANI预筛选，`place_species`仍为官方默认false。旧跳过ANI的运行与新标准流程可能不可直接比较，须按方法变化记录并重算相应结果。

## 输入与输出契约

模块在任务内将所有声明的FASTA bin转换为私有`gtdbtk_input/<原stem>.fna`，并显式最后指定`--extension fna`。`.fa/.fna/.fasta`及gzip后缀均忽略大小写；gzip解码后保留原FASTA全部字节，plain直接复制，不改header、序列、记录边界或genome stem。最终bin通道、CheckM2和宿主关联仍使用原生产文件；私有格式适配仅供GTDB输入。

所有输入先检查再写结果；重复stem、GTDB不允许的ID、未知后缀、非文件、坏gzip、空/非FASTA和错误空目录明确失败，不能静默少读。全无bin的样本不进入任务。精确相同的任务重试可复用私有文件；有额外/不同残留则拒绝，避免混入旧bin。输入目录不可被输出或manifest覆盖。成功时发布`<sample>.genome_inputs.json`，记录每个原文件/目标名/ID及压缩与解压字节的hash和长度；它不声称分类正确。stub输出明确标为stub_not_validated。

## 验证与限制

9个独立单元方法检查原始字节/ID保留、混合格式、大小写、重复/非法ID、坏压缩、空输入、异常文件、源保护及重试残留。接口回归使用已锁定OPERA归档中NC_013656.1、NC_019427.1的完整真实染色体；人工样本/文件副本不计独立生物重复。

原模块实际Nextflow执行，调用已安装且未改写的GTDB2.7.2完整CLI parser和完整`_genomes_to_process`方法，并由其FASTA reader检查DNA。**OptionsParser构造器被绕过，参考ID名册是明确的接口fixture；未运行任何taxonomy模型。** summary中的分类值始终是`INTERFACE_OBSERVER_NOT_TAXONOMY`，只用于验证输入ID传递。旧混合后缀3个bin只选择`.fna`一个、旧全`.fa/.gz`直接失败均复现；新代码全部ID/字节/DNA正确，固定fna不受ext.args另给gz影响。重复、坏压缩、废弃参数及显式工具失败均传播，失败任务不发布部分结果；空样本0任务。10唯一场景的选定正式配置重放共12trace：5COMPLETED（其中1个是预期旧漏读反例）、2CACHED、5预期FAILED；此前有效CLI重放与初始过期参数失败保留，不增加独立场景分母。

原MAG_HOST与宿主关联的7场景/93trace（91完成、2预期失败）回归通过：单个MetaBAT2/CONCOCT/SemiBin、多分箱+DAS、部分无bin、关闭和工具失败。合成分箱/质量/分类器observer、真实CONCOCT I/O/DAS转换助手和实际R关联各自标明，不称为真实分箱/分类模型。GTDB输入文件名oracle按新格式更新，但所有bin成员DNA/metadata/下游宿主ID真值保持；CheckM2及最终bin名仍按原文件核对。

当前9配置文件的12个既有profile场景已重放，确认GTDB空ext.args及引擎/资源声明一致，0分析任务；不新增场景分母。完整参考数据要求r232，官方安装资料约100GB而本地仅约66GB可用，因此没有用伪造/裁剪数据库冒充分类验收。真实marker、ANI、placement、最终taxonomy ID/数量、镜像、nf-test及完整平台仍未验；TA-031继续开放，整体模块仍investigating。

原始材料：`results/tool-audit/20261023-gtdb-input/`，正式输入回归`native-interface-standard-config/run.json`、直接真实CLI`direct-cli.json`、MAG回归`mag-regression-runtime-path/run.json`、环境`runtime-proof.json`。最初MAG回归因调用环境缺少nextflow路径在任何分析前停止，日志保留；提供已锁定运行时PATH后重放，不算生产故障。正式来源和两份分开的补丁见该批receipt。
