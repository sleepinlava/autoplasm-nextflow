# 辅助脚本与恢复运行契约（TA-089）

> 当前状态：2026-10-25 已完成本契约列明局部修复的统一验收；见 [接受记录](../../../results/tool-audit/20261025-consolidated-acceptance/receipt.json). 下文按历史顺序保留尝试及限制。

2026-10-24，工作批次 `results/tool-audit/20261024-optional-binning-native/`。本批尚未整体接受；既有 receipt 保持冻结。

## 已复现的差异

Nextflow 26.10.0 的实际运行中，在 `script:` 局部以 `file(...).text` 读取 Python 辅助脚本，再插入 heredoc，并不保证脚本内容进入缓存键。对真实 GPLAS2_NODES 辅助脚本作等长、保持 mtime 的状态字符串修改，原实现恢复运行仍为 CACHED，结果保留旧字符串。不能以当前仓库 SHA 代替缓存任务实际执行脚本的 SHA。

原缺陷与修复的六次原生调度对照见 `helper-cache-probe-path-v2/run.json`：原实现冷启动 COMPLETED，修改后错误复用；修复实现冷启动 COMPLETED、未修改恢复 CACHED、修改内容后 COMPLETED 并输出新状态、还原内容后恢复原缓存。所有修改只发生在私有副本；没有分类器 observer，没有据此推断生物学效果。尝试过的 ext/global 方案失败记录保留，未纳入生产实现。

## 当前修复

18 个 process / 16 个模块文件改为显式普通文件输入，使用 `cache 'deep'`。单脚本为一个 path 输入；多脚本为一个 tuple 输入，各脚本保留原来落地文件名，直接执行。生产及 `.nf` 测试调用一并补齐辅助输入；11 份 `.nf.test` 中 25 个辅助文件表达式同步迁移。精确清单见 `helper-input-interfaces.json`、`helper-input-callers.json` 和 `helper-input-nftest-complete.json`。25 是文件表达式数，不是测试用例数。

[Nextflow 缓存说明](https://docs.seqera.io/nextflow/cache-and-resume)列出任务输入与深度文件内容散列。本项目以上述实际反例及修复运行作为验收依据，不将文档描述当作已执行证明。

历史模块对照必须保留原模块的输入数量。`tests/module_harness.py` 在生成私有对照时依据所选模块接口保留或删除新增辅助输入，并将辅助路径固定到实际仓库，避免证据目录中的 moduleDir 指向错误。已同步 SemiBin、GTDB、RGI、OPERA-MS、CONCOCT 的对照入口；十个当前/旧版生成结果已检查。旧版原生对照尚未全部重放，不能声称全量原生验证完成。

## 当前验证与限制

- 当前 GPLAS2 实际双样本运行、精确 session UUID 恢复、私有源码等长损坏拒绝、还原恢复通过；见 `gplas-module-helper-input/run.json`。
- 当前 gplas 原生 nf-test 0.9.5 一例通过；独立核对成员及 DNA，见 `gplas-nf-test-helper-input/execution.json`。
- 当前完整图节点 geNomad/共识/gplas 原生分支六任务完成，运行前后来源哈希相同（临时空行格式整理后恢复，详见source_capture_note）；见 `gplas-real-helper-input/run.json`。独立原始图 DNA/全部节点域/边核对见同目录 `independent-products.json`。
- CONCOCT 实际原生明文/gzip 切分、损坏 gzip、错误源码拒绝四场景通过，见 `concoct-helper-input/run.json`。
- Illumina 和 hybrid/hybridspades 模拟端到端通过；使用外部 CLI observer，不计作原生分类、组装或科学效果证书。旧 mock 提供无真实执行计划的伪 FASTG 导致来源校验失败；现明确不生成图，图路径由单独原生测试覆盖。
- 当前 main 原有 75 个拒绝场景重放通过；gplas 另有七个拒绝与两个允许解析预览。预览不等于分析执行通过。

TA-089 保持 in_progress，直到所有受影响调用/测试与必要原生检查纳入下一批验收。旧 receipt 及其中的历史输出不因本次修改而被改写或升级为当前源代码认证。

2026-10-25 补验：从已接受的 285 来源边界恢复字节完全一致的 CONCOCT 模块与辅助脚本，在真实 CONCOCT 1.1.0 切分中将私有 helper 的循环变量作等长、保持 mtime 的损坏。原实现恢复运行 CACHED，而强制冷启动实际 NameError；当前显式输入冷启动成功、原样恢复 CACHED、损坏后失败、还原后恢复原缓存。八阶段的实际脚本字节、原始 BED 坐标/切片/DNA 与 UUID 见 `results/tool-audit/20261025-batch-review/accepted-concoct-helper-cache-v2/run.json`。这证明缺陷存在于此前已接受模块；18 个迁移 process 中 15 个为既有实现，3 个为本批新 gplas 实现。

当前 18 个 process 的输入数/deep 声明、36 个 `.nf` 调用和 23 个 nf-test `when` 片段通过独立词法检查；见同批 `helper-call-audit.json`。此检查不等于 Groovy 编译或 nf-test 实际执行。扫描器首次遗漏 `input [1]` 的合法空格产生六条误报，原报告保留，修正扫描器后通过；生产/测试输入未因误报修改。

同批 `plasx-complete-helper-input/` 完成当前两阶段原生自动注释/全十组 de novo 搜索/原模型打分，独立公式和官方 predict 验收见 `plasx-complete-independent/run.json`。196 个基因、39 条评分序列，公式最大差异 2.22e-16；自动注释20阳性与预计算19阳性的既有差异保留，不据此声明分类准确率。源代码前后相同。PLASMe 当前迁移也完成原生阳性、真实 Transformer 和独立 DNA 校验，见 `plasme-current-helper/run.json`。其他节点仍按当前运行结果逐项补齐，不能据这些局部结果关闭 TA-089。

当前实际生产模块的可复用缓存回归为 `tests/run_helper_cache.py`；`helper-cache-current/run.json` 的四次调度依次为 COMPLETED/CACHED/COMPLETED/CACHED，改变和还原状态字符串均与实际执行相符。它只修改私有副本并保持字节数及mtime，不依赖历史模块快照。


本批当前补验汇总：`helper-native-matrix.json` 逐一关联18个迁移process的真实task、当前模块SHA和实际落地helper字节；17个为原生工具/输入处理，GTDB仅原生解析/选取且分类模型明确observer。PlasX2、PLASMe1、COPLA1、Platon1、SemiBin1、蛋白桥接13、HOTSPOT1、RGI3、OPERA1、真实minigut SPAdes/Recycler4，共28条本轮原生COMPLETED（不含此前gplas/CONCOCT及GTDB边界）。各自DNA/表/模型/失败语义断言见run.json；无全调用者、完整nf-test、全GTDB分类、准确率或AWS认证。HOTSPOT首次引用已清理私有模型路径失败，v2使用原始完整模型目录通过，首次失败保留。矩阵扫描器起初误以为每个helper都直接出现在命令行；RECYCLER_REFERENCE验证库实际被提取器import，后改为同时核对精确Python导入依赖，未改生产代码。TA-089现ready，仍未统一接受。

2026-10-25 统一复核后，上述局部修复已接受，详见 `results/tool-audit/20261025-consolidated-acceptance/receipt.json` 及同目录 `review.md`、`evidence-recheck.json`。仅关闭列明缺陷；原有在线/全冷部署/完整平台/科学效果限制继续保留，历史ready/待验收文字描述的是当时状态。
