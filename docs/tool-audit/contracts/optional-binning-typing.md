> 2026-10-21 当前覆盖范围：SCAPP检测与binning已按用户明确要求退役，旧选项/权重/FASTA输入被拒绝；TA-006/035不再开放修复但不计verified。以下SCAPP相关段落为历史取证，不能视为当前支持或待实施方案。当前验证见 ../retirements.tsv 和 ../acceptance.md。

# 可选 binning/typing 包装器审查

2026-10-20；本地基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。以下固定官方源码快照用于比对接口；实际 Conda 安装均未解析/锁定，不能冒充部署版本。

PlasMAAG：官方 RasmussenLab/PlasMAAG，固定 commit a6b39ac6e8e38ccc8419fc7b4a3f304b0f511803。源码 [PlasMAAG/__main__.py](https://github.com/RasmussenLab/PlasMAAG/blob/a6b39ac6e8e38ccc8419fc7b4a3f304b0f511803/PlasMAAG/__main__.py) 定义 reads_and_contigs 清单，[click_file_types.py](https://github.com/RasmussenLab/PlasMAAG/blob/a6b39ac6e8e38ccc8419fc7b4a3f304b0f511803/PlasMAAG/click_file_types.py) 校验列和文件路径。生产却传 CONTIG_COVERAGE 的 CoverM 数值表。不是列重命名即可解决：需要原始 reads/assembly 路径与多样本分析单元。CLI 大小写/包安装入口还需环境验证。TA-018，未真实运行。

COPLA：官方 santirdnd/COPLA，固定 commit 6b89285ef16d721d93d3c84f3645e76455ba8621。[bin/copla.py](https://github.com/santirdnd/COPLA/blob/6b89285ef16d721d93d3c84f3645e76455ba8621/bin/copla.py) 自报 1.0，sequence/refgraph/reflist/outdir 是位置参数；包装给未定义长选项。只提取固定源码 argparse 声明进行无分析依赖复现，本地 argv 退出 2，对照位置参数成功，见 results/tool-audit/20261020-optional/copla-parser.json。工具本身未运行，不能计 P3。输出应明确 PTU prediction，不能拿任意第一个 TSV。TA-019。

COPLA 生物学实体另为 TA-020：该源码将 multifasta 作为单一 query，计算合计长度并标记 unordered_replicon；完整样本中的多个独立质粒不应被这样分类。即便修正 CLI，整样本调用仍可能静默产生错误 PTU。应按明确的独立质粒实体调用；尚无重建归属时不能伪造归并。

GPLAS2：[官方 GitLab README](https://gitlab.com/mmb-umcu/gplas2/-/raw/master/README.md) 当前说明 GFA + 节点分类表，程序入口 gplas，结果 *.tab；包装的 FASTG+FASTA、gplas2 入口和 *.tsv 搜索均可疑。尚未取得固定部署版本和源码 commit，故 TA-021 保持 evidence_missing。此前 support-matrix 的 metaspades 条件仅表示存在 graph channel，不代表格式正确；已补充此限制。

ISEScan 的 seqfile/output/nthread 命令已读取，尚未对应固定 1.7.3 CLI。SCAPP_BIN 与 detection 同样硬编码 k=77，但没有图来源 provenance；须与 TA-004 同类复验。Dorado/native、hifiasm-meta、MUMmer、clinker、PlasmidHostFinder、HOTSPOT 已做包装器阅读，官方版本/环境/真实输出契约仍待闭环，当前均不得标为 matched。

原始固定源码在 evidence/optional-wrappers-upstream.json；COPLA/PlasMAAG 安装版本未知，Conda 范围版本无法作为精确复现标识。
