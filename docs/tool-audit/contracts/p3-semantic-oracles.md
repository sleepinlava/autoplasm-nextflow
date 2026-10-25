# P3 分箱与长读长证据断言（TT-002、TT-014）

> 当前状态：2026-10-25 已完成本契约列明局部修复的统一验收；见 [接受记录](../../../results/tool-audit/20261025-consolidated-acceptance/receipt.json). 下文按历史顺序保留尝试及限制。

2026-10-25；原始记录位于 `results/tool-audit/20261025-p3-semantic/`。候选补丁，未改此前正式 receipt。

## 输入与部署

MetaBAT2沿用原P3锁定的三个nf-core输入，170条contig、配套BAM/BAI，逐个校验原提交Git blob/尺寸。minigut为上游合成软件fixture，不声称真实生物样本。重用已核验读段；缺失的0.51MB组装从固定官方提交补取，另下载约3.7MB分箱输入。没有复制样本制造统计重复。

模块声明的MetaBAT2 2.17 `hd498684_0`原生环境冻结35包官方URL/SHA，全部原始归档独立校验。初始htslib1.21符合当前索引放宽到1.25的上限，并非求解器忽略约束；随后固定1.20以同时符合原构建配方，旧元数据/探测运行保留。原配方源码归档v2.17 SHA `fb46f5c3d3b0c327f62a58fceee04a55b9003276bc768040ba93c9b7913b52e2`验证通过，原始源码未修改。

长读长链使用实际minimap2 2.30、SAMtools1.22.1及宿主R/Rsamtools。`runtime-versions.json`与原始stdout/stderr记录实际版本。nf-test0.9.5加载仓库声明的nft-utils1.2.1/nft-bam0.7.0。原生结果不能认证未运行的镜像。

## 断言与实际运行

- 默认分箱：独立深度/长度筛选只有2条共80000bp可用，低于默认200kb分箱下限，明确验证空结果。170条深度记录与源FASTA的ID/长度完全对应，数值有限、非负。
- 非空分箱：原vendored测试固定参数为 `--minContig 1500 --minCV 0.1 --minCVSum 0.1 --minClsSize 10 --minS 2`。检查完整DNA、唯一成员与全部成员分区。本次167个单成员输出只认证发布/成员契约，不认证MAG质量或生产默认表现。
- 首个oracle误把membership簇号当FASTA编号。固定源码 `output_bins()` 在矩阵用内部 `kk+1`、文件用独立顺序计数器；保留首次失败及错误假设源码，改为比较完整分区。未删除DNA/唯一性/成员断言。合法重编号通过，错误合并分区仍失败。
- 长读长：生产R从BAM计算，独立Python从SAMtools导出的SAM复核候选对、唯一支持读段、默认筛选及2读段门槛、样本、分数、长度归一化与名次。首五条contig是测试分区，不是质粒/宿主生物学真值。
- 阳性控制：预先按源FASTA顺序选六条至少10kb的contig，用第一/第六条各前4kb构造两个技术FASTQ记录。实际mapper产生主/补充比对；预定预期为一对候选、2条支持读段。两个人工记录不作生物学重复。

`metabat-framework/execution.json`与`longread-framework-v3/execution.json`的实际4例通过、来源前后一致，合计8条原生COMPLETED。`oracle-controls/run.json`为12个实际产物副本对照：9个损坏拒绝、3个合法结果通过，原产品未改。现有6项R单元方法复验通过；100M比对参考从4bp修正为100bp，避免把超界SAM当合法阳性。人工输入不计生物学数据验证。

## 比对错误传播与失败记录

TT-014：原 `ALIGN_FOR_LINK` 的 `minimap2 | samtools sort` 没有pipefail。`mapper-failure-controls/run.json`让真实mapper生成有效控制比对后，由明确测试包装返回29：旧脚手架仍2任务COMPLETED并运行R；当前1任务FAILED/exit29，R不运行、无关联产物发布。observer只注入退出状态，不伪造比对内容。修复限定测试脚手架，不能据此推断生产其他管道有相同缺陷。

框架首次未正确设置Nextflow入口，0任务；第二次本地配置漏载声明插件，实际任务完成但原文件发现函数不可用。补齐既有插件后通过，未删原函数，也不把此启动配置问题登记成原套件缺陷。所有尝试保留。MetaBAT归档定位初次沿metadata猜测tar.bz2后缀失败，后按实际`fn`/URL找到并核对SHA，不据此声称上游缺失。Recycler附加框架重放首次继承64GB声明而无任务启动，后为小型fixture明确与既有原生成功运行一致的2CPU/2GB上限，结果单独记录。

本批改善测试语义与脚手架错误传播；生产算法、阈值与科学结论不变。整体M0–M4、真实非空shotgun P4、数据库/镜像与AWS验证仍未完成。

2026-10-25 统一复核后，上述局部修复已接受，详见 `results/tool-audit/20261025-consolidated-acceptance/receipt.json` 及同目录 `review.md`、`evidence-recheck.json`。仅关闭列明缺陷；原有在线/全冷部署/完整平台/科学效果限制继续保留，历史ready/待验收文字描述的是当时状态。
