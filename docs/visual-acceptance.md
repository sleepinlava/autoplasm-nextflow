# Nextflow 流程设计页 · Computer Use 验收

日期：2026-10-17（Asia/Shanghai）。对象：[流程网页](analysis-framework.html)。

页面使用原生 HTML + CSS + TypeScript，以本仓库的 Nextflow 设计为主线：五个平台入口、
00–12 与报告共 14 个阶段、共享子工作流、可选分支、启动命令和输出约定。
完整科学事实审查另见 [事实可靠性审查](fact-reliability-audit.md)。

## 实际环境与方法

- 使用 Computer Use 的 Codex In-app Browser，经明确授权的 `127.0.0.1` 临时 HTTP 服务打开。
  预览仅提供明确列出的文档、CSS、编译 JS 与相关源码，没有目录浏览或外网监听。
- 使用实际截图、可访问性树与 DOM 可见内容检查页面；通过真实点击、选择、勾选及滑块键盘操作验证交互。
- 桌面最终使用默认 1280 × 720 视口，内容宽度与 clientWidth 均为 1265；手机使用
  390 × 844 视口覆盖，内容宽度与 clientWidth 均为 375，没有页面横向溢出。
  该模拟不等于真实手机硬件验收。最终浏览器 console 未记录脚本 error。
- 页面加载本地 `analysis-framework.css` 与 `analysis-framework.js`；TypeScript 源码为
  `analysis-framework.ts`，通过 `tsc -p docs/tsconfig.json` 编译，开启 strict 与 noEmitOnError。

## 已完成检查

| 检查 | 实际操作与观察 | 结果 |
|---|---|---|
| 五平台路由 | 依次选择 ONT、PacBio HiFi、Hybrid、Assembly、Illumina，核对输入、QC、组装、比对与命令 | 通过 |
| 平台限制 | Assembly 禁用 MAG、linking、network 开关，命令省略相应参数及 MetaPhlAn 数据库 | 通过 |
| 14 个阶段详情 | 下拉选择 00–12 与 R，检查标题、阶段计数、参数、产物与源码说明 | 通过 |
| 桌面流程图 | 实际点击 08 注释节点，详情切换到相应内容 | 通过 |
| 手机阶段导航 | 手机显示双列阶段按钮，隐藏桌面 DAG；点击 10 定量可打开详情 | 通过 |
| 模块开关 | 勾选 binning、MAG、linking、network，示例命令新增对应参数及 MAG 数据库 | 通过 |
| 环境选择 | 选择 Docker，生成命令末尾变为 `-profile docker` | 通过 |
| 网络门槛 | 开启网络后，6 样本显示低于门槛；滑块到 40 后显示达到 ≥20 门槛 | 通过 |
| 共识规则 | 加载 geNomad 阳性、其余阴性的分歧示例；加权得分 0.60；严格多数 / 交集不通过，加权 / geNomad 单工具通过 | 通过 |
| Markdown 下载 | 点击导出；浏览器返回已下载路径，读取实际文件确认含平台、各阶段和命令 | 通过 |
| 复制按钮 | 点击后收到复制完成回执；浏览器会话剪贴板读取为空 | 仅确认按钮回执，未将系统剪贴板内容计为通过 |
| 版式 | 查看桌面首屏、流程、参数区，手机首屏、阶段列表、参数区；检查页面宽度 | 已检查并修正下述问题 |

## 验收中修正的问题

1. 页面主线改为实际 Nextflow 工作流；研究设计沙盘和大篇幅审查不再占据主体。
2. 手机主标题调整字号，章节标题按完整短语换行，避免留下单字 / 双字尾行。
3. 手机参数卡片头部允许换行，避免标题被旁边标签挤压；增加执行环境与样本滑块的明确可访问名称。
4. Assembly 平台的条带说明、宿主模型标签、覆盖度显示与定量产物说明按实际跳过分支更新。
5. 流程图最左侧节点移入画布，避免边框裁切。
6. 暂停动画同时关闭根页面平滑滚动，避免跳转后尚在滚动时检查到中间画面。

## 截图

- [桌面首屏](visual-acceptance/desktop-hero.jpg)
- [桌面流程总览](visual-acceptance/desktop-flow.jpg)
- [手机首屏](visual-acceptance/mobile-hero.jpg)
- [手机流程导航](visual-acceptance/mobile-flow.jpg)
- [手机参数区](visual-acceptance/mobile-parameters.jpg)

## 验收边界

本轮验证的是页面内容呈现与交互。没有执行 Nextflow 作业、安装生信工具、下载数据库或验收生物学准确性。
打印入口保留，但未将浏览器打印对话框或生成 PDF 计为通过。没有宣称跨浏览器和真实移动设备全覆盖。
生产算法未在本轮修改，因此未重复前轮已通过的 43 项脚本回归。
