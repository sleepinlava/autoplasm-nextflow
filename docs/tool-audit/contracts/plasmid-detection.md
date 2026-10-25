## 当前决定：SCAPP 退役（2026-10-21）

用户明确要求“删掉SCAPP节点”。已删除 detection/binning 两节点、环境、调用和对应4份测试来源；工具 registry 不再接受 SCAPP。旧选项、旧共识权重与 SCAPP FASTA 输入明确失败；共识表固定工具列为 genomad/plasme/plasx/platon。其余默认权重与投票算法不变。

TA-006/TA-035 标记 removed_by_user/retired，保留原严重度和历史证据，不计为 verified 修复。此前仅合入 SCAPP 重建序列的实验无法解决候选实体不同造成的投票偏差；实验已撤销并保存在 results/tool-audit/20261021-scapp-consensus-sequences，不能用于认证当前实现。无需继续该方法调整。

保留通用输入一致性校验：分类结果的全部ID必须属于输入assembly，空序列记录拒绝；真正的空FASTA/空结果仍允许。回归产物见 results/tool-audit/20261021-scapp-removal/receipt.json。全量检测子工作流/分类器DB及科学效果仍需原计划验证。

以下为退役前发现及其他未决契约的历史记录；其中“当前/修复需”指当时状态，不再代表SCAPP支持承诺。

# PLASMID_DETECTION 与共识接口

2026-10-20；代码基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

主链：assembly → geNomad summary → 与原始 assembly 按完整 meta join → 四个 optional remainder join → PLASMID_CONSENSUS → PLASMID_STRUCTURE。可选关闭时 Channel.empty；extras 剔除 null。连接按完整 meta 而非仅 id。当前各生产者保留同一个 meta，但重复键/缺失必需项没有显式断言；运行时乱序、空结果、额外键和重复键仍待 Nextflow 测试，不将词法审查当作运行证明。

TA-006：SCAPP 输出是重建图环，不是原始 assembly contig 的分类。固定版本 [SCAPP v0.1.4 scapp_utils.py:471](https://github.com/Shamir-Lab/SCAPP/blob/v0.1.4/scapp/scapp_utils.py#L471) 生成 RNODE 名；[recycle.py](https://github.com/Shamir-Lab/SCAPP/blob/v0.1.4/scapp/recycle.py) 将该名写入 FASTA，scapp.py 将筛选后的环写入 confident_cycs.fasta。本地直接解析这些 ID，并只从 assembly 按相等 ID 写出 FASTA，缺少映射/重建序列接入。

独立最小复现：results/tool-audit/20261020-detection/run.json 记录完整命令及共识脚本 SHA256。人工 fixture 以 NODE 为 assembly ID、RNODE 为 SCAPP ID，设置 genomad:0,scapp:1 以隔离该工具接口。当前退出 0、表中一条 plasmid、长度/GC 空、最终 FASTA 0 bytes，stdout 却为 1/1 called plasmid。此为接口失败证据，不是 SCAPP 真实运行或科学基准。默认启用 geNomad + SCAPP 时，SCAPP 未配置权重会取 1.0，该问题同样不能由默认 weighted_vote 保证规避。

修复需先定义生物学实体：图环序列单独并入目录，或通过路径/序列关系建立可验证映射；不得把 RNODE 字符串改成 NODE 伪造对应。应断言每个阳性都有对应最终序列。SCAPP 阴性/未支持平台的空 channel 与工具正常阴性也需区分。

PLASMe/PlasX 的镜像仅 python runtime 和未锁 Conda 另待完整契约审查；尚不计通过。
