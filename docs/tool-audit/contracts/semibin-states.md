# SemiBin 2.4.1：合法零 bin 与真实检查点输出

2026-10-23，TA-049及新增TA-079局部verified。只验下述CPU/default短读长方法、输出与路由边界；不认证完整模块/GPU/镜像/平台或生物学分箱效果。

## 固定依据

官方[v2.4.1提交932d98b](https://github.com/BigDataBiology/SemiBin/tree/932d98b13761c3f64a928e1b74e41649d3c8bf14)，tag对象43c8f441；完整169个Git blob、77,710,133字节已核对。实际Conda构建2.4.1 pyhdfd78af_0，Python3.12.15/PyTorch2.14.1 CPU；128包归档SHA256/MD5完整锁定，安装后16 Python、12内置模型、1 marker HMM、3 Markdown共32个blob与固定源码一致。这只证明安装身份，不代表12个内置环境模型都运行过。锁在`tests/semibin-state-native.lock.json`，原始证明在`results/tool-audit/20261023-optional-boundaries/semibin-runtime-proof.json`。

[utils.py](https://github.com/BigDataBiology/SemiBin/blob/932d98b13761c3f64a928e1b74e41649d3c8bf14/SemiBin/utils.py)的write_bins只保留达到minfasta的bin；[main.py](https://github.com/BigDataBiology/SemiBin/blob/932d98b13761c3f64a928e1b74e41649d3c8bf14/SemiBin/main.py)和cluster路径在合法零bin时仍生成诊断CSV/TSV及空output_bins目录，正常退出。contig_bins.tsv的标签不等于过滤/重聚类后最终保留的FASTA集合，不能用非负标签数当最终bin数。

默认无预训练environment时，2.4.1进行自监督训练并写`model.pt`；[semi_supervised_model.py](https://github.com/BigDataBiology/SemiBin/blob/932d98b13761c3f64a928e1b74e41649d3c8bf14/SemiBin/semi_supervised_model.py)提供安全weights_only加载器。原包装器model glob仍是*.h5，成功分箱也不发出实际检查点（TA-079）。

## 修复契约

只将最终`output_bins/*.fa.gz`改为optional。原必需CSV/TSV及工具错误仍保留约束；工具异常不能转换成no_bins。新binning_status.json必需，记录`bins_ready`或`no_bins`、数量及最终文件/长度/contig数/N50/L50。适配器以固定recluster_bins_info.tsv表头与最终gzip文件集合逐一对应，拒绝缺目录、未知压缩格式、空文件、错表头、重复/缺失/残留文件或无效指标；先验证再写状态。不修改分类标签、最小长度、阈值、训练或随机性设置。其他非默认压缩/方法没有因此获支持。

模型输出单独改为真实*.pt，预训练模式未产生本地模型时仍可为空；不是升级工具或改变算法。两份顺序补丁分别记录状态/空结果修复及检查点格式修复。stub不再凭空造四个bin或模型，输出明确`stub_not_validated`且bin_count=null；这不代表生物学零结果。

MAG既有路由消费实际FASTA；单个SemiBin零结果不调用质量/分类器，DAS汇总仅使用可用分箱器。所有选定分箱器均无bin时不启动DAS/质量/分类模型；样本的状态/诊断与无MAG关联结果仍保留，不吞掉其他样本。没有改变用户决定的“多分箱必须显式DAS、单分箱直接下游”规则。

## 原生与测试逻辑验证

使用完整官方single_sample_data：FASTA/BAM来自同一固定commit，40条contig共800,000bp。此为官方软件fixture，不能称独立真实群落/湿实验真值。保持默认CPU自监督15epochs，测试固定seed0；未借预训练模型或降低epoch绕开训练。默认运行产生非空最终bin；零bin边界显式设minfasta1000KB，大于输入总长度，因而在不依赖分类真值的条件下应无最终FASTA。

原模块此时工具正常退出0、CSV/TSV存在，却被Nextflow判FAILED（缺必需FASTA）；实际模型训练并非失败。修复后此输入COMPLETED且no_bins，不造FASTA，模型检查点正常发出并可用固定程序的weights_only加载器读出、所有参数有限。原模块阳性同样真实产生model.pt但model通道为空；修复后正确发出检查点。

6个选定原生包装运行记录（原阳性、新阳性、指定目标resume、新零bin、stub、非法原生CLI），加保留的原零bin对照，共7trace：4COMPLETED、1CACHED、2预期FAILED。其中包含1个stub；原零bin的trace FAILED/exit0是被复现的旧输出契约错误，不能计工具失败或成功分类。独立BioPython逐条验证最终bin的ID/DNA来自原FASTA、无跨bin重复，并独立重算长度/contig数/N50/L50；不把首次聚类成员当生物学真值。原生模型安全加载检查覆盖阳性/缓存/零bin。4个独立单元方法另验状态、最终过滤语义、错误文件集/表头/压缩/重复数据及无部分状态输出。

原CPU/GPU nf-test的关键“全部featurised contig只出现一次”断言保留；旧空model/伪阳性stub快照改为显式文件集合、真实.pt/状态/数量、版本和CPU/GPU运行声明断言，未更新快照去接受错误输出。单文件/多文件形状均归一。**这些修改后的vendored nf-test和GPU尚未执行，不能称框架通过。** 真正原生P3检查由版本化tests/run_semibin_states.py执行。

MAG原子工作流11场景126trace（124完成、2预期失败）通过，包括单独/部分/全部SemiBin为空及DAS全空、混合分箱、原3种分箱器、关闭和工具失败。分箱器/DAS/质量/GTDB为明确标记的observer，实际CONCOCT I/O助手、DAS转换助手和R关联另行说明；这些126项不是126个真实模型任务。observer按官方最终summary schema输出受控数据，不借文件名推测bin身份；DNA/ID/meta及可用分箱集合由独立受控输入核对。首次状态路径oracle误写`<sample>.semibin`，实际默认prefix是`<sample>`；失败材料保留，按已声明prefix修正后重放，同一11场景不重复计数。

未改任何配置，沿用蛋白批次按当前9配置hash通过的12个profile；未新增main拒绝场景，仍61。原始材料在`results/tool-audit/20261023-optional-boundaries/`。本批另固定HOTSPOT提交0e3e3013及14个blob，仅用于后续TA-046准备，未修其解析器、下载权重或运行推理，不计入本批通过。完整M0–M4、其余tests逻辑、TETRA阈值失败、GTDB完整分类和AWS真实运行继续开放。
