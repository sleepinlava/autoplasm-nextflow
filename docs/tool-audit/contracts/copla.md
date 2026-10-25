# COPLA 独立候选、部署与错误语义

2026-10-23，当前批次 `results/tool-audit/20261023-copla-entities/`。
TA-019/020/074 已按固定官方1.0、完整RS84与原生执行的有界范围验证。原生双候选任务与真实nf-test已完成，不等于科学准确率或其他后端/完整平台认证。

## 固定来源和数据

- 官方 [COPLA commit 6b89285e](https://github.com/santirdnd/COPLA/tree/6b89285ef16d721d93d3c84f3645e76455ba8621)，全部30 Git blobs逐项匹配，脚本1.0；实际入口为 Python `bin/copla.py` 和4个位置参数。实际完整导入后的原长参数调用exit2，help成功；不是只提取argparse的证明。
- 官方精确环境188个包和独立MacSyFinder环境98个包，URL/MD5/SHA256归档均核验。graph-tool2.35真实加载完整9894节点/89591边及NestedBlockState；Numpy1.19.4/Pandas1.1.5/Python3.9.0。MacSyFinder1.0.5/MacSyView1.0.1原源码构建，103单元和1功能自检不计为流水线测试。
- 原数据库站点再次超时。上游[问题17讨论](https://github.com/santirdnd/COPLA/issues/17#issuecomment-4335493958)给出的历史归档能完整读取，原URL的2022-07-09快照，原Last-Modified为2020-12-14。357,242,880字节归档SHA256 `977fdc4fb31b56fc901b1ec4908266f581748276c46cc10218abe8e5a3d4df5c`，SHA1与Wayback CDX的Base32 `QFHEUVZJSHNSGZ3XAUL7U4KOA77N5TSP`独立相符；10228普通文件、9894个完整参考解压/逐SHA，包含原MOB/CONJ/PlasmidFinder/CARD3.1.0资源。不是最新库或缩小参考集。
- Enveomics `ani.rb` 固定说明中下载日期前的最后文件提交 `fcf1517fbe0a9a2b499a6e4dadebc1c26758ea9c`；实际原生参考配对99.976/0.050/157/162与官方示例一致，错误传播补丁前后的同输入数值逐字相同。
- 旧Perl/Ruby在宿主缺`libcrypt.so.1`；从已锁定Debian镜像取到兼容库，并与官方Debian `libcrypt1_4.4.38-1_amd64.deb`解包字节核对相同。只置于已声明安装目录的`lib/`，不覆盖共享Conda文件。完整来源见公共`tests/copla-native.lock.json`和运行锁。

## 输入、实体与输出

原模块将整样本FASTA一次传入，而COPLA把其所有记录简单拼接为单一query。当前每条候选记录独立调用，保存原始ID、完整DNA、长度及映射；它们是候选记录，未声称是已闭合质粒或已知归属的多contig质粒。未知拓扑按linear，明确`topology=circular`/`circular=true`才用circular；冲突标记失败。不能因一条描述里出现普通单词circular就改变模式。

输入为样本tuple、显式参考graph/list、完整准备好的安装目录和独立MacSyFinder前缀。列表引用必须位于已声明安装目录内，防止未跟踪的全局参考；目录名称不限。用任务内安全文件名链接参考和候选，内部未引用路径的旧shell不再收到带空格路径。参考accession集合必须与图一致；不静默忽略缺少的参考文件。

只读确定的`<query>.ptu_prediction.tsv`，检查唯一完整行、原始分数有限且在[0,1]、宿主范围罗马等级；`-`的合法未分类结果保留。规范化表含contig_id/length/topology/entity_scope/predicted_ptu/host_range/score/notes；分数是分区一致性，适配器不再按0.9筛选。原始FASTA/FAA/ANI/PTU/annotation等及entities.json全部保留。全部候选成功后才生成样本汇总；任一失败不得发布部分结果，也不选择任意首个TSV。发布前移除数据/模型链接，避免把整库复制进每个样本产物。

## 有界源码适配及审查纠错

只为匹配的官方脚本和4个辅助脚本SHA生成任务私有副本：检查Python、Perl、Ruby、shell的外部退出码，保留诊断；非空蛋白的HMMER错误不能当作MOB未检出；去除旧shell对全局Conda环境名的依赖，显式调用已声明Python2前缀，并约束线程。源码和数据安装保持不变。ANI的1000bp窗口/200bp步长及其他阈值、图模型、MCMC参数未变。

完整参考中29条长度≤1000bp，按原窗口生成规则无可评估窗口；明确记录`not_evaluable_no_fragments`，不把这类可判定的无窗口状态当成BLAST故障。每个候选的ANI评估表必须覆盖全部声明参考；子程序错误仍失败。

真实边界复核纠正了一次错误初判：固定位置截断在未启用的FastANI函数，实际`insert_ani_edges`本就正确。撤回该多余改动，不登记解析器缺陷。最初边界脚本还错误期待“缺参考文件”在Perl处被忽略，实际该读文件错误本来就失败；改为有效真实DNA加缺BLAST可执行程序环境，才复现真正被忽略的Ruby子进程错误。两次错误测试的原始记录保留，没有用错误假设改生产凑通过。

## 当前验证边界

16个候选/格式方法、9个原生ANI/真实图函数/HMMER错误控制、5个原downstream的DNA驱动observer选择/跨样本/原子失败场景已经过验证；它们不能替代完整模型。上一批51个入口场景之外，曾拟加11个COPLA检查；其中固定参考目录名的额外限制已撤回。当前61个实际非法输入场景已按当前main重放通过，全部0分析任务/0命令文件。

最终全库原生双候选与真实nf-test单候选均完成，使用同一个完整图/全部9894参考，其中一个参考路径特意放入含空格/单引号的自定义目录，DNA逐字不变。原生同一样本的33305bp NZ_CP028167.1与49442bp NZ_CP028329.1分别得到预先锁定的PTU-X4/PTU-Lab26，均1.0000；独立BioPython核对ID/DNA/长度。nf-test0.9.5的1个压缩Lab26用例通过，是同一生物样本重放，不计第三个独立阳性。三个候选执行各覆盖9894参考，短窗口不可评估单列；产物无数据库/图/参考外链。全部30 Git blobs及20122份归档/解压数据文件终验SHA不变。两个此前中断的任务没有完整模型结果，不计阳性或阴性；首个带多余FastANI改动的实验也显式终止并保留。真实RGI下游开启/关闭回归通过。完整证据见本批verification.json、source-proof.json和receipt.json；科学准确率、其他后端及完整平台仍需独立验证。
