# 目录资源与缓存身份（TA-091，S0，进行中）

2026-10-26。证据目录为 `results/tool-audit/20261025-genomad-provenance/`。本项发现晚于718项正式接受清单；修复和新增测试保留为未接受候选。

真实 Nextflow26.10 的最小文件读取控制表明，standard 和 deep 的目录 path 输入均可能在内部文件等长且保持mtime时复用旧任务。`native-old-directory-cache/run.json` 在固定 geNomad1.12.0、完整DB1.9及真实完整质粒上复现：私有版本文件损坏后恢复任务命中旧缓存，但强制冷执行失败。共享原库未改变。

首版修复显式传入全部普通文件；geNomad 原生对照通过，但COPLA约3.4万文件生成约9.8MB staging 包装器，在科学程序启动前以139退出。实际 Bash 语法检查通过；把文件操作替换为空函数后，原 staging 函数执行仍SIGSEGV，故不能归因为COPLA算法失败。该实现已替代，原源码、包装器和控制保留。

续接前候选在缓存查找前计算紧凑的目录内容身份，避免逐文件 staging。geNomad和PLASMe的真实变化/恢复控制在已测目录中通过，COPLA冷运行触发1800秒驱动超时，尚无完成任务记录，不计通过。**该版本的独立属性检查未通过**：Nextflow的文件glob遗漏文件名含换行符的成员，因而不能声称内容身份覆盖完整资源目录。不得删除或弱化该断言来获得通过。

下一步需定义并实现目录、普通文件、隐藏文件、合法特殊文件名、符号链接和异常成员的完整语义，再执行独立属性与缓存控制、必要原生工具回归，并盘点所有目录资源消费者。只有全项验收条件满足后才能关闭TA-091；三个工具的局部对照不代表全仓库、OCI、平台或科学性能认证。


## 2026-10-26 续接：完整枚举与边界候选

已将当前紧凑指纹调用方（geNomad、PLASMe、COPLA）的 `files(".../**")` 换成 `ResourceIdentity.capture(root)` 内部的 NIO `walkFileTree(FOLLOW_LINKS)`。目录内部合法 UTF-8 特殊成员文件名不经 glob 或逐行解析；根路径定位仍需单独验证元字符语义。当前实现面向 POSIX 文件系统；不支持的权限/provider 操作明确失败，不以空身份继续运行。

schema v2 在原逐文件 SHA-256 基础上加入排序后的目录/文件类型、相对路径、成员链接的原始目标和 POSIX rwx 权限。空目录、权限变化和链接改指向均参与身份；根目录别名可共享身份。成员链接允许指向根外，按资源相对路径散列链接后的实际内容，同时散列链接目标；它们因此也是须保持不变的资源。断链、循环链接、FIFO 等非普通文件及遍历/读取失败均中止。文件大小、mtime、file key 在单文件读取前后校验。资源必须从指纹计算至任务结束保持只读/不变；本实现不提供跨文件事务快照，也不宣称抵抗并发恶意篡改。v2 与旧身份不同，首次使用会使已测消费者重新执行。

独立 Python oracle 的22个属性场景及16轮真实 Nextflow26.10缓存控制已通过，见 `results/tool-audit/20261026-resource-identity/final-controls/run.json`。包括换行、tab/CR、glob元字符、Unicode/UTF-16排序、隐藏文件、末尾字节、等长同mtime变化、重命名/删除、空目录、执行权限、根别名、链接内容/改指向及失败边界。16轮为9个COMPLETED与7个CACHED；原生 `cat` 任务脚本SHA始终相同。这是字节/缓存控制，不是分类器或生物学验证。初始v1枚举控制及v2的20场景中间控制保留，均由各自源码SHA区分。

COPLA现场与源码/输入/部分产物身份已保存于 `results/tool-audit/20261026-resource-identity/copla-timeout-inspection.json`。第一候选已给出PTU-X4，第二候选留有2091/9894个ANI参考状态；仍无任务退出码及最终trace。此证据把超时定位到已启动的真实计算阶段，不能给出完整任务通过结论或推出隔离进程空间以外的后代状态。重试必须保留两个候选和全部9894参考，在新目录使用至少7200秒驱动预算并监测进度，不复用部分产物、不下调科学断言；不重复相同1800秒尝试。本轮先完成当前资源边界和消费者复核，再安排该长运行。

