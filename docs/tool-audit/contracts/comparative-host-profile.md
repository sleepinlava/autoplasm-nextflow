# 比较分析与宿主 profile 审查

2026-10-20；基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

catalog：生产通过 ch_plasmids 的显式 path channel 收集，脚本按 sample|contig 生成唯一 ID 并拒绝重复，避免读取发布目录。当前复验 test_catalog_prepare.py 7/7，通过正常 ID、多个样本同 contig 名、非法命名/重复等用例；Nextflow catalog suite 还验证 stale OLD sample 不混入、空输入不启动目录/聚类、输入变化使缓存失效、未变输入缓存命中。原始工件保留在 --keep-temp 目录，路径和 hash 收据见 runs.jsonl。该 suite 不执行真实 MMseqs；它证明输入准备和缓存依赖，不是聚类正确率。

MMseqs 本地 arity 与 module 匹配，输出文件名/发布模式一致。固定 [18-8cc5c Parameters.cpp](https://github.com/soedinglab/MMseqs2/blob/18-8cc5c/src/commons/Parameters.cpp#L74) 定义 cov-mode=1 为 target coverage；当前配置 c=0.8 不可写成双向 80% 覆盖。此为参数意义已确认，不将选择 target mode 本身当缺陷；若研究目的要求双向全长归并，应单独科学方法评估。聚类仍无当前真实运行/独立真值；聚类映射没有回接 abundance 也仍受 TA-010 约束。

BLASTN 使用共享 DB value，未发现与 TA-022 相同的多 queue 配对；核酸输入和 outfmt 6 类型匹配。自动发现 .nal/.nin 的数量与多 volume、多个数据库边界仍需实际 fixture，不能靠单库自比 P3 全面认证。MUMmer 当前 P3 仅证明 accession/长度字符串出现在坐标文本，未证明精确对角覆盖或负样本零命中；应将结构断言与完整自比语义区分。clinker 使用 Bakta gbff.parent 的 task 目录而非发布目录，避免异步发布依赖；跨多个独立 GenBank record 的行为及 final HTML 仍待实际测试。

host profile：HOST_PROFILE_READS 对 short/long 分别加 single_end false/true；hybrid 只传 short reads，避免一 sample 重复 MetaPhlAn profile。MetaPhlAn DB 为一个共享 value；module 自动发现 bowtie2 DB，多个 index 版本共存的行为尚未验证。Kraken2 只在 Illumina 分支调用，其他平台选择该工具时的静默不运行仍属入口能力校验范围（TA-007 同类）。coabundance 消费的是 MetaPhlAn profile，不是 Kraken2 report；只启用 Kraken2 不能据此宣称共丰度关联具备输入。未将 community taxonomy profile 当作每质粒直接宿主预测。

本轮没有新增已确认缺陷。上述未验证项目保留 investigating/evidence_missing；不能将局部成功推导为整条比较或宿主预测路径通过。
