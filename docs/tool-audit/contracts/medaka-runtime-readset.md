# Medaka 2.2.2 原生模型选择边界（候选，未正式接受）

本增量仅准备原生软件并观察模型解析；没有修改生产 MEDAKA 命令、执行比对/神经网络推理或证明缓存正确。TA-091 和 MEDAKA 资源对保持 pending。用户“不许使用病毒元素”约束持续适用，原病毒 fixture 不执行；控制 FASTQ 仅含单个 N，BAM 仅有头部，均不是生物样本或科学阳性。

## 固定来源与环境

上游 v2.2.2 固定提交 `293b33dbf168935aee4d5b2f3e1a92f4a54e409f`，仅下载 tag/tree 元数据和六份软件代码/配置。实际下载字节在 `results/tool-audit/20261026-medaka-runtime/primary/`，来源 URL/hash 见同目录上级 `source-downloads.json`。浏览器 raw tag 缓存曾给出不同长度脚本，不用其渲染内容实现或断言。

独立 CPU prefix 为 `results/tool-audit/runtime/medaka-2.2.2-cpu`。原生 Conda 包 `medaka=2.2.2=py312h3050eb1_0` SHA256 为 `8cca1d7aca2e6f2caef04fdec9e94a025467e347cd3671d7490464126e449d9b`；141 包锁、原始归档/安装元数据逐项核验见 `linux-64.lock`、`packages.json`、`native-install-verification.json`。安装显式跳过 link scripts；不代表原生产环境或 OCI 镜像已验证。Python 3.12.15、PyTorch 2.9.1 CPU；实际 `medaka --version` 为 2.2.2。

五份关键安装代码与不可变提交逐字节相同。`mini_align` 在原始 Conda 包中，但固定 tag tree 没有该脚本，因此只绑定归档/实际安装 SHA，不宣称其 tag 字节相同。软件包自带四份通用 DNA 模型，逐个记录实际路径、大小和 SHA；未另行下载模型或序列，没有推理这些权重。不能将软件安装/通用模型存在当作细菌样本正确性证据。

## 原生行为与控制范围

`tests/run_medaka_readset_native.py` 必须以该环境 Python 运行，先核对 `tests/medaka-readset.lock.json` 中六份源码/入口 SHA，再调用实际 `medaka.models` 和原 CLI。18 个 API 控制覆盖显式路径、basecaller alias、三种 FASTQ 元数据、前100条边界、混合/缺失/未知元数据、BAM RG.DS、细菌模型选择与不兼容、废弃/未知模型和未准备模型拒绝。

五个 Bash 控制执行安装脚本从头至 `echo "Checking program versions"` 之前的精确前段，保留原 getopts、默认值和回退分支；截断后只追加输出 MODEL 的 printf。私有 CLI shim 只拦截 requests.get，其他解析交原 CLI；记录请求后拒绝，不提供虚假模型文件。该范围不包含版本依赖检查、is_compatible、mini_align、inference、stitch。输出中的成功只表示前段完成。

- 已准备 sup5.2 元数据自动选择实际随包路径。
- 无元数据时保留原默认模型 ID。
- 显式 `-m` 优先于 `--bacteria`，保持原行为。
- 兼容细菌元数据选择 bacterial_methylation，但该模型未准备：记录并拒绝下载，原脚本 exit1。
- 旧 R9 元数据能识别模型，但未准备、下载被拒绝时，原脚本仍 exit0 并回退默认模型。这不是正常缺元数据回退，不能被后续 readiness 当作成功准备。

第二轮增加模型 stores 前后完整普通文件 SHA 清单相同断言，保留生成的非生物学控制和脚本前段/shim。第一轮为 superseded 观察，不计双倍用例。所有 HTTP 尝试被拒绝；不是声称不存在任何系统缓存写入。

## 尚待完成

需实现逐样本实际模型字节身份和执行前核对，区分模型推断失败与模型未准备，保持显式参数与 bacteria 科学语义，并接生产/cache:false 探测与查缓存前上下文。原默认 fallback 本身属于原程序行为，当前不擅自改变科学方法。还需完整、来源审查合规的细菌 ONT reads/assembly 真实阳性/阴性/错误传播、模型变异/损坏/还原缓存和框架/provider/OCI 验证；不能拿本轮 N 元数据或截断脚本替代。

141 包环境和四份模型仍供下一阶段使用，不能为清理空间删除。无新可确认废弃的大资源，本轮不虚构清理回收量；既有六批清理仍见清理台账。
