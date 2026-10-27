# 测试资源清理

用户于2026-10-24将及时清理已测模块中间文件和不再使用的软件加入完整审计目标。每批完成后，保留来源、锁、命令/退出值、输入身份、最终产物、日志/trace/JUnit、反例和必要原始证据；清理可重建的重复参考/模型、已解包下载缓存、废弃负例环境及无需再用的临时工作数据。

删除前核对明确路径、活跃任务及后续验证依赖，不能只按文件年龄清理。目录符号链接不作为递归删除目标；核对所有 selected-artifacts.json 和 receipt 的显式哈希索引，防止删除固定证据。不改写旧 receipt 以掩盖已清理资源：以独立清理记录说明历史资源何时移除、如何重建以及当前保留的主资源。

2026-10-24 第一批见 results/tool-audit/20261024-cleanup-1/cleanup.json。已删除PLASMe已解包ZIP缓存、四份HOTSPOT旧模型覆盖目录、Platon故意欠配依赖的负例环境，以及PlasX完整重建验证的重复下载/参考副本。原始完整主数据库/模型、当前需要的环境、所有显式哈希索引证据、重建证明和中断搜索结果保留。实际文件系统可用字节增加24,847,663,104（约23.14GiB）；不能用被删除文件的逻辑总字节代替物理释放量。

PlasX重建receipt是历史成功准备证据；其中重复大文件已按清理记录移除，不能再声称这些已删除路径当前可用。后续分析使用保留的主参考目录，或按 tests/prepare_plasx_resources.py 和固定锁重建。

第二批见results/tool-audit/20261024-cleanup-2/cleanup.json：完整原生和nf-test验收后，删除已完成缓存控制的私有模型及重建测试的重复源码/模型；主源码、全库和所需环境保留。逻辑删除395986900字节，观察到可用空间变化119549952字节，后者可能受同时系统活动影响。MOB发布回归另在核对后删除两份私有work并保留task证据，最终copy产物仍完好。历史准备/缓存命令中的重复路径已不再可用，可从锁与主资源重建，不能当当前运行资源。

可选分箱环境恢复后的清理见 `results/tool-audit/20261024-optional-binning-native/cleanup-unused-genomad-prefix/cleanup.json`：完整官方PlasMAAG测试及独立产物核验通过后，移除不再使用的第一份geNomad1.11.1前缀；当前实际使用其Snakemake部署的同版本锁定环境。原163包校验、远程/本地锁、全部Conda元数据、入口和删除文件SHA清单保留，完整源/模型/DB及原始归档保留可重建。逻辑文件约4.11GB，观察到文件系统可用空间增加661626880字节（约631MiB）；硬链接仍可被包缓存使用，不能宣称物理释放4.11GB。该旧前缀的历史验证路径现已删除，当前运行应使用清理记录的replacement_in_use。

## 2026-10-25 PlasMAAG已完成独立原生中间文件

完整原生、生产cohort、框架及contigs模式的最终产物检查通过后，清理 `20261024-optional-binning-native/plasmaag-official-native-v2/native/out/intermidiate_files/`。删除前保存121项原始文件/链接身份、大小、SHA及完整清单；保留日志/配置文本、geNomad aggregated 表、原始fixture/source/锁/DB、完整最终结果、子程序失败与恢复记录，以及其他生产/框架work目录。清单和删除结果见同批 `cleanup-plasmaag-standalone-intermediates/cleanup.json`。

该目录逻辑文件大小1,859,112,273字节；保留诊断文本并考虑共享文件后，实测空闲增加981,241,856字节，不能把逻辑大小当物理释放量。正在运行的新部署验证资源未清理。

完成当前实际框架环境验证后，另移除仅供安装证明的 `plasmaag-remote-pin-probe-v2` 前缀；保留48,617项文件/链接身份清单、完整163包元数据、CLI/模型核验、原始归档/哈希锁和实际使用中的新嵌套环境。逻辑4,106,702,522字节，实测空闲增加658,415,616字节。证明见同批 `cleanup-plasmaag-deployment-probe/cleanup.json`；未删除活跃的私有归档缓存或新框架环境。


