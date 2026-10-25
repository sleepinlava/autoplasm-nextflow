# 当前审计进度

由 scripts/refresh_status.py 从台账生成；日期 2026-10-21。基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

- 生产 .nf 台账：104（当前=102，按用户要求退役=2）；investigating=102，not_started=0，matched=0。历史分母保留。
- 问题：65；S0=21，S1=2，S2=42，S3=0。TT 前缀为测试逻辑/覆盖问题，TA 为生产契约问题。
- tests 来源台账：109（当前=105，按用户要求退役=4）；investigating=105，not_started=0。包括 harness/config，不能作为测试用例分母。
- 运行记录：118 条；类型、退出码和限制见 runs.jsonl。已验证修复=25，按用户要求退役=2，其余未决=38（S0=7，S1=2，S2=29）；退役不计修复通过。生产/测试补丁与基线以各修复receipt为准。

原 main 拒绝输入场景：45/45；当前 main 文件哈希对应=45。重放不增加场景分母；不是完整输入契约或 nf-test 框架认证。映射见 p0-main-cases.tsv。

include 扫描：102 文件、173 导入符号、96 文件主入口词法可达、0 未解析 include、133 配置声明；不证明动态连接或执行成功。

已复验：当前共识 33/33 方法（原28+PlasX5）、PLASMe适配7/7方法；R smoke上一批54/54检查、检测连接3场景26任务（分类器CLI observer，真实R消费者）；linking 单元 22/22。SCAPP检测/binning按用户要求退役，旧参数和预测输入明确拒绝；人工反例及上游 parser 结果见 runs.jsonl。缓存的 Nextflow 26.10.0 build 14055 已可通过 Java21 启动；多 queue 乱序复现产生错配，补 JVM opens 后无缓存序列化警告。当前真实节点证据：QUAST5.3.0 native对锁定pUTI89 plain/gzip基础指标及同序列reference比对通过（同一工具）；另已恢复Bowtie2 2.5.4/SAMtools1.21固定版本原生栈，原build/align8任务确认旧接线静默错参考、keyed候选正确；TA-022四个Bowtie2调用点现已修复并公开原生22任务验证；完整平台与长读仍需另验。Recycler已完成同图BAM/BAI/k接口修复，真实minigut原工作流4任务输出1条1871bp图自环序列，及k33/k55受控正负/失败传播验证；非科学准确率结论。PlasX TA-023仅消费者分数解析已验证；PLASMe TA-024/053适配ready，固定官方writer受控7场景16任务通过但完整模型/DB推理未验。RGI TA-028实际原生数据库选择已验证：两份完整CARD、VIM-77错库对照、真实质粒及原downstream；6叶任务（含1预期失败）+2子流程任务/6方法通过，不是临床性能基准。MAG TA-008/030局部路由和DAS导出已验证：13受控observer场景201任务+原生R关联；实际DAS1.1.7完整官方gut样本15个bin独立成员/长度/DNA一致，最终阳性使用原生产参数，真实无达标bin失败传播；45个main独立拒绝场景及8个直接include检查。CONCOCT TA-032/055/056局部验证：17真实helper场景、原MAG两个样本12真实节点（固定官方DNA+受控合法BAM），各122 bins成员/DNA及plain/gzip一致；默认重叠切片BED越界修复，切片/聚类参数不变。路由13旧场景+1空CONCOCT=14场景217任务复验，actual CONCOCT I/O helpers/native R与core/model observers分开。TA-054可选DB接口已真实验证：8原生任务，完整六文件DB的空格/db保留名/默认3正例15 bins独立预期一致，预检错误及自定义lookup读入负例正确失败，32任务MAG/R回归通过；不认证任意DB的生物学有效性。TA-036结构误判局部修复已验证：独立线性SCP1不再凭ITR计为环状，13结构/3报告方法、54smoke、5原结构+1原REPORT任务及检测26任务通过；图/reads确认与TA-015生产报告屏障仍未解决。TA-031/049仍未决。缺少nf-test launcher及完整工具/DB环境，全量P3/P2/P4与科学效果基准仍未认证。

未完成：M0 动态配置/完整 channel 图/历史证据归属及默认真实基线；固定版本 contracts、各项最小修复、平台与阳性回归；tests 的剩余断言和 fixture 审查。全量审计未完成，不给支持路径放行结论。

详细阶段记录见 journal.md，当前缺陷以 findings.tsv 为准；历史日志中的当时计数不代表当前状态。
