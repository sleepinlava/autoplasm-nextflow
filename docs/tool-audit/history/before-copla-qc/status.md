# 当前审计进度

由 scripts/refresh_status.py 从台账生成；日期 2026-10-23。基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

- 生产 .nf 台账：110（当前=108，按用户要求退役=2）；investigating=108，matched=0。历史分母保留。
- 问题：87；S0=27，S1=5，S2=55，S3=0。TA 为生产契约，TT 为测试逻辑/覆盖问题。
- tests 来源台账：162（当前=158，退役=4）；包括 harness/config，不是用例分母。
- 已验证局部修复=62，按用户要求退役=2，其余未决=23（S0=4，S1=0，S2=19）。退役不计修复通过；运行记录=195。

原 main 独立拒绝场景 61/61；当前 main 哈希对应=61。重放不增加场景分母；不证明完整输入契约或 nf-test 框架通过。

已纳入证据的来源哈希清单 204 项；当前工作区匹配=False。这不是全仓库来源或测试用例分母。

词法扫描：108 文件、211 导入符号、101 主入口可达文件、0 未解析 include、146 配置声明。不能代替动态连接与执行证据。

最近接受的修复批次：[20261023-plasme-native](../../results/tool-audit/20261023-plasme-native/receipt.json)；完成日期 2026-10-23。

本批局部验证项：TA-024、TA-053、TA-069、TA-070、TA-071、TA-072、TA-073。

原生 trace 8 条：COMPLETED=5、CACHED=0、FAILED=3。包含旧错误对照与预期失败，不能当作科学样本数或全部正例。

独立计数的单元方法=20；重叠运行按test ID去重，不代表全部测试或科学效果认证。

未决问题按严重度列出；ready仍是未决，未执行/范围不足不能算通过。

| ID | 级别 | 修复状态 | 范围 |
| --- | --- | --- | --- |
| TA-020 | S0 | in_progress | copla sample multifasta biological entity |
| TA-039 | S0 | ready | TETRA numerical method / claimed pyani parity |
| TA-074 | S0 | in_progress | COPLA child failure masked as absent annotation/reference relation |
| TA-075 | S0 | in_progress | MultiQC source sample/stage/mate identity |
| TA-005 | S2 | ready | illumina / platon; hybridspades / platon |
| TA-007 | S2 | planned | graph-dependent optional tools across platforms |
| TA-016 | S2 | ready | methods.md / report_data.json / rendered HTML |
| TA-018 | S2 | planned | plasmaag input contract |
| TA-019 | S2 | in_progress | copla CLI/output |
| TA-021 | S2 | planned | gplas2 graph and prediction types |
| TA-025 | S2 | planned | PlasX gene-call and annotation interface |
| TA-026 | S2 | planned | conjscan/macsyfinder nucleotide input |
| TA-027 | S2 | planned | eggnog_mapper sequence type |
| TA-029 | S2 | planned | mob_suite/mob_recon final publication |
| TA-031 | S2 | planned | gtdbtk input extension |
| TA-046 | S2 | planned | HOTSPOT CRLF lineage adapter |
| TA-049 | S2 | planned | SemiBin legitimate no-bin output contract |
| TT-001 | S2 | planned | mock E2E sample attribution oracle |
| TT-002 | S2 | planned | P3 assertion completeness |
| TT-003 | S2 | ready | P4 nonempty statistics and filtered sample gating |
| TT-005 | S2 | planned | vendored P1 prerequisite readiness |
| TT-009 | S2 | in_progress | native MultiQC test version alignment |
| TT-012 | S2 | in_progress | QC oracle report-prefixed data discovery and per-source counts |

全量审计未完成，不给支持路径放行结论。M0动态配置/完整channel图/历史证据归属与默认真实基线、固定版本工具/DB/model契约、剩余缺陷修复、nf-test及真实阳性平台/科学基准仍须完成。

源代码与补丁链见 evidence/post-fix-source-state.json；原始来源是488个普通文件hash加1个目录symlink，共489个tracked对象，冻结表保持不变。SCAPP按用户要求退役；DAS多分箱器规则、统一参考重映射和TETRA方法决定保持。TETRA真实宿主阈值仍未校准。

当前缺陷以 findings.tsv 为准；逐项范围见 acceptance.md、native-real-nodes.tsv 和各receipt。历史计数、尝试与被替代实现留在 journal.md/history/，不从旧摘要推导当前验收。
