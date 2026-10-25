> 2026-10-21 当前覆盖范围：SCAPP检测与binning已按用户明确要求退役，旧选项/权重/FASTA输入被拒绝；TA-006/035不再开放修复但不计verified。以下SCAPP相关段落为历史取证，不能视为当前支持或待实施方案。当前验证见 ../retirements.tsv 和 ../acceptance.md。

# 共识边界与工具身份

基线 f57d0f91454ee0c99cf462ac9093bdf68349991a；2026-10-20。

TA-042：parse_weights忽略无法转数字的token，weight_of对缺项返回1。原CLI同一阳性geNomad/阴性generic Platon fixture：genomad:0.6,platon:0.4 → plasmid；platon改为garbage → chromosome，两个退出码均0。全零active总权重输出chromosome且退出0；负权重也未拒绝。权重影响最终FASTA，输入错误不应默默改变方法。需定义有意缺省键行为，但显式非法值必须拒绝；有限性、重复/未知键、非负与active总和均需约束。未声称分数列一定参与weighted_vote：当前按binary vote及工具权重计算。

TA-043：identify_extra按文件名任意位置匹配 .plasme. 等，不按最终producer后缀。合法sample_id S.plasme.X经Platon产出 S.plasme.X.platon.tsv，会先命中plasme。原CLI对照使用相同assembly、空geNomad、Platon positive-only表p1/0.9、有效自定义权重genomad0.4/platon0.6/plasme0.1：普通S输出plasmid、tool_id=platon和非空FASTA；S.plasme.X输出chromosome、tool_id=plasme和0字节FASTA，均exit0。该样本ID符合生产允许正则，Platon标准文件命名直接来自生产module。默认权重下不承诺每个输入都翻转；使用文档允许的自定义权重已证明合法样本名可改变结果。

完整命令、退出码和人工fixture保留 results/tool-audit/20261020-consensus-boundary/run.json（4种权重）及identity-run.json（2种样本名）；未运行真实classifier，不是检测准确率基准。修复宜显式传tool/file关联，若暂用后缀则必须锚定精确producer后缀，覆盖全部工具关键字出现在样本名的情况，不能靠限制现已允许的样本ID绕过问题。

现有consensus测试具有正负分类token与weighted/majority差异断言，尚缺非法权重和样本名中工具名的变化不变性；计入TT-002覆盖差异。重复FASTA ID、重复同工具预测和分数边界仍待进一步验证，不在本批凭静态猜测新增缺陷。

## 重复 ID 与引用完整性

TA-044：原CLI输入两条归一化ID均p1的FASTA（描述不同、长度1200与1400），exit0；consensus只有一条p1，length1400，但最终FASTA含两条p1，长度分别1200/1400。contig_info使用字典覆盖最后记录，输出却用ids %in% keep保留所有重名记录。同一工具表重复contig_id也直接覆盖：p1 chromosome→plasmid输出阳性，交换两行后输出阴性；相同记录集合因行序改变结果。此为故意不一致输入边界，不声称上游工具正常运行必然生成重复。应在输入阶段明确拒绝，不能让静默覆盖成为去重策略。

同批unknown_summary_id：assembly仅p1，geNomad人工summary为absent；exit0、表中absent为plasmid/length空，但FASTA空。这是既有TA-006工具ID对齐问题的一般消费者边界证据，未重复计新问题，也未声称真实geNomad会输出不存在ID。需按工具契约区分原assembly ID和重建序列ID，后者必须有自身FASTA与显式映射，不能统一靠丢弃未知ID“修复”。

完整四场景命令、stdout/stderr和记录数位于 results/tool-audit/20261020-consensus-boundary/duplicates-run.json。均为原生原R脚本，无真实classifier。本地catalog_prepare已有重复sample|contig拒绝及相关单元，说明该consumer存在防护；但catalog可能未启用且位于下游，不能替代consensus阶段验证，也不能说catalog当前会静默吞掉重复。现有共识9测试不覆盖这些重复/引用完整性边界。

## TA-043修复与验收

已实现并验证，仅改变identify_extra：根据最终producer后缀识别TSV/CSV（含gzip）或SCAPP FASTA/cycles；不再把合法sample ID内的工具词当作producer。未知后缀仍沿用警告/忽略行为。保留原生CSV、gzip、大小写及confident_cycs兼容；不再支持任意位置出现工具词但没有已知终结格式的文件名。这些不是生产模块声明的输出格式。未改分类阈值、投票/权重定义或实际分类器。

