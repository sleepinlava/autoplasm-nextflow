# 方法、结果契约与解释边界

通用入口的方法细节从项目 README 移至此处。各平台实际接线见[平台路线](platform-workflows.md)，protocol 独立门槛见 [PROTOCOL](../PROTOCOL.md)。

## 实现说明与已知简化

- 共识整合（`plasmid_consensus`）完整实现了四种策略
  （intersection/majority_vote/weighted_vote/single_tool），权重阈值取
  "支持权重占参与工具总权重 ≥ 0.5"。默认只启用 geNomad；严格多数要求
  支持数大于半数，single_tool 取 geNomad 判定。实际参与共识取决于收到的工具
  结果；启用工具的缺失 contig 记录按未支持处理，不是独立的染色体鉴定。
- `plasmid_structure` 使用 header 标记，以及 **21 bp** 种子的精确 DTR / ITR
  与低复杂度过滤；ITR 延伸上限 1000 bp，DTR 并非统一限制在 1000 bp 内。
  header 阳性标记限于独立的 `circular=true`、`topology=circular` token，
  或序列 ID 的 `_circular` 后缀；`not_circular`、`circular=false`、
  `topology=linear` 等否定标记禁用 header 阳性推断。冲突标记会写入 warning；
  序列重复证据仍独立评估，未命中 header 阳性不等于证实线性拓扑。
  `repeat_type` 记录通过过滤的 `dtr`/`itr`/`dtr+itr`/`none`；单独 ITR
  保留 `method=itr` 和重复长度，`is_circular=false`、`topology_status=unknown`、
  `topology_evidence=none`。只有 header/DTR 支持环状候选，标为
  `topology_status=circular_candidate`；false/unknown 不代表已证实线性。
  原八列保留，追加三个证据字段；环状候选数量仍需组装图与跨接 reads 等复核。
- Platon 固定 1.7，发布原始阳性 TSV/FASTA、详细 JSON、运行记录和明确状态。
  `no_plasmids` 表示本次评估无检出，`not_assessed_length_filter` 表示所有序列
  不在该工具的长度范围；两者不能当作已证实的染色体鉴定。gzip 在任务内解压，
  数据库文件内容参与缓存，子工具或工作线程错误会阻止发布。四处上游零命中日志
  错误仅修复日志，不改变搜索、过滤或共识投票规则；见
  [Platon 原生契约](../docs/tool-audit/contracts/platon-native.md)。
- 序列组成关联采用 TETRA 的双链256维 z-score Pearson 相关：
  按每条 FASTA 记录分别计数，再汇总 MAG 计数；不跨 contig 拼接。
  不能计算完整向量的低复杂度输入不产生伪造的零分或关联。
  `sequence_scores.tsv` 保留所有比较（含未过阈值和无法评分），
  `sequence_method.json` 记录方法与可评分状态；旧关联分数需要重算。
  55份来源的独立分组留出基准未通过阈值验收，因此**停用TETRA宿主链接**。
  `sequence_links.tsv`仅保留空表头，不进入统一宿主关联通道；分数不是宿主归属或概率。
  旧 `link_min_similarity` 参数不再用于此节点；直接脚本的 `--min-similarity`
  仅兼容旧调用，明确提示忽略，不能重新启用链接。分类信息保留在分数表的
  `host_taxonomy`列，不输出阈值通过标记。方法、基准失败与结果迁移见
  [TETRA 方法与校准](../docs/tool-audit/contracts/tetra-sequence-method.md)。
- 长读桥接通过 Rsamtools 解析 SAM/BAM，要求同一 read 有 primary 与
  supplementary 记录，支持质粒与非质粒 contig 连接；默认 MAPQ≥20，并过滤
  secondary、QC-fail、duplicate、paired 等标记。桥接仍可能来自嵌合、重复或
  整合，不能单独证明游离质粒的宿主。
- 共丰度关联输出 Spearman/Pearson、Jaccard、p 值和对所有测试对作 BH 校正的
  q 值；脚本 `max-qvalue` 默认 1.0，流程未传显著性筛选阈值。即使额外按 q 值
  筛选，也不消除组成性、混杂或特征不可比问题，仍应按探索性解释。
- MAG 单独选择 MetaBAT2、CONCOCT 或 SemiBin 时，其 bins 直接进入最终通道。
  同时选择多个分箱器必须在 `--mag_tools` 中显式加入 `das_tool`，否则入口报错；
  选择 DAS Tool 时，汇总全部已选分箱器的可用结果并导出 FASTA。
  CheckM2、GTDB-Tk 与序列宿主关联接收同一套最终 bins；质量/分类工具及 DAS Tool
  不能在没有分箱器时单独启用。CONCOCT 已适配 plain/gzip，并修正重叠切片的 BED
  坐标步长；切片参数保持不变，空成员表不伪造 FASTA。旧默认重叠路径的覆盖度和
  bins 可能受错误坐标影响，应在新目录重算。完整数据库、真实 cohort 的 MAG 链仍需原生端到端验收；protocol 使用
  PlasMAAG cellular bins 的独立路线及其质量/唯一位点门槛，见 PROTOCOL。
