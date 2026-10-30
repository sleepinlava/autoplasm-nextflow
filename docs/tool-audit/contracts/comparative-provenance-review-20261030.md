Takeaway: 比较基因组目录和MMseqs2的队列来源已贯通最终报告，空样本保留，真实nf-test及代码缓存反例通过，TA-016仍开放。

本轮复现了比较基因组任务全部成功、最终报告却失败的问题。实际MMseqs2任务把跨样本目录名作为普通样本ID传给报告，目录构建命令本身也未作为可校验来源记录进入报告。修复后，目录构建器输出实际读取的样本清单，两个生产者携带同一队列身份进入最终报告。原始目录DNA和聚类成员与修复前逐项一致，空样本仍出现在报告与来源中。原生模块nf-test、10项R测试和四阶段代码缓存验证均通过。这里使用同一完整pUTI89序列重复构成技术控制，不是独立生物学重复或聚类准确率验收。

## Scientific context and question

输入是既有完整NC_007941.1质粒的两个技术副本（样本`001`、`NA`），以及空样本`1`。使用生产COMPARATIVE配置的0.95序列身份、0.8覆盖阈值和固定MMseqs2 18.8cc5c。执行的只是该通用二进制，没有调用其所在环境的geNomad入口或任何病毒模型。

## Question, lifecycle, and endpoint

证据目录`results/tool-audit/20261029-comparative-report-review/`沿用开始时名称；结论日期2026-10-30。前态两个生产者COMPLETED，REPORT因`plasmid_catalog`不在样本域中失败；修复后三任务COMPLETED。原生nf-test 0.9.5实际目标1/1通过，其此前历史目录扫描警告不是额外测试执行。[机器证据](../evidence/20261030-ta016-comparative-review.json)绑定来源及结果。

## Key findings

- 目录构建器新增可选样本清单输出，复用实际FASTA解析得到的样本身份；空输入或长度过滤后的样本仍保留。不同合法输入文件属于同一样本时只列一次。
- 生产模块新增显式R脚本path输入和deep缓存，所有当前调用点及nf-test输入已更新。运行时命令使用暂存脚本，不依赖PATH中的同名文件。
- 目录构建器发送cohort来源事件；MMseqs2从实际样本清单读取cohort域，保留原目录输出前缀。最终报告包含2条已核对原件、SHA、探针和样本域的来源记录。
- 实际目录含2条完整质粒记录，MMseqs2形成1个包含两条记录的簇；完整目录DNA及cluster成员与前态一致，`001`、`1`、`NA`均保持字符串身份。
- 10项R方法通过，涵盖空/过滤样本清单、同样本多文件去重及拒绝清单覆盖FASTA输出；原有命名和序列控制保留。
- 真实四阶段cache控制：冷COMPLETED、不变CACHED、只改隔离R脚本的同大小/同mtime字节后COMPLETED、恢复后CACHED。各任务暂存脚本字节与对应版本一致，两份目录产品始终一致；生产源文件没有被该控制修改。

## Interpretation

目录样本域现在来自实际输入解析结果，不从非空聚类记录推断，因此空样本不会消失。目录构建器代码变化可以使自身缓存失效。两条来源记录均通过实际报告消费者，弥补了单节点完成不能证明最终报告可用的缺口。没有更改聚类阈值或用简化工具替代MMseqs2。

## Artifacts

- Results：`out/09_comparative_genomics/`的完整目录、样本清单和聚类结果。
- QC and visual reports：`out/report/`实际HTML、methods和JSON，`report-check.json`记录独立核验。
- Provenance：before/after traces、`fixture-source.json`、`helper-cache/run.json`、`framework/junit.xml`及机器证据中的来源SHA。
- Model synthesis：本文；本轮没有创建Workbench注册分析运行。

## Limitations and blockers

TA-016保持in_progress；只验证本次MMseqs2比较路线，不由此验收BLAST/MUMmer/clinker、全部来源/数据库/模型/环境或完整平台。样本清单和deep缓存解决了本模块的局部问题，不能关闭整个TA-091。重复同一质粒和空样本是技术控制，不能作为真实shotgun科学验收。

## Recommended next step

按现有阶段继续TA-091资源读取身份及TA-016其他生产者的报告集成，随后推进TA-031完整r232与TT-003真实shotgun检验。
