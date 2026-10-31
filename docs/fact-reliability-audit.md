# AutoPlasm 分析路线事实可靠性审查

> 历史快照：正文保留原日期的设计、发现与验证结论，不代表2026-10-31的全部当前状态。最新入口见[文档导航](README.md)、[平台路线](platform-workflows.md)及[实施状态](protocol-implementation-status-20261031.md)。

审查日期：2026-10-17。范围：当前工作区源码、README、原计划书及方法官方资料。
基准提交：`f364043`；审查起点已存在未提交实现修改，结果对应工作区快照，不仅对应该提交。

[交互框架](analysis-framework.html) · [分析计划](analysis-framework-plan.md) · [更新后的 README](../README.md)

## 结论

五平台入口、必选检测主干与大量可选模块在源码中可追溯，但“实现存在 / 工程测试通过”
不足以支持完整的质粒生态推断。优先缺口是 **跨样本特征可比性、真实计数与设计适配、
环化语义、MAG 输出路由，以及真实数据与报告完整性验收**。

本次修正文档与网页中的错误或过强表述；没有修改生产分析算法、默认参数或已有用户代码。
下文“已修正文档”不表示对应实现缺口已修复。

证据状态：`observed` 为读到的源码行为 / 实际检查结果；`inferred` 为基于该事实的解释或风险；
`unknown` 为未执行 / 未获得证据的事项。优先级 P1 表示会直接影响生物学结论，P2 表示设计或工程可靠性需补强。

## 逐条审查

