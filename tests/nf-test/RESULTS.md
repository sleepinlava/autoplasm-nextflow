# 实际执行记录：2026-10-16

本次仅新增测试资料，未修改生产代码或上游快照。执行基于
`731f98063bce69a59d03cfa989f46e34ed0b9c3a` 加当时工作区已有改动；期间工作区仍有
其他修改，因此这些结果不等于对该 Git 提交本身的验证。

| 级别 / 套件 | 实际执行 | 通过 | 失败 | 说明 |
| --- | ---: | ---: | ---: | --- |
| P0 输入契约 | 5 | 5 | 0 | 在最终 uv 环境中重跑通过 |
| P1 fastp | 18 | 18 | 0 | 9 项真实工具 + 9 项 stub |
| P1 FastQC | 12 | 12 | 0 | 6 项真实工具 + 6 项 stub |
| P1 MEGAHIT | 4 | 4 | 0 | 3 项真实工具 + 1 项 stub |
| P1 SAMtools sort | 11 | 10 | 1 | 8 项真实工具（1 项失败）+ 3 项 stub |
| P2 五个平台 | 5 | 0 | 5 | 均由缺失外部程序阻断，未完成端到端验证 |

P1 合计 45 项：26 项真实工具测试中 25 通过、1 失败，19 项 stub 均通过。
P0/P1/P2 去除重试后的总计为 55 项、49 通过、6 失败。P2 dry-run 的 5 项用例发现
不计入通过数。没有通过更新快照、降低断言或替换真实可执行程序来消除失败。

## P1 的失败

`SAMTOOLS_SORT / bam_csi_index` 的进程执行成功，BAM reads MD5 一致：
`894549ee3ced6b5ca2eed2563a985217`。失败发生于 CSI 文件的原始字节 MD5 快照匹配，
两个值为 `43f545200e545ca2075c475d194a5130` 与
`01394e702c729cb478df914ffaf9f7f8`；工具版本同为 SAMtools 1.24。

目前证据不足以判断这是索引语义差异还是序列化/压缩字节差异，保留为未解决失败。
没有修改生产实现，也没有接受新快照。

## P2 的环境阻塞

| 平台 | 首个报告的失败过程 | 缺失程序 | 退出码 |
| --- | --- | --- | ---: |
| Illumina | `ILLUMINA:MULTIQC` | `multiqc` | 127 |
| assembly | `ASSEMBLY:PLASMID_DETECTION:GENOMAD` | `genomad` | 127 |
| ONT | `ONT:NANOPLOT` | `NanoPlot` | 127 |
| hybrid | `HYBRID:NANOPLOT` | `NanoPlot` | 127 |
| HiFi | `PACBIO_HIFI:HIFIADAPTERFILT` | `hifiadapterfilt.sh` | 127 |

以上仅为首先暴露的依赖，不能推断安装这四个程序后所有平台即可通过。
P2 在 `workflow.success` 处失败，下游产物内容断言尚未到达；不声称这些断言已通过。
数据库和数据确已下载：9 个文件均校验了固定 Git blob 身份、长度及下载后 SHA256。

## 环境及证据

- uv 0.12.23、Python 3.12.15，实际解释器前缀为 `tests/nf-test/.venv`。
  基础依赖 `uv sync --locked` 已成功安装，含 pytest 8.4.2；94 个依赖解析已锁定。
  `pipeline` extra 只完成解析锁定，未完成安装，不能视为 P2 环境就绪。
- Java 21.0.12、Nextflow 26.10.0、nf-test 0.9.5；插件 nft-utils 1.2.1、nft-bam 0.7.0。
- P1 使用独立 `/tmp` 路径中的 fastp 1.3.6、FastQC 0.13.0、SAMtools 1.24、
  MEGAHIT 1.2.9、pigz 2.8；它是 Java/原生程序测试，不安装 Python 全局依赖。
- 原始 JUnit：`results/nf-test/p0-final.xml`、`p1.xml`、`p2.xml`。
  同名 `.log` 和 `results/nf-test/work/tests/` 保留过程命令、stderr、Nextflow 日志。
- [execution.json](execution.json) 保存逐用例结果、测试源 SHA256 与原始 JUnit SHA256，
  方便核对本次记录；它不是用于断言的新快照。
- `results/nf-test/upstream-data/download-receipt.json` 记录全部数据 URL、版本和校验值。
- 数据适配器通过 Python AST 语法检查；上述 9 份下载数据在 uv 隔离环境内再次核对
  SHA256 一致。没有运行或改写其他工作区新增的测试集合。

后续需先备齐各平台声明的真实工具，再执行 [README.md](README.md) 中相应分级命令。
P2 的环境阻塞和 P1 的 CSI 差异都尚未解决。
