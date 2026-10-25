# TETRA 数值与 MAG 边界

当前输出更新（2026-10-24）：标准256维数值保留；科学阈值验收失败，按用户决定停用未校准宿主链接。以下为历史缺陷取证，当前契约见 [tetra-score-only.md](tetra-score-only.md)。

基线 f57d0f91454ee0c99cf462ac9093bdf68349991a，2026-10-20。

TA-039：本地声称 z-score math ported EXACTLY from pyani。但固定 [pyani v0.2.12 tetra.py](https://github.com/widdowquinn/pyani/blob/v0.2.12/pyani/tetra.py)（blob c0d11a434afd3a3b30c44418dad7772f8b34d2ea）逐条 FASTA、逐正反链计数，在256种四联词上做相关；本地将di/tri/tetra先按反向互补折叠，回文仅计一次，使用136类及有限共同槽。这不仅是重排：回文/非回文相对权重以及 Markov 分母都会改变。此处固定上游作为“完全移植”声明的对照，不将该历史实现视为生物学真值或无错误的唯一算法。

人工4000bp序列，seed=20261020，第二条以0.18概率替换随机碱基。原 R 函数 score=0.958894148388，原 upstream 两个数学函数 score=0.43147980812542064；原 CLI 在默认0.7阈值输出0.9589。这证明方法选择影响关联纳入，未证明某一真实宿主错误。测试只用相同周期序列score1会遗漏该差异。

参考执行：原 upstream calculate_tetra_zscore/tetra_clean AST保持不变；因无Biopython，以最小SeqIO FASTA/反向互补适配器提供本次纯ACGT序列，相关用独立标量Pearson公式。R按原源文件解析定义，仅不执行最后main()，然后另行原CLI确认。没有安装/声称完整pyani执行成功。完整源码、命令、fixture、z向量与适配器位于 results/tool-audit/20261020-tetra/，run.json记录退出码与限制。

TA-040：load_bins 将多个MAG记录直接 paste(..., collapse="") 后计数，跨contig端点产生人工窗口。上游逐record累计。相同4000bp分为2条记录，上游z向量最大差0.435331；本地读取后与单条拼接序列完全相同。应逐record累计计数，再计算一次整体期望/方差；不能改成简单平均各contig z向量。碎片化本身会丢失真实跨断点窗口，故不要求分割/未分割数值完全一致，而应断言没有凭空添加跨记录kmer。

这两项属于方法/结果兼容性任务，不能只改注释或放宽测试完成验收。需要声明目标版本/定义，先固定独立数值真值，再比较多个组成/长度/片段数/歧义碱基、反向互补与已知宿主基准。生产未修改。
