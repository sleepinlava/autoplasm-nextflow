Takeaway: Medaka可选CLI分支（-x强制重建、-B regions、RLE检测）完成探测级真实验证；helper行为与固定原生脚本逐行依据一致，RLE真实变换执行仍因无本地RLE模型而未覆盖。

继 [缓存队列复核](medaka-cache-queue-review-20261027.md) 之后，本轮补TA-091的可选参数读取集合与调用端边界。验证为probe级（不执行抛光推理），使用完整真实细菌reads身份与任务私有draft副本，原始资源前后哈希不变。驱动 `tests/run_medaka_optional_branches.py` 在固定medaka-2.2.2-cpu prefix下运行，全部断言通过。

## Scientific context and question

沿用NO-MISS sample_1_1完整filtered读段与同样本draft；无新下载、无病毒元素、无生物学真值宣称。问题：可选CLI分支下helper绑定的资源读取集合是否与原生日志真实一致，以及生产调用端probe/consumer配置边界是否健全。

## Key findings

- 原生依据（固定medaka_consensus 2.2.2，SHA钉住）：RLE分支148–165行在输出目录生成draft.fastrle.gz变换副本，DRAFT指向变换后文件；`-x`在170–172行给mini_align加`-f`强制重建索引；`-B`在186–204行仅向`medaka inference`传`--regions`。
- `-x`+故意损坏的相邻FAI/MMI：探测rc 0，receipt `force_indexes=true`、`source_indexes=null`——helper不绑定原生从不读取的索引，与`mini_align -f`语义一致。
- 同一损坏fixture不带`-x`：rc 1拒绝（"Adjacent Medaka index differs from native reference rebuild: .fai"），不出receipt。
- `-B regions.bed`（contig_2:0–81815）：receipt记录BED内容SHA256与native_args回显；无`-B`对照receipt `regions=null`。注意边界：`-B`路径经ext.args传入，不是Nextflow暂存输入，缓存身份靠helper记录内容身份+执行前复核维持。
- RLE检测等价：原生`medaka tools is_rle_model`CLI、helper `is_rle_encoder`、receipt `rle`字段在所选sup_v5.2.0模型上一致为false。包内恰有4个非RLE模型，无任何已准备RLE模型且禁止下载，RLE变换分支仅以钉住源码与检测等价为据，未真实执行。
- 调用端边界：`conf/nfcore_qc_assembly.config`的`withName '^MEDAKA(_RESOURCE_PROBE)?$'`选择器给probe/consumer相同ext.prefix/args；运行身份含args并在查缓存前比较；暂存输入身份经符号链接解析到同一原始文件，故probe receipt与消费者复核一致（cache-v2真实运行已证）。

## Interpretation

可选分支的helper读取集合声明在探测级与原生行为一致：force模式跳过相邻索引绑定、regions身份被纳入缓存上下文、RLE检测与原生CLI等价。支持TA-091候选继续推进，但RLE真实变换执行与`-x`/`-B`全推理执行仍缺，不按本轮关闭TA-091。

## Artifacts

- 驱动：`tests/run_medaka_optional_branches.py`（SHA256 646148752d…）
- 结果：`results/tool-audit/20261027-medaka-optional-branches/run.json`（SHA256 d3924227b4…）及4份receipt/fixture
- 固定证据：[evidence/20261027-medaka-optional-branches.json](../evidence/20261027-medaka-optional-branches.json)

## Limitations and blockers

探测级验证未执行`-x`/`-B`下的完整推理；RLE分支无真实执行（无已准备RLE模型，禁止下载）；regions仅单contig单区间，未覆盖多区间/空区间；无OCI/平台/provider验收。正式99项verified、2退役、718来源清单与TA-091 in_progress状态均不变。

## Recommended next step

在资源身份队列框架内补`-x`强制重建与`-B` regions的完整真实推理执行（复用cache-v2 harness模式），或先转MOB Recon/Typer默认非病毒资源与Dorado隐式模型；RLE分支只有在合规获得已准备RLE模型后才能真实验证，否则保持源码级依据并明确记录该缺口。
