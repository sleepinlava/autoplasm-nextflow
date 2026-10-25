# Platon1.7 完整数据库与真实节点

2026-10-24。[官方v1.7](https://github.com/oschwengers/platon/tree/3cce2dd295348e25be4b5bd64f3622c2603d6ba0)固定提交 `3cce2dd295348e25be4b5bd64f3622c2603d6ba0`，完整79个Git blob校验；安装的7个Python文件逐字匹配。完整[官方数据库v1.5.0](https://zenodo.org/records/4066768)的公开MD5为 `6712717fedea5819ef0d63d7b2460fa4`；下载归档1,690,687,855字节、SHA256 `68e6875b4a75fe156aa694e6baf1634c91f6b254e7945a6b56906d021edfeb9f`，31个文件共2,899,290,072字节，未裁剪或重建索引。逐文件身份、源码、85个Conda包SHA256/MD5见 `tests/platon-native.lock.json`。

## 已证实的差异

- TA-005：冻结HEAD包装器把真实gzip pUTI89直接交给原生1.7，plain-text SeqIO解析明确失败。当前私有解压保持原字节，plain/gzip/GZ和原始nf-test gzip产物均验证真实分类器结果，而非ASCII输入观察替身。
- TA-082：原数据库目录path输入按目录元数据缓存。原生基线完成后，只替换私有 `replication.h3m` 一个字节、保持大小和mtime，旧节点仍CACHED；当前显式目录加递归文件列表/deep缓存能重算。原始完整数据库不被改写。
- TA-083：上述损坏HMM触发实际hmmsearch失败，但上游警告后返回，原包装器仍COMPLETED/exit0。上游也不读取ThreadPoolExecutor的future异常。当前审计子进程退出和future异常，分析错误阻止结果发布，不伪装成无检出。记录保留原生参数、命令、返回码和失败stderr。
- TA-084：所有记录小于1000bp或不小于500000bp时，原生合法exit0但没有结果文件，原包装器随后的mv失败。当前仅在确认真实exit0、全部记录均被固定长度域排除且没有半成品时，写兼容空表/空阳性FASTA/空JSON，并明确 `not_assessed_length_filter`；不是已评估阴性，不造染色体FASTA。空FASTA、损坏输入和执行错误仍失败。
- TA-085：原 `platon>=1.7` 没有可重建的依赖边界；实际1.7包可求解到DIAMOND2.0.6，但原生CLI会拒绝低于2.0.14。旧README也列有过时下限。本批按固定源码的实际要求使用明确依赖和Linux64锁，验证全新Nextflow离线Conda部署；不声称默认无约束求解必然选中坏版本。
- TA-086：四个批量HMM函数在零命中后引用只在命中分支赋值的contig，导致被上游丢弃的UnboundLocalError。严格future审计在真实pUTI89首次运行中揭示此问题。只把四条末尾汇总log改为已有hits计数，内存中编译并替换这四个函数；原安装文件及包缓存硬链接不改写，原/有效源码SHA和完整diff入运行记录。搜索命令、命中解析、RDS、阈值和分类代码不变，不全局忽略异常。

## 方法与输出

继续默认accuracy和生产 `--meta` 模式。RDS为分布分数，不是概率。Python3.10.14、BioPython1.81、Prodigal2.6.3、DIAMOND2.0.14、BLAST2.12.0、MUMmer4.0.0rc1、HMMER3.3.1、Infernal1.1.4及其85包构建均固定；未跳过数据库或子分析。上游在RDS过滤后可能对空蛋白文件调用HMMER，只有明确的 `hmmsearch ... proteins-filtered.faa` 且该文件真实0字节被记为无查询、无注释证据；不把任意失败豁免。

`platon_checked.py`严格核对原生TSV的14列表头、唯一ID、长度、源DNA、计数、RDS舍入与详细JSON，阳性FASTA/JSON/TSV集合必须一致。常规非阳性FASTA必须与原始记录构成完整分区，但该上游文件名不代表每条序列有独立染色体真值。重复ID在原生调用前拒绝，避免上游字典覆盖后重复FASTA；损坏gzip在任何子工具前失败。原始基因、模型分数与序列不被重写来求通过。

发布原有 `<sample>.platon.tsv`、`<sample>.plasmid.fasta`，另发详细JSON、`platon_state.json`和`platon_runtime.json`。状态区分 `plasmids_found`、`no_plasmids`、`not_assessed_length_filter`。meta完整沿tuple输出；源码助手内联在任务命令中参与缓存。数据库根目录保留原结构，单个文件另列内容依赖，支持同路径/大小/mtime下的变化识别。

## 验证及限制

在完整数据库上直接运行原CLI和检查包装：pUTI89阳性、未修改的官方无质粒fixture无检出；两者修复前后TSV/阳性及非阳性FASTA字节完全一致，详细JSON语义完全一致。四处日志修复不是改变结果的方法调整。8个单元方法验证真实子进程失败、future异常、空查询边界、仅四条日志变更、ID/DNA/模式状态与半成品拒绝；首轮diff测试把hunk中的同一return误算作源码变化，失败记录保留后修正断言。

真实输入传输2个方法（3个阳性技术变体+1个损坏gzip任务）；实际nf-test0.9.5原P3文件2用例通过native overlay（静态backend-podman标签不作为后端证据）。独立原/当前节点验证内容缓存、实际损坏HMM、长度域、重复ID、空channel和新建锁定Conda环境；任务数和失败/缓存/取消均按receipt实际trace分列。DETECTION三场景使用明确分类器/Platon审计入口观察替身，仅原工作流连接和R消费者为真，不能认证分类器或本运行器。

pUTI89所有plain/gzip/Conda/nf-test重放是同一个生物阳性，且可能属于数据库训练参考；官方阴性软件fixture不是独立实验真值或检出性能基准。没有改变共识投票规则。镜像、完整Illumina/HybridSpades平台、全部P1或科学敏感性/特异性仍未认证。旧缓存与含子工具警告的历史结果应在新目录重算，不能将新状态表与旧发布目录混合作本次结果。证据：`results/tool-audit/20261024-platon-native/receipt.json`。