## 2026-10-26 已被最终验证取代的ISEScan私有环境

用户再次明确要求清理不再使用的数据库/模型/原始数据/中间产出/日志后，核对三个已终态、已还原、已被native-cache-v6取代的native-cache-v3/v4/v5私有安装。共删除46,746个普通文件、4,122个链接；全路径/类型/权限/mtime/逐文件SHA或链接文本保存在`results/tool-audit/20261026-cleanup-3/deleted-env-files.ndjson.gz`，83包元数据及各自锁另保留。删除前审查receipt/selected-artifacts显式路径+SHA索引，无所选固定产物；最新ISEScan收据的所有直接产物SHA删除前后复核一致。

删除逻辑普通文件4,064,656,248字节；实测文件系统可用字节增加1,635,164,160（约1.52GiB）。这是删除窗口观察值，不能把逻辑大小当物理释放量。保留主ISEScan环境、最终native-cache-v6私有环境、完整原始fixture、当前主模型/数据库、所有固定日志/trace/JUnit/反例/最终产物和83份原始包归档。历史v3/v4/v5的private-install路径现已不存在，旧收据未改写；可用各自保留native.lock、原始包归档与主资源按原路径重建并核对逐文件清单。详见同批`cleanup.json`、`reference-index-review.json`和`retained-runtime-metadata/`。

这不是按年龄或文件扩展名全仓库清理。PlasmidFinder修复后另评估其不可运行的Python3.15环境；其余大型重复模型/旧中间结果继续按依赖与证据核对逐批处理。


## PlasmidFinder失效Python3.15私有安装清理（20261026-cleanup-4）

实际2.1.6因distutils导入失败的未约束Python3.15安装，已被完整上游阳性/生产模块验证通过的Python3.10安装替代。仅删除 `results/tool-audit/runtime/plasmidfinder-2.1.6`，保留 `plasmidfinder-2.1.6-py310` 及其中完整打包数据库；没有删除新的DB或原始fixture/原始包归档。旧历史命令路径已不可执行，历史记录原样保留。

删除前保存17,430普通文件的SHA256/大小/权限/mtime、1,294原始符号链接和1,724目录到compressed NDJSON；保存84包conda-meta、显式linux-64.lock，逐一验证保留的84归档SHA256。检查compact证据索引及一/二层receipt无该新prefix的固定产物引用，验证当前原生执行来源与正式清单哈希。

逻辑普通文件1,283,557,363字节，allocated blocks1,325,998,080字节；可用空间实测增加502448128字节（观测窗口约0.61秒）。后者不是可保证独占物理回收量，受共享硬链接和同期文件活动影响。清理后正式718清单不变，可用py310安装和原生证据保留。`results/tool-audit/20261026-cleanup-4/cleanup.json`、plan、reference-index-review、retained-archives、retained-conda-meta和完整清单为权威记录。


## 被成功重试取代的PlasMAAG失败任务BAM清理（20261026-cleanup-5）

仅删除 `20261026-resource-consumers/plasmaag-native` 超时失败任务assembly_mapping_output内6份生成BAM/排序BAM/BAI。该轮原生Torch multiprocessing resource_sharer PermissionError并超时，scientific_result_accepted=false；独立 `plasmaag-native-v2` 完整成功及缓存控制仍保留。未删除原始reads/assembly、软件副本、FASTA、最终成功产物或任何日志/trace/失败记录。

对compact证据、各批receipt及递归JSON产物引用共2160个JSON核对，无这6个路径的固定产物引用；保存逐文件SHA256/大小/权限/mtime/allocated blocks，删除前后重新核对最新453项固定证据与正式718清单。权威路径/哈希为 `results/tool-audit/20261026-cleanup-5/plan.json`、reference-index-review.json、cleanup.json。

