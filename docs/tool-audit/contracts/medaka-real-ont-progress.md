# Medaka真实ONT准备与新增相邻索引边界（进行中）

本文件记录进行中的工作，不是完成或接受证据。原独立选择器9CLI控制与1注入observer不改变真实科学验证尚缺的状态。用户禁止病毒元素约束继续适用。

## 数据选择与范围

[ONT官方NO-MISS 2026说明](https://epi2me.nanoporetech.com/nomiss_96bc_p2i_sup_2026/)描述细菌分离株真实测序，使用R10.4.1/SUP5.2.0。本次选择发布顺序的第一个完整分析样本sample_1_1，不按结果或更小文件挑样本。只下载该样本的完整已发布filtered FASTQ、同名已抛光装配和映射JSON；不下载raw、其他样本、模型或病毒数据。公开GET不创建AWS计算资源，不是原计划的AWS真实执行验证。

`results/tool-audit/20261027-medaka-nomiss/` 保存S3清单和按ETag条件读取的小型配置/样本/分类元数据。metamap将barcode01、sample_1_1、run_id 853a956f关联，basecall_models只有dna_r10.4.1_e8.2_400bps_sup@v5.2.0，n_seqs=392181待完整FASTQ核对。下载中的前100条有真实测序标签及同一模型；这是临时元数据观察，不能替代整文件完整性/计数/生物学来源与覆盖验证。raw目录的文件命名不作为本次配对依据，不额外下载或宣称与分析FASTQ逐条相同。

完整FASTQ对象预期1,114,523,520字节，使用If-Match防止对象替换，完成后校验multipart ETag与整文件SHA256；HTTP版本ID亦需锁定。下载进程session77923、后续运行控制session89079均需以工具最新状态核对，文件或此记录本身不是任务仍存活的证明。partial文件不当完整输入；不会重新启动仍活跃的下载。

已完整获取的同名装配含contig_2=81,815bp、contig_1=4,724,790bp，原头部保留basecall_model，完整压缩/解压SHA记录于published-assembly-review.json。它是发布者已经抛光的同样本装配，后续仅作完整draft以验证原生计算和模块输出；不能当独立真值或推断本轮有错误率改善。分类元数据指向Salmonella属，当前不以分类输出代替真实比对覆盖证明，也不声称细菌来源证明不存在任何病毒同源片段。

## 排队的实际验证

新增两个未接受driver：`tests/run_medaka_real_ont.py` 和 `tests/run_medaka_framework.py`。前者在完整下载后严格核对来源hash、完整读段数、原生模型选择，再运行未修改的Medaka2.2.2原始CLI；要求非空神经概率HDF、全contig产物、>95%参考覆盖、输入/源码/model stores不变。后者仅在原始CLI通过后执行实际nf-test native/stub两例，以完整原生FASTA作软件比较基线；它不是独立基因组质量基准。两者尚未运行时，不能因源码存在或语法检查通过而计科学/框架通过。

continue.py只在完整文件及3项成功校验下载记录就绪后启动，任何driver非零即停止，不改模型或下采样来绕过失败。continuation-state.json是状态记录，必须配合实际会话/进程观察。后续接入模型/索引生产门禁和缓存、完整环境/provider/OCI等仍属于原目标。

## 新发现的索引读取集合

固定Conda原包mini_align SHA256 717ad91898f1e4f04fc7c221c2db5885b1274d77b32b57ff6f322852a03b4634中，参考先被原medaka_consensus解析到实际路径；mini_align检查该路径旁的`.fai`及`.map-ont.mmi`，存在则复用。它们不由当前单独模型选择观察绑定。

`index-selection-v2/run.json` 两个真实`mini_align -X`控制：完整同样本细菌装配实际创建FAI/MMI，并独立核对两序列长度及MMI格式标识；另将两索引替换为明确非生物学损坏控制，原脚本仍exit0、原字节不变，日志为复用而非重建。这只证明存在性分支，不称损坏索引能支持比对，未运行alignment/inference。首次错误地要求FAI>100bytes导致断言失败；实际两行FAI更小，改为完整记录/长度与真实MMI格式检查，保留首次日志及有效索引，不降低科学运行标准。

该资源族作为额外pending对登记于[清单增补](../resource-directory-consumers-20261027-addendum.tsv)。旧主表42对为已固定历史证据，不改写；当前有效清单为主表42+增补1，共43对（38candidate、5pending）。TA-091仍未决，既有109项问题/8未决不因新增同类读取边界自动增减。未来需补真实索引损坏错误传播、还原及查缓存前身份；不能只测模型就宣布Medaka资源完成。

完整计算后另执行 `tests/check_medaka_probability_coverage.py`：直接核对实际HDF概率的有限值、五分类归一化和每条draft contig去除重叠/插入重复后的真实神经位置覆盖>95%。这是尚未执行的独立数值/范围核验，不能用BAM高覆盖、完整FASTA或draft回填替代，也不是独立生物学错误率真值。两个已排队driver源码未改，原生/框架顺序不变。


## 完整filtered文件的官方计数对照（尚未执行计算）

追加获取目标文件的独立 `fastcat_stats/per-file-stats.tsv`，文件名精确为sample_1_1.filtered.fastq.gz：392,014reads、1,384,109,852bases、长度1000–120531bp。metamap的392,181保持原始字节，两者统计对象/阶段有差异，不能将metamap数值不加区分地当filtered文件计数。尚未证明167条差异具体由哪个处理环节产生，不自行编造原因。

原生driver现改为对目标文件专属统计的四个数值全部精确一致，保留metamap计数及是否相同标记，不用容差放宽、不修改FASTQ或源metadata。旧driver完整字节与SHA、队列修订原因保存在drivers/run_medaka_real_ont-before-file-stats.py和queue-revision.json。旧控制session89079仍在等完整下载；它已捕获旧SHA，下载完成后应由源码guard拒绝，必须工具确认终态后按新源码重新布置后续验证。原下载session77923没有重启，尚无科学执行，不把源码门禁拒绝计作Medaka算法失败。
