# 使用指南

更新：2026-10-31。完整分支图见[平台流程路线](platform-workflows.md)。

## 选择入口与准备环境

一次运行只处理一个 `--platform`。Illumina 通用入口默认 MEGAHIT；短读长 protocol 使用 `-profile short_read_protocol,conda`，改用 metaSPAdes/PlasMAAG，并启用新交付链。后者不是其他四个平台的通用开关。

仓库通过模块级 Conda 环境运行工具，也声明了 mamba、Docker、Singularity profile。新增 protocol 当前以 Conda/mamba 路径为实现入口，尚无覆盖全部新增工具的统一 OCI 部署验收。Dorado 和默认 Hybrid 组装器 OPERA-MS 需要另行准备并可从运行环境调用。环境可解析不等于数据库、权重与固定源码已经就绪。

## 样本表

使用带表头的 TSV，`sample_id` 必填且全局唯一，只使用字母数字开头、后续字母数字及 `_.-`。每行一个样本；优先填写绝对路径。完整格式见[样本表规范](../assets/samplesheet_schema.md)。

| 平台 | 每行需要的输入 | 多种长读输入同时存在时 |
| --- | --- | --- |
| `illumina` | `read1`、`read2` | 不使用长读列 |
| `ont` | `pod5`、`bam`、`long_reads` 至少一个 | POD5 → BAM → FASTQ |
| `pacbio_hifi` | `bam`、`long_reads` 至少一个 | BAM → FASTQ |
| `hybrid` | `read1`、`read2`，再加 ONT 长读输入之一 | POD5 → BAM → FASTQ |
| `assembly` | `assembly` FASTA | 不使用 reads |

样本表的 `platform` 列仅作记录，实际路由由命令行决定。每行 `host_reference` 覆盖全局 `--host_reference`；两处都为空则不去宿主。`group` 供组间分析使用；protocol 的公式可以使用额外元数据列，原始表保留到最终包。

可生成一个最小 Illumina 表（路径需替换）：

```bash
printf 'sample_id\tgroup\tread1\tread2\nS01\tcontrol\t/data/S01_R1.fastq.gz\t/data/S01_R2.fastq.gz\n' > samples.tsv
```

只有一个样本的示例用于说明输入，不能进行组间推断。重复测量应提供 subject、batch 等真实字段；不应把同一受试者的多次观测作为独立重复。

## 启动通用流程

下面资源 JSON 适用于通用 reads 默认工具；替换为已经准备且匹配工具版本的路径。Assembly 可去掉 MetaPhlAn，并按需显式启用 PlasmidHostFinder。

```json
{
  "genomad_db": "/db/genomad",
  "bakta_db": "/db/bakta",
  "amrfinderplus_db": "/db/amrfinderplus/latest",
  "mob_suite_db": "/db/mob-suite",
  "metaphlan_db": "/db/metaphlan"
}
```

保存为 `resources.json` 后，选择与样本表相符的一条命令：

```bash
nextflow run . -profile conda -params-file resources.json --platform illumina --samplesheet illumina.tsv --outdir results/illumina
nextflow run . -profile conda -params-file resources.json --platform ont --samplesheet ont.tsv --outdir results/ont
nextflow run . -profile conda -params-file resources.json --platform pacbio_hifi --samplesheet hifi.tsv --outdir results/hifi
nextflow run . -profile conda -params-file resources.json --platform hybrid --samplesheet hybrid.tsv --outdir results/hybrid
nextflow run . -profile conda -params-file resources.json --platform assembly --samplesheet assembly.tsv --outdir results/assembly
```

Hybrid 可加 `--hybrid_assembler hybridspades`。ONT 抛光通过 `--polishing_tools medaka` 启用，并需要与数据匹配的模型资源。Assembly 默认不会运行 MetaPhlAn；要做序列宿主预测，显式设置 `--host_prediction_tools plasmidhostfinder --plasmidhostfinder_db /db/plasmidhostfinder`。

列表参数使用逗号分隔，如 `--plasmid_detection_tools genomad,platon`，并提供 `--platon_db`；配置文件中可使用数组。只启用有实际资源的工具。gplas2/Recycler 要求同次 SPAdes 图；PlasMAAG 仅在 Illumina 接线。SCAPP 已移除，CRISPR 宿主链接尚未实现；不能把选择器名称当成已支持能力。

## 启动短读长 protocol

```bash
nextflow run . -profile short_read_protocol,conda \
  --samplesheet illumina.tsv -params-file protocol-resources.json \
  --outdir results/protocol
```

资源文件、MOSTPLAS/PLSDB 格式及固定来源见 [PROTOCOL](../PROTOCOL.md)。该 profile 默认启用宿主模型、进化和菌株链；资源不足时可显式关闭 `--protocol_host_models false --protocol_evolution false --protocol_strain false`。其余核心资源仍需准备。默认 ANCOMBC2/生态公式为 `group`；含 batch/重复测量时应设置实际的固定/随机公式和 block，不能照抄不存在的列。

## 运行恢复和结果检查

在同一仓库与 work/cache 环境，使用相同命令追加 `-resume` 恢复。改变资源内容或分析参数后，应检查缓存身份与本轮方法记录；不要把发布目录存在视为本轮成功。保留 work 目录直至确认不再需要恢复。

通用输出按 `00_input_validation/`、`01_qc/` 至 `12_network/`、`tables/`、`report/` 分区，目录只在相关分支发布输出时出现。优先检查：

1. `report/` 的本轮汇总和生产者记录，再看各工具日志与原始表。
2. `tables/contig_abundance.tsv`、`plasmid_abundance.tsv` 与 `sample_states.tsv` 是否覆盖完整样本。跨样本推断使用质粒子表；局部样本丰度不能替代共享参考测量。
3. 统计的 status/资格记录：禁用、无候选、低覆盖、组数或重复数不足均不等于生物学阴性。

Protocol 另检查 `catalogue/`、`final/delivery/` 和 `pipeline_info/`。最终包包含冻结 FASTA、代表级 metadata、counts/TPM、coverage/prevalence、系统/ARG/宿主/菌株/事件表、HTML/PDF及溯源清单。生态和 ANCOMBC2 分别有 `plasmids.`/`systems.` 前缀。`pipeline_info/run_state.json` 和 `failed_samples.tsv` 描述本次调用；失败归属可能是样本、cohort 或 workflow，不能将整批失败强行分摊给样本。

通用 counts 是 read 比对数，paired mates 分开计数；protocol counts 是经过双端质量门控的 fragment 数。两种表不可拼接。检测模型分数、环化预测、共丰度、宿主模型或 A/B/C/D 事件均属于候选证据；直接转移、方向与物理宿主需要额外验证。
