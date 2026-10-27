# ABRicate运行资源与子进程错误候选契约

最新[候选收据](../evidence/20261026-abricate-runtime.json)记录第八份TA-091资源补丁及第九份独立TA-092错误补丁及第十份元数据/框架接口补丁。未覆盖项继续开放。正式718项来源清单、99项有界接受修复与2项用户退役不变；新增真实S0发现TA-092后，当前106项问题、5项未决（2S0+3S2）。TA-092已有候选验证但未正式接受。

## 原生解析与资源身份

ABRicate1.0.1的实际固定Perl源码来自[原始发布](https://github.com/tseemann/abricate/tree/v1.0.1)，归档SHA256为5edc6b45a0ff73dcb4f1489a64cb3385d065a6f29185406197379522226a5d20，与包配方一致；安装入口与原始源码逐字节相同。176个锁定安装包原始归档SHA直接复核；tests/abricate-native.lock.json记录URL/hash/完整fixture与数据库。当前环境无Python，使用已有Perl核心模块，不增加容器Python要求。OCI尚未运行。

探测器在独立Perl进程加载可信固定版本源码，只在原setOptions()后插入返回解析JSON的边界；保留原Getopt::Long大小写/缩写/重复参数语义及FindBin::RealBin真实入口路径。默认datadir为真实入口目录../db，默认db为ncbi。--fofn的实际Path::Tiny行读取覆盖普通ARGV输入；显式databasedir保留原调用次序，在ext.args之后作为最终--datadir参数。不手写另一套选项解析器。--setupdb须先准备资源，不能在科学任务内出现未记录的索引重建。

身份覆盖入口、resolver、Perl解释器、blastn/blastx/makeblastdb/blastdbcmd/any2fasta/gzip/unzip/bash、有效输入/fofn、整个选定数据库目录，以及blastdbcmd -info报告的所有实际卷前缀成员（精确前缀及prefix.开头文件，无glob）。这使.nal指向选定目录外的真实数据库卷也参与身份。目录/链接/权限/内容递归记录；循环、断链、特殊文件失败。身份与执行均使用同一份已展开argv；资源仍须在探测至执行期间不可变，未提供原子快照或完整环境证明。

生产探测cache:false，每次resume先刷新；全meta连接identity/receipt/helper给深度缓存消费者。缓存查找前比较Conda/container/engine/accelerator/beforeScript/modules/containerOptions/ext.args/prefix/显式目录，配置必须对ABRICATE和ABRICATE_RESOURCE_PROBE共享选择器；实际conf/nfcore_downstream.config已共用。原科学参数、输出文件命名和报告接口保留。探测receipt作为08_annotation报告事件记录；不能据此关闭完整TA-016方法/环境来源。

## TA-092实际失败与精确错误边界修复

真实缺少私有ncbi/sequences.nhr时，blastdbcmd -info仍可成功；原BLAST报Database memory map file error，原ABRicate却退出0并输出只有表头的零命中报告。旧工作目录、exitcode、命令日志和报告SHA在real-error-pair.json保留。这不是合法零命中或模拟数据库错误。

固定1.0.1执行适配器只修改两处：以bash -o pipefail运行原any2fasta|BLAST命令，在close BLAST失败时非零退出；参数、算法、默认80/80阈值、FindBin路径和原生报表逻辑不变。仅接受原始两处边界各匹配一次的1.0.1源码，其他布局拒绝；有效源码完整字节与SHA保存在native-errors/guarded-source.pl，helper内容与execution_adapter身份随缓存输入记录。不会把损坏DB或失败子进程当有效空结果。

真实损坏卷在当前生产科学任务FAILED。另两项明确晚退出observer：实际完整转换或BLAST输出后分别exit7/9，原工具仍0/5条命中，当前guard非零；这些是故障注入边界，不称为真实二进制自身缺陷或新科学样本。显式256bp合成合法零命中仍原/当前0且报表完全相同。

## 当前通过范围

完整上游assembly.fa2521797字节、完整原始5386条ncbi参考不裁剪；原始5条命中报告为软件契约基线，不是独立生物学真值。最终13阶段24条trace：18 COMPLETED（13探测+5科学成功）、5 CACHED、1真实BLAST错误科学FAILED；两次上下文不匹配探测完成后消费者未提交。私有.nhr真实产品注释的一个大小写字节变化，等长同mtime，不改核酸/数值；正常与外部别名两条路径均重跑且精确只改变预期PRODUCT字段。恢复字节/权限/mtime后复用原任务哈希；默认与显式datadir均验证。17个私有原资源文件最终逐字节/权限恢复，未改原安装。

7个原生参数/读取集合方法另列，包括真实入口别名、Getopt缩写和最后覆盖、fofn优先、外部卷、隐藏换行sidecar等长同mtime变化及不完整/循环/特殊资源拒绝；它们不作分类推断。实际PLASMID_DOWNSTREAM可选annotation入口运行2个真实任务，完整5行报告及probe/消费者报告事件核对通过；空输入0任务/0事件。这里没有把被测装配当质粒生物学真值，也未运行完整主流程或报告渲染器。

22条执行源码全部直接匹配当前来源；十份顺序补丁对145个候选路径正向精确字节/权限、反向精确HEAD核对，当前759项快照与正式718项分离。前九份补丁保持原样，第八份未加错误guard的中间候选包含真实失败复现，不单独升级为通过。所有失败和被替代尝试保留，包括DNS/安装限制、原生错误发现、guard插值编译错误及slurp记录分隔符错误；未把开发失败计入最终通过分母。native-v4完成收据及13个终态trace证明结束；用户steering后控制器句柄不可用，未重启。

## 尚未完成

Dorado、Medaka、PlasmidFinder、MOB-recon、IntegronFinder五个隐式消费者待接线；41资源对现36候选/5待办。ABRicate完整Perl/XS及系统共享库来源、OCI/provider/when/自定义部署、多输入与summary等全部模式尚未完全认证。其他显式可选读取集合、SemiBin其他可执行文件与完整可选模型/GTDB、TA-016/TA-031/TT-003、真实shotgun P4、M0–M4/全平台和AWS范围继续保留。本批无提交/推送/AWS资源/上传/收费。


## 原始vendored框架接口回归

元数据新增真实runtime_identity/receipt/helper输入，原nf-test两输入通过薄workflow wrapper接入生产探测及消费者，没有伪造身份。固定nf-core test-datasets提交618f1541382c4ad49eff566dadf13d5ccbd0ebb4的完整Bacteroides genome.fna.gz1564005字节、解压5314727字节，下载/解码SHA锁定；未截短或换fixture。nf-test0.9.5原native/stub两例均通过，native原报告MD5 b48f4f5f78982a221038fd9f0a3aa504保留，没有更新oracle；stub仍空文件/无推断。4条COMPLETED trace分属原生探测+科学任务、stub探测+stub任务，不计作4次科学计算。

首轮原项目配置只覆盖探测器名字，未覆盖ABRICATE_RUN，两个消费者均被门禁正确拒绝；添加共享测试配置后通过。首轮同时扫描了大量历史证据源码，最终用逐字节/权限核对的隔离临时源码副本运行同一模块/库/helper/原始测试，所有实际加载源码保持相同，避免依赖扫描历史证据；没有绕过运行上下文检查。复制证明与原/当前源码SHA、JUnit和真实trace保留于framework-v2。原先九补丁/757快照收据另存before-framework，新第10补丁只增加/修复元数据、测试包装/配置及来源锁和单元收集的无环境skip保护。最终单元7方法全部实际运行、未skip；旧7方法首轮不重复增加用例分母。
