# OPERA-MS 首轮契约核对

基线 f57d0f91454ee0c99cf462ac9093bdf68349991a；取证日期 2026-10-20。

官方固定版本：[v0.8.3 OPERA-MS.pl](https://github.com/CSB5/OPERA-MS/blob/v0.8.3/OPERA-MS.pl)，GitHub 返回 blob SHA `08c41900c791669dabd0755329d4fe615a7ca04a`。定位：`read_argument`、`set_default_value`、`write_final_assembly`。CLI 的 short-read1/2、long-read、out-dir、num-processors 与当前包装相符。默认 POLISHING=0；最终输出为 OUTPUT_DIR/contigs.fasta，由 scaffoldSeq.fasta.filled 和 scaffolds.scaf.cname 生成。

本地模块先选 GF3/contigs.fa，再选最终文件，最后任意搜索，不能保证最终产物身份。TA-001 为静态确认差异；具体数据集受影响程度尚未运行量化。建议固定最终路径并删除搜索回退。若以后启用 polishing，应另行约定 polished 输出。

本机实际 OPERA-MS 版本、依赖锁、数据校验、Nextflow 版本未核实；无真实运行通过结论。启动方式 perl 与固定版本无 shebang 的源码一致，但 PATH 启动和依赖完整性仍需运行验证。

## 2026-10-20 OPERA-MS 输出选择及PATH调用适配

重新从GitHub读取v0.8.3 OPERA-MS.pl，blob08c41900c791669dabd0755329d4fe615a7ca04a，默认POLISHING=0，write_final_assembly写out/contigs.fasta。保留固定版本摘录evidence/opera-ms-v0.8.3-output.json。发现新增TA-050：原perl OPERA-MS.pl在任务目录无法按PATH查找脚本；原Nextflow任务exit2，chmod可执行的PATH observer按bash -ue重放同样exit2。改perl -S后，原结果选择4场景3失败：选中GF3中间结果、接受仅中间文件、任意decoy。最小补丁仅接受非空最终contigs.fasta并显式诊断缺失/空产物。

最终5/5人工接口场景通过（16.301秒）；原P3增加output_dir/contigs.fasta与下游FASTA全文一致断言，但未执行。receipt和完整命令/trace/输入/产物哈希保存在results/tool-audit/20261020-opera-adapter-fix/。早期observer未chmod的探针和缺-ue的手动重放单独保留，不能作为生产语义证据。

TA-001、TA-050均ready但未关闭：本机无OPERA-MS可执行及完整依赖，未运行真实组装、真实P3、hybrid子工作流或平台验收。此处Perl替身只生成带独立标签的产物，不计真实工具通过。历史若使用中间assembly，下游检测、coverage、注释和统计都可能受影响，真实验证后需重生成受影响结果。

## 2026-10-23：真实默认节点、内部失败与P3执行

以上为历史状态；本批局部验收见 `results/tool-audit/20261023-opera-native/receipt.json`。
官方v0.8.3固定commit a55285272ea5efb17b79f0b51800776b1a3cb4d3，Codeload归档逐项核对469个Git blob。
用上游Makefile编译sigma/OPERA-LG/SHORT_READ_ANALYSIS，源码文件未修改；系统g++绕过只读ccache，保持上游编译选项。
Perl5.32.1/R4.4.3/MUMmer3.23等110包、独立ncurses5.9一包、CPAN Switch2.17及完整DB锁见
`tests/opera-ms-native.lock.json`。Switch的590个上游依赖自测不计流水线测试分母。
同一锁还明确记录已实际使用的Python3.12前缀41包（包括Biopython1.85），避免漏掉脚本运行时；没有据此宣称新增任何模型推理验证。
默认参考库Figshare文件17290589为2,934,421,515 bytes/MD5 3d979db1bd72d2c0dff33cdfdec8ff89，
配套sketch17290511为42,858,600 bytes/MD5 67abfbd6ea87f99faca9ebc742204d60。
全量解压5242文件共9,770,538,818 bytes，逐文件SHA留在database-lock.json；没有用截断DB或关闭参考/菌株聚类代替默认运行。

新增TA-067：真实check_data拒绝.gz长读，当前hybrid及原P3恰好传gz。原模块真实任务在这里失败；
现在.gz/.GZ在任务私有目录解压，源文件SHA不变，坏gzip先于OPERA调用失败。
9个原模块Perl observer方法包括原5个最终选择、gzip/GZ/坏gzip和内部崩溃拒绝；observer不计算法运行，
带空格文件名只证明包装器边界，不证明上游内部所有路径支持空格。

新增TA-068：初始真实节点和修复setup后的旧P3都“通过”，但内部short_read_analysis.err有
SAMtools0.1.19的compressBound断言崩溃。系统libz是1.3.1.zlib-ng，compressBound(65280)=69373，
不满足旧工具要求的<65536；独立前缀libz1.3.2为65311。help/依赖检查均无法暴露此故障。
修正审计运行环境的库绑定，原二进制/算法不变；生产模块另在发布前检查必需覆盖度诊断和所有常见日志，
已识别的断言崩溃/segfault/aborted/缺共享库或可执行文件会失败。它是有界致命诊断防线，不能证明每种未报告的子进程失败都会被捕获。
真实故意坏ABI运行仍生成原始最终FASTA，但当前模块失败且不发布FASTA/目录；不能把该场景当作阳性组装。

新增TT-011：原nf-test的GString提前解释嵌入Nextflow代码中的root，产生MissingPropertyException，0任务。
对内层root插值转义，保留环境读取；又给P3加入覆盖度日志断言，防止仅文件存在/FASTA header造成假绿。
官方nf-test0.9.5（release SHA256校验）及固定nft-utils1.2.1/nft-bam0.7.0实际运行原P3，通过1个原始用例。
dry-run的PASSED不是执行通过；旧setup失败和旧P3内部崩溃却green的证据都保留。
扫描全仓库时仍报告其他vendored测试缺依赖，TT-005继续open，不从这一个P3推导全套框架就绪。

默认参数的真实原模块与原P3各完成一次，独立BioPython解析、最终文件身份、FASTA统计和完整解压流SHA相符；
分别57contigs/1,776,306bp与56contigs/1,791,905bp，最长均874,908bp。
同一固定输入重放产物不完全一致，未给差异归因，也未声称字节级复现或科学组装准确率；各运行只对自己的最终产物和stats交叉核对。
没有为凑数字修改算法、阈值、参考库或用一次结果硬编码所有重放。
六样本hybrid连接回归201任务通过，其中宿主过滤用真实minimap2/SAMtools，独立核对送入组装器的全部read ID/DNA/质量；
组装/分类等其他CLI仍是明确observer，六OPERA任务均使用当前内嵌检查器。

TA-001/050/067/068及TT-011仅按上述有界接口/错误传播/原P3范围关闭；完整真实hybrid平台、替代参数/镜像与科学基准仍未认证。
原45独立main P0分母未变。其他严重问题（COPLA实体、PLASMe推理、TETRA阈值）不由本批关闭。
