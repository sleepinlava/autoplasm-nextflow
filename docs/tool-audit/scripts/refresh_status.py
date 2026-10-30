#!/usr/bin/env python3
"""Render current ledger counts and accepted evidence, keeping history in journal."""
from pathlib import Path
from collections import Counter
import csv
import json
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/tool-audit'


def rows(name):
    with (OUT / name).open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def latest_receipt(runs):
    boundary = (ROOT / 'results/tool-audit').resolve()
    for run in reversed(runs):
        path = (ROOT / run.get('artifact', '')).resolve()
        if not path.is_relative_to(boundary):
            continue
        candidates = [path] if path.name == 'receipt.json' else []
        candidates += [p / 'receipt.json' for p in path.parents if p.is_relative_to(boundary)]
        for candidate in candidates:
            if candidate.is_file():
                data = json.loads(candidate.read_text())
                if data.get('pass') and ('source' in data or 'source_state' in data):
                    return candidate, data
    return None, None


def main():
    inventory, findings, tests = rows('inventory.tsv'), rows('findings.tsv'), rows('tests-inventory.tsv')
    edges, reachability, selectors = rows('include-edges.tsv'), rows('reachability.tsv'), rows('config-selectors.tsv')
    counts = Counter(r['audit'] for r in inventory)
    test_counts = Counter(r['review'] for r in tests)
    severity = Counter(r['severity'] for r in findings)
    verified = [r for r in findings if r['audit'] == 'fixed' and r['fix'] == 'verified']
    retired = [r for r in findings if r['audit'] == 'removed_by_user']
    unresolved = [r for r in findings if r not in verified and r not in retired]
    open_severity = Counter(r['severity'] for r in unresolved)
    tetra_disabled = any(r['id'] == 'TA-039' for r in verified)
    tetra_note = ('按用户决定只保留组成分数，停用未校准宿主链接；TA-039仅关闭错误链接风险，不代表科学校准通过。'
                  if tetra_disabled else '0.7仍未校准，TA-039保持开放。')
    runs = [json.loads(line) for line in (OUT / 'runs.jsonl').read_text().splitlines() if line.strip()]
    p0 = rows('p0-main-cases.tsv')
    assert len({r['case'] for r in p0}) == len(p0)
    p0_passed = sum(r['result'] == 'pass' and r['trace_tasks'] == '0' and r['command_files'] == '0' for r in p0)
    main_sha = hashlib.sha256((ROOT / 'main.nf').read_bytes()).hexdigest()
    p0_current = sum(r.get('source_main_sha256') == main_sha for r in p0)
    manifest = json.loads((OUT / 'evidence/post-fix-source-state.json').read_text())
    source_hashes = manifest['source_sha256']
    source_matches = all((ROOT / name).is_file() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value
                         for name, value in source_hashes.items())
    text = ['# 当前审计进度', '',
        f'由 scripts/refresh_status.py 从台账生成；日期 {datetime.now(ZoneInfo("Asia/Shanghai")).date()}。基线 f57d0f91454ee0c99cf462ac9093bdf68349991a。', '',
        f'- 生产 .nf 台账：{len(inventory)}（当前={len(inventory)-counts["removed_by_user"]}，按用户要求退役={counts["removed_by_user"]}）；investigating={counts["investigating"]}，matched={counts["matched"]}。历史分母保留。',
        f'- 问题：{len(findings)}；S0={severity["S0"]}，S1={severity["S1"]}，S2={severity["S2"]}，S3={severity["S3"]}。TA 为生产契约，TT 为测试逻辑/覆盖问题。',
        f'- tests 来源台账：{len(tests)}（当前={len(tests)-test_counts["removed_by_user"]}，退役={test_counts["removed_by_user"]}）；包括 harness/config/文档，不是用例分母。',
        f'- 已验证局部修复={len(verified)}，按用户要求退役={len(retired)}，其余未决={len(unresolved)}（S0={open_severity["S0"]}，S1={open_severity["S1"]}，S2={open_severity["S2"]}）。退役不计修复通过；运行记录={len(runs)}。', '',
        f'原 main 独立拒绝场景 {p0_passed}/{len(p0)}；当前 main 哈希对应={p0_current}。重放不增加场景分母；不证明完整输入契约或 nf-test 框架通过。', '',
        f'已纳入证据的来源哈希清单 {len(source_hashes)} 项；当前工作区匹配={source_matches}。这不是全仓库来源或测试用例分母。', '',
        f'词法扫描：{len(reachability)} 文件、{len(edges)} 导入符号、{sum(r["include_reachable"] == "True" for r in reachability)} 主入口可达文件、{sum(r["resolution"] == "missing" for r in edges)} 未解析 include、{len(selectors)} 配置声明。不能代替动态连接与执行证据。', '']
    path, latest = latest_receipt(runs)
    if latest:
        text += [f'最近接受的修复批次：[{latest["run_id"]}]({path.relative_to(OUT) if path.is_relative_to(OUT) else "../../" + str(path.relative_to(ROOT))})；完成日期 {latest.get("completed_local_date", "见receipt")}。', '']
        text += ['本批局部验证项：' + '、'.join(latest.get('verified_findings', [])) + '。', '']
        if 'native_trace_entries' in latest:
            values = latest.get('native_status_counts', {})
            text += [f'选定原生 trace {latest["native_trace_entries"]} 条：COMPLETED={values.get("COMPLETED", "见receipt")}、CACHED={values.get("CACHED", "见receipt")}、FAILED={values.get("FAILED", 0 if values else "见receipt")}。observer与旧错误对照按各receipt单列；这些任务数不能当作科学样本数或全部正例。', '']
        if 'unit_unique_methods' in latest:
            text += [f'独立计数的单元方法={latest["unit_unique_methods"]}；重叠运行按test ID去重，不代表全部测试或科学效果认证。', '']
        if 'r_smoke_checks' in latest or 'platform_observer_tasks' in latest:
            details = []
            if 'r_smoke_checks' in latest:
                details.append(f'R smoke={latest["r_smoke_checks"]}')
            if 'platform_observer_tasks' in latest:
                details.append(f'外部CLI observer平台任务={latest["platform_observer_tasks"]}')
            text += ['；'.join(details) + '。不等于完整真实工具/镜像/科学效果认证。', '']
    text += ['未决问题按严重度列出；ready仍是未决，未执行/范围不足不能算通过。', '',
             '| ID | 级别 | 修复状态 | 范围 |', '| --- | --- | --- | --- |']
    for r in sorted(unresolved, key=lambda r: (r['severity'], r['id'])):
        text.append('| ' + ' | '.join(r[k].replace('|', '\\|').replace('\n', ' ') for k in ['id','severity','fix','path']) + ' |')
    text += ['', '全量审计未完成，不给支持路径放行结论。M0动态配置/完整channel图/历史证据归属与默认真实基线、固定版本工具/DB/model契约、剩余缺陷修复、nf-test及真实阳性平台/科学基准仍须完成。', '',
        '源代码与补丁链见 evidence/post-fix-source-state.json；原始来源是488个普通文件hash加1个目录symlink，共489个tracked对象，冻结表保持不变。SCAPP按用户要求退役；DAS多分箱器规则、统一参考重映射和TETRA方法决定保持。TETRA的55来源分组留出基准已执行：数值通过、预定科学阈值验收失败。' + tetra_note + '详见 contracts/tetra-source-benchmark.md。', '',
        '当前缺陷以 findings.tsv 为准；逐项范围见 acceptance.md、native-real-nodes.tsv 和各receipt。历史计数、尝试与被替代实现留在 journal.md/history/，不从旧摘要推导当前验收。', '']
    (OUT / 'status.md').write_text('\n'.join(text))


if __name__ == '__main__':
    main()
