# MOB-suite recon 3.1.9资源读取调查

本批为源码边界验证，**未安装或运行原生MOB分类、未接入生产资源身份、未接受TA-091**。41资源对仍38候选/3pending。用户禁止病毒元素，原MOB vendored病毒fixture不允许运行，后续应迁移到细菌数据；本批没有下载任何序列、DB、taxonomy或模型。

## 固定来源

固定tag3.1.9对应提交 `eb86064884338c9ec19c19b4043aaa7ea1c9361b`。只获取mob_recon.py/utils.py/constants.py/mob_init.py/version.py/config.json和tag JSON，六个文件经tag与不可变提交URL逐字节核对，hash保存在tests/mobsuite-readset.lock.json。浏览器缓存先返回1348行mob_recon，而直接下载并核对不可变提交为1491行；缓存渲染不作为实现依据。

源码：[mob_recon.py](https://github.com/phac-nml/mob-suite/blob/eb86064884338c9ec19c19b4043aaa7ea1c9361b/mob_suite/mob_recon.py)、[utils.py](https://github.com/phac-nml/mob-suite/blob/eb86064884338c9ec19c19b4043aaa7ea1c9361b/mob_suite/utils.py)、[mob_init.py](https://github.com/phac-nml/mob-suite/blob/eb86064884338c9ec19c19b4043aaa7ea1c9361b/mob_suite/mob_init.py)。

## 已验证的选择行为

`tests/run_mobsuite_readset.py`只编译执行原AST中的parse_args、default_database_dir赋值和main资源路径选择片段。verify_init为明确记录调用的observer，不执行初始化器；未导入MOB科学依赖、打开任何FASTA、建立DB、联网或调用外部科学程序。19个路径场景及一个未知参数拒绝通过，不能称19次原生科学/资源探测运行。

- 默认目录为实际package constants.py相邻databases。此分支采用八个逐项参数：plasmid_db、plasmid_mob、plasmid_mash_db、plasmid_replicons、plasmid_meta、repetitive_mask、plasmid_mpf、plasmid_orit，并调用verify_init。
- 显式 `-d` 指向其他目录时，原程序改用该目录内约定文件名，忽略以上逐项覆盖参数；路径先abspath再作字符串比较，不作realpath统一。本驱动直接执行原分支而非重写选择表。
- taxa.sqlite和host_range_literature_plasmidDB.txt仍取自最终database_dir；前者在阳性质粒宿主范围报告分支会交给ETE3。资源身份不能只hash八个FASTA/sketch。
- 可选filter_db和genome_filter_db_prefix在解析器中保留；后者还涉及实际BLAST卷/别名及.msh。仅glob同名前缀不等于完整实际读取集合，后续应按实际BLAST解析验证。

## 原生前置条件与待完成范围

原verify_init在status.txt不存在时调用mob_init；初始化器会下载数据库并创建ETE3 taxonomy。因此科学任务内隐式准备不符合已固定资源验收边界。代码中的“bundled DB”注释已改成真实的环境DB/可能自动初始化；**注释不是已实现的运行时门禁**。

后续必须先具备可核对来源且满足禁止病毒元素约束的完整资源集合，独立准备并验证status、FASTA/BLAST/sketch、clusters、literature和taxonomy，禁止科学执行时下载/更新。不要下载未审核内容的默认DB/全量taxonomy，也不要用虚拟DB/删减科学范围制造原生通过。若必需数据含被禁止元素，则跳过该真实执行，记录未完成，继续其他工作。

仍需实际固定3.1.9包环境与归档/source核对、完整DB内容约束核对、实际二进制/动态依赖、过滤库的写入/建索引语义与ETE3更新行为、两别名生产probe/上下文/identity join、缓存变异/恢复/坏资源、原生阳性/细菌阴性及nf-test/OCI/provider验证。原病毒测试不得因“恢复原覆盖”被执行。此前发布测试是输出协议observer，不证明原生MOB推理。
