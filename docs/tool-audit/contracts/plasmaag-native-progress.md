# PlasMAAG 原生生产接线进度（TA-018、TA-090）

> 当前状态：2026-10-25 已完成本契约列明局部修复的统一验收；见 [接受记录](../../../results/tool-audit/20261025-consolidated-acceptance/receipt.json). 下文按历史顺序保留尝试及限制。

2026-10-25，进行中，尚未形成本批接受 receipt。用户已明确批准修复项目隔离环境。所有运行路径以下列工作目录为根：`results/tool-audit/20261024-optional-binning-native/`。

## 固定来源和错误边界

官方 [RasmussenLab/PlasMAAG](https://github.com/RasmussenLab/PlasMAAG/tree/a6b39ac6e8e38ccc8419fc7b4a3f304b0f511803) commit `a6b39ac6e8e38ccc8419fc7b4a3f304b0f511803`，85 Git blob 核对，官方 SCM 构建版本 `1.0.2.dev142+ga6b39ac6e`。完整 Snakefile/scripts 是额外运行资源，不能由 Python wheel 替代。

原生 CliRunner 丢弃子命令返回值：真实无效 Snakemake 参数使子程序退出2，但原 CLI 退出0；`bin/plasmaag_checked.py` 同一边界退出1并记录子程序2。新守卫检查85原始文件、实际安装的 Python 源文件和精确 SCM 版本；将同一安装构建的 C 扩展复制进任务私有有效源码。原始源码不变。守卫只检查执行边界，最终产物由独立适配器和测试检查器核验，不把目录存在或外层退出0当作成功。

`--plasmaag_genomad_splits` 默认0保留原生默认；显式非零值只在任务私有的两份 Snakefile 实际 geNomad 命令上添加官方资源分区选项，保存原始/有效 SHA，恢复时再次校验。没有修改模型、阈值或图算法。`--plasmaag_vamb_arguments` 默认为空；测试使用上游小数据参数，不带入生产默认。上游默认非确定性 Node2Vec 固定8个 worker，因此当前生产 task 要求至少8 CPU；此前2线程的原生/生产记录不能解释为所有子程序只使用2 CPU。

## 生产输入与样本语义

旧 lowercase 入口、逐样本阳性质粒和 CoverM 表已移除。`subworkflows/plasmaag_binning.nf` 在全部组装和原始配对 reads 齐备后运行一次完整 cohort；样本按 ID 稳定排序，拒绝缺失、重复或不一致 meta。metaSPAdes 使用同一原生任务保存的 `contigs.fasta`、`contigs.paths`、`assembly_graph_after_simplification.gfa`；MEGAHIT 输入模式使用完整 FASTA。支持范围为 Illumina + metaSPAdes/MEGAHIT，其他平台在入口拒绝。

`bin/plasmaag_inputs.py` 不按检测阳性预过滤，检查 DNA/唯一 ID/完整配对、同一 reads 路径复用，接受 plain 和按 magic 识别的 gzip（含大写扩展名）。保存原 meta、源哈希及 S0C/S1C 命名空间映射。输出检查最终成员表、三类互斥、分数域、原生基因组200kb写出门槛和逐条原始 DNA；按样本恢复原 contig ID 和 meta，合法零质粒 bin 发显式状态。

`SPADES.plasmaag_assembly` 在移动/压缩 contigs 前保存三件套。`spades-plasmaag-bundle/run.json` 原生 SPAdes4.1.0 测试通过，原始/压缩 DNA 字节及路径/GFA来源均核对；这不是本项目完整 Illumina 从 QC 到 PlasMAAG 的端到端认证。

## 原生与框架证据

官方 [Zenodo 两样本 fixture](https://zenodo.org/records/17953597)完整归档495,494,417字节，MD5 `d96c3fad91e04a7827327e511aea58a3`，SHA256 `0bc6dc1d9861a72fb5022ef1af64fd867069e9501c869e7d40e011339b8b4932`。使用完整 geNomad DB1.9、默认模型和分类阈值。上游 fixture 是软件测试数据，不能作独立生物学真值。测试显式 VAMB `-o C -e 200 -q 25 75 150 --seed 1`，资源 splits16；Node2Vec 原始默认未固定随机种子。

- `plasmaag-official-native-v2/native/resume-allowed-ipc.json`：实际 VAMB200epoch 和后续原生规则完成。首次 Conda 解释器激活失败、沙箱 IPC 失败及精确终止记录均保留；批准本机 IPC 后复核私有源码并恢复，不替换 VAMB 计算。独立产物核验111个质粒 bins/123成员，14个满足200kb的基因组 bins/3102写出成员，79个病毒 bins/147成员。
- `plasmaag-production-native-v2/run.json`：真实生产 cohort 单任务完成，9m43s、峰值约2.4GB；112个质粒 bins/129成员，两个原 meta 正确恢复。该次请求2 CPU但上游 Node2Vec实际8 workers的限制已记录，后续生产加入至少8 CPU保护。
- `plasmaag-nf-test-declared-v3/execution.json`：实际 nf-test0.9.5 一例通过，8 CPU/6GB，新建声明核心环境，任务258.959s；独立原始组装/成员/样本导出核验126个质粒 bins/140成员。嵌套环境复用，不是全部嵌套环境冷部署。
- `plasmaag-megahit-compatible-native/run.json`：8 CPU真实生产 contigs 模式完成，4m21s、峰值约2.5GB；独立核验123个质粒 bins/139成员，A.1的80个和A__1的43个 bins 各自原ID/DNA/meta正确。输入是完整官方 SPAdes FASTA 作为 MEGAHIT 兼容 FASTA（一个大写GZ、一个plain），故不认证实际 MEGAHIT 组装器。
- `plasmaag-product-controls/run.json`：真实产物正例及私有 DNA 篡改、缺失成员、NaN、等长保留mtime源码篡改共5场景通过；原始产物不变。
- `plasmaag-validation-current/run.json`：8个主入口拒绝、2个合法解析预览和6个真实 cohort 完整性拒绝通过，零分析任务；不是生物学执行。

各次 bin 数不同，未更新快照或改种子追求一致。`plasmaag-repeat-differences.json` 记录原始/生产 geNomad aggregated 表哈希相同，而 Node2Vec/邻域产物不同；与上游默认随机性一致，但不是独立的因果或准确率验证。`tests/check_plasmaag_native.py` 独立读取原始输入及最终文件，不导入生产适配器，不把首次输出当真值。

测试框架首次失败均保留：Groovy `Map.get(key,default)` 会插入默认值，多 channel 共读 ConfigMap 导致并发修改；两个测试 harness 现复制记录并用 getOrDefault。第二次请求 process_high 的64GB超出本机内存；随后 withName 明确8 CPU/6GB才成功，不能把资源启动失败计为工具失败。

## 声明环境及剩余部署边界

`envs/plasmaag.yml` 固定科学依赖、官方 CPU Torch2.13.0+cpu URL及SHA、pyrodigal3.6.3、psutil5.9.8和固定 Git源码；补齐编译器及 Conda24.11.3。`plasmaag-declared-install.json` 和 `plasmaag-declared-with-conda-versions.json` 证明全新核心环境构建/实际版本；pip check 无破损，VCS direct_url实际提交一致。没有把失败的 editable 构建记成功。

三个内部环境采用官方 strobealign0.16.1/samtools1.22.1、Python3.12/networkx3.4.2/fastnode2vec0.0.7、geNomad1.11.1。geNomad 加入兼容的 Click8.1.8/rich-click1.8.3。远程部署先遇连接和 h5py 校验失败，未绕过校验；163个原始缓存归档核验后使用 Snakemake 原生平台 pin。当前 prepared 资源的 **file URI pin仅供本机**，不是可移植发布锁。远程锁另存，`h5py-source-probe/run.json` 后续3个官方URL都返回预期SHA，先前校验失败不能推断上游永久不可用。全新可移植嵌套环境、CPU架构约束、容器及 AWS 还未完成。

因此 TA-018/TA-090 保持开放；当前事实是生产接线及真实框架已通过局部验证，不能继续写“尚未接线”，也不能提前关闭完整部署和批次验收。`environment-recovery-checkpoint.json` 是较早恢复检查点而非本批最终 receipt，当前源码已有后续变化。

## 当前部署补充与成功复核

新增 `envs/plasmaag-genomad.linux-64.pin.txt`：163个官方远程归档 URL 与 SHA256，SHA `ae1e493114b464e956d5d4210700143ae15a1b42419d377e39a9f3fd24634d6e`，不含本机 file URI。资源准备器核对格式/来源并复制到新 prepared 资源，85个上游文件仍保持原始哈希。该解析包含 x86_64_v4 包，需核对目标CPU，不能宣称适用全部 x86_64。

当前守卫总是使用任务私有副本，只在私有 geNomad YAML 添加 Click8.1.8/rich-click1.8.3兼容依赖，记录原始/有效 SHA；原工具版本1.11.1、模型、阈值不变。`plasmaag-private-source-controls/run.json` 的3个实际CLI对照通过：不传splits的默认help、完全校验私有源码后恢复、等长保留mtime的私有依赖篡改在子程序前拒绝。

`plasmaag-nf-test-remote-pin-v4/execution.json` 保留在线失败：Snakemake远程pin失败后回退YAML，最终geNomad归档HTTP000，真实子程序1由守卫传播；没有推理成功或空结果成功。另一个全新离线缓存的首次尝试也失败：Conda24.11.3从原始归档自动创建的缓存记录有MD5、缺SHA256，无法匹配精确SHA的远程URL MatchSpec。只在新私有缓存记录补充独立核验的实际归档SHA256，不修改共享缓存元数据/归档、不绕过校验、不更改锁。`plasmaag-remote-pin-cache-proof-v2/run.json` 以同一远程URL/hash锁新建163包环境成功；包身份及6个原始模型、实际1.11.1 CLI再次核对。

**`plasmaag-nf-test-remote-pin-v5/execution.json` 实际框架一例通过**，总耗时368.7秒，8CPU/6GB，10项捕获源码前后一致。复用已有strobe/node2vec，另新建并实际使用 `599bf2058781945f99d7c06b3050d26f_` geNomad环境；163个remote URL/SHA身份、6模型资产与固定原始来源一致，日志明确使用pin且无YAML回退，详见同目录 `deployment-proof.json`。这是完整cohort真实训练/原生分类/最终写出，独立检查85个质粒bins/90成员，14个基因组bins/2933写出成员，95个病毒bins/147成员；A.1的56个和A__1的29个质粒bins各自保留原ID/DNA/meta。未把默认随机性下的变化改成固定快照。

这次成功证明离线原始归档缓存的精确重建及当前守卫的完整执行，不证明远程网络可用、三个嵌套环境全部冷部署、任意CPU或AWS。TA-018/090及本批最终接受仍待统一复核；旧v3结果继续只认证各自源码，新v5独立认证当前部署补丁。

2026-10-25 统一复核后，上述局部修复已接受，详见 `results/tool-audit/20261025-consolidated-acceptance/receipt.json` 及同目录 `review.md`、`evidence-recheck.json`。仅关闭列明缺陷；原有在线/全冷部署/完整平台/科学效果限制继续保留，历史ready/待验收文字描述的是当时状态。
