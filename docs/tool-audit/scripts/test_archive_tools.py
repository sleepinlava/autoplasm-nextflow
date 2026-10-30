#!/usr/bin/env python3
"""Exercise capture, restore, cleanup and corruption refusal on a tiny fixture.

Run on a CoW filesystem with --scratch /path/to/writable/directory.
Only the temporary fixture created by this script is cleaned.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile


def module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scratch',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    args=p.parse_args();here=Path(__file__).resolve().parent
    capture=module('capture',here/'archive_test_review.py');manage=module('manage',here/'manage_test_archive.py');checks=[]
    with tempfile.TemporaryDirectory(prefix='archive-tools-qa-',dir=args.scratch) as tmp:
        root=Path(tmp);(root/'tests').mkdir();(root/'tests/test_demo.py').write_text('def test_one(): pass\n')
        (root/'tests/empty-fixture').mkdir()
        (root/'tests/data.fa').write_text('>one\nACGT\n');(root/'tests/absolute.fa').symlink_to(root/'tests/data.fa')
        env=root/'results/tool-audit/old/env';(env/'conda-meta').mkdir(parents=True)
        (env/'conda-meta/a.json').write_text('{}');(env/'lib').mkdir();(env/'lib/code.py').write_text('regenerable\n')
        (env/'model.h5').write_bytes(b'weights');(root/'results/tool-audit/old/result.json').write_text('{"status":"failed"}')
        (root/'results/tool-audit/old/large1.bin').write_bytes(b'A'*(1024*1024))
        (root/'results/tool-audit/old/large2.bin').write_bytes(b'A'*(1024*1024))
        cache=root/'results/tool-audit/runtime/mamba-root/pkgs';cache.mkdir(parents=True);(cache/'unused.txt').write_text('cache')
        for cmd in [['git','init','-q'],['git','add','tests'],['git','-c','user.name=Archive QA','-c','user.email=archive-qa@example.invalid','-c','commit.gpgsign=false','commit','-qm','fixture']]:
            subprocess.run(cmd,cwd=root,capture_output=True,check=True)
        a=root/'results/test-review-archive/test';capture.build(root,a);capture.verify(a)
        manage.deduplicate(a)
        first=a/'snapshot/results/tool-audit/old/large1.bin';second=first.with_name('large2.bin')
        assert first.stat().st_ino==second.stat().st_ino
        assert (root/'results/tool-audit/old/large1.bin').stat().st_ino!=first.stat().st_ino
        checks.append('dedup checks content and shares only archive inodes')
        assert not (a/'snapshot/results/tool-audit/old/env/lib/code.py').exists()
        assert (a/'snapshot/results/tool-audit/old/env/model.h5').read_bytes()==b'weights'
        checks.append('dependency omission preserves environment receipt and model')
        dest=root/'restore';manage.restore(a,dest,'tests')
        assert (dest/'tests/absolute.fa').read_text()=='>one\nACGT\n';checks.append('restore verifies content and relocates internal absolute link')
        assert (dest/'tests/empty-fixture').is_dir();checks.append('empty fixture directories survive capture verification and restoration')
        # A changed file must prohibit cleanup before any original is removed.
        q=root/'results/tool-audit/old/result.json';original=q.read_bytes();q.write_text('changed')
        try:manage.cleanup(root,a)
        except RuntimeError:checks.append('changed originals refuse cleanup')
        else:raise AssertionError('changed original was removed')
        # Restore source metadata from the capture record for a valid cleanup.
        import os
        row=next(r for r in manage.inventory(a) if r['path']=='results/tool-audit/old/result.json')
        q.write_bytes(original);os.utime(q,ns=(row['mtime_ns'],row['mtime_ns']))
        manage.cleanup(root,a)
        assert (root/'results/tool-audit/old').is_symlink()
        assert json.loads((root/'results/tool-audit/old/result.json').read_text())['status']=='failed'
        assert not list(cache.iterdir());checks.append('verified cleanup preserves failed results and clears cache')
        (a/'snapshot/tests/data.fa').write_text('corrupt')
        try:capture.verify(a)
        except RuntimeError:checks.append('corruption fails independent verification')
        else:raise AssertionError('corruption accepted')
    args.report.write_text(json.dumps({'checks':checks,'passed':len(checks)},indent=2)+'\n')
    print(json.dumps({'checks_passed':len(checks)}))


if __name__=='__main__':main()
