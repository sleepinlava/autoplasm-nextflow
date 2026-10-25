# Mock 多样本测试的来源与断言

TT-001原反例：所有样本具有同一DNA，CoverM替身根据输出文件名生成丰度。因此把S2 reads接到S1文件名仍会得到预期计数。旧代码和直接反例保存在results/tool-audit/20261024-mock-provenance/before-control/；不能把它描述为完整旧流程重跑。

修复后六个样本的12条DNA均不同，本地contig ID仍相同。生成器在固定种子下登记所有read的样本、序列类别、contig、坐标、方向、长度及期望计数/碱基数；组装替身根据实际reads选择来源。精确匹配的比对替身记录实际read身份、DNA摘要、参考DNA与匹配坐标，合并验证共同参考并去重。CoverM替身仅从这些匹配计算计数和丰度，文件名不参与数值生成。它们是JSON协议替身，不是可交给原生程序的BAM，也不证明原生比对或分类效果。

验证器以生成器的read真值和源DNA独立核对当前trace所指向的任务；旧尝试目录不能补齐本轮缺失证据。全局统一参考为12特征×6样本，质粒参考为6特征×6样本，分别72及36行，空质粒表为0行；检查来源不匹配时非零计数、计数/覆盖/TPM/RPKM、完整特征域与报告。不能使用第一次当前输出反推这些期望。

9项来源单元反例覆盖输出名不影响丰度、换reads、换index、混合mates、顺序颠倒、参考被修改、混样组装以及过期证据；与已有samtools和Bowtie命名方法共15项通过。当前五场景共652条trace：Illumina阳性160、ONT空91、HiFi mixed137、assembly63、hybrid宿主201。两次中断恢复使用显式UUID，缓存单列；一次默认resume误指向其他会话被锁拒绝、一次旧trace被Nextflow禁用后断言拒绝，均保留，不计成功。当前验证器重新只读核对五场景通过，不声称产生新的652任务。

hybrid的6个长读宿主任务为真实Minimap2 2.30、SAMtools1.24，按原始read ID/DNA/quality核对输入和保留集合。短读宿主过滤仍是全部配对reads透传的命名观察，BAM/POD5来源仍为明确JSON替身，其他分类器和组装器也为替身。未据此认证全部平台真实工具、hybridSPAdes、所有正/负分支、科学性能、容器或AWS。

早期hybrid记录误写204任务，实际本轮为201；错误记录保留为final-validator-source.incorrect-task-count.json，纠正记录与当前trace一致。早期验证器误要求未请求的本地count列，以及读取旧尝试造成StopIteration，均在保留失败后修正；原始计数仍由全局表严格验证，没有删掉来源/计数断言来求通过。
