# 样本表（samplesheet）格式

TSV（制表符分隔），首行为表头。列均为可选（除 `sample_id`），按平台需要填写；空单元格表示缺失。

| 列名 | 说明 | 平台 |
|---|---|---|
| `sample_id` | 样本唯一标识（必填） | 全部 |
| `group` | 分组标签（用于差异丰度/多样性） | 有读段的平台 |
| `platform` | 仅作记录；实际由 `--platform` 决定 | 全部 |
| `read1` | 短读 R1 FASTQ(.gz) | illumina, hybrid |
| `read2` | 短读 R2 FASTQ(.gz) | illumina, hybrid |
| `long_reads` | 长读 FASTQ(.gz) | ont, pacbio_hifi, hybrid |
| `assembly` | 预组装 FASTA | assembly |
| `pod5` | ONT POD5 目录（触发 Dorado basecalling） | ont, hybrid |
| `bam` | 长读 BAM（触发 samtools fastq 转换） | ont, pacbio_hifi, hybrid |
| `host_reference` | 宿主参考 FASTA（触发宿主去除；覆盖 `--host_reference`） | 有读段的平台 |
| `notes` | 备注 | 全部 |

优先级：ont/hybrid 的长读输入按 `pod5` → `bam` → `long_reads` 顺序取第一个非空值。
示例见 `assets/samplesheet_example.tsv`。

PacBio HiFi 的优先级为 `bam` → `long_reads`。Hybrid 当前长读链为 ONT，不是任意长读技术自动识别。每次运行仅选择一个 `--platform`。

`sample_id` 必须全局唯一并匹配 `[A-Za-z0-9][A-Za-z0-9_.-]*`。缺失列、空行与重复 ID 不可用来隐式合并样本。

短读长 protocol 额外保留原始样本表中的元数据列：`collection_date`、`site`、`environment` 用于候选事件/环境汇总；`batch`、`subject_id` 等由所配置的生态/ANCOMBC2 公式、block 和宿主关联分层显式引用。字段必须反映真实设计；普通通用流程不会自动将所有额外列当成模型协变量。

当前启动方式见 [使用指南](../docs/usage.md)，分支与平台能力见 [平台流程路线](../docs/platform-workflows.md)。
