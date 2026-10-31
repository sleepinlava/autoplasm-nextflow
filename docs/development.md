# 开发指南

更新：2026-10-31。当前交付状态见[实施矩阵](protocol-implementation-status-20261031.md)，用户入口与结果解释见[使用指南](usage.md)。

## 代码组织与修改位置

| 目录 / 文件 | 职责 |
| --- | --- |
| `main.nf` | 参数与工具选择校验、样本表、五平台分发、跨样本汇总；protocol 运行结束状态 |
| `nextflow.config`、`conf/` | 默认值、profile、模块资源/参数与发布路径 |
| `subworkflows/{illumina,ont,pacbio_hifi,hybrid,assembly}.nf` | 平台输入与前端、共享下游接线 |
| `subworkflows/short_read_protocol.nf`、`protocol_catalogue.nf` | 冻结目录、定量与两级分析、候选整合及最终包 |
| `modules/nf-core/`、`modules.json` | 固定来源的 vendored 模块；存在本地契约修改 |
| `modules/protocol/`、`modules/cross_sample/` | 新协议包装、跨样本工具与报告 |
| `bin/`、`lib/` | 实体/统计/资源身份与来源整合、共享选择器和代码资产声明 |
| `envs/`、`containers/` | 模块环境及特殊部署资源 |
| `tests/`、`tests/protocol/` | 规则回归、编排替身、真实生产模块接口验证 |
| `assets/` | 样本表、schema、报告模板 |

## 开发约束与扩展顺序

优先复用已有子流程、vendored nf-core 模块或上游原生包；包装器只处理真实接口差异和结果契约。统计调用 vegan、ANCOMBC2、FastSpar 等原实现，不在整合脚本中重写方法。当前不开发 benchmark。

新增工具时先明确输入实体、计数单位、坐标、资源身份、空输入资格和输出消费者，再选择最小接入点。需要新 selector 时同步修改 `main.nf` 的选项/校验、默认配置和子流程门控；不要仅添加参数而无可达调用。校验真实边界，不把解析失败转换成零命中，不为了未支持输入增加静默回退。

模块应声明实际文件输出、版本和来源记录，通过 `reportEvidence` 接入本轮报告，避免扫描共享发布目录。数据库、模型和固定源码通过现有资源身份机制进入缓存键；不能只记录路径而忽略内容变更。被缓存任务的原始命令与本次 trace 应区分保存。

修改 vendored 模块时核对 `modules.json` 的来源和已有本地补丁；来源 SHA 不代表当前文件未经修改。更新上游模块应保留资源身份、输出 ID、命令、BAM/FASTQ 和报告等已有契约，先审查差异再替换。

Protocol 中需显式暂存的脚本资产通过 `lib/protocol_assets.nf` 管理，保证 task 内可执行且纳入 Nextflow 缓存。ANCOMBC2 2.8 的兼容 helper 是对指定版本的最小公式处理修正，结果 status 记录应用情况；升级包时重新验证该补丁是否仍适用。

## 必须保持的数据契约

- sample ID、参考 ID 与原始来源一一可追溯。bin 实体和 contig 记录分开；多个无序 contigs 不拼成完整分子。
- 通用统计的共享质粒表与 protocol 冻结代表表不可交换；通用 read counts 与 protocol paired-fragment counts 不混用。零候选样本仍在完整矩阵中；缺失测量不能填作真实零值。
- 代表上的注释统一为 1-based inclusive；近重复成员不能直接继承精确坐标。Bakta FAA 是 protocol 下游蛋白来源。
- AMR、STRESS、VIRULENCE 保留原始类型/方法；ARG 矩阵仅统计 AMR。图/环化/模型分数与独立完整性证据分开。
- system 丰度排除片段关联与多系统歧义成员；MAG 使用保守唯一位点。strain 复用定量合格 BAM，不能旁路过滤重新引入不合格 pairs。
- 组间统计区分禁用、不适用、拟合失败与生物学零值；资格满足后失败不回退另一种方法。A/B/C/D 保留支持、反证和替代解释。
- 最终包包含两级统计、版本、数据库内容身份、代码/命令及 SHA256 manifest；失败状态只能按已知任务标签归属样本。

## 验证方法与已有证据

按照改动影响选择已有检查。仅文档修改检查链接、示例参数及 TypeScript 编译，不启动耗费数据库/计算的科学任务。规则改动使用针对性单元回归；编排改动使用 mock/DAG 和相关生产模块接口；算法准确性必须另行设计真实数据验证。

```bash
python3 -m unittest discover -s tests -p 'test_protocol_*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
tsc -p docs/tsconfig.json
```

这些 Python 回归部分需要 R、vegan、pysam、PDF 环境等，不能将环境缺失的跳过记作通过。真实接口驱动器在 `tests/protocol/run_core.py`、`run_connected.py`、`run_native_extensions.py`；先用 `--help` 查看实际 runtime、资源和 outdir 参数。它们调用生产模块；connected 当前走空候选资格路径，并非有候选完整 cohort。

截至2026-10-31的结果：95项功能回归（含22项 protocol）、27个真实任务空资格连接链、178条旧 Illumina mock 记录。证据汇总位于 `results/protocol-validation/20261031/completion-validation.json`；细目与原生工具、ANCOMBC2 追加重跑限制见 [PROTOCOL](../PROTOCOL.md)。results 为本地忽略产物，其他检出环境未必包含。早期多平台 mock 记录只证明对应日期的编排，不把其提升为当前全部平台的原生验收。

完整数据库/真实 cohort 的原生端到端验收已按用户要求跳过，benchmark 未实现。单元测试、上游阳性 fixture 和空资格连接链均不证明阈值校准或宿主/转移准确性。

目录的保留、忽略和提交层级见[开发目录与提交管理](workspace-layout.md)，测试分类见[测试导航](../tests/README.md)。

## 文档维护

当前文档从 [docs 首页](README.md) 进入。新增或变更平台能力同时更新路线、使用示例与根 README；protocol 门槛/资源/产物同步更新根 PROTOCOL 和实施矩阵。历史审查按日期保留，在入口标注历史范围；交互网页展示通用五平台，修改 TS 后生成对应 JS。版本化的文档应有精确 `.gitignore` 例外，不应依赖本地被忽略文件传达使用条件。

2026-10-31 目录整理与分层提交前，复跑上述 protocol、共享目录/丰度、统计身份/完整矩阵、diversity、DESeq2 状态及 PlasMAAG 输入相关回归：95项全部通过（85.443秒），日志为 `results/protocol-validation/20261031/precommit-workspace-regression.log`。此次未重新执行完整资源 cohort 或 benchmark。
