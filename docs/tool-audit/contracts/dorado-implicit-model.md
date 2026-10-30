Takeaway: Dorado资源对保持pending的合约级审查——模块存在三重隐式性（浮动模型名自动下载、无容器钉住、PATH软件无版本断言），未执行任何下载或basecalling。

## 范围与方法

仅合约/词法审查：`modules/basecalling/dorado.nf`、调用端（`subworkflows/ont.nf:47`、`subworkflows/hybrid.nf:87`）、`envs/basecalling.yml`。本机无dorado安装、无POD5执行，不据此宣称任何运行证据。上游行为依据[Dorado官方模型选择文档](https://software-docs.nanoporetech.com/dorado/latest/models/selection/)与[下载文档](https://dorado-docs.readthedocs.io/en/0.8.2/models/downloader/)（2026-10-27访问），非本地实测。

## 确认的隐式行为

1. **浮动模型名自动下载**：模块默认`params.dorado_model ?: 'hac'`；`dorado basecaller hac <pod5>`在模型缺席时自动下载**最新**匹配数据的hac模型。模型版本（如`dna_r10.4.1_e8.2_400bps_hac@v5.2.0`）随上游发布漂移，管道不钉住。
2. **模型搜索路径隐式**：优先级为`--models-directory`参数 > `DORADO_MODELS_DIRECTORY`环境变量 > 当前工作目录。模块三者都不用，模型落到任务CWD，缓存键不含模型内容身份。
3. **无容器/环境钉住**：模块明确不带`container`指令（注释：docker/singularity profile下仅当部署方提供`ontresearch/dorado:latest`才用——`:latest`浮动标签）；`envs/basecalling.yml`只装samtools，要求手动安装dorado到PATH。无`dorado --version`断言、无versions输出。
4. **无缓存控制**：进程无`cache`指令声明（用默认），输出身份不含模型/软件版本哈希。

## 与其他已审工具的差距

Medaka/MOB等已获得：固定来源+钉住包/镜像digest、显式资源path输入与deep缓存身份、执行前probe核对、版本topic输出。Dorado全部缺失。

## 建议的门禁设计（未实施）

- 显式`--dorado_model`必须为完整版本化模型名（拒绝'hac'类别名），或提供已验证本地模型目录path输入；
- 模型目录作显式path输入入缓存键，probe核对模型文件身份后再basecall；
- 钉住具体OCI镜像digest（替代:latest）或固定本地dorado二进制SHA256+版本断言；
- 补versions topic输出与网络拒绝控制（basecalling阶段禁止任何下载）。

## 当前状态

TA-091资源对清单中Dorado保持pending；本审查不构成接受。无病毒元素、无下载、无科学运行。
