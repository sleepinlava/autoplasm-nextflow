# 当前审计进度

由 scripts/refresh_status.py 从台账生成；日期 2026-10-30。基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

- 生产 .nf 台账：119（当前=117，按用户要求退役=2）；investigating=117，matched=0。历史分母保留。
- 问题：111；S0=39，S1=6，S2=66，S3=0。TA 为生产契约，TT 为测试逻辑/覆盖问题。
- tests 来源台账：361（当前=357，退役=4）；包括 harness/config/文档，不是用例分母。
- 已验证局部修复=105，按用户要求退役=2，其余未决=4（S0=1，S1=0，S2=3）。退役不计修复通过；运行记录=461。

原 main 独立拒绝场景 75/75；当前 main 哈希对应=75。重放不增加场景分母；不证明完整输入契约或 nf-test 框架通过。

已纳入证据的来源哈希清单 718 项；当前工作区匹配=False。这不是全仓库来源或测试用例分母。

词法扫描：123 文件、274 导入符号、112 主入口可达文件、0 未解析 include、155 配置声明。不能代替动态连接与执行证据。

最近接受的修复批次：[20261030-ta097-acceptance](../../results/tool-audit/20261029-ta097-review/receipt.json)；完成日期 2026-10-30。

本批局部验证项：TA-097。

未决问题按严重度列出；ready仍是未决，未执行/范围不足不能算通过。

| ID | 级别 | 修复状态 | 范围 |
| --- | --- | --- | --- |
| TA-091 | S0 | in_progress | Directory reference/source cache identity across reachable scientific tools |
| TA-016 | S2 | in_progress | methods.md / report_data.json / rendered HTML |
| TA-031 | S2 | ready | gtdbtk input extension |
| TT-003 | S2 | ready | P4 nonempty statistics and filtered sample gating |

全量审计未完成，不给支持路径放行结论。M0动态配置/完整channel图/历史证据归属与默认真实基线、固定版本工具/DB/model契约、剩余缺陷修复、nf-test及真实阳性平台/科学基准仍须完成。

源代码与补丁链见 evidence/post-fix-source-state.json；原始来源是488个普通文件hash加1个目录symlink，共489个tracked对象，冻结表保持不变。SCAPP按用户要求退役；DAS多分箱器规则、统一参考重映射和TETRA方法决定保持。TETRA的55来源分组留出基准已执行：数值通过、预定科学阈值验收失败。按用户决定只保留组成分数，停用未校准宿主链接；TA-039仅关闭错误链接风险，不代表科学校准通过。详见 contracts/tetra-source-benchmark.md。

当前缺陷以 findings.tsv 为准；逐项范围见 acceptance.md、native-real-nodes.tsv 和各receipt。历史计数、尝试与被替代实现留在 journal.md/history/，不从旧摘要推导当前验收。
