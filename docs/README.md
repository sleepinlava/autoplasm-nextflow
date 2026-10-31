# AutoPlasm 文档导航

更新：2026-10-31。本文档组按当前工作树的入口、配置和数据流维护；源码与配置是执行行为的依据。

| 阅读目的 | 当前文档 |
| --- | --- |
| 项目能力、启动与默认配置 | [项目说明](../README.md) |
| 通用方法和结果解释 | [方法与边界](methods-and-limits.md) |
| 准备输入、选择平台、运行与恢复、读取结果 | [使用指南](usage.md) |
| 五个平台的具体路线、可选分支、统计对象 | [平台流程路线](platform-workflows.md) |
| 代码结构、扩展方式与验证方法 | [开发指南](development.md) |
| 开发目录、缓存与提交层级 | [目录与提交管理](workspace-layout.md) |
| Illumina protocol 资源、实体、门槛与交付 | [短读长 protocol](../PROTOCOL.md) |
| P0–P2 的20步实施进度与证据边界 | [实施状态](protocol-implementation-status-20261031.md) |
| 工具版本、资源接口和历史原生证据 | [工具接口审计](tool-interface-audit-plan.md) |
| 通用五平台交互演示 | [流程网页](analysis-framework.html)；不模拟 protocol profile |

## 当前开发状态

五个平台入口均保留。新增的 `short_read_protocol` 是 Illumina 的 opt-in profile，覆盖 P0/P1/P2：PlasMAAG 主候选、冻结目录、paired-fragment 定量、两级生态/ANCOMBC2、系统/宿主/进化/菌株及最终交付。通用入口与 protocol 的参考目录、计数单位和报告契约不同，结果不可直接混用。

已有95项功能回归、27个真实任务的 protocol 空资格连接路径，以及178条旧 Illumina mock 任务记录。上述为截至本次开发的历史证据，本次文档更新未重新执行科学分析。完整数据库、真实 cohort 且存在合格候选的原生端到端验收按用户要求跳过；benchmark 未实现。详细原生模块证据、失败记录及限制见实施状态和 PROTOCOL。

## 历史材料的使用

[2026-10-17 计划书](计划书.md)、[分析框架草案](analysis-framework-plan.md)、[事实审查](fact-reliability-audit.md)、[早期 mock 记录](mock-e2e-validation.md)、[2026-10-30 需求核查](protocol-requirements-audit-20261030.md) 保留当时的设计或问题快照，不作为当前缺陷清单或最新验收结论。历史截图、工具设计图及 PDF 也不作为当前 profile 的执行图。读取其中的“待实现”“尚未接线”等表述时，应对照实施状态。

维护时同步更新使用指南、路线和开发指南；涉及默认值同时核对 `nextflow.config` 与 `conf/short_read_protocol.config`，避免只改示例。

根 README 的历史验证条目已迁移到[历史开发验证记录](development-validation-history.md)；项目首页不记录开发进度。
