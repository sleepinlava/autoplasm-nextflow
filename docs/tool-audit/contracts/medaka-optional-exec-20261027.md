Takeaway: Medaka -x/-B可选分支完成完整真实推理验证，生产probe+consumer输出与原生基线逐字节一致；同时发现原生-B语义——只限制推理区间，不限制输出contig集合，非区间contig由draft回填。

承接 [可选分支探测级验证](medaka-optional-branches-20261027.md)，本轮用完整真实CPU推理闭合`-x`/`-B`执行缺口。驱动 `tests/run_medaka_optional_exec.py`：先跑原生medaka_consensus基线，再经 `tests/nextflow/medaka_runtime_resources.nf` 跑未修改的生产MEDAKA_RESOURCE_PROBE+MEDAKA，对照完整FASTA（头部+DNA）与gaps BED。原始模型/draft/FAI/MMI/reads前后哈希不变。

## Scientific context and question

沿用NO-MISS sample_1_1完整读段与同样本**已抛光**draft及固定SUP5.2.0模型；无新下载、无病毒元素。问题：可选参数分支下生产接线的真实推理输出是否与原生软件基线一致。

## Key findings

- `-x`：原生基线与默认native-v1共识完全一致（证实-x只强制索引重建、不改变结果）；生产运行probe+consumer均COMPLETED，receipt `force_indexes=true`、`source_indexes=null`，输出FASTA与gaps BED（空）均与原生基线一致。
- `-B contig_2:0-81815`：原生行为为——推理限于BED区间，但stitch仍输出全部contig，非区间contig_1作为gap从draft回填（gaps BED `contig_1 0 4724790`）。生产-B输出的FASTA与gaps BED均与原生基线逐字节一致，receipt记录BED内容SHA256。
- 新原生行为记录：`-B`不限制输出contig集合。由于本fixture draft已是抛光结果，序列层面无法区分"抛光"与"draft回填"，判别性证据是gaps BED与receipt，这是本fixture固有的oracle弱点。
- v1失败尝试保留：初审者误设"-B限制输出contig集合"断言失败，原生证据修正oracle，生产代码与helper未改动。

## Interpretation

可选分支在真实执行下与原生软件一致：`-x`不改变科学输出、跳过相邻索引绑定；`-B`的regions身份进入缓存上下文且推理范围受控。TA-091的默认/压缩/缓存/可选参数(-x/-B)现均有真实证据；RLE分支仍只有源码级依据。

## Artifacts

- 驱动：`tests/run_medaka_optional_exec.py`（SHA256 4beb5848c3…）
- 结果：`results/tool-audit/20261027-medaka-optional-exec-v2/run.json`（SHA256 441d49befe…），native-x/native-b基线与production-x/production-b完整trace/log/consensus
- 保留失败尝试：`results/tool-audit/20261027-medaka-optional-exec/`（v1）
- 固定证据：[evidence/20261027-medaka-optional-exec.json](../evidence/20261027-medaka-optional-exec.json)

## Limitations and blockers

fixture为已抛光draft，序列级oracle弱；-B仅单contig单区间；RLE真实执行缺（无已准备RLE模型，禁止下载）；无重试/OCI/平台/provider验收。TA-091保持in_progress，正式99/2/718不变。

## Recommended next step

TA-091仅剩RLE真实执行与全环境/OCI边界——无合规RLE模型则保持源码级依据并记录缺口；建议转MOB Recon/Typer默认非病毒参考库准备与Dorado隐式模型（原计划第7步），并独立复核TA-092/093/094/095候选。
