# 测试目录导航

| 路径 | 用途 |
| --- | --- |
| `test_*.py` | Python/R 实体、输入、统计与报告契约回归 |
| `nextflow/` | 共享流程等专项 Nextflow harness |
| `protocol/` | 新 protocol 的 core / connected / native extensions 驱动与 ANCOMBC2 兼容检查 |
| `mock_e2e/` | 外部生信工具替身；验证编排和报告契约 |
| `nf-test/` | 模块/工作流测试、受控 fixtures 与资源准备；其 `.venv` 不提交 |
| `r_mock/` | 特定测试使用的 R 替身，不代表真实统计计算 |

在仓库根目录执行单元回归；需要实际 R/Python 依赖的用例不得以缺环境跳过代替通过。真实接口驱动需先查看 `--help` 并指定 runtime、资源和独立 outdir。开发方式与证据范围见 [开发指南](../docs/development.md)，目录管理见 [开发目录](../docs/workspace-layout.md)。

当前已有验证结果保留在被忽略的 `results/`；资源、模型、环境与大规模运行输出应放在外部资源目录或独立结果目录，不放进 fixture。不要运行 `git clean -fdx` 清理开发环境：这会同时删除恢复缓存与未入库的科学证据。
