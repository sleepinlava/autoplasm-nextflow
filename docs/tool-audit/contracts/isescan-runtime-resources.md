# ISEScan运行资源身份候选契约

本批仅为TA-091的第六份未接受增量，正式718项源码清单与99项有界修复、2项用户退役、4项未决保持不变。完整证据见[候选收据](../evidence/20261026-isescan-runtime.json)。

生产ISESCAN新增cache:false资源探测，经完整meta连接资源身份、receipt和校验脚本，再进入原消费者；Conda/container/engine/accelerator/beforeScript/modules/containerOptions/output prefix不一致时，在消费者缓存查找前拒绝。消费者深度缓存并在执行前重新测量；资源须在探测至运行期间保持不可变。配置部署须保持探测关闭缓存；未添加未经验证的task.cache钩子。原输出目录接口及科学参数不变，stub明确标记无推断。

身份覆盖固定1.7.3入口及8个Python源码、实际constants按入口argv0解析的两个pHMM资源、序列、run_FragGeneScan.pl及其调用路径的二进制/整个17文件train目录、phmmer/hmmsearch/BLAST工具、Python/Perl，以及由已加载ssw_init符号通过dladdr确定的SSW实际对象。记录真实定位路径及内容/长度/权限/符号链接；不猜测prefix/lib或LD_LIBRARY_PATH。constants执行使用可信固定发布源码，保留argv0；别名路径单元检查已捕获并修复runpy临时改写argv0的问题。Linux原生已测，其他系统未认证。

ISEScan继续使用上游默认FragGeneScan illumina_5/w0。SemiBin可选FragGeneScan使用complete/w0，尚未接入该可选分支；不得为指纹便利替换模型。FragGeneScan实际C源码按argv0定位train并读取8个共享参数及选定模型，整个17文件目录保守记录。来源为[ISEScan固定发布](https://github.com/xiezhq/ISEScan/tree/1.7.3)（提交83a74eccb0eef89674e1e49fba31cb4cab29018f）及[FragGeneScan1.32归档](https://sourceforge.net/projects/fraggenescan/files/FragGeneScan1.32.tar.gz/download)，归档哈希、83包锁与完整fixture哈希记录于tests/isescan-native.lock.json；所有83个缓存包归档SHA-256直接复核。固定版本独立envs/isescan.yml已接生产，原annotation.yml仍保留；本地现代依赖环境确实原生运行成功。

最终native-cache-v6为12阶段/22条trace：16 COMPLETED（12探测、4原生科学成功）、5 CACHED、1预期真实hmmsearch失败；两次上下文不匹配仅探测提交，消费者未提交。完整原始NC_012624.fna不裁剪，默认参数运行，输出1个IS5（30355–31343，989bp）及ORF（30399–31298，900bp）。四次原生阳性均比对原始工具TSV及独立从完整输入提取的IS/ORF DNA，不将它当生物学真值或准确率基准。不变/还原复用原冷运行精确哈希；私有pHMM DATE元数据、FGS模型空白、SSW非分配.comment段等长同mtime变化触发重跑，算法数据未改；坏HMM头真实失败后还原复用缓存。全83包独立always-copy环境避免原环境RPATH影响，30个观察文件结束时逐字节恢复，原环境未修改。

6项最终单元方法检查版本拒绝、argv0别名读取位置、SSW实际对象及篡改receipt执行拒绝。主流程mock最终166任务包含6个探测，真实Nextflow/R/report保留原全部producer覆盖断言，资源JSON纳入08_annotation报告证据；外部科学工具与资源扫描均明确observer。17条执行源码比较全部直接匹配当前源码。六份顺序补丁对130个候选路径正向字节/权限、反向HEAD字节精确核对；748项当前快照独立保存。

失败/替代尝试在results/tool-audit/20261026-isescan-runtime/attempts.json逐项保留：不存在DESC的驱动假设、薄复制RPATH、旧/proc解析、runpy别名失败、错误PATH、sandbox DNS/cache权限等；不累计为最终成功分母。

仍未覆盖：NumPy/SciPy等完整Python与系统共享库身份、OCI digest/provider/GPU/全部when与自定义配置、所有合法零结果/压缩输入路径及完整科学平台。资源JSON报告事件不等于TA-016完整方法/环境来源。其余6隐式资源对待接线；TA-091仍S0，S2、完整GTDB r232、真实shotgun P4、M0–M4和AWS范围继续保留。本批无提交/推送/AWS创建/上传/收费。
