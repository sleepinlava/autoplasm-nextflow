# IntegronFinder模型资源与已批准拓扑规则候选契约

本批是TA-091/TA-093联合第11份未接受补丁，见[候选证据](../evidence/20261026-integronfinder-runtime.json)。原十份补丁和正式718项清单保持原样；当前768项来源快照/157候选路径独立保存，正向字节/权限与反向HEAD精确核对。26条执行源码比较全部直接匹配。正式99接受修复+2用户退役不变，新增TA-093后当前107项问题、6项未决（3S0+3S2）。

## 原生来源与真实读取集合

固定[上游v2.0.5源码](https://github.com/gem-pasteur/Integron_Finder/tree/v2.0.5)完整归档SHA256为02c68944c01eb566a05202cfe6792dab4a67756e0d25ef53b8f318fdf1c5d74a。75个Conda原始包归档SHA直接验证；安装后全部23个非pycache包文件逐字节等于另取固定tag文件。配方中的PyPI sdist SHA只作配方来源记录，未谎称另行下载该sdist。tests/integronfinder-native.lock.json锁定来源、包URL/hash、完整上游输入。

使用实际2.0.5 parse_args/Config/scan_hmm_bank，不另写CLI或模型选择规则。默认记录整合酶HMM、phage-int HMM和选中attC CM、包源码、真实工具/解释器/入口、输入/外部蛋白/解析器/拓扑文件。功能注释严格保留bank_hmm工作目录优先、包默认库、显式--path-func-annot语义；清单内glob由原函数展开，清单及目录外实际匹配模型均散列。GemBase使用原静态定位函数记录相应LST与Proteins文件，不初始化科学推断。--no-proteins分支按原功能库选择规则跳过可选库。循环、断链、特殊资源拒绝。可选布局单元控制不当完整可选分支推断通过。

入口解释器必须与资源探测Python真实路径一致，兼容普通shebang/env及实际Conda长前缀exec格式；否则拒绝，防止探测一套包却执行另一套。非已支持的解释器启动格式明确拒绝；不认证任意自定义入口脚本的内部读取集合。完整Python字节码、第三方动态导入、系统共享库/OCI等来源仍未覆盖；资源仍需在探测/查缓存/执行之间不可变。

生产INTEGRONFINDER_RESOURCE_PROBE关闭自身缓存；全meta关联身份/receipt及两个显式helper文件后才进入消费者深度缓存。运行上下文Conda/container/engine/accelerator/beforeScript/module/containerOptions/args/prefix须匹配，不一致在消费者查缓存前拒绝；配置应共用两个名字。原压缩输入处理、输出接口及TT-007已有--gbk stub修复保留；receipt纳入08_annotation报告事件。实际基因/模型计算与mock资源扫描明确分开。

## TA-093：落实现有未知线性规则

现有用户批准规则在work-summary中明确“未知拓扑按线性处理”。原2.0.5对单条未标注序列默认circ；上游完整ACBA输入20301bp在这种默认下得到1complete，同一DNA/模型/阈值在原程序显式--linear下得到1CALIN+1In0。这个软件fixture被作为无明确拓扑输入测试规则，不是宣称它的生物学真拓扑变成线性，也不称原complete为已证实生物学假阳性。

候选生成完整逐replicon拓扑表，再将相同表作为最终--topology-file传入原程序。优先级保留：显式拓扑文件、显式CLI、明确GemBase类型、明确header标记，然后未知按lin；显式--circ仍精确得到原环状结果。文件默认值/模型阈值/序列字节不换，只有已授权拓扑规则显式执行。冲突header/重复ID/无法表示的ID拒绝；生成路径不允许覆盖用户拓扑输入或符号链接。身份包含拓扑规则、来源说明及完整确定性内容。

## 当前验证范围

最终native-cache-v4完整ACBA原文件20739字节/20301bp，未裁剪。12阶段22trace：16 COMPLETED（12探测+4科学成功）、5 CACHED、1真实cmsearch坏CM FAILED；2次上下文不一致仅探测完成、无消费者提交。HMM/CM的DATE元数据等长同mtime变化重跑，恢复复用原哈希；模型数值不变。4个科学成功完整integrons/summary数据表逐项等于不改动原始可执行文件显式--linear/--circ对照；23个私有包文件最终字节/权限还原，原安装未修改。

11个原生解析/模型/清单外glob/GemBase/外部解析器/拓扑/解释器单元方法通过；假蛋白/解析器/GemBase布局是读取集合observer，无模型推断。172任务生产主流程使用真实Nextflow/R/report，分类工具和资源扫描明确mock，不声称生物学或真实模型结果。

原vendored nf-test两例迁移至探测/消费者workflow。完整原始固定nf-core提交618f1541382c4ad49eff566dadf13d5ccbd0ebb4的Ecoli软件fixture解压49200bp，属于上游提供的片段，不是完整Ecoli基因组，也未再次裁剪。native case将当前完整表与同一完整输入上原可执行文件--linear的完整表比较；独立控制方法不把软件对照升级为生物学真值。6条框架COMPLETED中，native3任务=原参考科学+探测+当前科学，stub3任务均无推断。副本逐字节/权限等于实际源码，隔离依赖扫描而非替换实现。

## 版本来源与失败记录

原2.0.5 __commit__取当前cwd的git rev-parse；9a270d3是本项目HEAD，不是上游版本提交。源码/模型身份依据独立归档和全部23文件SHA，不采信这个字段作上游来源。TA-016继续开放。

首轮框架已完成科学表一致和空stub检查，但版本字段错取Matplotlib缓存警告路径；当前只提取原生版本行并要求2.0.5，重新跑native/cache、mock及框架均通过。旧失败/被替代收据保留，不计入最终用例分母。先前SeqIO读取句柄warning已用显式with关闭，10方法旧轮及其科学结果不重复累计；新增解释器拒绝后最终11方法。开发插入脚本的一次引号SyntaxError发生在文件修改/任务启动前，亦单列。网络DNS失败均经明确批准后重试，未绕过限制。

Dorado、Medaka、PlasmidFinder、MOB-recon四个隐式消费者仍待接线；41资源对现37候选/4待办。完整可选模型/GemBase/自定义解析器科学分支、完整环境/when/OCI/GPU/provider、TA-092独立接受、TA-016/031/TT-003、GTDB r232、真实shotgun P4、M0–M4/全平台及AWS继续保留。本批无提交/推送/AWS创建/上传/收费。
