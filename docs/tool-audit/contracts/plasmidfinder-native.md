# PlasmidFinder 2.1.6启动与原生CLI候选

未正式接受。启动阻断见前批候选；当前已增加TA-091资源探测接线及细菌输入测试，完整环境/OCI/provider和原生FASTQ科学分支仍待完成。

- TA-094：固定Bioconda `2.1.6=py310hdfd78af_1` 的依赖仅要求Python>=3，真实求解选到3.15.1；原脚本导入 `distutils.spawn` 即失败。候选environment显式Python3.10，与既有容器py310构建一致。实际使用3.10.22，87个原始包归档SHA256逐一核对；不把构建名当Python依赖约束。
- TA-095：Python3.10下原生参数解析明确拒绝生产配置 `--legacy`，exit2；去除此参数，保留模块 `-x`、原生data.json、五个输出及默认9数据库组/0.60覆盖/0.90身份阈值。未修改科学程序。
- 固定源码来自Bitbucket2.1.6完整归档，SHA256 `ce1535c2a227a7dfa798468e8c8e9ce8602e6b16f0cf33cd4802b8f40c8b61ec`。安装脚本仅有Bioconda数据库路径赋值和默认值替换；精确反向规范化后与固定源码全文相同。没有CLI版本接口，模块版本仍为声明值，不宣称已读到原生版本输出。

实际生产Nextflow模块加共享downstream配置运行5阶段/5trace：旧CLI FAILED、普通输入科学COMPLETED、未改输入CACHED、gzip科学COMPLETED、独立stub COMPLETED。保留完整原始上游test/test.fsa（569文件字节/540bp），不是完整质粒或生物学真值；两次科学运行逐字节匹配原始golden TSV，独立核对两份FASTA的全部DNA及JSON的100%身份/覆盖、540bp/1..540、AF250878和其余8组零命中。172任务主流程回归为明确外部工具observer，不能计作172次原生科学执行。首次mock启动重复-log拒绝保留，使用同版本Java/Nextflow无重复日志参数launcher后通过。

用户新增[不许使用病毒元素约束](../user-constraints.md)。原始病毒阴性fixture下载未成功、未执行；下载脚本和空目录删除。实际vendored框架改用固定提交完整Bacteroides细菌gzip，解压完整原始约5.3MB，未裁切或换为阳性。原始零命中TSV MD5 `c457f4c5f1eacaa47e8466c01c4a1e7c` 保留，实际native/stub两例通过；原病毒测试不再作为待执行项。完整540bp细菌复制子阳性继续独立验证。

## 当前资源候选

原始2.1.6为单文件顶层CLI。helper严格核对源码摘要（仅允许打包数据库路径规范化），AST执行原imports/functions/argparse、配置读取、分类选择和输入格式检查，停止在原BLAST/KMA调用之前。-d/--speciesinfo_json、默认9库、-p、-mp、-q及有效输入均复用原解析器；quiet的stdout在探测返回时恢复。生产FASTA分支实际读取 `<db>/<selected>.fsa` 并使用blastn -subject；FASTQ选择KMA。完整目录保守纳入所有sidecar，明确允许对FASTA未读取的KMA字节过度失效。

身份包括完整实际DB目录（文件/布局/模式/符号链接及目标内容、拒绝循环）、实际entrypoint/解释器及一致性校验、全部CGEcore .py、所选方法二进制、输入/argv/runtime上下文、helper自身。probe cache:false；consumer deep-cache，查缓存前上下文门禁，执行前再次核对identity后exec原CLI完全相同argv。生产完整meta join、report事件、元数据和测试调用均迁移。无CLI version接口，2.1.6依据固定源码校验，不把声明版本当原生version输出。

最终13阶段23trace：16COMPLETED（12probe+4科学成功）、5CACHED、2FAILED（缺FSA原生probe拒绝+损坏FSA真实BLAST失败）；两个上下文拒绝各只有probe，无消费者提交。私有48文件完整原打包DB、私有入口只替换打包默认DB路径并精确可逆。等长同mtime复制子note R27→R28，原生TSV只改变预期note、全DNA保持；还原精确缓存复用。未使用KMA sidecar变化也保守重跑并恢复缓存。原生-d enterobacteriaceae/-q成功，完整golden TSV/两份DNA/JSON核对；所有48文件字节/权限还原。

8个读取边界单元方法、178任务主流程mock、两例细菌native/stub nf-test通过。mock资源扫描明确observer，不当真实包或178次科学执行。初版driver误判原config的extensions:fsa规则，实际正确在probe拒绝缺文件；失败保留，v2分别验证probe缺失拒绝和consumer真实坏FSA失败，未削弱错误检查。

41资源对现38候选/3pending：Dorado、Medaka、MOBSUITE_RECON。完整runtime环境/动态库/其他Python依赖、原生可选FASTQ、OCI/provider/when/profile、独立接受与其余计划范围仍未完成；TA-091及TA-094/095不因此关闭。任何要求病毒模型的后续真实运行受新增约束禁止，不能照旧重放。


清理：先保存完整17,430普通文件/1,294符号链接/1,724目录清单、84包元数据/显式锁与实际归档哈希，再移除不能启动的Python3.15私有安装。保留可用py310环境、完整原始fixture、包归档和所有运行证据；旧安装历史路径现不可用。见cleanup台账及20261026-cleanup-4/cleanup.json。
