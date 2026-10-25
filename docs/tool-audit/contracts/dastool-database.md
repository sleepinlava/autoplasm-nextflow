# DAS Tool1.1.7 可选数据库接口

2026-10-21；TA-054现局部fixed/verified。基线f57d0f91454ee0c99cf462ac9093bdf68349991a，仍未给完整MAG或科学结果放行结论。

固定[DAS Tool1.1.7源码](https://github.com/cmks/DAS_Tool/blob/1.1.7/src/DAS_Tool.R)定义--dbDirectory。本地原module非空数据库却拼成--db_directory；真实原module任务在CLI解析阶段失败且无查询产物。源码、包归档与六文件DB来源验证见results/tool-audit/20261021-dastool-custom-db/upstream-receipt.json及tests/dastool-db.lock.json。实际包为das_tool1.1.7-r44hdfd78af_1，归档SHA256与缓存实际字节一致；六文件DB共85,354,910字节，文件SHA256与完整包清单逐一相同。R/bash源码Git blob再次核对固定primary，未修改工具/版本/环境声明。

只改拼写仍不足：上游bash launcher的$@以及R生成的辅助命令不保留带空格的路径；参数值恰为db时还被视为内置数据库默认值。module现在把非空目录暂存为固定dastool_db，用--dbDirectory dastool_db传入，目录来源保持Nextflow的实际path关联，不把原路径手工拼成shell字符串。[]仍走原内置DB分支，生产MAG_HOST默认传[]不变。

自定义DB要求bac/arc各自all.faa、scg.faa、scg.lookup共六个非空文件。查询前明确拒绝非目录、缺文件或零字节文件，防止不完整用户DB落入上游自动解压/替换分支；不把工具错误转成空结果或写入用户DB。这个预检只证明结构满足接口，不证明任意文件的生物学正确性。

最终原生8场景/8任务：原错误参数反例；含空格完整DB、basename为db完整DB、未指定DB默认分支三个正例；缺文件、空文件、文件冒充目录三种预检错误；以及basename为db的明确受控不匹配lookup负例。正例全部使用完整正版六文件、固定官方gut assembly与四套预测，以固定上游15-bin成员表/汇总表核对数量、大小、成员和全部DNA。没有改变score0.5、导出选项或其他算法默认值。部分场景使用此前同一assembly实际Prodigal生成的蛋白，原文件运行前后不变；含空格/默认正例实际执行默认基因预测。

负例保留完整真实reference FASTA，仅把两个lookup换成不匹配的测试ID；原生DAS明确报告No single copy genes predicted。如果工具忽略指定DB或因basename为db回退内置库，这个输入会像默认正例一样产出15 bins，故该对照检验了实际数据库读入路径，而非只检查命令字符串。它不是生物学阴性、灵敏度或自定义DB质量基准。

所有正负输入、内置DB与原生蛋白文件SHA256在运行前后不变；失败没有部分发布。32任务原MAG/R回归验证[]分支与样本/分组/成员/DNA/数量不变，quality/core分类器等observer范围与真实DAS分开。35次成功任务stderr无隐藏错误。main未改，只重放一项原拒绝用例；45独立P0分母保持。

正式receipt：results/tool-audit/20261021-dastool-custom-db/receipt.json。五源增量patches/TA-054.diff；nf-core revision5be91832f7c6a2d229f900a239d9532c9ae133c7和原upstream_blob保留，差异另列local-patches/dastool-dastool.diff。未提交或远程写入；没有镜像/nf-test框架/完整平台或任意自定义DB生物学有效性认证。