回归先于修复：新增样本名含全部工具词的CLI用例，在旧实现4个tool subcase中3个失败；原日志before.log保留。修复后全部11个共识测试方法通过（原9+新增2，新增覆盖4种producer及CSV/gzip/cycles），运行84.994s。

实际Nextflow原PLASMID_CONSENSUS wrapper使用锁定真实pUTI89序列、人工Platon positive-only标签和空geNomad，普通S与合法S.plasme.X两任务均成功、supporting_tools均platon、调用均plasmid，最终序列与原始序列逐碱基一致。标签是接口fixture而非真实分类结果；足以验收本文件身份adapter，不能认证Platon准确率或消除TA-005/042/044等其他问题。

改动与验证receipt：docs/tool-audit/patches/TA-043.diff，results/tool-audit/20261020-consensus-identity-fix/receipt.json；原数据/源码SHA和前后日志均保留。TA-043标fixed/verified，其他finding不因该补丁自动关闭。旧“生产未修改”记录为此前基线阶段；当前源码状态见evidence/post-fix-source-state.json。

## 2026-10-20 TA-044 共识输入完整性修复

assembly及SCAPP FASTA按现有规范化ID校验唯一性；generic/geNomad表按trim后的ID校验唯一性；同一工具不允许多份extra来源覆盖之前的calls。相同记录也拒绝，不隐式去重或聚合。诊断提供输入路径、重复ID、首个/再次出现的解析record序号，或先前工具来源路径；record序号不冒充多行FASTA/quoted TSV的物理行号。

修复前5方法触发6个失败子场景；修复后6方法7子场景全部通过（14.800秒），包含冲突行两种顺序及完全相同记录。原共识11/11通过（83.817秒）；原PLASMID_CONSENSUS wrapper五类重复任务全部明确失败且无发布产物，两个正常样本的调用及锁定pUTI89序列保持一致。证据：results/tool-audit/20261020-consensus-integrity-fix/receipt.json及positive/gates原trace、work和数据哈希。

TA-044关闭；增量补丁前态为HEAD+TA-043并已核对源码hash。未改变唯一输入的投票/权重/阈值，未认证实际分类器、生物学性能或完整检测E2E。TA-006等SCAPP重新映射、其他工具格式与权重边界仍未决；若某工具本来有多hit记录，应另建明确聚合适配，不能依赖最后一条覆盖。历史重复输入结果需从无歧义来源重生成。

## 2026-10-20 TA-042 共识权重配置修复

权重配置现在校验每项恰一个冒号、非空条目、已知且不重复的工具键及有限非负数字；weighted_vote实际参与工具总和必须有限且>0，检查提前到任何预测表/共识表/FASTA写出前。没有重新归一化权重；保留未提供工具权重1及空串全部默认1。非加权策略允许全零权重，但非法语法/数值仍拒绝。README已写明此边界。

修复前1方法4无效数值子场景失败；最终6方法20 CLI场景（15拒绝/5合法）通过43.946秒，覆盖多余/缺冒号、空条目、unknown/重复键、负/非有限数字、inactive正权重但active总和0、总和溢出、合法缩放/缺省、非加权零权重。原共识11/11通过82.449秒。原wrapper3类坏配置任务明确失败且无写出/发布任何结果；2正常样本调用及真实pUTI89字节保持，预测标签仍人工fixture。证据results/tool-audit/20261020-consensus-weight-fix/receipt.json，positive-final/gates与最终源码hash一致。

TA-042关闭，增量patch前态HEAD+TA-043+TA-044，README前态hash亦已核对。无阈值、投票或缺省科学规则变化；历史坏配置须更正并重跑。主入口工具列表校验TA-041、真实分类器及E2E仍未决；本检查在共识任务执行，不声称main启动前P0拒绝。

## 2026-10-21：PlasX分数不能按positive-only解析

TA-023消费者已修复：只接受固定官方contig/score列，有限[0,1]、严格>0.5。低分、等于阈值不再因“没有classification列”而成为阳性；17位分数可往返，所有负分记录仍在predictions/consensus中。原投票/权重不变；生产PlasX注释/模型输入TA-025仍未决。详情及原生33方法/原wrapper低高分证据见plasx-plasme.md与本批receipt。
