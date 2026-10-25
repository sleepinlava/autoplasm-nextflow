# TA-047 数值输入契约与修复边界

2026-10-20；当前五脚本hash以results/tool-audit/20261020-numeric-input-matrix/run.json为准，包含TA-048标识符修复后的代码。

目标：入口损坏值不能成为有效测量0。零代表明确数值；样本未检测到某feature的矩阵填0，与一个存在但为空/损坏的测量单元不同。schema及有效数值应在聚合、统计或写出前验证，异常应报告来源路径、数据行、sample/feature及字段，而不是压制转换warning后补0。

证据：../numeric-input-matrix.tsv。5脚本×6输入共30次原生CLI，逐个单元变动；NA/blank在network raw_count的coverage fallback单列，不声称该fallback本身是解析错误。

原定要求（实施结果见下方更新）：

- merge：校验提供的Mean/coverage语义与值；缺列、空值和明确零不得静默等价，输出保持合法数值的原有精度/字符串表示。
- diversity/internal differential：必需sample_id/contig_id/coverage schema，coverage必须可解析、有限、非负；验证在矩阵补齐前完成，不改变明确缺feature的填0行为。
- network/DESeq2：先明确实际选中的数值源，再校验该字段，不能把垃圾、无穷或负数改为0。TA-011的空raw_count选源与TA-012的coverage-count单位仍独立待决，不能借数值校验宣称单位已修复。
- header-only/零输入保持明确的合法空结果策略；存在记录但值缺失需显式决定/诊断，不能无声变成空生物学结果。
- 回归包括schema缺列、空字段、NA/NaN/Inf、负数、垃圾文本，来源/样本/特征上下文，失败无输出；普通整数/有限小数、明确0、合法空输入保持对照；再运行原wrapper及跨样本集成。

初次探针阶段只完成行为证据，未实施validator；该阶段状态已由以下修复记录取代。无科学模型、阈值或统计单位变化；不提供真实生物学/P4认证。预期修复将使此前被静默接受的损坏输入明确失败，应重新评估相应历史统计。

## 2026-10-20 TA-047 数值校验修复完成

五个入口在输出/统计前校验实际使用的数值为有限非负值，缺列明确报错；无效单元给出来源/行/sample/feature/字段。merge保留合法coverage原字符串精度，网络保留缺raw_count时使用有效coverage策略；不再用0代替损坏文本、无穷、负数或缺少的有效测量。DESeq选中的缺raw_count现在提前失败，TA-011计数来源仍待解决；TA-012单位/rounding未修改。

新增6方法共35拒绝子场景通过；原5方法garbage基线5失败。原identity7/7、merge5/5通过。重跑30-case矩阵，五脚本合法zero输出与修复前逐字节一致；network原NA/blank fallback保持。原四模块8任务对照通过（早于最终network缺列guard）；最终7次原模块gate另核验当前五源码hash，包括五类坏输入任务明确失败且不发布TSV，以及network/merge正常输入成功。完整命令/输入/trace/.command及哈希在results/tool-audit/20261020-numeric-validation-fix/receipt.json。

TA-047关闭，增量patch以HEAD+TA-048为前态，已与原30-case源码hash核对。没有宣称完整CROSS_SAMPLE/P4、DESeq2声明1.42容器或科学基准通过；原生1.52。此前损坏数值不再被接受，应从已验证测量重新生成受影响统计。失败测试使用隔离新输出目录，不承诺清理旧结果目录。
