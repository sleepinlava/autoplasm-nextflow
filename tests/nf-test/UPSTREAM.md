# 上游来源与适配边界

本集合复用 nf-test 和 nf-core 的完整测试实现，不新增测试引擎，也不通过
伪造命令输出实现流程成功。生产代码、已有模块测试和已有快照均不在本次改动范围。

| 来源 | 固定版本 | 复用方式 |
| --- | --- | --- |
| [nf-core/mag tests](https://github.com/nf-core/mag/tree/db7772f748fd160aabc0e7fde40c15ea8f388664/tests) | `db7772f748fd160aabc0e7fde40c15ea8f388664` | 保留完整 `default.nf.test` 于 `upstream/mag-default.nf.test.reference`；适配 workflow success、trace、按产物分区发现文件及内容断言；参考平台和坏样本表用例 |
| [nf-core/modules](https://github.com/nf-core/modules) | 当前仓库 `modules.json` 中各模块的 `git_sha` | 直接运行已 vendored 的 fastp、fastqc、samtools/sort、megahit 完整测试和快照，不再复制或改写 |
| [nf-core/test-datasets mag](https://github.com/nf-core/test-datasets/tree/f450b2e3f8d45b6101978ddeda7e1a522b9be25b) | `f450b2e3f8d45b6101978ddeda7e1a522b9be25b` | 两份 minigut 双端样本、ONT 数据、预组装 FASTA、宿主参考及 geNomad 小型真实数据库 |
| [nf-core/test-datasets modules](https://github.com/nf-core/test-datasets/tree/618f1541382c4ad49eff566dadf13d5ccbd0ebb4) | `618f1541382c4ad49eff566dadf13d5ccbd0ebb4` | 模块测试输入和 gallus PacBio fixture |
| [nf-test](https://github.com/askimed/nf-test/releases/tag/v0.9.5) | `0.9.5` | 使用原生执行、断言、快照、JUnit 和 dry-run 功能 |
| [QUAST](https://github.com/ablab/quast/tree/c3eb988a2fa8a815e1b0bfff55a58cb8d6ff0152) | `quast_5.3.0` / `c3eb988a2fa8a815e1b0bfff55a58cb8d6ff0152` | PyPI 未提供该版本，uv 从官方固定提交解析可选流程依赖 |

`upstream/LICENSE` 保留 nf-core/mag 的 MIT 许可，`upstream/test-datasets.LICENSE`
保留数据仓库的 MIT 许可。下载数据另存 `results/`，不把压缩数据和数据库加入 Git。

## 适配与证据

- `validation.nf.test` 是 AutoPlasm 特有输入契约的本地适配；不能称为逐字复制的上游测试。
- `integration.nf.test` 保留上游按输出分区验证的模式，将输入、输出路径及断言映射到
  AutoPlasm。没有使用首次运行生成的快照作为正确性依据。
- `prepare_data.py` 只下载、校验和转换样本表：每个文件锁定提交、长度和 Git blob SHA1，
  下载回执还记录 SHA256。压缩包通过 Python 3.12 的 `filter='data'` 解包。
- minigut 是上游已有的合成数据；其两份样本不构成有统计功效的处理/对照重复。
  禁止改名复制成六个样本以制造差异分析或网络的通过结果。
- 该数据未提供经过确认的质粒阳性真值，P2 不评估质粒检出率、灵敏度或特异性。
  不把宿主基因组误当作质粒阳性，也不强制每个样本必须检出质粒。
- P2 覆盖所选核心流程从输入到报告；它关闭 typing、host prediction、MAG、linking 和
  comparative 等需要额外数据库的可选分支。不能表述为所有可选工具均完成验证。
- P1 中 upstream 自带的 stub 用例仍保留；统计时须与实际运行工具的用例分开。
  P2 没有 `-stub-run` 或 mock 可执行文件。
- 部分其他 vendored 测试缺少 untar、gunzip、makedb 等 setup 模块，nf-test 全库发现时
  会给出警告；本次 P1 明确选择不依赖这些缺失模块的四套测试，不改生产模块填补依赖。

测试运行结果和环境限制见 [RESULTS.md](RESULTS.md)。
