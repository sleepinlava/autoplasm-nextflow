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


## 废弃工具构建缓存与重复HOTSPOT模型/COPLA库（20261027-cleanup-8）

按用户再次明确授权，删除50个已确认不再复用目标：47个无当前安装环境引用的旧Conda包解压缓存（包括失效Python3.13/3.15、旧TensorFlow等构建），两份HOTSPOT私有测试模型目录，以及COPLA缓存试验的私有databases目录。没有删除任何已安装工具环境或唯一主数据库/模型。57个保留Conda prefix、1730个实际使用包构建参与核对；47份原始包归档全部保留并校验，历史旧解压路径不再存在，可从包归档重新解压。

两份HOTSPOT副本逐文件等于保留的20261023-hotspot/assets/models，COPLA私有库逐文件等于runtime/copla-install-1.0/databases，共20,142份替代文件SHA核对。原测试的模型变异/损坏/还原与科学结果证据、全部日志/trace/JUnit仍保留；若需重放这些私有旧attempt，先从保留主资源重建目录，不能再称已删除路径当前可用。PLASMe/PlasX/Platon等仍需主库、当前Medaka模型/完整1.11GB真实细菌样本以及所有现存工具环境保留。

删除前审查2650份递归JSON证据索引，无目标内固定文件hash绑定；检查71,914个已安装环境符号链接无指向目标，宿主同用户进程复查无目标程序/目录/打开文件占用。67,707普通文件/8279目录/188符号链接的模式、mtime、大小、SHA/链接目标及硬链接数完整清单保存在deleted-files.ndjson.gz；原始包元数据、重建归档及替代主文件SHA列表另存。

逻辑删除7,384,706,875字节，删除窗口实测可用空间增加4,540,817,408字节（约4.23GiB）。后者受硬链接/共享extent和同期文件系统活动影响，不等同于逻辑总量或独占回收保证。删除后116项固定证据与270项已提交源码/文档逐项核对不变，正式718来源清单不改，未移除任何已安装环境。

最初只读引用扫描因重复路径构造耗时，宿主CPU/堆栈检查后仅中断自己的审查进程，退出130且未开始删除。优化为预计算/记忆匹配后同样50目标/2650索引重新完成；357个匹配等价控制通过，范围未缩减。所有准备尝试和实际清理结果在results/tool-audit/20261027-cleanup-8/保留；cleanup.json、plan.json、reference-index-review.json、installed-prefix-review.json、host-process-review.json为权威记录。

清理后原生geNomad --version为1.12.0；Medaka须使用其原prefix/bin PATH（入口为env python），首次未设置该PATH误选全局Python而导入失败，按原环境PATH重跑、未重装依赖或改科学代码。实际结果另存同批medaka-version.json；版本检查不等同于原生推理/科学验收。


## Medaka已完成阶段中间产物与冗余缓存（20261027-cleanup-9，用户当日明确授权）

用户明确要求清理退役/不再使用的大文件。两批执行，逐文件清单（路径/大小/模式/mtime/SHA256/硬链接数）保存于 `results/tool-audit/20261027-cleanup-9/deleted-files.ndjson.gz` 与 `deleted-files-2.ndjson.gz`。

批一：Medaka已完成验证的中间产物570文件、逻辑13,171,180,717字节、实测可用+12,256,165,888字节——cache-v2/framework-gzip-v1/podman-v1的work目录、optional-exec v1失败轮与v2通过轮的BAM/HDF。全部run.json/exit.json/trace/log/最终consensus/gaps BED及钉住哈希证据保留；ordinary-gzip-v1被引用为结果的work产品明确保留；完整NO-MISS样本、模型、索引、环境不变。一个目标（optional-exec/production-b/work）在执行时已不存在（v1未走到该阶段），如实记录。删除后旧缓存队列不可原样resume，重建须用保留输入/环境。

批二：plasmaag-remote-url-pkg-cache与results/nf-test/uv-cache，65,240文件、逻辑9,105,961,114字节、实测+1,280,614,400字节。pkg-cache全部158个.conda与保留的mamba-root/pkgs逐字节SHA256一致，其余硬链接字节经pkgs/https命名空间仍可达；uv-cache为可重建工具缓存而非证据。实测增量小于逻辑量系硬链接与共享extent，不虚构回收量。

