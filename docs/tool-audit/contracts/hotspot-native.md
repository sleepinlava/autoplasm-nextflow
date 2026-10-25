# HOTSPOT 原生推理、谱系转换和资源缓存

固定官方 [Orin-beep/HOTSPOT 0e3e3013](https://github.com/Orin-beep/HOTSPOT/tree/0e3e3013a6a29fbdadc8e58180c9eb259877ce99)，完整14个Git blob。官方 README 的公开数据库和模型各完整下载、校验及安全解包：数据库17文件273,686,908字节，模型19文件1,911,643,940字节。六层模型和元数据均保留；逐文件SHA256见 `tests/hotspot-native.lock.json`，原始记录在 `results/tool-audit/20261023-hotspot/`。

## 输出和方法

原程序使用 Python csv.writer 写出CRLF。旧AWK把末列 `-\r` 当作有效Species，或者把真实物种附上CR。`convert_hotspot_lineage.py`按TSV解析、严格核对七列表头、ID唯一性及来源FASTA（含gzip），仅从实际上游非空/非 `-` 的分类层级中选择最深者。没有分类的行不生成链接，缺失输入ID单独记录，不能视为阴性；结构正确的空表有效，畸形/重复/外来ID失败。标准六列链接的score留空，不把分类层级伪造成概率。

`host_lineage.tsv`保留原字节，另发布转换记录与运行记录。正常模式可能在树中沿唯一子节点继承分类，而该分类未必有分类器输出槽；测试核对固定labels、parent和树的唯一子节点规则，不错误要求每个继承分类都在对应labels里。

继续执行原始preprocessing.py和hotspot.py，固定CPU、正常模式，不改权重、特征、模型源码、MC-dropout或阈值。正常模式输出不能宣称“高置信”。上游无合格长度/无PC特征时会退出0但不写特征字典；适配器明确失败说明未执行宿主推理，不伪造生物学无检出结果。

## 运行库和缓存

102个Conda包按SHA256/MD5固定。Python3.10.14符合本项目要求；PyTorch1.12.1 CPU、NumPy1.21.6、Pandas1.3.5、BioPython1.81、bidict0.22.1、treelib1.6.1、DIAMOND2.1.4、Prodigal2.6.3、BLAST2.13.0、HMMER3.3.2等保持官方依赖版本，未靠升级推理库改变模型。生产module使用Linux64显式锁文件。

旧Torch库的GNU_STACK PF_X在本机glibc被拒绝加载。运行器只复制任务私有libtorch_cpu.so，清除GNU_STACK PF_X位，原始Conda库及可能的包缓存硬链接不变；运行记录保留前后SHA及偏移。解释器载入私有SONAME后清除LD_PRELOAD再启动原程序，避免给Prodigal/BLAST等子进程注入Torch。未改可执行代码或模型字节。不把这个Linux64兼容处理推广为其他平台认证。

三个实际执行的程序文件、数据库文件列表和递归模型文件列表为显式path输入，逐文件使用deep缓存。模型目录还作为原结构输入，完整保留六份嵌套label_info表；另一个初始仅暂存顶层模型的中间尝试被完整资源断言拒绝并保留，不算验收通过。内容改变即使路径、大小和mtime相同，也必须重跑；旧module仅在命令中引用params路径，会错误复用缓存。首轮修复把整个目录设为deep输入仍缓存了目录元数据，没有逐文件追踪内容；实际失败控制及该中间实现保留，最终改为实际文件列表。固定Nextflow26.10.0 HashBuilder源码亦确认只有regular file进入deep内容哈希。助手文本内联到任务脚本，修改助手也参与任务hash。程序核心三个源码hash必须匹配固定提交，避免声称未知源码已验证。

## 验收边界

13个独立单元方法覆盖CRLF、缺失分类、格式/ID异常、空表、gzip、私有ELF与资源指纹。实际完整原生直接运行官方四条序列，逐样本流程运行包括gzip输入、正常恢复、私有模型内容损坏、禁用/空输入及显式Conda锁部署。旧反例使用明确记录的ELF启动兼容层，只隔离系统加载问题；没有替代分类器或修改预测。首次原生流程因测试遗漏唯一子分类继承而失败的记录和脚本保留，不能计为通过。

具体完成数和状态以本批receipt为准。输入为官方软件示例，可能与训练集重叠；分类标签/层级、样本ID、格式、缓存和失败传播的验证不构成独立宿主准确率、宿主范围、阴性性能或科学基准。镜像、GPU、nf-test框架、AWS和全平台尚未认证。
