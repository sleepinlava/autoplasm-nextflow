# RGI实际CARD数据库选择与版本

## 2026-10-21 TA-028：真实RGI本地/全局CARD选择修复

上一目标轮完成PlasX/PLASMe适配与测试修正，本轮为继续推进，未重定义审计范围。TA-028已用真实固定版本工具/完整数据库复核并修复：RGI6.0.8原代码与GitHub固定tag的RGI.py/settings.py/Database.py/load.py/ORF.py/Filter.py匹配；native环境另含KMA1.6.11（仅version eval）、DIAMOND2.2.8、BLAST2.16.0、Prodigal2.6.3，Python3.11.17，256包explicit lock。Conda环境文件和nf-core revision0a93f68a28f5e07bb7ae82aeb005720faf8a3b35保持不变；原始blob a11398832cbd7675cd4fe28a34fe637ae903cd1c与GitHub重新获取结果一致，本地差异单独登记。

两份完整[官方CARD归档](https://card.mcmaster.ca/download)为3.3.0、3.2.8（非裁剪/虚构版本），下载包和解出JSON逐一锁hash；测试的全局路径由DB_PATH/DATA_PATH指向审计目录，未使用或覆盖系统库。上游6.0.8锁定的真实NC_020818.1质粒、NDM-1蛋白和CARD3.3.0的VIM-77真实参考序列用于限定sanity；独立预期VIM-77 model6038在3.2.8不存在、在3.3.0唯一，NDM-1/mphE/msrE参考断言来自固定上游tests/test_1.py。随机DNA为明确人工阴性，不是科学效果基准。

原模块在load本地3.3.0后仍用global3.2.8运行main，3任务全部COMPLETED/0，DB_VERSION甚至显示3.3.0，却把VIM-77记录报为VIM-2 model391/Strict99.62。原始全局库的独立protein CLI能Perfect100命中NDM-1，说明不是故意损坏global造成的失败。修复为main显式--local，与既有load --local一致；DB_VERSION来自card.json，不再任意ls/SED匹配文件名。加载前检查对应canonical/all注释文件；加载后确认localDB/card.json逐字节SHA256及loaded_databases.json版本与输入一致，避免load失败/陈旧库继续查询。验证器嵌入实际任务脚本并参与缓存身份，未改变模型、阈值、Prodigal模式或其余生产默认参数。

验证闭环：validator6方法全过；当前模块四个独立场景共6任务（global存在3、global为空1、版本/文件不符1预期失败、上游参数oracle1）全部符合独立预期。原PLASMID_DOWNSTREAM+真实RGI启用/关闭两场景，启用2样本2任务正确命中VIM-77及真实质粒参考，禁用0任务；逐样本加载CARD JSON hash一致，最终JSON/TSV样本名/数目正确，全局CARD保持原hash。合计8个当前任务脚本均含完整当前验证器两次；这是一个RGI工具节点的多个case，不是8个独立工具。actual main原有unknown optional tool拒绝场景也在新include下精确失败且0任务/0.command.sh，不增加37个P0分母。

保留全部校准失败：初始dry-run误用KMA1.4.14，明确中断且未安装；依据真实environment.yml更正1.6.11后256包安装成功。新测试最初把上游NDM-1断言套在生产默认Prodigal参数上；读固定上游才确认其使用low_quality/include_loose/include_nudge/clean/debug，默认本地和全局库均能找到mphE/msrE而未必找到NDM-1。生产算法未改，默认模式的原生检查与完整上游参数NDM-1/Perfect100检查分别保留并通过，不能把模式差异误归数据库补丁或盲目删断言。测试还出现fixture/case目录重名，以及上游专用配置选择器语法错误（0任务），均保留；只纠正并重跑受影响上游参数控制，未抹去final-native中失败记录。最终receipt聚合三个有效原场景和修正后的一个oracle，明确引用各自原始记录。

TA-028现在fixed/verified，仅限实际数据库选择/版本元数据及受影响注释子工作流；inventory整体仍investigating。镜像、nf-test框架/JUnit、wildcard分支、完整平台/P4及临床AMR检出性能尚未认证。旧RGI输出若不能证明查询库与配置一致，应在新输出目录重算。证据与8源增量补丁：results/tool-audit/20261021-rgi-database-scope/receipt.json，patches/TA-028.diff，local-patches/rgi-main.diff。当前62问题=18verified+2按用户要求退役+42未决（10S0/2S1/30S2），全量审计未完成。

本批测试可复现入口另已放入tests：rgi-database-scope.lock.json锁定两份完整归档和上游质粒SHA256，prepare_rgi_scope.py只读本地数据、拒绝覆盖准备目录并调用实际固定RGI；完整运行成功，生成的10项关键输入与本批原始fixture逐字节一致，旧global真实查询仍为VIM-2 Strict。原生运行说明已加入tests/nf-test/README.md，明确独立native测试不冒充nf-test执行。增量补丁最终共11源（含测试数据锁/准备器和说明），来源台账94份中当前90、用户退役4；manifest不充当测试用例计数。成功任务stderr已逐项复核，无隐藏ERROR/Exception。
