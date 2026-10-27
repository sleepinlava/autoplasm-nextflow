# MOB科学入口禁止隐式准备（候选，未接受）

承接无post-link软件安装候选。生产MOB_RECON/MOB_SUITE_ANNOT/MOB_TYPER现均显式接收并stage同一份mobsuite_preflight.py，在原科学入口前执行准备检查。**完整参考库/非病毒内容/隐式资源身份与缓存仍待完成；没有MOB科学阳性计算，本批不能关闭TA-091。**

## 执行边界

- helper严格核对固定发行包7个代码/配置文件，使用实际安装的mob_recon或mob_typer原parse_args及原5条DB路径选择AST语句；不执行原main的临时目录创建、BLAST或初始化。
- 缺少默认status或任一必需文件/有效ETE3 schema2时exit2，native main未调用。显式目录沿原程序约定文件选择，保留默认分支与自定义分支差异。
- 检查通过才调用原模块main，argv向量完整保留。只替换隐式MOB初始化器和ETE3更新器为拒绝函数，并在实际verify_init调用点重新检查status，防止检查后丢失资源又触发下载。没有exec到另一个Python进程而丢失这些约束。
- ETE3连接和版本健康检查使用只读SQLite URI；失效/丢失/旧schema不会创建空DB或升级。原NCBITaxa查询在明确合成元数据控制上得到同一lineage，写入被SQLite拒绝；这不是生物学真值或可用参考库证明。
- 执行结束/异常时恢复argv和模块函数，原返回/退出状态保留。原生科学代码/阈值/所选资源规则未删改。可选filter参数在执行路径继续交给原生main，完整filter读取/写入验证标为deferred；不以未完成审计为由静默取消该原生方法。独立只读预检仍明确拒绝尚未实现的filter准备认证。

两模块输入新增显式helper，调用点、meta、测试均迁移；Recon使用deep缓存保护FASTA/helper输入，与Typer一致。这**不是默认环境DB的内容缓存身份**，仍需查缓存前的probe/runtime上下文与模型/元数据完整读取集合。缓存命中不会重跑当前准备检查，不据此宣称资源变异已解决。内部preflight JSON不是已完成的科学结果或全量来源报告。

## 证据分别计数

最终native-v2用完整原始540bp细菌软件fixture，3个真实生产别名×默认/显式未准备库：6个实际FAILED/exit2，日志为准备拒绝，无科学输出目录或成功preflight JSON；默认库/显式空目录前后不变。另3个独立stub COMPLETED，只验证接口和版本，不运行科学程序。

8个原准备单元+8个新执行边界单元，共16唯一方法，不累计旧版重复运行或循环内两个工具为更多样本。新边界方法中的main是明确observer，测试资源丢失/初始化器/ETE3升级拒绝、只读schema、argv/返回值及状态恢复。metadata/placeholder阳性不是MOB真实参考DB。

实际nf-test0.9.5仅选两个stub标签，以完整原始约5.3MB细菌FASTA运行，精确源码字节/权限副本检查通过。原病毒输入已移除；完整细菌native案例另有prepared标签，保留全DNA/数值校验目标，但没有运行，仍需完整合规DB。旧snapshot保留历史、不自动重录，不把stub当原科学案例通过。

178任务主流程为明确外部工具mock，新准备observer标签不代表真实DB通过。发布控制12trace（8COMPLETED输出协议observer+4CACHED）通过；保存task-evidence后删除两个私有work，最终逐样本/阶段副本hash仍可读。额外只针对MOB_db执行4轮52trace（14COMPLETED stubs/38CACHED），等长同mtime目录变异只重跑MOB，还原精确复用；只证明显式目录旧候选契约，没有证明环境默认库缓存。

## 已保留的尝试

native-v1在只读ETE连接扩展/Recon deep指令之前通过，已存原loaded helper；不用它冒充当前源码或重复累计。首次nf-test缺helper是每case工作目录下new File相对路径错误，在任务提交前拒绝；改为projectDir.resolve后原断言通过，未削弱检查。

## 当前边界

42资源对=38候选+4pending（Dorado、Medaka、Recon默认库、Typer默认库）。接下来必须完成实际完整参考内容与“不使用病毒元素”约束核对、完整科学阳性/阴性、科学错误传播、实际BLAST/alias/filter/Mash/ETE3读写身份、查缓存前probe/上下文及OCI/provider。现阶段没有下载或使用病毒输入、模型或未审核DB，正式718清单和99接受/2退役/8未决不变。
