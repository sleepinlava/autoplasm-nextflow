Takeaway: Medaka真实早期失败重试成功；原始模块普通gzip冷失败与当前全序列对照齐全，TA-096仅按压缩接口范围接受。

本轮继续核查完整细菌样本的Medaka压缩接口及失败恢复，先确认旧缓存队列已终态而未重启。实际Nextflow控制在模型和私有draft准备后注入一次版本检查失败，首个尝试没有生成成功FASTA。Nextflow重试时分配了不同工作目录，第二次真实推理完成，完整头部和DNA与原始软件基线一致。原始模型、参考、索引、读段和生产来源在前后复核保持不变。补跑修复前原模块还确认，同一完整普通gzip输入确实冷失败于samtools索引。结合既有真实原生、压缩和缓存对照，TA-096获得有界接受，完整资源审查TA-091继续开放。

## Scientific context and question

沿用完整NO-MISS sample_1_1细菌来源filtered读段、同样本已抛光draft及固定Medaka2.2.2 SUP5.2.0。没有新序列/模型下载、没有下采样或更改科学阈值，没有病毒元素执行。同样本draft仅是软件比较输入，不是独立生物学真值。Rosalind与NGS Workbench的证据和生命周期解释原则继续适用，本轮未执行BioNeMo替代推理。

## Question, lifecycle, and endpoint

旧72092工具句柄不存在，实际cache-v2/run.json已记录14阶段终态；后续逐阶段原始trace和产品又重读确认。新增tests/run_medaka_retry.py显式使用errorStrategy=retry/maxRetries=1，只有medaka_version_report shim首次返回7；真正的原生程序因此返回1，之后shim转交原有版本检查器。未修改生产helper。第二次实际消费者使用完整相同输入执行真实推理，不以stub或小片段替代。

## Key findings

- retry-v2：probe COMPLETED/0；MEDAKA attempt1 FAILED/1、attempt2 COMPLETED/0。两个workdir不同：ef/698cb34ba6a6f8685650546ab9e88e及7e/01dcff66f4892de207c01a273332d7。首个attempt已经生成medaka_private/draft.fasta，但无test.fa.gz与consensus_probs.hdf；第二次完整FASTA对应原始CLI全头部/DNA。
- first failure为明确注入的版本检查器错误，不是新发现的Medaka软件故障。实际重试分配新目录，故未出现此前怀疑的private.mkdir残留目录阻断；无需为这个假设改生产代码。
- retry-v1首次测试配置把$PATH当Groovy变量而在分析任务前失败。已保留原driver与observer-review.json；改用单引号配置字面量，retry-v2才是实际重试证据。未将配置失败当科学执行或测试通过。
- original-gzip-v1：从HEAD取出的原MEDAKA模块SHA与首次framework-v1记录完全一致，使用完整同一细菌reads和普通gzip参考冷执行，真实任务FAILED，samtools明确Cannot index files compressed with gzip，无成功输出。
- 当前cache-v2的11个guard来源和4项原始资源哈希再次匹配，独立重读10份成功/缓存输出完整FASTA均对应原软件基线。plain、ordinary-gzip、BGZF、同大小同mtime有效模型归档变化重算/还原CACHED、坏模型/MMI/FAI探测拒绝、上下文查缓存前拒绝构成14个阶段；重放不新增科学样本分母。
- 既有TA-092～095接受记录存在，但audit字段仍mismatch，runs也缺该接受receipt登记，生成器仅识别source而忽略source_state。此次按现有接受校正为fixed/verified、登记旧receipt并扩展schema识别，未扩大四项范围。
- 当前110项=104有界verified+2退役+4未决；TA-091是唯一剩余S0，TA-016/031及TT-003为S2。13份Medaka测试/observer/快照来源补入tests来源台账，总355份；来源存在不增加执行用例分母。冻结718清单现有123项不匹配，明细保存，不沿用旧18项说法。

## Interpretation

完整原模块的实际冷失败与当前完整推理成功明确支持压缩接口修复。重试真实行为验证了正常Nextflow早期子进程失败恢复和无失败产物发布，不支持所有失败阶段的泛化结论。完整FASTA与HDF概率检查分别证明软件一致性与实际神经覆盖；不能据已抛光同样本draft宣称降低错误率。独立来源、产品与失败证据的交叉核对支持关闭TA-096的压缩接口范围，不支持关闭TA-091完整资源范围。

## Artifacts

- Results：results/tool-audit/20261027-medaka-retry-v2/run.json及第二attempt/test.fa.gz；原模块对照为results/tool-audit/20261027-medaka-original-gzip-v1/run.json。
- QC and visual reports：原14阶段trace、框架JUnit2/2、ordinary-gzip-v1/review.json神经位置覆盖。本轮没有独立生物学质量图。
- Provenance：retry-v1原driver/config失败，retry-v2命令/shim/trace/代码与原始资源SHA；接受清单results/tool-audit/20261027-ta096-acceptance/receipt.json及review.md。生成器状态修正为evidence/20261027-status-reconciliation.json，冻结源差异为evidence/20261027-accepted-manifest-drift.json。
- Model synthesis：本文件。

## Limitations and blockers

只接受已验证的ordinary-gzip无旁索引完整解压及默认plain/BGZF对照。歧义gzip旁索引仍明确拒绝，RLE无已准备合规模型未真实执行。晚期推理失败、外部杀进程恢复、手动在同workdir重跑、所有OCI/provider/环境与完整ONT科学链仍开放。单一Podman镜像结果仅是有界证据。TA-091、TA-016、TA-031和TT-003未关闭，正式718清单保持原字节。

## Recommended next step

回到TA-091的MOB Recon/Typer默认资源与Dorado模型读取集合。固定MOB3.1.9软件config指向[Zenodo10304948](https://zenodo.org/records/10304948)；该公开记录元数据称MOB-suite数据库3.1.8、归档472.9MB及MD5，但未下载、解包、建立或认证生物参考库。先验证实际归档身份、内容与用户非病毒约束及可用空间，再使用既定完整参考与固定软件实施准备；不能直接调用会关闭TLS验证和自动初始化taxonomy的原mob_init，也不能用占位库宣称通过。