| 编号 | 原说法或待核实点 | 源码事实与依据（observed） | 可靠性判定与处理 |
|---|---|---|---|
| F01 | 默认进行多工具共识 | [config](../nextflow.config) 仅默认 genomad；[检测工作流](../subworkflows/plasmid_detection.nf) 始终调用 geNomad，其他按开关实例化 | 应写“支持多工具共识，默认单工具”。已修正文档 |
| F02 | 默认 ensemble 带来独立交叉支持 | [共识脚本](../bin/plasmid_consensus.R) 的 weighted_vote 为支持权重比例 ≥0.5；四默认权重为 0.6/0.15/0.15/0.1 | 四者都参与且用默认权重时，geNomad 单独支持即可通过。得分不是校准概率；工具也不保证独立。页面可复现此规则 |
| F03 | 共识输出的所有判定列等价 | 同一脚本的 `plasmid_call` 按所选策略产生，`combined_prediction` 为 ensemble 多数类标签；现有测试专门覆盖二者不同的情形 | 不能将 combined_prediction 直接当成实际筛选规则；最终候选 FASTA 与 plasmid_call 对齐。缺失 contig 行按未支持处理，不是独立染色体证据 |
| F04 · P1 | “20–1000 bp 末端重叠判定环化” | [结构脚本](../bin/plasmid_structure.R) 为 21 bp 种子；DTR 精确匹配，ITR 可延伸至 1000 bp，有低复杂度过滤；ITR 也写 is_circular=true | 旧算法描述已修正。ITR 是反向末端重复，不自动证明首尾闭环；当前字段有过度解释风险。应拆分重复类型 / 闭环支持并做 reads / 图验证（inferred，待改实现） |
| F05 · P1 | 已有跨样本非冗余目录就能直接做定量比较 | [comparative.nf](../subworkflows/comparative.nf) 建立 catalog；[plasmid_abundance.nf](../subworkflows/plasmid_abundance.nf) 仍用每样本自身候选作参考，没有读入 catalog 代表序列 | 目录未形成统一回贴链。样本间同名 contig 不等于同一 feature；不同名字也可能指向同源质粒。统计必须先解决可比性 |
| F06 · P1 | 默认“质粒多样性 / 差异丰度” | [cross_sample.nf](../subworkflows/cross_sample.nf) 将 ch_contig_merged 传给 DIVERSITY 和 DIFFERENTIAL_ABUNDANCE；plasmid 表用于 DESeq2 / 网络 | README 改为 contig 统计；不能将其直接称为统一质粒 catalog 上的生态变化 |
| F07 · P1 | “CoverM 不输出原始计数” | [配置](../conf/nfcore_upstream.config) 仅请求 mean/tpm/rpkm；[合并脚本](../bin/merge_abundance.R) 写空 raw_count。CoverM 官方支持 count [S3] | 限制来自本项目配置，不是 CoverM 能力。已更正文档；后续需明确 read / fragment 与多重比对规则 |
| F08 · P1 | DESeq2 / FastSpar 输入为可用计数 | [DESeq2](../bin/deseq2_plasmid.R) 与 [network_prepare](../bin/network_prepare.R) 在 raw_count 缺失时取整 coverage | 取整只改变数值形式，不建立原始计数的观测机制。不能作为计数模型输入已有效的证据 [S2]；当前只能视为待验收的代理分支 |
| F09 · P1 | 两组各 ≥3 即足够统计检验 | 内部脚本为 Welch + Hedges’ g + BH，DESeq2 为 `~ group`；没有批次 / 配对协变量；DESeq2 自身最小组样本阈值 3 写死 | 阈值不是功效保证，完全混杂不可识别 [S2]。独立生物学重复与 contrast 要先明确；`min_group_replicates` 仅传入内部差异模块 |
| F10 | 序列宿主关联为“余弦相似度 + GC 惩罚 / 密码子” | [sequence_similarity_link.R](../bin/sequence_similarity_link.R) 使用 canonical 四核苷酸计数，经 Markov 期望和方差构造 z-score，再取 Pearson 相关 | 当前是 TETRA 风格实现，未建模密码子；不宜未经独立基准验证声称与外部算法逐位等价。已修正 README 与页面 |
| F11 · P1 | 任一 MAG binner 都能接入下游链 | [mag_host.nf](../subworkflows/mag_host.nf) 的 ch_final_bins 初始来自 MetaBAT2，DAS Tool 可替换；CONCOCT 只经 DAS Tool 路径进入，SemiBin 未接最终通道或 DAS Tool | 仅开 CONCOCT / SemiBin 不能保证 CheckM2、GTDB-Tk 和 sequence linking 获得 bins。源码接线可确认；具体运行后果需场景测试。需修路由，不能宣传完整互换链 |
| F12 | MetaPhlAn profile 即质粒宿主 | [host_prediction.nf](../subworkflows/host_prediction.nf) 产出群落 profile；[host_linking.nf](../subworkflows/host_linking.nf) 是单独默认关闭的分支 | 群落组成与质粒宿主不同。模型和共丰度都应报告为候选，不能直接赋予真实宿主身份 |
| F13 | 共丰度显著性已经保证宿主关系 | [coabundance_link.R](../bin/coabundance_link.R) 计算相关、Jaccard、cor.test 与全测试对 BH；脚本 `max-qvalue` 默认 1.0，模块未传显著性阈值 | 有 q 值并不等于默认执行显著性筛选；校正也不解决组成性 / 混杂 / 特征 ID 问题 [S6]。应记录证据类型及限制 |
| F14 | 长读桥接直接确定宿主 | [longread_bridge_link.R](../bin/longread_bridge_link.R) 要求 primary 与 supplementary，MAPQ 默认 ≥20，过滤 secondary / QC-fail / duplicate / paired；对同一 read 连接的质粒与非质粒 contig 计数 | 该规则比“任意双比对”严格，但还不能排除嵌合、整合和错配；非质粒 contig 也不必然具备可信宿主分类。应作物理连接候选证据 |
| F15 | CRISPR 已实现；HOTSPOT “高置信” | [main.nf](../main.nf) 对已启用的 CRISPR 明确报错；HOTSPOT 要求 home/db/models 路径 | CRISPR 未实现。HOTSPOT 接线存在不等于已在本数据校准，删除无本项目证据支持的“高置信” |
| F16 | ≥20 样本就能得到可信共现网络 | config 中 run_network=false；[fastspar.nf](../modules/cross_sample/fastspar.nf) 仅调用相关 / 协方差估计 | 没有接官方 bootstrap / pvalues 步骤 [S5]。门槛仅用于运行，网络应作探索性共变，不宣称互作 / 转移 |
| F17 | “hybrid 跨样本统计使用短读” | [hybrid.nf](../subworkflows/hybrid.nf) 的质粒合并表来自 short；CONTIG_COVERAGE 合并长短读 BAM，而默认 DIVERSITY / 内部差异读取 contig 表 | 原句过度概括。现在区分质粒表与 contig 表；长读按 map-ont，不能无条件声称支持 HiFi hybrid |
| F18 | 多样性已做标准化，零距离表示相同 | [diversity.R](../bin/diversity.R) 的 Bray–Curtis 默认 beta-normalization=none；全零样本对 NaN 改写为 0；模块没有传 tss | 原始 coverage 距离可能受深度影响；全零替换只是兼容输出，不是生态相同。需明确归一化、空样本策略和敏感性检查 |
| F19 | 所有平台都有相同 QC / 宿主能力 | [assembly.nf](../subworkflows/assembly.nf) 无 read QC / 丰度 / MAG / linking；[pacbio_hifi.nf](../subworkflows/pacbio_hifi.nf) 未接 MultiQC；assembly 默认 MetaPhlAn 被跳过 | README 与页面写明平台边界；PlasmidHostFinder 要在 assembly 显式启用 |
| F20 | MMseqs2 95% / 80% 表示同一完整质粒或物种 | [配置](../conf/nfcore_host_comparative.config) 设置 min-seq-id=0.95、c=0.8、cov-mode=1；官方定义后者为 target coverage [S4] | 不是双向覆盖，不是普适质粒物种定义。需要考察截短与模块化序列对聚类的影响 |
| F21 · P2 | 流程完成后报告一定完整 | [report.nf](../modules/cross_sample/report.nf) 传入完成 trigger，但 [generate_report.R](../bin/generate_report.R) 仍扫描 publish 目录 | 完成 trigger 不等于发布完成屏障；旧结果也可能混入。需使用本次显式产物与状态清单；这是源码推导风险，未在本次制造真实运行故障 |
| F22 | 历史通过数证明当前真实分析可靠 | README 与 tests/mock_e2e 中的历史记录使用外部工具 mock；本次工作区也含后续 R 脚本修改 | 历史结果保留并标注来源；本次重跑单独记录。不能将随机合成序列的 mock 阳性当作 geNomad 性能证据 |

