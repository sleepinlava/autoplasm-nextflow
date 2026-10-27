# MOB-suite原生软件环境与独立只读预检候选

2026-10-26增量，承接[source读取调查](mobsuite-runtime-readset.md)。**已安装软件并验证实际CLI；没有MOB科学分类或完整数据库验证，没有接入生产资源缓存，也未接受TA-091。** 41资源对仍38候选/3pending。

## 实际来源与安装边界

实际Conda求解3.1.9 build `pyhdfd78af_1`、Python3.10.14、BLAST2.15.0、Mash2.3、ETE3 3.1.3，共180包，原始归档SHA256逐项核对，完整URL/hash锁为tests/mobsuite-native.lock.json。生产声明OCI为build0，本批没有拉取或运行它，不能以build1代替容器验收。

安装使用显式锁、`--skip-run-link-scripts --no-pyc`。包内post-link确实只有 `mob_init` 调用，已跳过；实际默认databases目录仅含零字节__init__.py，没有status/FASTA/sketch/taxonomy。本批没有另行下载DB/模型/测试序列。软件包自带10份FASTA示例/测试文件，清单/首header/hash保存在bundled-software-fixtures.json，未用于运行；不能把“软件安装”误报为整个包里不存在序列文件。未来使用仍需核对细菌/非病毒范围。

安装包源自recipe记录的PyPI sdist（SHA256 c5313378d22fb45d684101054eee6153244261e355668f843d2d956209f9fb97），sdist本身未下载。六个实际安装代码/配置文件与原始Bioconda归档精确相同；其中五份与固定GitHub eb860648提交相同，version.py不同：标签写3.1.8，发行包写3.1.9。实际CLI输出 `mob_recon 3.1.9`，版本来源三者分别记录，不静默把tag字面值当原生版本。

离线求解缓存不全、沙箱元数据/包下载DNS失败保留；获准软件网络后求解/安装成功。在线求解中有非阻断的java-jdk shard TLS告警，最终success=true并锁定180实际包；不是声称所有远程请求都成功。

## 独立预检覆盖

bin/mobsuite_preflight.py严格核对实际六份发行代码/配置摘要，再调用已安装MOB真实parse_args；资源路径取原main的AST选择片段，把verify_init调用替换为只检查默认status的拒绝门禁。不会调用原mob_init、MOB科学main、NCBITaxa或科学子进程。

只检查选定必需文件存在且非空，以及已有SQLite的只读结构：用mode=ro连接，核对实际ETE3 DB_VERSION=2、quick_check、species/synonym/merged必要列及非空species。缺失/过时/损坏时拒绝，不用ETE3的可能建库或自动升级接口。可选filter_db/genome_filter_db_prefix的完整实际卷/写入准备尚未实现，独立预检明确拒绝该范围，不能据此删减最终支持目标。

完整原始细菌540bp软件fixture仅作为拒绝路径的输入参数，字节未改；两个真实helper子进程对默认未准备库/显式缺资源目录均exit2，无科学输出目录或成功receipt，默认库文件不变。4个实际CLI help/version检查通过；这些不是科学任务。

8个单元方法使用实际安装包的解析器与明确非生物学文件/SQLite元数据控制。子进程创建器、原verify_init及ETE3对象均被明确禁止observer拦截，防止误触下载。一个结构阳性包含故意非生物学placeholder文件，证明只读结构检查可通过，**不证明这些占位文件是可用MOB参考库**；任何后续科学执行仍需真实完整资源验证/来源核对。独立预检没有execute选项，也未接到生产module。

## 下一步条件

1. 先核对完整DB/metadata是否符合不使用病毒元素约束；不运行原病毒nf-test，不下载未审核默认库或全量taxonomy。
2. 生产Conda安装本身会触发post-link，发生在任务探测之前。必须设计并验证可重建的无隐式初始化软件准备方式；仅加科学任务前probe不能覆盖安装阶段，注释/本工具都不代表已解决部署门禁。
3. 完成实际BLAST卷/alias、Mash、filter写索引、ETE3状态/依赖、全读取身份及probe/consumer上下文，接入两个alias并跑真正完整资源/原始细菌阳性阴性/cache变异恢复/坏资源/框架/provider/OCI控制。

MOB仍pending，TA-091和TA-016来源范围继续未决；正式718来源清单、99已接受局部修复/2用户退役/8未决不变。