正式718来源清单、钉住证据与各接受receipt不变；PlasX/PlasMe/HOTSPOT主库、全部安装环境、当前完整样本与MOB新建库均保留。SCAPP退役目录（约8M）为退役证据，体量小且属历史记录，未删。


## 已通过轮中间work、PlasMAAG中间映射与已解包/可重下归档（20261028-cleanup-10，用户当日授权）

用户当日要求清理本目录大文件，并清理不再使用的相关副本。三批执行；逐文件路径/大小/模式/mtime/SHA256/硬链接数清单与归档SHA、解包映射、provenance一并保存在 `results/tool-audit/20261028-cleanup-10/`。

批一（中间产物与可重建缓存）：删除 `20261028-shotgun-p4-deployment-v4/work/tests/f8bd…/work` 内层Nextflow intermediate；5份 `plasmaag-*/…/.plasmaag_native/intermidiate_files`（plasmaag-production-native-v2、plasmaag-nf-test-remote-pin-v5、plasmaag-nf-test-declared-v3、plasmaag-megahit-compatible-native、20261026-resource-consumers/plasmaag-native-v2）；以及 `runtime/mamba-root/pkgs/cache` repodata缓存。共2,561普通文件、557目录、311符号链接，逻辑18,513,239,431字节；窗口实测可用+8,141,934,592字节（btrfs共享extent，逻辑量不等于物理回收）。保留v4 `output/`（4.3G，456文件）、junit/stdout/stderr/nf-test.log，以及各run其余work、最终产物和全部receipt/selected-artifacts/run.json；清单为 `deleted-files.ndjson.gz`。删除前扫描64,279份JSON/JSONL索引：v4/v5内层work无外部引用；5份intermidiate_files无selected-artifacts/receipt哈希绑定；无外部符号链接指向目标。

批二（逐成员核对已解包的下载归档与Conda包归档）：`20261024-platon-native/platon-db-v1.5.0.tar.gz` 1,690,687,855字节（31成员逐一等大存在于 `database/db`）、`genomad_db_v1.9.tar.gz` 842,023,773字节（27成员存在于 `genomad-db/genomad_db`），以及 `runtime/mamba-root/pkgs` 下1,945份 `.conda`/`.tar.bz2` 包归档 7,673,545,912字节。逻辑10,206,257,540字节，实测+9,209,925,632字节；清单 `deleted-archives.ndjson.gz`。

批三（其余已解包下载归档）：`20261023-opera-native/downloads/complete_ref_genomes.tar.gz` 2,934,421,515字节（5,242成员等于 `runtime/opera-ms-0.8.3/complete_ref_genomes`）、`20261023-hotspot/models.tar.gz` 1,764,744,646字节（19成员等于 `assets/models`）、`20261024-plasx-native/PlasX_mmseqs_profiles.tar.gz` 1,700,322,242字节（54成员等于 `profiles/`）。逻辑6,399,488,403字节，窗口实测+5,703,544,832字节；清单 `deleted-archives-3.ndjson.gz`。三批逻辑合计35,118,985,374字节；文件系统可用空间4,597,522,432→29,386,518,528字节（约+23.09GiB，含btrfs延迟回收窗口）。

保留：全部解包主库/模型（OPERA 9.2G参考树、HOTSPOT assets/models、PlasX 54 profiles、Platon database/db、两份geNomad DB）、全部已安装Conda prefix及conda-meta/显式锁、下载provenance JSON（database-lock、models-response、assets-download、database-proof、genomad-db-download）、各run最终产物/日志/receipt。删除后冒烟通过：genomad-1.12.0 prefix可导入TensorFlow 2.21.0，plasmaag-a6b39ac prefix可导入torch 2.13.0+cpu；Conda包归档删除不影响已安装环境。

删除后上述tar与包归档路径不再存在，不能声称当前可用；重建须按保留的锁/conda-meta与记录URL/SHA重新下载。历史receipt与selected-artifacts未改写。未清理：失败轮 `20261028-shotgun-p4-deployment-v5/work`（约3.0G，保留Join mismatch诊断证据）、`tests/nf-test/.venv`（约3.8G，活跃开发环境）、`runtime/plasme-DB-8046934/DB/plsdb.zip`（约1.1G，PLASMe主库组成部分）、真实样本与输入fixture。
