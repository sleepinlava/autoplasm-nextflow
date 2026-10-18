# test profile 对齐后的验证（2026-10-17）

验证针对当前工作区（包含原有未提交生产代码改动），不代表纯 Git 提交。
历史 P1/P2 结果仍见 [RESULTS.md](RESULTS.md)，本次没有重跑 P1 或更新任何快照。

- `nextflow config -profile test -flat`：成功解析；默认样本表、geNomad 路径、
  禁用的数据库工具和资源上限符合预期。
- 固定上游数据：9/9 文件的长度及 Git blob SHA1 与 `datasets.lock.json` 一致。
- `validation.nf.test`：11/11 通过；均明确检查目标诊断和无成功分析任务。
  原始 JUnit：`results/nf-test/p0-profile-update.xml`。
- `test_prepare_test_data.py`：4/4 通过。HTTP 传输由内存数据隔离，仅测试适配器；
  不代表运行了生信工具，也不构成生物学真值。
- 现有 Python/R 脚本回归测试连同新增数据适配器测试：47/47 通过（136 秒）。
  JUnit：`results/nf-test/python-profile-update.xml`；其中包含上面的 4 项适配器测试，
  不重复累计。
- 真实 assembly P2：1 项失败，geNomad 命令退出 127，`genomad: command not found`。
  已确认共用配置成功加载，命令使用 2 线程以及
  `--cleanup --disable-nn-classification`。输出契约断言尚未执行。
  原始 JUnit：`results/nf-test/p2-profile-update.xml`，同名 `.log` 包含任务位置。

缺失真实工具不能通过 stub、跳过或放宽断言转换为成功。准备各平台依赖后仍需
执行 README 中完整 P1/P2 命令；本次结果不证明五个平台已端到端通过。