消费者清单见 `../resource-directory-consumers.tsv`，39条为“消费者—资源”对，包括显式目录、文件集合、可选入口、上游模型目录及隐式环境资源，不是39个通过工具。已确认PlasX/Platon/gplas/PlasMAAG/HOTSPOT仍有glob枚举，MOB-Typer/Bakta/AMRFinderPlus/RGI/eggNOG/MetaPhlAn/Kraken2/GTDB等仍需逐一补齐或核实目录身份；CheckM2、BLAST和PlasmidHostFinder需核实具体文件/目录输入形状。下载模型、环境内置数据库和容器内容另列待审。未将此次候选推广为全消费者修复。

TA-091保持S0 in_progress，正式718项来源清单与最近接受批次不变。当前候选的原生回归及来源记录见本轮receipt；不据本轮字节控制放行全流程、科学性能、OCI或AWS。


本轮当前源码的 geNomad1.12.0/fullDB1.9 与 PLASMe1.1/full-model 回归均完成；各4轮为1个COMPLETED、2个CACHED和1个预期FAILED，损坏/还原仅作用于私有资源。检测子工作流3场景共28个COMPLETED，分类器是显式observer，原始R消费者真实执行；首轮因默认PATH无Nextflow未启动，追加固定runtime/bin后在新目录重试通过，失败保留。汇总与逐文件SHA见 `../evidence/20261026-resource-identity.json`，完整receipt见 `results/tool-audit/20261026-resource-identity/receipt.json`。


## 显式消费者候选更新（2026-10-26）

前述“39条/尚待完整COPLA重试”为初次现场历史状态。当前清单为41个消费者—资源对，33条显式候选记录、8条隐式待审记录；不是41个通过工具。共享 `lib/resource_inputs.nf` 在任务查缓存之前计算schema2身份，31个val身份输入接入21个模块文件/22个process定义及生产调用方；可选缺省资源显式传递absent身份。HOTSPOT程序仍按实际选定3个文件散列。

COPLA完整9894参考/两个候选已完成；PlasX、PlasMAAG、gplas、Platon及HOTSPOT等限定原生运行/私有损坏/还原对照和接口回归见 `../evidence/20261026-resource-consumers.json`。15个隐藏或含换行成员的等长同mtime变化在13个真实process定义中完成32轮缓存控制，观察器不冒充科学推理。anvi’o的13个固定子模块已完整补齐，主源码原摘要不变，子模块独立锁定验证。

本批119条运行源码比较匹配；102个候选源码路径的两份补丁正反应用精确核对。TA-016补丁仅保留既有报告候选，不代表新增报告验收。3个未改动模块的既有vendored比较链不在本批证据认证范围。

仍须处理8个隐式环境模型/数据库资源对，审查可选前缀/sidecar数据库实际读取集合、根路径定位元字符及不同provider语义。资源从指纹到任务结束须不可变；当前实现不提供跨文件事务快照。显式输入候选接线与选定原生通过不能替代完整TA-091验收、完整科学/OCI/平台验证。正式718项接受清单保持不变，TA-091继续S0 in_progress。


### 根路径定位修复与快照边界

上批receipt中的119条哈希比较为捕获当时的结果；随后共享入口单独更改为 `file(location, checkIfExists:true, glob:false)`。真实引擎已证明旧入口会拒绝实际存在的`[]`/`*`/`?`根路径；当前7个入口控制通过，13个原observer任务精确复用原缓存哈希。缺失的字面根即使有模式匹配的兄弟也不会替代。此修复针对定位语义，不声明各科学CLI均支持任意特殊shell路径。

后续证据 `../evidence/20261026-resource-root.json` 精确标记上一快照仅共享入口变更，保留旧receipt、原始失败以及两份旧补丁；新增顺序补丁后103个候选路径正反逐字节核对。仍须处理8个隐式资源对及可选前缀/sidecar读取集合与provider边界。SemiBin默认自训练模型与条件预训练资源另分支审查，包内marker.hmm仍须纳入默认实际读取集合。


