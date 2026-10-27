# MOB-suite无安装阶段数据库初始化候选

承接原生软件/只读预检调查。本批修复生产recon和typer的Conda环境声明；**没有MOB科学分类、完整参考库验证或资源probe生产接线，未正式接受TA-091**。

## 软件安装变化

Bioconda3.1.9包的post-link会运行mob_init，发生在科学任务前，任务内probe无法阻止。两份environment.yml改为Conda安装原依赖范围，再由pip安装固定SHA256的官方3.1.9 wheel；未设置全局跳过link脚本选项，也没有删改MOB科学代码。

官方[PyPI3.1.9发布元数据](https://pypi.org/pypi/mob-suite/3.1.9/json)提供wheel URL和SHA256 `467039630b3364f05ed736713db6119c5902b11cb0051b8b5891ca3ed73b808f`。实际下载3,189,647字节，经SHA核对，16份Python源码与原始Bioconda build1归档及原生安装逐字节相同。全部179个Conda依赖的版本/build/hash与上批180包除mob_suite本身外一致；原始归档SHA逐项复核。wheel无Conda link脚本，pip check无损坏依赖。软件包仍自带此前列明的示例/测试FASTA，未用于科学运行，也未另行下载DB/模型/序列/taxonomy。

[Nextflow官方Conda配置](https://docs.seqera.io/nextflow/reference/config/conda)提供Micromamba选择与环境缓存；createOptions是环境创建选项，不能靠一个MOB任务内部动作选择性阻止旧包post-link。本批用实际Nextflow26.10.0/Micromamba验证新环境，没有任何createOptions或skip-run-link-scripts。Conda/Mamba CLI本身及OCI仍待各自验证，不能以Micromamba替代全provider验收。

## 实际验证

- 从不存在的Nextflow环境缓存冷创建，任务实际使用生产recon环境YAML，179Conda包且无mob_suite Conda记录；MOB的direct_url.json记录官方wheel SHA，与模块声明一致。
- recon未变恢复CACHED，typer环境声明冷任务COMPLETED，再恢复CACHED；两份YAML字节相同，四轮共用同一真实环境。4trace为2COMPLETED版本信息任务、2CACHED，**不是科学分类任务**。
- 实际检查mob_recon/mob_typer/mob_cluster/mob_init --version均3.1.9，默认数据库除__init__.py及正常__pycache__外为空；没有status/FASTA/sketch/taxonomy。版本参数会在解析器内退出，没有调用mob_init初始化main。
- 新环境再次通过原独立预检：默认/显式缺资源2次真实拒绝、8个唯一结构单元方法、4实际CLI info检查。重复运行不累加单元方法或科学样本。原预检驱动仅补充排除Python字节码缓存，仍严格检查真正数据库内容为空；不能把__pycache__当作生物数据库。

首次沙箱环境创建因元数据网络失败；批准的软件联网创建成功。首个provider控制器错误地只在stdout查创建日志，而Nextflow写入stderr；检查修正为两流后通过，没有放宽实际创建/trace/源码断言。原失败记录保留。无MOB科学执行、病毒输入或独立生物资源下载。

## 新发现的Typer隐式分支

生产MOB_TYPER默认传缺省目录身份及7个空可选文件。实际安装mob_typer真实parse_args与原5条DB选择AST语句证明：未给目录时使用环境数据库，并进入verify_init；还读取环境taxa.sqlite/literature。verify_init以明确observer记录，未真正初始化或执行main。

原MOB_TYPER/mob_suite_db行只覆盖显式目录输入，不能代表该默认分支。新增独立环境默认资源对，当前42对=38候选+4pending：Dorado、Medaka、MOBSUITE_RECON、MOB_TYPER默认库。仍属TA-091，不因软件安装成功减少未决数。新分支还需资源身份/上下文/prepare/no-download/缓存变异恢复/原生完整细菌阳性阴性/框架/OCI/provider验证。

科学任务调用原MOB main时仍可能因库未准备而初始化，本批只解决新Conda声明的安装阶段。必须继续核对满足不使用病毒元素约束的完整资源，再接生产门禁；原病毒测试不允许运行。

## 清理边界

确认同179依赖/16源码/10随包FASTA在新环境保留，实际核心import路径均属于新prefix后，删除旧 `results/tool-audit/runtime/mobsuite-3.1.9` 独立软件基线。它没有科学结果或生物数据库；保留新Nextflow环境、180原始归档/锁、旧180包元数据、完整删除清单及全部receipt/log/trace。历史旧prefix命令已不可执行，重建需原锁并跳过原post-link。详见cleanup台账；不把逻辑2.11GB误报为物理释放量。
