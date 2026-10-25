# CONCOCT1.1.0 输入、BED坐标和空提取

2026-10-21；基线f57d0f91454ee0c99cf462ac9093bdf68349991a。TA-032/055/056现为局部fixed/verified；整个MAG、镜像、nf-test框架和科学准确率尚未认证。

生产声明1.1.0 py39构建、setuptools70未改。实际隔离原生环境为CONCOCT1.1.0 py39h8907335_8、Python3.9.23、setuptools70.3.0、SAMtools1.24，共63包显式锁。cut_up_fasta.py的Git blob为c4e7f4dbff1ca0ff763ac9d7feda28e8c10c11c3，extract_fasta_bins.py为4c91e6c739243239a37b528b5c729b478a601ded；与固定官方[cut源码](https://github.com/BinPro/CONCOCT/blob/1.1.0/scripts/cut_up_fasta.py)、[extract源码](https://github.com/BinPro/CONCOCT/blob/1.1.0/scripts/extract_fasta_bins.py)逐字节一致。nf-core revision6d46786420b4d7bc88eba026eb389c0c5535d120保留，两个module的local-patches和bin/run_concoct_cut_checked.py另记。

两个脚本都按plain FASTA读取，因此包装器先把.gz/.GZ输入解压到任务内.concoct_input/assembly.fna，保留原输入及contig ID。plain不改写。未知contig、错CSV表头、损坏gzip均继续失败；不把异常转为无bins。

原cut helper以chunk_size-overlap为切片步长，却以chunk_size*i写BED坐标。生产未覆盖其chunk1999/overlap1900默认值，2400bp真实原生命令产生25个切片及24个越界区间。官方[集成示例](https://github.com/BinPro/CONCOCT/blob/1.1.0/tests/test_integration_with_scripts.py)采用10000bp无重叠末段合并，但本修复不替换科学参数：只在经Git blob核对的原源码中，把唯一BED表达式改为实际步长。切片DNA与原helper逐字节相同；不符合已审查source的脚本立即拒绝。默认重叠、显式非重叠/末段合并、无BED输出均验证，实际BED逐条满足原序列[start:end]等于对应切片，且在参考范围内。

extract helper对合法header-only成员CSV正常exit0且不写FASTA。旧wrapper随后因未匹配*.fa的循环及必需glob而失败。新wrapper使用nullglob和optional FASTA，只在真实命令成功时允许空结果；不创建假空bin。真实merge/extract在原MAG流的受控空成员场景中成功，质量/分类没有输入，原R宿主关联为空表。未证明核心CONCOCT在任意科学输入下产生header-only成员表，也未改变其失败行为。

证据：results/tool-audit/20261021-concoct-gzip/receipt.json。原wrapper四反例分别确认gzip cut、gzip extract、空extract失败，以及default cut成功却坐标错误。修复后17个原生叶场景验证ID/DNA/坐标/压缩/空结果/错误与source拒绝；完整原MAG的CONCOCT分支使用固定官方composition.fa350条真实DNA与明确构造的合法映射BAM，2样本12个真实节点，每样本122 bins，成员/原DNA一致，plain/gzip聚类成员集合相同。默认clusters400、seed1、iterations500、cut参数均未变。BAM不是实际测序/比对基准，分箱一致性不是独立生物学聚类准确率。

受影响路由额外14场景217任务：实际CONCOCT cut/merge/extract和原生R；核心分箱/覆盖度/质量/分类/DAS的observer与完整native分支分开。238次成功任务stderr复核无隐藏错误；预期失败从实际任务stderr检查诊断，不只搜索Nextflow显示的命令文本。

初始完整MAG测试误把六节点算成七节点，工具和其他语义检查成功而计数断言失败；保留mag-native/run.json为false。改为12任务及每个命名节点每样本恰一次后，真实分支重新运行通过。旧源、失败断言、source/数据锁和校准均保留。历史默认重叠BED会影响coverage及bins，应在新目录重算；DNA切片策略虽不变，修复前后分箱结果不能假定相同。