逻辑普通文件1,779,612,564字节，allocated blocks1,779,625,984字节；实测可用空间增加550785024字节（窗口约0.28秒），不是保证独占物理回收量，受硬链接和同期活动影响。保留的是删除文件哈希和元数据，不是原BAM字节；旧私有失败attempt不能再依赖它们resume，重建需原始输入/环境。不能把该失败轮当科学成功，成功证据来自保留的v2。


## 被实际Nextflow wheel环境取代的旧MOB软件prefix（20261026-cleanup-6）

仅删除旧独立 `results/tool-audit/runtime/mobsuite-3.1.9` 软件基线prefix；不含生物数据库或科学结果。新prefix见 `20261026-cleanup-6/cleanup.json`，两份生产YAML实际Nextflow4轮共用它，保留其全部环境和成功证据。179依赖构建与旧180包除mob_suite外完全一致；16Python代码/10随包FASTA字节在新环境保留，实际MOB/numpy/pandas/scipy/ETE3 import都来自新prefix。

保存37,844普通文件/2,036原始符号链接/5,055目录的完整压缩清单（模式、mtime、SHA、硬链接数或目标），180conda-meta、显式锁、180归档哈希。2194个JSON索引及递归引用核对，没有固定选定产物路径/hash绑定在目标内；历史命令路径单列。删除前后最新55固定产物与正式718清单核对不变。

逻辑2,112,274,204字节，allocated blocks2,203,824,128字节；实测可用空间增加79757312字节，窗口约0.64秒。大量文件共享硬链接，逻辑字节不能当物理回收；该delta也受同期活动影响。旧prefix命令现不可运行；完整清单保留哈希/元数据、不保留原文件字节，重建须用旧180包锁/保留归档并跳过原mob_init post-link。所有原始输入、模型、最终环境、receipt/log/trace和source locks保留。


## MOB入口guard发布回归的私有work清理（20261026-mobsuite-execution-guard）

publication-v1由测试驱动在保存.command脚本/运行器/输出/退出值/observer.json到task-evidence后，删除本测试私有work和cold-work。所有最终逐样本/阶段发布副本仍按原SHA核对且可读。12条trace含输出协议observer和缓存，不是科学样本；新内部准备JSON不作全量资源来源receipt。空间回收未测量，不新增虚构字节数。真实负例/框架/主流程日志、完整原始细菌输入和保留的最终软件环境均保留。权威结果为 `results/tool-audit/20261026-mobsuite-execution-guard/publication-v1/run.json`。


## 不适用Medaka科学阳性的候选输入及重复解压参考（20261027-cleanup-7）

固定nf-core test-datasets原始10.3MB FASTQ下载后完整审查1000条read名称：494个NC-000913.3、506个NC-006347.1，所有comments为空；不能证明真实ONT，也不是保留B.fragilis FDAARGOS_1225参考的已知匹配输入。未做科学抛光，不将参考回填或N控制当真实阳性。删除该未使用候选FASTQ和重复解压的5.3MB参考，原完整参考gzip、软件/模型、来源/tree/SHA/审查/下载脚本、全测试诊断均保留。

逐文件大小/权限/mtime/SHA及删除计划见 `results/tool-audit/20261027-cleanup-7/plan.json`、cleanup.json。2585个递归JSON索引无既有固定产物路径引用，前批74固定证据与正式718清单不变。第一次核对因本轮已明确修改的Medaka测试不再等于旧source snapshot而提前拒绝、没有删除；随后绑定第19顺序候选补丁的精确往返证明，仅允许该已知来源差异，其余核对保留。

逻辑删除15,573,586字节，窗口内实测可用空间delta为0，不声明物理释放15.6MB。FASTQ正文不保留，来源调查如需重放须从固定blob完整重取并核对已保留SHA256/git blob SHA；原解压参考可从保留gzip无损恢复。后续仍须真实完整匹配细菌ONT案例，不因清理或候选控制通过而缩减验收范围。
