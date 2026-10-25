# 测试下载前提与 QC 输出契约

2026-10-23；基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。证据为
`results/tool-audit/20261023-prerequisites/receipt.json`，仅覆盖下列局部修复。

TT-004：原下载脚本对校验失败/下载失败不汇总，完整旧脚本在隔离目录中十项都失败仍输出 ALL DONE 且退出0。
旧脚本只替换 OUT 赋值，curl 是明确的退出22 observer；真实网络行为另由完整当前脚本测试。
当前按全清单聚合失败，继续成功项，任一失败退出1且不输出全部成功。临时文件校验后才移为正式文件；
校验和不符的既有文件保留，未有锁定摘要的现存文件不自动采用。空文件、截断HTTP、不可读归档不能新建 ARTIFACT 记录。
独立摘要与本地重放锁冲突时拒绝，缺失文件重下载仍需符合旧锁；不得把新字节重锁为同一资产。
默认十项URL没有改变，未运行多GB默认数据库下载。首次下载本地SHA不是独立上游身份认证，TA-016完整来源追溯仍未关闭。

20个独立 unittest 方法运行整个脚本，使用真实 curl、本机HTTP/file传输、tar/unzip；
两项用明确observer控制默认十项失败和manifest写入失败。覆盖成功后不再下载、混合404/成功、
已锁损坏、未锁部分文件、旧part、截断Content-Length、空200、独立摘要、格式/冲突/精确名称、
坏归档、软链接、空/非法/重复清单及不可写清单路径。Python3.12/3.15重复不增加方法分母。

TA-034：部署环境保持 fastp1.3.6，8个包的原生环境锁在
`results/tool-audit/runtime/fastp-explicit.lock`。官方
[v1.3.6](https://github.com/OpenGene/fastp/tree/23d6211d4f05d61f561899f1b7702435a4b5d408)
文档确认单端 out1 以及 interleaved_in/STDOUT 语义。本地 clean 后缀契约先前只改成了双端，
单端/交错脚本与stub仍写fastp后缀，因output optional而静默丢失reads事件。
现在统一clean后缀，保持双端文件名和参数。原模块/固定官方版本分别运行SE/PE/交错三种真实节点及三种stub；
旧版4个单端/交错场景任务成功但通道为空，当前都正确输出样本归属和文件。
真实对照用明确生成的12单端/12对短读，禁用相应过滤/修剪以独立核对每条ID、DNA、质量和JSON计数；
不认证真实样本QC效果、容器或整个流水线单端/交错支持。其他可选flag组合不由本批认证。

TT-007：原IntegronFinder --gbk stub把路径当命令，任务127；默认stub通过。
修复仅为创建文件，两种当前stub都通过，检查gbk通道缺省为空、请求时样本ID和文件存在。
版本命令是明确observer，不运行IntegronFinder原生注释。vendored nf-test框架/快照依赖仍由TT-005单列，
本批直接运行原模块的Nextflow harness不冒充nf-test执行。

总计16条原生Nextflow trace=15完成+1旧版预期失败；其中6个真实fastp调用、6个fastp stub、4个IntegronFinder stub。
stderr已逐项读取；成功fastp的“reads failed ...: 0”是统计行，唯一任务失败为旧gbk路径错误。
主入口未变，原45个P0及以前平台证据分母不增加；未重跑未改变的整个平台，不把历史hash当作当前全平台认证。

COPLA另有只读调查，不计修复或真实节点通过。固定官方spec是graph-tool2.35/Python3.9，
除CLI/逐实体拆分外还需repo运行目录、相对helper/DB、绝对参考列表和Python2 MacSyFinder环境。
官方latest数据库地址一次连接超时，没有获得版本/大小；不能推断永久不可用。源文件和
`readiness-copla.json`保留在本批结果目录，TA-019/020继续未决。
