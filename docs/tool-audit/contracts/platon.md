# Platon 契约核对

2026-10-24当前契约更新：完整1.7源码/数据库及真实包装器、缓存、错误传播、nf-test与锁定Conda已有有界验证。见 [platon-native.md](platon-native.md)。以下保留2026-10-20历史调查，不以当时缺环境状态替代当前证据。

2026-10-20；代码基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。

官方固定版本：[v1.7 platon/platon.py](https://github.com/oschwengers/platon/blob/v1.7/platon/platon.py)，blob c6b205e939d1aba88ca6f6deaee3deb5bba35a86。此前猜测 main.py/platon.py 路径 404 只是路径错误；读取固定 tag 的树后找到真实入口。参数定义在 [utils.py](https://github.com/oschwengers/platon/blob/v1.7/platon/utils.py)，blob fe5381245dbf75c59c0dbfef8678951d19548734；数据库和输入配置在 config.py，blob ebcacebe9942279deafc4df6f8ccce1fd0a63263。原始响应存 evidence/detection-upstream.json。

CLI threads/output/prefix/meta/db 与本地参数匹配；输出写入 prefix.tsv 和 prefix.plasmid.fasta，TSV 为阳性集合，不能将 RDS 当作概率。共识的 generic parser 用 ID 列并把无分类列的行当阳性，与此集合语义相符。源码始终打开输出 FASTA，因此 optional 声明比上游实际行为宽松。

TA-005：platon.py:80 用 SeqIO.parse(str(cfg.genome_path), 'fasta')，未解压。SPAdes/MEGAHIT 发出的 contigs.fa.gz 沿 ch_assembly 直接送入 PLATON；当前 P3 只测未压缩 pUTI89.fasta，未覆盖此生产接口。该结论为固定源码+调用链静态证据，当前无真实复验。

历史 w3-platon.xml 为 2026-10-17 单阳性测试通过，未含代码 SHA；不能覆盖压缩输入、阴性或多样本 join。Conda platon>=1.7 与镜像 1.7 不是同一精确锁；实际版本、镜像 digest、数据库 checksum 当前仍缺。

## 2026-10-20 TA-005 压缩FASTA输入适配

PLATON包装对.gz/.GZ先gzip -cd生成任务内plain FASTA，未压缩文件原样传入，不改变classifier参数/模型。使用锁定pUTI89真实序列（114230bp，来源commit618f1541382c4ad49eff566dadf13d5ccbd0ebb4，plain SHA256 f48980b3e15eb733333493755a432de7e2380b71abf8ac682d92e94353ad8431），由明确标注的ASCII输入observer记录内容与hash。基线原模块2方法均失败；补丁后2方法、4原Nextflow任务符合预期：plain/gzip/GZ三样本输入字节完全一致，损坏gzip任务exit1且observer未调用。原P3另增锁定上游gzip阳性场景，保留既有plain阳性；未运行nf-test。

证据：results/tool-audit/20261020-platon-input-fix/receipt.json及保留trace/work/输入输出。TA-005标ready，保持未决：本机native platon不在PATH且官方DB目录不存在，尚无实际分类器阳性/阴性plain/gzip一致性、版本/DB锁、容器或平台认证。真实序列来源不能把接口observer升级为真实Platon节点。
