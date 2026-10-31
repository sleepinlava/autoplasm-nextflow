# 开发目录与提交层级

整理日期：2026-10-31。生产路径保持现有布局，便于 Nextflow 模块解析、测试定位和历史证据复查。

## 目录分层

| 层级 | 目录 / 文件 | 管理方式 |
| --- | --- | --- |
| 入口与配置 | `main.nf`、`nextflow.config`、`conf/` | 版本管理；按平台/profile 接线 |
| 分析实现 | `subworkflows/`、`modules/`、`bin/`、`lib/` | 版本管理；复用上游实现，保留本地契约 |
| 环境与资源契约 | `envs/`、`containers/`、`modules.json` | 版本管理；不包含大型数据库/权重 |
| 输入与展示 | `assets/` | 版本管理；示例与模板不包含真实样本数据 |
| 自动验证 | `tests/test_*.py`、`tests/nextflow/`、`tests/protocol/`、`tests/mock_e2e/`、`tests/nf-test/` | 版本管理测试源码、受控 fixture 和资源准备脚本；运行环境与缓存忽略 |
| 当前文档与历史依据 | `docs/`、根 `README.md` / `PROTOCOL.md` | 精确放行维护文档、网页源文件、审计契约和历史视觉证据；本地草稿及大型导出图不自动入库 |
| 可恢复计算状态 | `.nextflow/`、`.nextflow*`、`work/` | 本地保留、Git 忽略；不搬移、不自动清理 |
| 科学结果与数据 | `results/`、`data/` | Git 忽略；结果需通过 manifest/独立存储交付 |
| 本地开发杂项 | `.local-dev/bin/`、`.local-dev/logs/`、`.local-dev/scratch/` | Git 忽略；不作为生产输入 |
| 机器专有状态 | `.aws/`、`.agents/`、`.codex/`、`.code/` | Git 忽略；凭据不得进入提交 |

本次将根目录的 `lazygit` 移至 `.local-dev/bin/lazygit`，将 `blast-log.txt` 移至 `.local-dev/logs/`，将历史异常发布目录 `null/` 移至 `.local-dev/scratch/null/`。这些都是既有本地产物，未删除；运行日志或旧报告中的原路径仅作为当时的记录保留。Nextflow 恢复目录、数据库、测试 runtime 与验证结果未搬移。

`docs/tool-audit/` 必须允许新增契约文件；不要在后续追加同名目录忽略项，否则会覆盖放行规则。新增当前指南需要同步精确放行和文档导航。截图是历史验收证据，不能代表当前功能已重新通过视觉验收。

## 提交分层

按依赖顺序拆分，便于审查和定位；历史开发积累不按文件扩展名混成一个提交：

1. **目录与规则**：忽略规则、目录用途及测试导航。
2. **独立修复**：FASTP 普通/压缩 FASTQ 命名修复。
3. **协议组件**：目录、paired 定量、系统/宿主/注释/进化与交付的脚本、模块、环境和资源证据输出。
4. **统计方法**：vegan/ANCOMBC2、公式与区间兼容、共享质粒表消费。
5. **流程接线**：profile、主入口、平台分支、MAG、报告和失败状态。
6. **回归测试**：规则、真实接口驱动与 mock 契约更新。
7. **用户与开发文档**：平台路线、使用/开发指南、实施状态和历史范围说明。

前三至六层组合后构成完整 protocol 功能；新增组件提交本身不等于已从主入口启用。验证证据应注明测试范围，不把 mock、空候选链或接口 fixture 称作真实 cohort 或 benchmark。提交记录仅包含源码、环境、测试和维护文档，不纳入本地缓存、数据库和运行输出。
