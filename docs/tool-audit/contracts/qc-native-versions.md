# QC 目标版本、来源身份与测试契约

2026-10-23。TA-075、TT-009、TT-012 的有界验证，原始产物见 `results/tool-audit/20261023-multiqc-version/`，联合复核见 `results/tool-audit/20261023-copla-entities/verification.json`。

生产模块声明 FastQC 0.13.0、fastp 1.3.6、MultiQC 1.35。原 Python 测试环境却锁定 MultiQC 1.33，旧兼容结果不能认证 1.35。现已同步 pyproject/uv.lock，QC 启动前读取三个生产 environment.yml 的精确版本并核对实际可执行程序；错误版本、伪匹配和版本命令失败均拒绝。真实旧 1.33 被拒绝的记录保留；版本响应 observer 只用于前置检查，不计工具运行。

MultiQC 固定 [v1.35 commit 87e504bb](https://github.com/MultiQC/MultiQC/tree/87e504bb77e3d94687dd980638724b7ef8e1e92f)。其 [CLI](https://github.com/MultiQC/MultiQC/blob/87e504bb77e3d94687dd980638724b7ef8e1e92f/multiqc/multiqc.py) 的 `--fullnames` 关闭名称清理；默认 `fn_clean_exts` 中的 `.clean` 会截断后续名称。实际 PyPI wheel SHA256 `818ad8aa75572f13be55b66c0bafd7877c1e119a0903e004855ec04385a94dc6` 与锁一致，安装目录844份包文件逐字匹配。保存的 GitHub 核心源码正文相同，文本工件多一个尾换行，已明确核对而非声称原文件逐字相同。FastQC [官方0.13.0发布](https://github.com/s-andrews/FastQC/releases/tag/v0.13.0)的完整ZIP与GitHub asset独立SHA256 `c9504d47752e79ecfe61691e09bf367fc3f15167ac3fe83d9e33534fffbcc301` 一致；当前目标回归使用Java21。fastp沿用已接受的固定1.3.6环境。

真实原模块的8份 FastQC 报告只汇总为6行，清洗后的两个 mate 发生覆盖。进一步对相同的16份真实报告使用原默认 MultiQC 调用，输出10行，合法样本 `A.clean.B` 和 `A.clean.C` 的4份报告混为 `A`。现对 MULTIQC 与 MULTIQC_ONT 保留完整源名称，报告中会显示 `.fastq.gz` 等后缀，避免默认截断造成的覆盖。输入和单份 FastQC 统计未改变。

测试同时存在三项问题：trace 没有 workdir 却回退到仓库当前目录，可能读到旧产物；硬编码 `multiqc_data` 与实际报告前缀目录不符；仅搜索子串不能保证独立来源和读数。现显式记录 workdir，只接受本轮指定 work 根内唯一的实际 MultiQC 任务和唯一 `*_data` 目录，解析精确 `multiqc_fastqc.txt`，逐来源核对完整名称、原始 Filename 与独立生成的读数。缺少/越界 workdir 的反例均拒绝。

原手写 fastp JSON 缺少目标解析器要求的 `command`，被1.35正确跳过，不能当作合法上游。测试现由真实 fastp1.3.6处理200条已知75bp reads生成完整JSON；输入/输出数均200，MultiQC实际解析的来源和统计也单独复核。该人工reads是格式/计数控制，不能用于科学性能结论。

当前真实QC五场景24条trace：19完成、5缓存，包含标准8份、扩展16份来源、原输入缓存重用、FastQC关闭而真实fastp报告开启、MultiQC关闭。另一个原模块 MULTIQC_ONT 别名的真实任务对同16份 FastQC 报告保留全部身份；它不证明 NanoPlot 解析。8个去重oracle方法包含此前4个退出状态方法，不按重放增加方法数。初次数据目录/缺workdir/手写JSON错误及原默认覆盖结果均保留。

这只认证上述原生版本与输入控制；不认证其他QC工具、OCI/Conda执行后端、NanoPlot语义、完整平台或测序质量分类性能。uv解析只更新MultiQC与其必要Polars依赖族，其他包版本未改变，具体差异、93个实际安装包及来源见运行锁。
