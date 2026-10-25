# gplas 固定源码、图节点分类与原生验证

> 当前状态：2026-10-25 已完成本契约列明局部修复的统一验收；见 [接受记录](../../../results/tool-audit/20261025-consolidated-acceptance/receipt.json). 下文按历史顺序保留尝试及限制。

2026-10-24。工作证据：`results/tool-audit/20261024-optional-binning-native/`；本批整体验收尚未结束。

## 工具身份与原始依据

官方仓库 [mmb-umcu/gplas2](https://gitlab.com/mmb-umcu/gplas2)，固定 commit `00cf37bec5e44b05ee30c8a4c99e987abbbb4c4f`；源码归档 SHA256 `4c70b36255d83ee6e243373eafd9dbeb95059a59657bcceb0a35044710578d40`。45 个 Git blob 均核对；Git describe 为 `1.1.0-8-g00cf37b`，实际 setuptools-SCM 构建版本为 `1.1.1.dev8+g00cf37b`。生成的 version.py 单独核对，合计守卫 46 文件。完整源码和 R/Snakemake 资源是运行输入；只有 Python wheel 不足以部署。

`tests/prepare_gplas_resources.py` 从固定归档制备完整目录。`gplas-source-proof.json`、`gplas-resource-preparation.json` 记录来源，`gplas-explicit.lock` 和 `gplas-official-pip-requirements.txt` 记录实际 208 Conda / 58 pip 版本。Python3.7.3、R3.5.1、Biostrings2.50.2、Snakemake5.5.4 与官方环境一致。pycosat0.6.3 通过系统编译/链接器构建，包版本不变，保留原失败及成功日志。固定入口为 `gplas`；输入为 GFA 与节点预测表，最终结果为 `<sample>_results.tab`、`<sample>_bins.tab` 和对应 FASTA。

## 输入及连接

用户已明确采用“对图节点重新分类，再运行 gplas2”。这是已批准的输入实体变化，不能投射原 assembled-contig 的分类 ID。

SPAdes 同一成功任务导出的 `assembly_graph_after_simplification.gfa` 独立于普通 contig 阳性通道进入 `GPLAS_BINNING`。入口只允许 illumina/metaspades 或 hybrid/hybridspades；其他组合及缺失完整源码在主入口拒绝。图与组装按实际 sample ID 连接，拒绝重复、缺失和不同 metadata；节点内部样本 ID 使用完整 SHA256 命名空间，最终输出恢复原 meta。

适配器要求显式节点 DNA、唯一数字节点 ID、有效 KC 计数及链接端点。SPAdes4 同时写 DP 与 KC，而固定 R 实现按标签位置读取；DP 在前会产生 NA。适配仅将 S 行规范为 `S id DNA KC:i:count`，保持全部节点 DNA/ID、KC 和 L 边。原始标签保留在状态记录中。官方 KC/节点长度/中位数覆盖算法不变，不能把 DP 深度代替 KC。`gplas-coverage-controls.json` 保存原始 DP-first 的 NA 反例及规范化后与独立计算的数值核对。

节点长度至少 1000 才进入同一选择集、权重及策略的 `PLASMID_DETECTION`；不足长度明确为未评估。图分支共识显式输出全节点域，普通 contig 共识默认行为保持。必须取得完整原始节点的 geNomad aggregated assessment，校验精确 ID 域、四列表头、有限分数范围和和；缺行不能当作阴性。然后把共识决策编码为 gplas 接受的 one-hot 表。该编码不是校准概率，也不是独立染色体鉴定。无种子不启动 gplas；全短序列不启动分类器。节点证据单独发布，不增加组装 contig 的报告计数。

## 运行与结果守卫

`bin/gplas_checked.py` 先核对完整 46 文件，源目录不变；任务私有有效副本只修复两个未格式化的文件名字符串及四处重复节点表的表头读取。保留原始/有效 SHA 与所有子命令状态。原生 Python 丢弃部分非零状态，当前任何子命令失败必须传播，禁止将失败转换为空 bins。

`gplas-no-repeat-controls-v3.json` 保存有效覆盖方差、无重复节点输入的原实现失败/修复成功；早期不合法或未修完对照保留。`gplas-filename-ablation.json` 在四处表头修复保持时单独还原两个文件名缺陷，实际子步骤完成后仍触发错误文件名，支持这两处独立修复。

结果必须满足最终表/成员表对应、原始节点长度/DNA、有限概率和覆盖值、覆盖方差大于零以及 FASTA 成员集一致。原生 Bin 标签包括整数、Isolated_N、Unbinned、Repeat_like；后两类不计为候选质粒 bins。允许重复节点跨 bin，但拒绝相同成员对重复。没有把节点集合当作重建的完整闭环质粒。

所有本地 Python 守卫作为显式深度散列文件输入，见 [缓存契约](helper-cache-inputs.md)。恢复运行使用精确 session UUID；已保留 Nextflow26.10 按 run name 错恢复其他会话的失败尝试，不用它们证明缓存正确。

## 实际证据

- 官方 E.coli GFA/提供的节点预测：未经修改的完整原始 CLI 成功；规范检查器成功，结果身份/DNA 独立核对。这是软件输入输出 fixture，不证明分类准确率。
- `gplas-module-helper-input/run.json`：当前模块两样本（第二份显式合成 DNA 变体）、冷启动、恢复、固定源码私有等长损坏失败和还原恢复通过。
- `gplas-nf-test-helper-input/execution.json`：原 nf-test0.9.5 真实模块一例通过；未声称冷建 Conda 或镜像验证。
- `gplas-workflow-routing-v3/run.json`：三样本 positive/no-seeds/all-short，12 个任务，分类器明确为输出协议 observer，R/适配/gplas 原生。不是完整真实分类器证据。
- `gplas-real-helper-input/run.json`：来自既有成功原生 SPAdes4.1.0 --meta 的同一真实 minigut GFA/contig；317 节点、130 边，210 评估、107 长度未评估。实际 geNomad1.12.0 + 完整 DB1.9，原默认模型/阈值，单独使用官方 --splits16 控制内存。26 个共识质粒种子后完成原生 gplas；当前观察为27成员、22候选 bins（2多节点组及20孤立节点）、1 Unbinned 集合。六任务均 COMPLETED，运行前后来源哈希相同（仅临时空行格式整理后恢复，详见run.json source_capture_note）。
- 同目录 `independent-products.json` 独立比较原始/规范化图完整节点 DNA/域/边与最终成员/FASTA；不导入生产辅助脚本。原始图 SHA256 `e7b3f7c0a5d1d9c1c3b2cb42e3f99d3ddb92b97696464cc02baa6a24d6deb599`。
- `genomad-model-assets-parity.json` 对1.11.1/1.12.0固定源码与各实际安装包的12份模型/校准/分类资产逐字节核对；完整外部 DB 见 `genomad-db-files.json`。rich-click/click 的兼容固定不改变 geNomad1.12.0 工具版本。
- 图身份缺失/重复/不同 meta 的三个失败对照见 `gplas-graph-identity-v2/run.json`；九个入口组合控制见 `gplas-main-helper-input/run.json`。独立单元方法18项通过；共识四策略/默认输出独立回归另存日志。

以上没有独立生物学真值、precision/recall、完整 hybrid 平台原生链或 OCI 证据。随机游走结果可能变化，记录的 bins 数是该次观察，不是对任意数据的验收常数。最终支持声明等待本批验收及剩余审计工作。

2026-10-25 统一复核后，上述局部修复已接受，详见 `results/tool-audit/20261025-consolidated-acceptance/receipt.json` 及同目录 `review.md`、`evidence-recheck.json`。仅关闭列明缺陷；原有在线/全冷部署/完整平台/科学效果限制继续保留，历史ready/待验收文字描述的是当时状态。
