# 跨样本样本身份、零结果与最终网络资格

日期2026-10-22；对应TA-013/014/038/059/060，TT-003仅部分补强。固定证据 `results/tool-audit/20261022-statistics-eligibility/receipt.json`，每一项限于该receipt源码哈希。

生产输入需带全体预期样本的metadata及共享定量状态，且每类表只有一个产物。非空表是完整sample×feature矩阵，不得把缺测补零、重复取最后一条或与metadata静默求交。状态声明全参考/质粒特征数及各自read计数总和；质粒表必须是相同ID/DNA目录所定义的contig表子集，计数与coverage逐格一致。全局无特征只允许生产者明确的零状态，真实全零测量保留全体样本。STATISTICS_INPUTS使用磁盘SQLite索引和流式hash；百万行受控规模检查峰值25100KiB，非任意数据规模性能保证。

DIVERSITY逐样本计算richness、Shannon、Simpson、Pielou。vegan2.7.6单列矩阵按向量计算的旧行为会将样本混成一个群落；仅添加名字不能修正，必须逐行调用。零输入alpha定义0，零/零Bray兼容策略仍为0且在status中标明；这不表示空样本有生态相似性的独立科学证据。7个独立公式方法涵盖raw/TSS、0/1/多特征和1/多样本。

NETWORK_PREPARE严格读取整数raw_count，coverage不可替代。先去初始全零样本，按剩余初始非零cohort作为一次性prevalence分母，再移除新产生的全零列，不迭代重算prevalence。每次发布矩阵及network_status.json；最终至少4特征且达到network_min_samples才生成可选eligible产物供FASTSPAR。固定[FastSpar v1.0.0源代码](https://github.com/scwatts/fastspar/blob/v1.0.0/src/fastspar.cpp)明确至少4components；原生少于4时实际进程退出0但不生成结果，Nextflow因缺产品失败。最终正例8特征20样本保留默认50iterations/10exclusions/threshold0.1/seed1；矩阵有限、对称、ID完整并与同版本直接CLI一致。正例存在官方exclusion提前结束提示，未关闭或隐藏；不认证相关边的生物学准确率、bootstrap或p值。

R输出网络计数不再as.integer，保留2^31+123以上的可精确整数文本；拒绝超过2^53-1范围。此处保证输入文本不损坏，不声称FastSpar内部任意大数浮点精度。

七个custom流程将分析程序/辅助库声明为path输入。旧SHARED_ABUNDANCE_TABLES通过绝对路径调用Python，修改程序仍CACHED，直接CLI可见新marker；原生3旧+3新trace确认当前不变缓存、改变重算。另6条R/helper对照在私有副本刻意改公式，证明新helper纳入缓存；该helper由本轮引入，不能冒充旧基线已有依赖。仅在script块中读取本地hash的初稿未触发重算，不采用该方案，未断言引擎“剥除注释”。Nextflow[缓存机制](https://docs.seqera.io/nextflow/cache-and-resume)的通用说明与实际26.10.0原生对照分开记录。

验收：原CROSS_SAMPLE13场景37trace、共享真实比对/计数三模式58trace、缓存12trace、现有P3 wrapper2trace，共109=101完成+5缓存+3预期失败。外部CLI替身平台793任务单列，nf-test框架未运行；TT-003/P4保持open。DESeq1.42仅环境准备完成，完整模型TA-011与未读取min_group_replicates的TA-061另行修复；TETRA真实宿主阈值TA-039亦不由本契约认证。
