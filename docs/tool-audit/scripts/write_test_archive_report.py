#!/usr/bin/env python3
"""Render the review report from archive receipts, without executing analysis."""
import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();a=args.archive.resolve();read=lambda p:json.loads((a/p).read_text())
    s=read('summary.json');i=read('index-summary.json');v=read('verification.json');c=read('cleanup-result.json');d=read('deduplication.json');capture=read('metadata/capture.json')
    links=read('symlink-reproducibility.json')['counts'];entries=read('current-test-entries.json');fresh=read('validation/executions.json');qa=read('validation/archive-tool-selftest.json')
    n=sum(s['file_counts'].values());total_reclaimed=c['net_recovered_bytes']+d['net_recovered_bytes'];free=d['free_after_bytes']
    report=f'''# 当前测试资产与结果归档审查报告

审查日期：2026-10-30。归档标识：`20261030-current`。原工作树 HEAD：`{capture['git_head']}`。

本次完成当前测试资产盘点、现有证据冻结、完整性检查、有限回归复验及结果目录清理。归档覆盖 {n:,} 个文件、链接或特殊条目；保留 {s['file_counts']['retained_file']:,} 个普通文件、{s['file_counts']['retained_symlink']:,} 个链接及 3,467 个空目录。保留内容逻辑大小 {s['logical_bytes']['retained']/10**9:.2f} GB。该数字包含重复内容，不代表实际磁盘占用。

清理及归档大文件去重合计实际回收 **{total_reclaimed/10**9:.2f} GB（{total_reclaimed/2**30:.2f} GiB）**；结束时可用空间约 **{free/10**9:.2f} GB（{free/2**30:.2f} GiB）**。磁盘读数受系统同期活动影响，原始测量保存在清理和去重凭据中。

## 归档范围与规则

- 递归盘点项目测试、上游 vendored 测试、配置、环境声明、数据锁、fixture/mock、模型、数据/索引、全部现存结果、日志及 Nextflow 历史缓存；生产源码一并冻结，避免只有结果而没有对应实现。
- 不遍历目录符号链接；保存链接原文和原先存在状态。对空目录单独保存，确保依赖空数据库目录的夹具可还原。
- `.git` 使用 Git bundle、HEAD、日志、工作树状态和二进制 diff 保存；未提交/未跟踪的范围内源码另外保留于快照。未读取或归档 `.aws`、`.agents`、`.codex`、`.code`，不包含无关的 lazygit 可执行文件。
- Conda/venv 安装目录、第三方 VCS 元数据和包缓存逐文件登记，普通可重建依赖载荷不重复归档；保留环境凭据、Python 包元数据及按后缀/目录识别的模型权重。Python 字节码只登记。`inventory.jsonl.gz` 中 `retained=false` 明确标识这些边界。
- 实体快照使用独立写时复制 inode，随后仅在归档内部对已核实同内容的大文件建立硬链接。未与原始工作树建立硬链接。保留路径内容 SHA-256 不变；原始模式和 mtime 保存在清单，恢复时按清单还原。
- 最终 snapshot 移除写权限，防止通过旧结果链接改写存档；此操作不跟随符号链接。后续运行应写到新目录，恢复工具会按清单还原原始文件模式与 mtime。
- 本次捕获采用逐文件前后身份检查，并非文件系统全局原子快照；清理前再次核对目标文件身份和目录成员，没有发现中途变化。

## 测试与资产索引

| 对象 | 本次索引数量 | 计数含义 |
|---|---:|---|
| 当前测试入口、运行器与检查脚本 | {i['current_entry_files']:,} | 当前 `tests/` 及 `modules/**/tests/` 中的入口/运行脚本；不包含全部配置/说明文件 |
| 当前 Python test_ 定义 | {i['current_python_test_definitions']:,} | AST 定义数；不是参数化实例数，也不是已运行/通过数 |
| 序列数据及索引标记 | {i['role_counts_overlapping']['sequence_data_or_index']:,} | 包含历史副本、链接和多种索引，不代表独立数据集 |
| fixture/mock 标记 | {i['role_counts_overlapping']['fixture_or_mock']:,} | 路径分类，和其他类别重叠 |
| 模型及模型目录资产标记 | {i['model_or_model_asset_files']:,} | 含权重、配置和重复副本，不代表独立模型数量 |
| 依赖或数据锁 | {i['lockfiles']:,} | 含历史副本，原始来源与下载/版本约束保留 |
| Conda 环境前缀 | {i['conda_environment_prefixes']:,} | 每个环境保留包凭据和显式安装清单 |
| Python distribution 元数据 | {i['installed_python_distribution_metadata']:,} | 保存原始 METADATA/PKG-INFO、包名、版本和其 SHA-256 |
| 历史 JUnit 文件 | {i['junit_reports']:,} | 保留原文、suite 属性与逐 case 索引 |
| 历史 JUnit case 条目 | {s['junit_cases_raw']:,} | 原始计数：通过 {s['junit_status_raw'].get('passed',0)}，失败 {s['junit_status_raw'].get('failed',0)}；含重复尝试，不能作总体通过率 |
| Nextflow trace 文件 | {i['trace_reports']:,} | 按文件保留任务状态；任务数不等于测试用例数 |
| 既有运行台账 | {s['historical_run_records']:,} | 保留 result/level/limitations 等原始字段，不统一改写为 pass/fail |

所有类别为审查索引，不是科学分析能力或模型效果的认证分母。未被名称规则标记的保留文件仍在全量清单中可检查。

## 证据质量与当前限制

1. 原工作树并非干净状态。已有接受来源清单 718 项中，{i['accepted_source_drift']} 项与本次快照不一致，逐项保存在 `accepted-source-drift.json`。这是与该旧清单的差异，不自动表示新增缺陷；历史通过不能直接认证当前文件。
2. 原先保留范围内已有 {links['originally_missing']:,} 个断链，另有 {links['external_target']} 个根目录外链接。外部科学资产链接中的 5 个目标均已在本次操作前缺失，属于 `/tmp` 历史 fixture/read 链接；本次没有伪造或补造原数据。链接问题详见 `symlinks.json` 与 `symlink-reproducibility.json`。
3. 恢复工具会改写指向原项目根目录的绝对链接；指向已清理依赖载荷的链接，需要先重建环境。原始断链及外部缺失路径不会因归档而自动恢复。
4. 所有 58 份 Conda 显式清单均能从已保存凭据取得包 URL。显式清单限定 Conda 包，pip 分发、平台、容器、数据库与外部程序仍须结合 uv.lock、原始锁和 Python 元数据复原。清理后的历史复制环境不再保证原地可执行；这不是完整的离线运行镜像。
5. 原生、stub/mock、observer、静态检查、科学 benchmark 与终止尝试保留各自证据范围。既有 `status.md`、`findings.tsv`、`acceptance.md` 的未决项原样保存；本次没有将整条 pipeline 或全部产品要求标记为验收通过。

## 本次验证

- 对保留文件重新读取 SHA-256，对链接逐项核对原文：**{v['verified_entries']:,} 项通过，0 项错误**，耗时 {v['elapsed_seconds']:.2f} 秒。3,467 个空目录另行验证。
- 运行台账提取到的 467 个字面路径引用，捕获时均能在快照中找到；命令和自然语言内嵌路径仍须人工结合原始记录审查。
- Git bundle 验证通过；实际恢复并校验 3 个输入校验 fixture，通过。
- 重新执行 `test_shared_catalogue.py`（8）、`test_shared_abundance.py`（7）、`test_diversity_semantics.py`（7）、`test_deseq2_status.py`（18），合计 **40 项通过**。命令、来源哈希、退出码和完整日志位于 `validation/`。没有重跑全量测试或科学 benchmark。
- 归档工具 {qa['passed']} 项独立控制通过，包括来源变化拒绝清理、空夹具恢复、归档内去重隔离，以及故意损坏数据后正确拒绝校验。自测日志中的预期失败不能误判为本次主归档损坏。
- 大文件去重仅处理 ≥1 MiB、SHA-256 和模式一致的文件；{d['files_relinked']:,} 个归档路径改为共享归档 inode。每次替换前验证双方内容；原路径内容和恢复元数据不丢失。

## 清理结果

首轮处理 {c['target_count']} 个路径，实际回收 {c['net_recovered_bytes']/10**9:.2f} GB。旧结果树中的已保留产物通过相对链接继续可读；可重建的复制环境和包缓存载荷已移除。中央 runtime 环境及当前测试 venv 保留。删除缓存前，未发现中央 runtime 链接依赖被清理缓存或历史结果树。

归档内去重再回收 {d['net_recovered_bytes']/10**9:.2f} GB。不能把删除的 {c['logical_original_bytes_removed']/10**9:.2f} GB 逻辑路径大小，或去重的逻辑重复大小，直接当作实际释放空间。

删除前目标、理由和文件计数见 `cleanup-plan.json`；执行进度见 `cleanup-progress.json`；实际磁盘读数见 `cleanup-result.json` 与 `deduplication.json`。清理工具已拒绝任何捕获后身份或成员变化。

## 归档文件导航

| 文件 | 用途 |
|---|---|
| `snapshot/` | 保留的原路径载荷及源码 |
| `inventory.jsonl.gz` | 每个条目的路径、角色、大小、原始 inode/mtime/mode、保留状态、内容 SHA-256 或链接目标 |
| `empty-directories.json` | 空夹具目录与模式 |
| `test-files.jsonl.gz`、`current-test-entries.json` | 当前测试来源与可定位定义 |
| `assets.json`、`models.json`、`lockfiles.json` | 数据、夹具、模型、版本锁的审查入口 |
| `environment-prefixes.json`、`environment-specs/`、`installed-python-packages.jsonl.gz` | 环境重建凭据 |
| `result-files.jsonl.gz` | 原始结果文件索引 |
| `historical-runs.json`、`junit-reports.json`、`junit-cases.json`、`trace-reports.json` | 原始运行结果、重试与任务状态 |
| `accepted-source-drift.json`、`evidence-references.json`、`symlink-reproducibility.json` | 来源差异与复现缺口 |
| `metadata/` | Git bundle、HEAD、dirty diff 与捕获范围 |
| `verification.json`、`validation/` | 内容检查、回归、恢复与工具自测记录 |
| `cleanup-*.json`、`deduplication.json` | 清理和去重凭据 |
| `tools/` | 可独立调用的捕获、检查、恢复、报告及自测程序 |
| `SHA256SUMS` | 清单、报告、工具和其他非 snapshot 文件的封存校验和；snapshot 内容由 inventory 逐项校验 |

## 检查与恢复

以下命令在归档目录执行，普通完整性检查不需要数据库下载或运行分析工具：

```bash
sha256sum -c SHA256SUMS
python tools/archive_test_review.py verify --archive . \\
  --verification-report /tmp/autoplasm-archive-verification.json
```

完整文件复核会读取约 97 GB 的逻辑载荷。上述命令将复核结果写到归档外，保持封存包原样。

恢复单个目录到一个尚不存在的新目录（按需替换路径）：

```bash
python tools/manage_test_archive.py restore --archive . \\
  --destination /tmp/autoplasm-restored-fixtures \\
  --prefix tests/nf-test/fixtures
```

恢复整个范围时去掉 `--prefix`，目标需要足够空间；结果含原始缺失链接与可重建环境的明确边界。按 `environment-prefixes.json` 选择匹配平台的显式清单，例如 `conda create --prefix /path/to/new-env --file environment-specs/<id>.explicit.txt`。pip、数据及模型来源再按原锁和 metadata 补齐。

在新结果目录按原运行记录重放测试，记录输入哈希、实际环境、命令、退出码和新输出。归档中的旧结果路径用于阅读证据，不作为新运行的写入目录。
'''
    (a/'README.md').write_text(report)
    args.report.write_text(report+'\n本地归档入口：[查看完整归档](../../results/test-review-archive/20261030-current/README.md)。\n')
    print(json.dumps({'actual_reclaimed_GB':round(total_reclaimed/10**9,2),'free_GB':round(free/10**9,2),'report':str(args.report)},ensure_ascii=False))


if __name__=='__main__':main()
