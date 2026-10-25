# 当前验收边界

全量审计未完成，不能给出支持路径放行结论。当前盘点 101 个 .nf 文件，162 个导入符号全部可解析；95 个文件在 main.nf 的词法 include 闭包中。平台矩阵覆盖 Illumina、ONT、HiFi、hybrid、assembly 五条声明路径，均无当前真实运行认证。

当前未决：17 个 S0、1 个 S1、39 个 S2（含 9 个 TT 测试逻辑问题）；累计台账58项，TA-043已修复并验证，其他57项仍未决。见 findings.tsv。

验证：现有共识单元测试 9/9 通过；SCAPP 人工接口复现失败（表中阳性、FASTA 为空），不能算真实工具执行或科学基准。Platon/Recycler 历史 JUnit 保留为未含代码 SHA 的历史执行证据。缺少已配置 Nextflow/nf-test runtime，P0/P2/P3/P4 当前未复验。

M0 的动态配置、完整 channel 依赖图、历史运行来源迁移和当前默认运行基线仍未闭环。核心、扩展、结果语义和发布回归继续按原计划执行；未排除任何能力以改变覆盖分母。

跨样本非空人工复现还证实局部 feature ID 合并错误、空 raw_count 误判为全零计数，以及单 feature diversity 指标 NA。统一参考/计数单位的修复尚待科学结果兼容性评估。

报告人工复现还证实旧目录样本混入、空目录当作分析存在、方法声称未执行步骤。report_data.json 未声明发布输出。宿主方法的本地接线已检查，尚无完整科学基准认证。

可选包装器已进一步核对 PlasMAAG/COPLA 固定源码，COPLA 参数复现失败；整样本多质粒作为一个 query 是独立科学实体问题。GPLAS2 固定版本仍缺，保留 evidence_missing。

实际缓存 Nextflow 已恢复并复现多样本输入错配；此前 runtime 完全不可用的描述仅为当时 PATH/launcher 检查结果，不再代表缓存 JAR 状态。nf-test 和真实工具链仍未恢复完成。tests 已纳入同步逻辑审查，详见 tests-review.md。

数据准备 8 项单元与 R smoke 54 个检查通过；数据库下载失败传播有独立反例。四套配置当前解析通过；完整工具调用、统计数值真值与其他 profile 仍未验收。

PlasX/PLASMe 的真实格式消费者差异已复现；当前依赖安装和真实分类回归仍缺，不能将 synthetic CLI writer 视为真实 PLASMe 通过。

注释/typing 核酸-蛋白适配、RGI 查询库选择和 MOB recon 发布存在未决差异；vendored 测试辅助依赖尚未完整恢复。

MAG 的 final bin 导出、分类扩展名和 CONCOCT 压缩输入仍有独立未决契约差异；upstream test 显式参数与 production caller 不同。

长读长宿主去除存在输出桶错配；mock 未正确模拟 -0；FASTP SE emit 失配已 stub 复现。sample-ID 局部 5 场景通过，不替代全主入口回归。

52个vendored主模块已完成固定上游来源比对，45一致、7本地差异归档；该项不是52个工具验证通过。环境完整锁定与多后端同一性仍缺。

结构语义有新增 ITR/否定标题反例；正常 Welch 单样例独立数值对照通过。101 个 .nf 均已进入 investigating，并无 matched/真实全量验收完成结论。

网络准备阶段过滤后全零样本列仍保留（TA-038）；FastSpar 实际工具运行与网络真值尚未认证。

63份 tests 来源已完成首轮源码阅读，均仍 investigating；实际 merge→coabundance 局部链通过，固定当前来源哈希。真实工具、独立科学真值、边界补测和测试断言修复尚未闭环。

TETRA方法数值和跨MAG记录边界新增未决；独立参考函数对照不等于宿主准确性认证。

未知工具名入口校验缺失TA-041；原校验函数局部运行复现，完整P0仍待验收。

共识非法权重和合法样本名导致工具身份错判新增TA-042/043，原CLI复现；修复和回归未完成。

共识重复ID处理TA-044未决；人工不一致输入被接受，不声称上游正常输入必然触发。

报告合法样本名归并TA-045新增S0，当前完整文件也会混合样本统计；原R已复现。

HOTSPOT CRLF转换TA-046未决；PHF固定部署源码/模型仍缺，当前不能放行。

多样性非法数字TA-047未决；正常双feature alpha/beta独立对照通过仅覆盖该fixture。

数字sample ID在DESeq被合并TA-048新增未决；固定1.42源码证据补齐不等于该版本运行通过。

TA-048确认不局限于DESeq：多样性、内部差异分析和网络输入也受ID类型推断影响；literal NA和数字位置索引已有独立反例。

CheckM2文件列表准备固定源码与两组helper probe通过；这不是实际质量模型通过，MAG最终路由/导出未决项仍在。

当前原main三类非法样本表已实际验证：对应诊断、trace/command均无分析任务。并非完整nf-test/P0或成功平台基线。

当前validation.nf.test的11场景已有原main独立运行对应证据，全部按预期拒绝且无任务；未知工具/平台能力等未覆盖缺陷仍未决，nf-test/JUnit本身未恢复。

SemiBin合法no-bin结果被必需FASTA glob拒绝TA-049未决；原NXF格式探针不是实际分箱P3。

IntegronFinder --gbk stub缺陷TT-007复现，真实注释和当前四套P1不因此自动判失败。

sequence-optional重复键负向用例TT-008实际假通过，不能将该runner exit0用于重复拒绝验收。

CRISPR guard局部实际观察符合拒绝行为；main-disabled无CRISPR报错不代表完整成功路径。负向oracle映射已归档，TT-008未修。

当前已有一项真实P3局部证据：原QUAST5.3.0 native对锁定真实pUTI89 plain/gzip均通过基础统计独立核对。此前“当前P3未复验”是阶段历史；全量P3/五平台E2E仍不放行，模块整体investigating。

MultiQC native1.33对真实QUAST汇总兼容性通过；模块声明1.35仍缺对应验证，TT-009未决。

QUAST native真实局部证据扩展至相同reference比对；初始ccache权限降级后已构建依赖重跑通过，初始exit0非通过结果保留。全平台/全工具仍未验收。

TA-043本地适配修复验收通过（共识11/11、原wrapper2/2），当前生产源码已修改。其他缺陷/全平台验收仍未完成，不能整体放行。
