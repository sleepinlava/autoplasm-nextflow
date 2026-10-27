# Medaka逐样本模型选择身份（独立候选，未生产接线）

本增量接续 [固定原生读取边界](medaka-runtime-readset.md)。新增 `bin/medaka_model_selection.py`，调用真实2.2.2原CLI和固定原Bash脚本前段，输出逐输入实际模型身份；不是完整科学readiness、生产执行或缓存门禁。MEDAKA资源对、TA-091及原完整计划仍未完成。所有执行继续受[禁止病毒元素](../user-constraints.md)约束。

## 行为

先核对四份实际Python源码和 `medaka_consensus` SHA，脚本前段精确截断于 `Checking program versions` 之前；私有shim只允许原CLI的version、list_models、resolve_model。参数以argv传递，保留原getopts、显式model优先级、bacteria及原科学flag，不重写模型选择表。

记录原Bash最终变量（含model/reads/draft/threads/batch/quality/mapQ/gap/BED/force等）、实际模型普通文件路径/真实路径/大小/权限/SHA256、输入前后内容身份、已核对选择源码和Python/HOME/model stores上下文。默认fallback保留ID时，再用原resolver解析实际文件；模型解析请求一律拒绝。即使原Bash隐藏下载错误并回退默认、exit0，独立候选也拒绝该观察，不把它当作成功准备。合法无元数据fallback仍按原默认模型，不擅自改变方法。

可用 `--expect` 与先前观察完整比较；同大小、同mtime内容变化也拒绝，恢复原字节后通过。输出必须是新路径，失败不留下selection成功JSON，但保留独立diagnostics。它不验证模型归档内容/格式、feature编码与输入兼容性，不调用mini_align、inference、stitch，也未约束完整执行期依赖/资源集合。因此JSON明确 `scientific_readiness_certified:false`、`production_gate:false`，不得据此放行生产科学流程或声称缓存已修好。

## 实际验证

`tests/run_medaka_model_selection.py` 在已核验CPU环境下运行。最终 `results/tool-audit/20261027-medaka-selection/native-v2/run.json`：9个实际CLI进程，包含自动随包模型、合法缺元数据fallback、显式model覆盖bacteria/保留科学flag、未准备bacteria拒绝、隐藏fallback拒绝、完整私有模型基线、同大小同mtime变化、expect拒绝、恢复expect通过。模型stores前后全部普通文件SHA相同。所有生成reads仅N，不能当科学样本。

另1个明确注入observer只将父进程resolver的model_stores替换为空目录，子进程仍用原安装，验证前段exit0后最终模型未准备仍拒绝；不称真实环境变异或科学执行。v1为superseded，保留当时helper/driver字节，不重复计算18或更多个实际用例。v2增加最终resolver异常分类/拒绝诊断，9CLI重新执行。

Medaka vendored测试移除病毒fixture路径，新增要求完整、来源审查通过的细菌ONT reads、assembly和独立完整expected FASTA参数。native断言改为全FASTA（含ID及完整DNA）与2.2.2实际版本；不自动录制新snapshot，不用原病毒前100bp断言。stub保留接口snapshot，旧native snapshot仅历史。nf-test0.9.5实际 `--ci --dry-run` 能发现两例，**未执行任何testcase或Nextflow任务**；控制台的PASSED/Executed 2属于dry-run输出，不能计作两例native/stub通过。两例真实框架执行继续待办。

## 候选数据审查与清理

[nf-core官方教程](https://nf-co.re/bactmap/dev/docs/usage/tutorials)列出了Bacteroides目录下Nanopore FASTQ。按已使用的固定test-datasets提交 `618f1541382c4ad49eff566dadf13d5ccbd0ebb4`，下载该完整原文件10,258,859字节，并核对tree blob SHA及完整SHA256，没有另取片段/下采样。

完整解析1000reads/33,343,943bases：494个名称前缀NC-000913.3、506个NC-006347.1，所有comments为空，最长773,417bp。前者对应[NCBI E.coli K12记录](https://www.ncbi.nlm.nih.gov/gene/63925660)，后者对应[NCBI B.fragilis YCH46记录](https://www.ncbi.nlm.nih.gov/nuccore/NC_006347.1)。它们不是保留的B.fragilis FDAARGOS_1225参考accessions NZ_CP069563.1/NZ_CP069564.1；命名还提示可能是模拟数据，但本轮未取得生成来源证明，不断言真实ONT或模拟器身份。目录标签不能替代样本/技术/匹配关系来源；该候选不用于真实ONT或配对科学阳性。

按清理授权删除这份未使用候选FASTQ与重复解压参考，共15,573,586逻辑字节；实测可用空间delta为0，不声称释放15.6MB物理空间。保留download/tree/input-review/fetch脚本、逐文件SHA/元数据、所有诊断/软件模型，以及原始完整参考gzip；原FASTQ正文不再本地保留，未来调查需按固定blob重新下载核对。见 `results/tool-audit/20261027-cleanup-7/cleanup.json`。审查2585个递归JSON索引无既有固定产物路径引用，74项前批固定证据删除后不变。首次清理前置核对因本轮明确修改的Medaka测试与旧snapshot不同而拒绝，未删除文件；改为绑定新第19补丁精确往返证明，只允许这一个已知来源差异，非跳过来源检查。

## 下一步

需取得来源明确、basecaller及模型相容、与完整参考匹配的细菌ONT样本和独立结果基线；不得用上述候选、N控制或无覆盖的参考回填替代。随后完成模型格式/兼容与全执行读取集合、生产cache:false逐样本探测、执行前及查缓存前上下文核对、native科学阳性/阴性/错误、模型变异/损坏/还原缓存、实际框架与完整provider/OCI范围。当前独立选择器没有修改生产MEDAKA命令。
