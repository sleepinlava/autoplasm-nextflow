# 可选宿主预测接口

2026-10-20；基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

TA-046：HOTSPOT本地调用preprocessing.py和hotspot.py参数名，与本次官方GitHub源读取的parser对应；输出host_lineage.tsv表头为Contig/Phylum/Class/Order/Family/Genus/Species，AWK列位置一致。但upstream采用Python csv.writer(delimiter="\t")，默认行结束符CRLF；本地awk FS=TAB而未去除CR，最后一个Species为'-\r'时，不等于'-'且非空。倒序选host会将其输出为host_id，忽略有效Genus；lineage也追加了缺失placeholder。

原module提取AWK（只展开Nextflow转义和sample ID），同一输入p1/P/C/O/F/KnownGenus/-，默认csv.writer行尾输出host bytes=2d0d；LF control输出KnownGenus。完整脚本、module SHA256、原始bytes及退出码保留 results/tool-audit/20261020-hotspot-adapter/run.json。不是模型推理或生物学准确率验证。

来源：[Orin-beep/HOTSPOT hotspot.py](https://github.com/Orin-beep/HOTSPOT/blob/main/hotspot.py)，本次GitHub connector读得blob6dbf02672f9f641f68282f502b7af586c0994546；preprocessing.py bloba6909709a3d65a5f8ce96d0f6cb5d044a50a519c。部署依赖用户hotspot_home，当前未锁commit/model，不能声称所有用户checkout都有同一输出行为。无论模型版本，CRLF兼容是当前转换器可独立复现的缺口。保留Python版本、newline dialect和writer输出格式作为契约。

PlasmidHostFinder：当前声明conda>=0.1和容器0.1.0无法仅凭字符串证明可重建。历史w2-nodes-results.md已有模型/安装阻塞，但不能把历史报告当本次下载结果。本次bioconda recipe路径404、Bitbucket页面读取Internal Error，仅为这些访问的失败，不证明全网不存在包/仓库。原论文[Data availability](https://journals.asm.org/doi/10.1128/msystems.01180-21)指向deaytan/plasmid-host-prediction的Python2.7脚本；未取得本次固定bb9316d1源码和RF权重，不确认当前wrapper CLI/输出格式。任意find首个TSV仍需明确结果身份，保持evidence_missing，不根据论文网页推测CLI。未下载3.6GB模型。
