# 小型真实质粒测试：2026-10-17

最终结果：`plasmid.nf.test` 1/1 通过，nf-test 报告耗时 21.051 秒。
针对当前工作区，不能视为干净 Git 提交的验证。无 stub、mock 可执行文件或新快照。

## 数据

复用 nf-core/test-datasets 的完整参考质粒 pUTI89（`NC_007941.1`），单序列
114,230 bp；来源固定为提交 `618f1541382c4ad49eff566dadf13d5ccbd0ebb4`。
压缩 FASTA 35,478 bytes，geNomad 测试数据库 5,912,894 bytes，合计约 5.67 MiB。
下载文件的长度和 Git blob SHA1 均通过锁文件校验，SHA256 记录于
`results/nf-test/small-plasmid/download-receipt.json`。

## 实际运行

| 过程 | 状态 | trace 实际运行时间 | trace 采样 peak RSS |
| --- | --- | --- | --- |
| QUAST | COMPLETED / 0 | 730 ms | 20.4 MB |
| geNomad | COMPLETED / 0 | 7 s | 897.8 MB |
| PLASMID_CONSENSUS | COMPLETED / 0 | 2.4 s | 249 MB |
| PLASMID_STRUCTURE | COMPLETED / 0 | 1.9 s | 218.9 MB |
| REPORT | COMPLETED / 0 | 1.3 s | 107.4 MB |

QUAST 确认 `# contigs = 1`、`Total length = 114230`。geNomad marker 分类为：

| accession | chromosome_score | plasmid_score | virus_score |
| --- | ---: | ---: | ---: |
| NC_007941.1 | 0.2432 | 0.6440 | 0.1128 |

此配置仅使用裁剪数据库并禁用 NN，质粒分数低于默认 0.7 阈值，质粒汇总和共识表
只有表头，结构表也无数据行。测试验证了实际分类处理、合法分数范围及其总和、
共识与工具汇总的一致性、QUAST 长度/数量，以及 Markdown/HTML 报告。
**已知真实质粒在该配置下没有被检出**；测试通过仅代表真实执行与输出契约通过，
不能当作阳性检出通过或灵敏度基准。阳性下游注释（包括 Prodigal）、reads 质控、
从头组装、丰度、差异分析、网络及其他可选工具均未由本例验证。

## 首轮发现与修正

1. 原配置把 `--meta --max-ref-number 0` 传给 `quast.py`，真实运行退出 2：
   `no such option: --meta`。按 [QUAST 官方手册](https://quast.sourceforge.net/docs/manual.html)
   修正 `conf/nfcore_qc_assembly.config`，使用无参考基础组装统计；未修改 vendored 模块。
2. 新用例最初假设共识表包含每条输入序列，因只有表头而失败。核对当前脚本后确认
   它聚合工具提供的预测 ID，不保证覆盖所有输入。最终测试以 geNomad 实际汇总为
   共识行数契约，并额外检查 marker 分类确实包含本参考 accession，避免空输出蒙混过关。
   未降低分类阈值或修改输入来制造阳性。

## 复现与证据

执行命令见 [README.md](README.md) 的“小型真实质粒测试”。本次 native PATH 额外包含：

```bash
export JAVA_HOME=/home/sleepinlava/.local/share/mise/installs/java/21.0.12+101.0.LTS
export PATH="$PWD/tests/nf-test/.venv/bin:/tmp/autoplasm-small-tools/bin:$JAVA_HOME/bin:/tmp:$PATH"
export NXF_VER=26.10.0
export NXF_OFFLINE=true
export NFT_BIN=/tmp/autoplasm-nft-runtime/nf-test
```

Python 依赖通过现有 `uv.lock` 的 pipeline extra 安装；geNomad 1.12.0、QUAST 5.3.0。
原生工具在 `/tmp/autoplasm-small-tools`：MMseqs2 18.8cc5c、ARAGORN 1.2.41、
Prodigal 2.6.3（本例没有触发 Prodigal 分支）。系统 R 提供 Biostrings/data.table。
首次工具安装约数百 MB 至 GB，明显大于数据量；它不计入数据下载大小或 21 秒执行时间。

- JUnit：`results/nf-test/small-real.xml`；日志：`results/nf-test/small-real.log`。
- trace：`results/nf-test/work/tests/6fb8835c14e78bbf2bddd771faa90c8f/meta/trace.csv`。
- 输出：`results/nf-test/work/tests/6fb8835c14e78bbf2bddd771faa90c8f/output/`。
- HTML 报告：上述输出目录下 `report/report.html`。
- 数据适配器回归：5/5 通过，含小型数据集只下载两个文件和样本表映射的检查。

数据目录、虚拟环境和运行产物不提交 Git；保留测试、数据身份锁和此结果说明。