## 对旧计划书的差异处理

`docs/计划书.md` 的“权威规范”是设计定位，并非实时实现证明。至少以下内容不能直接当作当前事实：

- CRISPR 列在工具清单中，但实现明确拒绝。
- 宿主序列方法包含密码子描述，当前脚本并无该模型。
- Python / pandas 级依赖的描述已落后于当前 R / Bioconductor 脚本；不是“标准库即运行”。
- docker / singularity “仅预留接口”的表述过时，当前配置已启用相应 profile；但镜像依赖就绪仍需实际验证。
- “未配置数据库则可选步骤默认关闭”不准确：由工具开关决定启用，已启用且缺参数时启动失败。
- 参数、模块存在不证明所选组合具有完整接线；MAG 路由是具体反例。

本次通过 README 明确“设计意图 / 当前源码 / 审查差异”的关系，保留原计划书以避免把旧设计历史改写成已经完成的事实。

## 建议的验收顺序

1. 用同名不同序列、异名同源序列的样本检查 catalog / ID 映射；所有样本回贴统一参考，检查多重比对与漏检。
2. 确认原始计数单位及分配规则；以可识别的组别、配对 / 批次模型验证统计端点，报告效应量与误差。
3. 分开记录 DTR / ITR / header 与真正闭环证据；修复并测试 MetaBAT2 / CONCOCT / SemiBin / DAS Tool 组合的最终输出。
4. 对宿主候选保留原始证据和竞争解释；网络补齐统计稳定性与显著性步骤。
5. 以真实阳性 / 阴性样本、固定数据库和实际工具进行小规模端到端验收，再检查报告只使用本次完整产物。

## 本次验证

本节只记录本次实际运行，历史数值不计入。

- `python -m pytest tests/ -q`：未能运行，当前 Python 环境没有 pytest；不计通过。
- `python -m unittest discover -s tests -p 'test_*.py' -v`：**43 项通过**，
  126.836 秒，退出码 0。覆盖现有 catalog、共丰度、长读桥接、丰度合并、共识和
  序列组成测试；不等于未包含在测试集中的结构、统计、MAG 等模块均已科学验收。
- HTML 静态检查：无重复 ID、所有静态锚点和本地文件链接有效、无外部运行时依赖；
  内联 JavaScript 通过 `node --check`；`git diff --check` 无空白错误。
- 初版页面使用最小 DOM 替身进行 Node VM 逻辑检查：70 个平台 / 视角 / 章节组合、
  512 个共识判定组合、零权重、3,200 个样本门控组合、3 种证据文案和计划文本生成通过。
  这是函数与模板检查，未模拟浏览器布局、真实事件分发或实际下载 / 打印对话框。
- 未重新执行真实 Nextflow + 生信数据库端到端；不声称真实工作流就绪或生物学性能通过。
- 初版检查时没有可用浏览器；后续已按用户要求通过 Computer Use 实际完成桌面 / 手机视觉检查、
  五平台路由、14 阶段详情、参数联动、共识规则与 Markdown 下载验收。页面也改为原生
  HTML + CSS + TypeScript，以实际 Nextflow 流程设计为主体。当前验收与截图见
  [Computer Use 验收记录](visual-acceptance.md)；前述 Node VM 数字保留为初版历史检查。

## 方法依据

外部依据于 2026-10-17 检索。官方滚动文档说明工具原理或能力，不证明本地 vendored 版本或数据库已经实际运行。

- **S1** [geNomad 原始研究](https://www.nature.com/articles/s41587-023-01953-y) 与 [官方 quickstart](https://portal.nersc.gov/genomad/quickstart.html)：候选识别、输出与末端重复类型。其 topology 区分 DTR / ITR；这不构成本项目 ITR 即闭环的验证。
- **S2** [DESeq2 官方 vignette](https://www.bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html)：计数模型与设计矩阵；输入数值为整数不是把任意度量取整后即有效的证明。
- **S3** [CoverM 官方仓库](https://github.com/wwood/CoverM)：支持 count 与不同 coverage / 归一化度量；应区分工具能力和项目启用方法。
- **S4** [MMseqs2 官方参数定义](https://github.com/soedinglab/MMseqs2/blob/master/src/commons/Parameters.cpp)：cov-mode=1 指 target coverage。
- **S5** [FastSpar 官方工作流](https://github.com/scwatts/fastspar)：bootstrap 和 pvalues 为独立于相关估计的步骤。
- **S6** [Linear and nonlinear correlation estimators unveil undescribed taxa interactions in microbiome data](https://www.nature.com/articles/s41467-022-32243-x)：组成数据对相关解释的影响；不能据此将本地任意相关边当作已验证互作。

科学计划的组织采用 NGS Analysis Workbench 的 `design-ngs-analysis` / microbiome 指南与 Rosalind 的证据分层要求。
实际完成的是本地源码审查、文献 / 官方资料核查和文档构建；未调用插件的计算执行接口。
