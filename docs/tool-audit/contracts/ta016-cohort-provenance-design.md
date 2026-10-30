# TA-016 队列级生产者的 provenance 设计（2026-10-28，待实现）

2026-10-29更新：以下是原设计快照，已存在候选实现。当前集成复核见[本轮审查](ta016-integration-review-20261029.md)；嵌套别名、实际统计/共享参考/空参考报告已验证，TA-016仍未完成，不按下文“未实施”判断当前代码。

## 现状

- 单样本生产者（10 个已接入）的 task_provenance 键为 meta.id，经 reportEvidence 转 runtime_command 事件，报告 R 校验 sample_id ∈ 期望样本集合。
- 队列级生产者（modules/cross_sample/*：DIVERSITY、DIFFERENTIAL_ABUNDANCE、DESEQ2、FASTSPAR、NETWORK_PREPARE、MERGE_ABUNDANCE、SHARED_*、STATISTICS_INPUTS、REPORT 等）输入是 cohort 表（path），**没有逐样本 meta**，不能套用单样本 meta。

## 设计（未实施）

1. 队列模块在任务内以 eval 从暂存的 cohort 元数据实际读取样本域（而非信任 channel 内容）：如 `cut -f1 cohort/* | tail -n +2 | sort -u | paste -sd,`——以暂存文件为准。
2. task_provenance 元组携带 `cohort: true` 与实际读到的样本列表；reportEvidence 的 runtime_command 分支对 cohort 记录发 sample_id='cohort:<process>' + cohort_samples。
3. generate_report.R 对 cohort 记录：要求 cohort_samples 非空且全部 ∈ 期望样本域；拒绝空/超集/未知样本；其余校验（脚本字节校验和、探针完整性、重复身份）与单样本记录一致。
4. 不复制大表进事件（沿用现有证据语义）。

## 验证计划

- 单元：构造合法/空/超集/未知样本域的 cohort 记录，R 端逐一接受/拒绝。
- 端到端：留在全部生产者接入后的统一报告重跑。

TA-016 保持 in_progress。
