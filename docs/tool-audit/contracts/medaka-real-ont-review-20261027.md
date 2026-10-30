Takeaway: Medaka完整细菌样本原生计算、神经覆盖及框架2/2通过；损坏MMI仍exit0并产生空BAM，资源门禁未完成。

本轮沿用既定资源身份审计计划，检查完整细菌ONT样本的Medaka计算及模块输出。已复核完整下载身份、原生软件来源、完整读段统计和实际神经概率文件。两条contig的神经位置覆盖均为100%，概率有限且归一化。前两次框架运行的生产任务均成功完成，但断言上下文未获得预期FASTA路径，读取null失败；两次stub均通过，独立逐记录核对确认完整头部及DNA一致、顺序相反。修正参数传递与完整记录比较后，第三次实际框架测试native/stub共2/2通过。该结果支持有界软件一致性检查，尚不能证明资源缓存门禁、独立基因组准确率或完整平台通过。

## Scientific context and question

延续TA-091资源身份和缓存审计，使用既有ONT官方NO-MISS sample_1_1完整filtered细菌来源读段与同样本已抛光装配；遵守用户不使用病毒元素约束。分类来源为既有元数据，不声称已证明细菌基因组无任何病毒同源片段。已抛光装配仅为本轮draft及原生CLI软件比较输入，不是独立生物学真值。本轮没有引入GPU替代工具或更换模型/阈值。

## Question, lifecycle, and endpoint

旧工具会话77923、89079当前返回Unknown process id，不能当活跃下载或控制器。旧continuation-state.json仍写waiting，不足以证明旧guard实际执行；guard终态缺失继续记为未知。后续continuation-v2-state.json为terminal_framework/1；已通过实际JUnit、任务trace和产物读取独立确认首次框架终态。没有创建Workbench注册运行，也没有为保存审查启动替代科学运行。原生native-v1未重算；本轮独立重读概率并保留framework-v2失败；修正参数传递后以framework-v3目录再次实际验证。

## Key findings

- 完整FASTQ为1,114,523,520字节；重新计算SHA256和8MiB分块multipart ETag与下载记录一致；记录保存对象version ID。
- 原生input-review.json为392,014条读段、1,384,109,852碱基、长度1000–120531，精确匹配目标文件专属官方统计。metamap另记392,181条，未归因167条差异。
- 原生模型为Medaka2.2.2的SUP5.2.0；原生run.json记录的源码哈希及最终FASTA哈希重新匹配。
- 独立重读HDF：736个chunk、7,360,000行含重叠/插入的五分类概率，行和范围0.9999997615814209–1.000000238418579，所有值有限。去除chunk重叠和插入重复后的独立major位置为contig_1的4,724,790/4,724,790与contig_2的81,815/81,815。
- framework-v1原生任务trace为COMPLETED/0，版本2.2.2；完整头部分别为contig_1和contig_2，序列内容全长相同但输出顺序相反，字节不相同。原失败JUnit及stderr保留，不改写为历史通过。两次stderr均为FileNotFoundException: null，实际首先失败于读取预期路径；顺序差异通过直接产物核对确认，不冒称已由原断言观察。
- 当前测试以完整头部到完整DNA映射比较，拒绝重复ID、空记录、头部前DNA及空文件。实际nf-test附带Groovy运行8个反事实控制通过，不自动更新snapshot。

- framework-v2仍为native断言失败/stub通过；实际源码未变。修复driver生成fixture-params.json，通过MEDAKA_TEST_PARAMS传递给测试setup.loadParams，在计算前强制验证三条路径均非空。Nextflow配置与断言使用同一份路径身份。

- framework-v3实际JUnit为2 tests/0 failures/0 skipped，native260.066秒、stub7.690秒；driver退出0、所有当前来源及隔离副本哈希不变。独立重读第三次完整FASTA也与原始CLI的完整头部/DNA映射相同。
- 相邻MMI真实反例：在私有完整draft旁复制有效索引，仅将MMI四字节magic改为BAD!并保留大小16,845,330及mtime。第一次observer预期明确拒绝而断言失败，原生退出未保存；第二次单独attempt明确保存原生mini_align退出0。实际minimap2将损坏索引按FASTX解析，产生警告，mini_align仍生成可通过samtools quickcheck的432字节BAM及BAI，但BAM记录为0。完整392,014读段未下采样；这是损坏资源造成的无效结果，不是生物学阴性。原始资源哈希保持，两个私有MMI都已恢复；没有将恢复字节等同于缓存复用。

## Interpretation

实际HDF覆盖验证排除了仅靠BAM覆盖或draft回填宣称神经计算覆盖的错误。软件参考与模块首轮输出的全序列对应支持本样本的计算一致性，但不支持FASTA字节级复现；并行stitching顺序可变化的原因尚未作源代码级证明。记录顺序不影响按ID归属的序列结果，测试修订保持全部序列身份要求。不能据同样本已抛光draft推断本轮降低了错误率。

索引反例证明原生工具不一定显式拒绝损坏MMI，后续门禁必须在计算及缓存判定前核对索引格式、参考一致性与内容身份，并拒绝损坏资源；不能只依赖工具非零退出。该反例沿用TA-091，不新增重复问题或提前计修复。

## Artifacts

根目录：results/tool-audit/20261027-medaka-nomiss/。

- Results：native-v1/native/consensus.fasta、native-v1/native/consensus_probs.hdf；framework-v1/work/tests/f36e364003ca2c7b29fe5451c23fee80/work/77/651ffdd98d636f59115b0894bfd8ac/test.fa.gz。
- QC and visual reports：native-probability-coverage-recheck.json、native-v1/coverage.tsv、framework-v1/junit.xml。未生成图形或生物学准确率报告。
- Provenance：sample-downloads.json、native-v1/input-review.json、native-v1/run.json、framework-v1/run.json、review-recheck.json、record-oracle-controls.groovy。
- Provenance增补：framework-v3/run.json、framework-v3/junit.xml、framework-v3/fixture-params.json、index-error-v1/observer-review.json、index-error-v2/run.json及flagstat.txt。固定证据哈希清单见docs/tool-audit/evidence/20261027-medaka-real-review.json。
- Model synthesis：本文件；正式接受状态保持false。

## Limitations and blockers

TA-091仍未关闭：Medaka模型/相邻FAI和MMI读取集合、查缓存前身份、同大小同mtime变异重算、损坏真实失败及还原复用尚待生产集成和实际验证。环境/provider/OCI、Dorado隐式模型、MOB默认资源与其他开放问题未由本轮验证。正式718项接受来源清单不改，不将本轮候选自动计入99项已接受修复。Rosalind及NGS Workbench技能用于恢复上下文和证据解释；BioNeMo技能经适用范围检查，本轮没有执行BioNeMo/Parabricks模型或GPU任务。

## Recommended next step

framework-v3终态、JUnit和全产物身份已复核；下一步推进模型及相邻索引的生产门禁与缓存反例，必须包含损坏MMI原生exit0/空BAM的拒绝控制。保存首次失败与此次修订的独立来源身份；完整输入和当前模型/环境继续保留。