- 差异丰度"内部效应量法"为 Welch t 检验 + Hedges' g + BH 校正，默认按
  `--min-prevalence 0.1` 过滤低流行度质粒特征；它不是 MaAsLin2 或 ANCOM-BC 的
  实现，也未建模配对 / 批次。DESeq2 当前为 `~ group`。
- 共享定量使用全部样本组装序列竞争参考，完整 DNA/反向互补一致才去重；
  不折叠相近序列、片段或环状起点旋转，不能解释为家族丰度。参考中任一来源被
  共识判为质粒的序列进入质粒子表，逐来源判断保留在 `sources.tsv`。
  排除未比对、secondary、supplementary 和未知 MAPQ=255，仅保留 MAPQ≥10；
  Bowtie2 并列最佳匹配可能 MAPQ=1，不能只过滤 MAPQ=0。该阈值是明确的
  分配策略，不能保证唯一生物学来源，也会损失相近参考共享区域的计数。
  CoverM 在同一过滤 BAM 上计算 mean/TPM/RPKM/count，末端排除为0；计数为
  read 比对数，双端 mate 分开，不称为 fragment 数。hybrid 跨样本只用短读段，
  不混合长短读计数。DESeq2 / FastSpar 严格要求非负整数 `raw_count`，缺失不会
  回退 coverage。旧统计和共丰度结果需在新目录重新计算，不能与旧本地 ID 表混用。
  本地 MAG/链接用覆盖度路径及其原参数另行保留。参见 [CoverM 固定版本能力](https://github.com/wwood/CoverM/tree/v0.7.0)
  与 [DESeq2 官方输入说明](https://www.bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html)。
- 多样性基于共享质粒表；`beta_normalization` 已由流程传入，通用默认 `none`，
  protocol 默认 `tss`。vegan 推断排除空样本并记录，基础矩阵保留全零样本对距离置0
  的兼容约定，不能解释为生物学相同。protocol 在交付前分别执行质粒与 system 统计。
- 报告为汇总版（本轮样本的质粒数、环状候选数、已观察到输出的分析板块），HTML 由
  `assets/plasmid_report.Rmd` 模板渲染（rmarkdown+pandoc 缺失时回退为简版
  静态页）。输入来自声明的文件及分支输出记录，忽略旧样本和空发布目录；缺少当前
  样本的 FASTA/共识/结构、样本或特征不一致会失败。未观察到输出可能表示禁用或
  空输入门控，不表示已执行且无生物学命中。方法只列出有记录的 producer，并将
  版本声明与请求配置分开；完整 CLI、数据库/模型身份仍未全部记录，不能当作完整
  可复现方法。清单中的文件路径可能指向工作目录，不是原始数据的自包含归档。
  独立调用 `generate_report.R` 需提供 `--manifest` 和 `--samplesheet`；旧的
  `--outdir` 扫描接口已移除，不能用共享发布目录替代本轮输入。
- hybrid 平台的跨样本 **质粒** 和 **contig** 表均由统一参考上的短读重映射提供；
  局部 MAG 等用途的覆盖度仍可合并长短读 BAM。
- PLASMe/PlasX/COPLA 等工具输出列格式存在版本差异，解析器做了宽松启发式
  处理（按列名候选匹配）。

跨样本统计现在先核对完整样本清单、逐样本定量状态和完整特征矩阵。缺失测量、重复样本/特征或不一致的质粒子集会失败；真实零值与全局空目录保留预期样本。多样性按每个样本计算，单特征和全零输入有有限数值及状态说明。网络在流行率过滤后再次去除全零样本，只有至少4个特征且满足 `network_min_samples` 的矩阵进入 FastSpar，并发布筛选状态。分析脚本及辅助库作为任务输入参与缓存判断。DESeq2固定部署模型及TETRA真实宿主阈值仍有独立验收项，见 `docs/tool-audit/status.md`。

DESeq2 为全分组联合拟合后逐对比较，保留默认 ratio 大小因子、原计数过滤与 BH 校正。`11_diversity/deseq2_status.tsv` 记录全体输入样本、进入设计/拟合的样本、实际模型版本及未拟合原因。全零、过滤后零文库或无法计算 ratio 大小因子时不会伪造统计值、补计数或静默删除样本。独立 R 脚本仍支持显式 `--sf-type poscounts`；工作流默认不会自动切换估计方法。普通整数矩阵避免固定部署 1.42 的 table 类型兼容失败。四个统计节点分别暂存丰度和样本表，输入与结果同名也不会改写上游文件。分组标签通过标准 TSV 引号转义保留。
