# TETRA 序列组成方法与独立阈值校准

2026-10-22；用户明确选择“按标准 TETRA 方法修正，并单独校准关联阈值”。TA-039 的数值修复与科学阈值验收分开，不能用方法测试关闭完整 S0。TA-040 为跨记录虚构窗口；TA-058 为分类表暂存名造成输入损坏。

## 方法定义

方法标识 `tetra_markov256_v1`。采用 [Teeling等2004年 TETRA 方法](https://doi.org/10.1186/1471-2105-5-163)的双链、256维 z-score 与 Pearson 框架；另可参照[固定pyani0.2.12实现](https://github.com/widdowquinn/pyani/blob/v0.2.12/pyani/tetra.py)。本实现独立计算全部合法重叠窗口，不能称为逐字兼容pyani：该版本的序列尾部循环/补计数、仅对观察到的tetra更新等细节不同。已保存的上游blob与旧反例保留。

每条FASTA记录分别处理正向序列和反向互补序列；数完最后一个合法窗口，不能跨记录连接。小写转大写、非ACGT符号作为断点，不能删除后把两侧连接。对MAG先汇总各记录的di/tri/tetra原始计数，再计算期望；不是逐contig z-score平均。保留全部256个有序四核苷酸槽，正反互补不折叠，回文在两个链各计一次。

对 `XY ZW`（连续四碱基XYZW），`E=N(XYZ)*N(YZW)/N(YZ)`，`Var=E*(N(YZ)-N(XYZ))*(N(YZ)-N(YZW))/N(YZ)^2`，`z=(N(XYZW)-E)/sqrt(Var)`。两个完整、有限、非恒定的256维向量作Pearson相关，保留负分。方差无法定义或为零、完整向量恒定时标为不可评分，不造零分、不用可计算槽子集改变向量定义；这项边界策略明确属于本实现，不声称原始软件稀疏输入完全相同。长度不足1000bp的候选仍按原规则跳过。

2026-10-24用户决定更新：`sequence_links.tsv`保留六列空表头，不再生成宿主链接，也不进入HOST_LINKING统一links通道。`sequence_scores.tsv`继续保留所有实际比较、负分、不可评分状态和MAG分类信息，移除threshold/threshold_pass，以disabled_uncalibrated记录关联停用。`sequence_method.json`明确host_links_enabled=false。旧link_min_similarity不再传给节点，直接CLI旧参数合法时明确忽略，不能恢复链接。标准数值计算不变；历史136维分数不可比较，需新目录重算。详见 [仅保留分数的当前契约](tetra-score-only.md)。

## 数值和接口验收

`tests/test_tetra_math.py`以Python逐窗口/逐链计数和标量公式作独立参考，8方法覆盖全部合法窗口、回文双计数、256槽、序列尾部、碎片边界、重排/反向互补不变、歧义断点、退化profile和Pearson。原接口11方法保留原断言并增加零阈值不能把退化输入变成关联；旧周期性“正例”换成事先定义的非周期自匹配，另将周期输入明确测试为不可评分。

`tests/run_tetra_sequence.py --work-dir <fresh> --references <structure-reference.lock.json目录> --before-dir <本批before>` 用锁定真实pUTI89/SCP1 DNA作明确自匹配/碎片/无关输入的数值控制；这两份DNA不构成已知宿主配对。两份原LINK_SEQUENCE任务24配对分数/分类标签/状态和输入hash核对。旧人工序列反例0.9588941484、新标量参考及实际CLI0.4549428621，跨过0.7；不是把新输出倒推真值。MAG切片不是重组为闭环等额外方法。

`tests/run_sequence_taxonomy_input.py`实际冻结旧module+R任务复现：taxonomy.tsv暂存symlink与合并输出同名，head读取前被重定向截断、源fixture变0字节且任务仍0/分类NA。修复把分类输入暂存到 `host_taxonomy??/*`，单表及两域同名表的两个当前任务均保留原字节和准确分类marker。对照只损坏独立临时fixture；不是修改用户数据。旧真实输入若经该路径调用，需核查源表并从可靠上游重建。

原HOST_LINKING/可选输入与重复键控制共11任务、54项R smoke和4项测试退出码oracle另验；无真实分类器、已知宿主效果、镜像、远端executor或nf-test框架认证。TA-040/058仅按此局部边界关闭；该段为2026-10-22数值/接口验收；随后科学阈值失败，现按用户决定停用链接，不能将停用误称为校准通过。

## 校准工具、数据约束和验收未决项

调用 `python3 bin/calibrate_sequence_threshold.py --scores <一个或多个sequence_scores.tsv> --labels <labels.tsv> --endpoint recorded_assembly_host --min-calibration-precision 0.9 --out <calibration.json>`。另一个可选endpoint为experimental_permissiveness，两者不可混用。前者是有记录的分离/组装宿主归属，不能把其他候选宿主解释为实验上无法感染；后者需独立实验许可/拒绝证据。

标签表必需字段：sample_id、plasmid_id、host_id、label(0/1)、split(calibration/holdout)、plasmid_group、host_group、label_evidence。ID局限于sample_id，不能合并不同样本相同本地contig/bin名。分组应由预先登记的序列簇/宿主谱系定义，数据管理员须核对组定义及原始标签来源；工具检查组与实际实体分离，不能凭字符串独立验证生物学标签。校准/留出集在质粒组和宿主组均不得重叠；两组均需显式正/负标签。不能从“未检出”生成负标签，不能从首次TETRA输出选标签，也不能用这些人工自匹配控制充当已知宿主基准。

工具只在calibration集的生产参数域[0,1]候选阈值中，在最低precision约束下最大化balanced accuracy；并列时先specificity再较高阈值。holdout只能评估，不能反调阈值。输出完整TP/FP/TN/FN、precision/sensitivity/specificity、两类不可评分数量及输入hash；指标仅覆盖eligible配对，不可评分是弃权而不是真阴性。没有满足约束的阈值时输出no_feasible_cutoff并exit2；泄漏/缺标签证据/缺分数/方法不符/非有限值直接拒绝。不会自动写回生产配置。

7个方法和3个CLI控制验证选择/泄漏/缺失/不可评分/未找到阈值等实现；数值fixture得出的0.8不构成生物学校准，留出集故意不佳的结果也完整保留，不宣称方法有效。2026-10-23已完成55真实来源的NCBI元数据核验、预登记分组留出、实际30,250对评分和阈值复核，数值通过而预定科学验收失败：选定0.9534655970247977的完整质粒留出precision57.1%、sensitivity14.3%，片段无预测阳性。详见 [来源宿主基准](tetra-source-benchmark.md)。不能安装该阈值或把历史0.7称为已校准；科学阈值仍未通过；2026-10-24按用户选择停用未校准链接，TA-039仅关闭错误链接风险，未来方法/数据设计须另立独立验收。

证据：results/tool-audit/20261022-tetra-method/receipt.json；原始失败/被截断fixture、最终运行及所有边界记录保留。其他完整审查问题仍以findings.tsv为准。
