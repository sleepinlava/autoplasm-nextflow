# Vendored P1 测试前置依赖（TT-005）

> 当前状态：2026-10-25 已完成本契约列明局部修复的统一验收；见 [接受记录](../../../results/tool-audit/20261025-consolidated-acceptance/receipt.json). 下文按历史顺序保留尝试及限制。

2026-10-25，修复已实现、等待统一源码/补丁验收。范围是测试前置定义及真实归档I/O，不代表全部上游P1用例执行通过。证据根目录：`results/tool-audit/20261025-vendored-prerequisites/`。

## 固定来源及最小修改

原始静态扫描99个literal script引用，其中14处缺失；实际nf-test0.9.5在10个受影响suite的dry discovery也发出14处当前源码依赖缺失警告，但退出0。不能把退出0或dryRun打印的PASSED当测试执行通过。

从 [nf-core/modules](https://github.com/nf-core/modules) 按 `modules.json` 中各consumer实际revision取得8类helper：BLAST makeblastdb、DIAMOND makedb、MMseqs createdb、UNTAR、HiFiAdapterFilt downloaddb、PIGZ compress、GUNZIP、RGI cardannotation。共9个consumer revision、12组revision/helper组合；每组main.nf/environment.yml/meta.yml与各revision LICENSE共45个官方GitHub响应全部保存。逐文件重新计算Git blob SHA1与响应SHA匹配。五个UNTAR来源的三文件内容完全一致，合并保存一份并保留所有来源引用；其他各用其consumer对应的固定来源，没有统一取最新版或常见SHA。

`tests/nf-test/prerequisites/`保存24个未经修改的helper代码/环境/metadata文件、原MIT LICENSE和source-lock.json。只将10个vendored suite的14处setup script引用指向这份测试目录；未改变断言、快照、fixture或生产模块/版本，`modules.json`哈希未变。未来更新consumer revision时，独立检查器会拒绝旧锁不匹配。HiFi helper在通用6d467...查询404，而在其真实consumer9cc9ac...存在；两次原始响应保留，未据错误revision宣布上游永久不可用。

## 实际检查与范围

- `current-prerequisites.json`：当前99个literal引用全部可定位；14个setup引用、24文件的SHA256/Git blob及consumer revision、LICENSE均匹配。动态表达式数量另列，不假装已静态解析。
- `before/run.json`和`after/run.json`：实际nf-test0.9.5 dry discovery，10个suite/33个case定义，当前源码缺失警告14→0；没有`.command.sh`。历史不可变源副本/失败记录仍有独立警告，单列为other，不删除历史来清零。dryRun的33个PASSED不计入已执行测试分母。
- `native-archive-helpers-v2/run.json`：真正执行UNTAR单目录strip、UNTAR平铺、GUNZIP、PIGZ四个原始helper任务；完整846字节固定上游FASTA、源文件不变、输出逐字节相等及meta/group均核对。另一个CRC损坏gzip由真实gzip报错，唯一GUNZIP任务FAILED，未发成功输出；不以残留部分文件当通过。首次原生运行与随后收紧精确版本/任务名/输入不变断言的重放分别保留，不增加独立场景分母。
- 工具实际tar1.34/gzip1.13及现有pigz2.8；其他源环境coreutils9.5/grep3.11/lbzip2 2.5/sed4.8也与声明一致。新建14包工具环境，约5.62MB缺失归档，显式锁及14个原始包SHA256实际核对见`utilities-explicit.lock`、`utility-package-proof.json`。pigz复用已记录prefix，不宣称它是本次全新环境。

全新DB构建、HMM/模型、RGI/HiFi/eggNOG等其余实际P1用例和容器均未由本次证明。原HiFi下载helper引用master数据库，运行其原生数据库测试前仍须固定实际下载数据身份；未修改上游代码掩盖这项限制。

## 补丁和验收状态

`patches/TT-005-prerequisites.diff`为41源增量：10个既有suite及测试README、30个新增测试/metadata/许可/审计来源。独立反向check通过；将替换路径还原后，既有10文件与保存before逐字节相同，11项before SHA与上一未接受681源工作捕获一致。`patch-source-state.json`明确before仍是未接受工作状态，不冒充上一正式receipt。本修复ready，随统一源码链复核接受；不提前把全部P1或全仓库审计标为完成。

2026-10-25 统一复核后，上述局部修复已接受，详见 `results/tool-audit/20261025-consolidated-acceptance/receipt.json` 及同目录 `review.md`、`evidence-recheck.json`。仅关闭列明缺陷；原有在线/全冷部署/完整平台/科学效果限制继续保留，历史ready/待验收文字描述的是当时状态。