### 环境内资源探测机制的原生试验

`tests/nextflow/semibin_runtime_resources.nf` 在固定原生环境中先运行不缓存的资源探测，再将稳定JSON文件作为deep输入交给复制的生产SemiBin消费者。消费者执行前重新校验资源；不可变假设仍然适用。探测无时间戳/绝对环境路径字段，身份由资源字节/长度/权限和固定版本组成。该pilot只处理默认marker.hmm，不冒充通用目录捕获器或全部环境来源机制。

真实默认15epoch/完整官方fixture的6轮结果见 `../evidence/20261026-runtime-resource-pilot.json`：探测每轮实际完成，下游不变缓存、等长同mtime描述变化重跑、坏HMM头原生失败、还原复用均符合预期。仅消费者输入及执行前校验变化；没有改SemiBin科学命令。原共享安装未改，私有包结束时32文件字节一致。

生产接线尚未通过：必须统一探测/消费者实际Conda、容器、accelerator及参数解析；自定义外部数据库/模型、预训练分支和其他消费者未验收。Medaka的固定[2.2.2脚本](https://raw.githubusercontent.com/nanoporetech/medaka/v2.2.2/scripts/medaka_consensus)按输入reads选择模型并有回退，不能用一次全局模型标签替代各样本实际模型身份；[ABRicate1.0.1](https://raw.githubusercontent.com/tseemann/abricate/v1.0.1/bin/abricate)使用选中库的sequences前缀，须保全BLAST实际sidecar读取集合。[Dorado模型文档](https://software-docs.nanoporetech.com/dorado/latest/models/selection/)仅指导下一步调查；尚未固定实际部署版本，不据latest文档给原生通过结论。8个隐式资源对仍pending，TA-091仍开放。


### SemiBin生产候选接线更新

此前“8个隐式资源对仍pending”为历史状态。当前SemiBin默认路径已接入每次运行的环境内探测及查缓存前上下文门禁，其余7个尚待接线；SemiBin自身的可选ORF/完整原生分支和部署验证仍未完成。默认marker与包代码、选中模型/已准备GTDB及显式覆盖输入由固定原生解析器确定，不将默认自训练强行换为预训练。校验后exec同一argv。详细边界、42条来源比较（41直接匹配，1个仅控制台标签桥接）、120候选路径/五份顺序补丁及原生/缓存/框架恢复证据见 [SemiBin契约](semibin-runtime-resources.md) 和 [证据](../evidence/20261026-semibin-runtime.json)。TA-091保持S0，不关闭全消费者或全流程验收。


ISEScan生产隐式资源候选已完成限定原生缓存/读取边界验证，见[独立契约](isescan-runtime-resources.md)。41资源对现35候选、6待接线；完整环境及TA-091仍未关闭。六份候选补丁与748项当前快照不替换正式718项清单。


SemiBin可选FGS1.32 complete/w0分支的二进制/17train候选身份、完整原生缓存/缺模型对照已补齐，见[后续契约](semibin-runtime-resources.md)。其余外部可执行文件与完整环境边界未关闭；41资源对仍35候选+6待接线，749项当前快照/七份补丁不替换正式718项清单。


ABRicate默认/显式目录及外部BLAST别名卷身份已有生产原生候选，见[契约](abricate-runtime-resources.md)。同时发现独立S0 TA-092错误传播问题，候选已作有界验证但未正式接受。41资源对现36候选/5待接线，当前757来源与九份补丁不替换正式718项清单。

ABRicate原始压缩Bacteroides native/stub框架2例已验证；最新10候选补丁/759来源与旧9份快照分别记录，正式清单不变。


IntegronFinder原生模型/功能库清单与已批准未知线性策略联合候选已验证，见[契约](integronfinder-runtime-resources.md)。41资源对现37候选/4待接线；11补丁/768来源快照独立于正式718清单，新TA093仍未正式接受。
