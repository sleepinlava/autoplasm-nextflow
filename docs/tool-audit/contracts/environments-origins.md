> 2026-10-21 当前覆盖范围：SCAPP检测与binning已按用户明确要求退役，旧选项/权重/FASTA输入被拒绝；TA-006/035不再开放修复但不计verified。以下SCAPP相关段落为历史取证，不能视为当前支持或待实施方案。当前验证见 ../retirements.tsv 和 ../acceptance.md。

# 环境、来源与本地差异

2026-10-20；基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

modules.json 的全部 52 个模块已通过 GitHub 获取其登记 commit 下 main.nf 并作逐文本比较，52/52 获取成功。45 个与固定上游一致，7 个不同：coverm/contig、dastool/fastatocontig2bin、fastp、fastqc、hifiadapterfilt/hifiadapterfilt、nanoplot、spades。完整原始响应在 results/tool-audit/20261020-environments/nfcore-upstream.json，固定 revision/blob/local SHA256 在 vendored-diffs.tsv；7 份 unified diff 在 local-patches/。这确认来源和差异边界，不证明上游或本地工具语义正确。

已复核的差异作用：FASTP paired 命名改动伴随 TA-034 SE glob 回归；FastQC 别名/输入后缀调整；SPAdes 额外导出 FASTG；CoverM 后缀可配；NanoPlot 增加 plain FASTQ；HiFiAdapterFilt 空 DB 时按可执行位置寻找 DB；DAS list gzip 预处理。已有本地 patch 注释和固定 SHA 得以保留，不能在更新 vendored 模块时直接覆盖。

environment-specs.tsv 用 PyYAML safe_load 读取 72 份环境文件的 dependencies，列出 131 个直接依赖声明，其中 87 个精确直接版本，44 个范围或未固定声明。精确直接版本不是完整 transitive environment lock；本轮没有执行 Conda solve/install 或验证所有镜像 digest。容器 R-analysis 使用 latest，本地 Dockerfile 的 CRAN/Bioc 安装也未锁全部包。应登记 evidence_missing，不把 native 结果自动迁移到其他后端。

TA-035：SCAPP env >=0.1.5 与容器 0.1.4 明确不满足同一版本约束；是否有更高可用版本本轮未查询/安装，不能基于该差异声称包永久不可用。版本选择需要单独评估算法与结果兼容性。

本机 native R 4.6.1，vegan 2.7.6、data.table 1.18.6.1、Biostrings 2.80.2、Rsamtools 2.28.0、DESeq2 1.52.0，完整 sessionInfo 在 results/tool-audit/20261020-environments/R-session.txt。该环境与声明 DESeq2 1.42.0 容器不是同一个验证目标。R sessionInfo 的 timedatectl 在 sandbox 报总线权限警告，不影响包版本读取；未尝试更改系统设置。

geNomad：实际 .venv 包为 1.12.0，源码已读。annotate.py cleanup 删除 annotate_mmseqs2_dir；find_proviruses.py cleanup 清理其 mmseqs2/input/aragorn 中间文件，之后仍写结果 taxonomy。不能从 conf/nfcore_detection.config 的“cleanup 删除整个 annotate/find_proviruses”注释推导现版必定缺必需输出。保留差异说明，不新增未经运行证实的失败项。此源码阅读也不等于已运行 marker/NN 分类；测试子集仍缺完整模型科学基准。

六个主入口 include 不可达文件仍保留来源：CRISPR 是明确拒绝直接调用的未实现边界；下载模块是可独立调用的 helper，没有接入 pipeline DB 参数链；samtools/sort 已由 mapper 内部排序替代。不可达不是删除依据。数据库下载 helper 的具体版本/输出已开始静态阅读，网络/数据库完整性尚未全部验证。

补充：mamba/docker/singularity 三套 config -flat 当前均退出0，与此前 default/test/podman/conda 合计七套配置解析证据。此为配置解析，未拉取镜像或运行环境求解。

## TT-009：MultiQC测试版本与声明不一致

2026-10-20：模块environment.yml精确multiqc1.35，container同为1.35；tests/nf-test/pyproject.toml pipeline extra精确1.33，本地.venv实际multiqc--version也为1.33。suite_qc只require_tools(fastqc,multiqc)，并不核对MultiQC版本，runner仅验证Nextflow主版本。这是版本证据覆盖缺口，不是认定1.33工具有运行缺陷，也不是说conda/container会选错版本。

为保留有用而不越界的证据，原MULTIQC模块实际native1.33汇总前批真实pUTI89 QUAST结果，workflow/task0，一个样本pUTI89，contigs/total length/largest/N50/GC在multiqc_quast.txt与原QUAST表逐值相同，HTML和data实际生成。完整配置、trace、logs和receipt在results/tool-audit/20261020-multiqc-compat/。这只是1.33兼容性，不计声明1.35的P3验证；也没有跑完整FastQC/FASTP输入收集分支。

应选择与当前声明一致的测试版本，或在测试/支持矩阵显式将1.33标为兼容性范围，同时为1.35保留待验收项；不能由旧版本成功自动升级到新版本通过。未升级依赖、修改lock或更改生产版本。
