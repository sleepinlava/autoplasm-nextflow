#!/usr/bin/env python3
"""Index, clean archived result trees, and restore retained test evidence.

Cleanup requires a completed capture and independent successful verification.
It validates the original file identities before deletion. Installed package
caches are reconstructible; result payloads stay in the verified CoW archive.
"""
import argparse
import collections
import email
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import time
import xml.etree.ElementTree as ET


def dump(path, obj): path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024), b''):h.update(b)
    return h.hexdigest()


def inventory(a):
    with gzip.open(a/'inventory.jsonl.gz','rt') as f:
        for line in f:yield json.loads(line)


def index(a):
    roots=collections.Counter(); categories=collections.Counter(); current=[]; envs={}; traces=[]; reports=[]; models=[];lockfiles=[]
    source_root=Path(json.loads((a/'metadata/capture.json').read_text())['original_root'])
    package_file=gzip.open(a/'installed-python-packages.jsonl.gz','wt',compresslevel=2)
    package_count=0
    with gzip.open(a/'test-files.jsonl.gz','wt',compresslevel=2) as tf, gzip.open(a/'result-files.jsonl.gz','wt',compresslevel=2) as rf:
        for r in inventory(a):
            p=Path(r['path']); parts=p.parts
            if p.name in {'METADATA','PKG-INFO'} and any(x.endswith(('.dist-info','.egg-info')) for x in parts) and r['kind']=='file':
                original=source_root/r['path']
                raw=original.read_bytes()
                s=original.stat()
                if (s.st_size,s.st_mtime_ns)!=(r['bytes'],r['mtime_ns']):raise RuntimeError('Python installation metadata changed: '+r['path'])
                text=raw.decode('utf-8',errors='replace');m=email.message_from_string(text)
                package_file.write(json.dumps({'path':r['path'],'name':m.get('Name'),'version':m.get('Version'),
                    'sha256':hashlib.sha256(raw).hexdigest(),'raw_metadata':text})+'\n');package_count+=1
            if r['retained']:
                roots[parts[0]]+=1
                for tag in r['roles']:categories[tag]+=1
                if parts[0]=='tests' or (parts[0]=='modules' and 'tests' in parts):tf.write(json.dumps(r)+'\n')
                if parts[0]=='results':rf.write(json.dumps(r)+'\n')
                if 'model_or_model_asset' in r['roles']:models.append(r)
                if 'dependency_or_data_lock' in r['roles']:lockfiles.append({'path':r['path'],'sha256':r.get('sha256'),'bytes':r['bytes']})
            if 'conda-meta' in parts:
                i=parts.index('conda-meta');prefix='/'.join(parts[:i]);envs.setdefault(prefix,{'prefix':prefix,'package_receipts':0,'history':False})
                if p.suffix=='.json':envs[prefix]['package_receipts']+=1
                if p.name=='history':envs[prefix]['history']=True
            if not r['retained'] or r['kind']!='file':continue
            q=a/'snapshot'/r['path']
            if p.suffix=='.xml' and r['bytes']<30_000_000:
                try:
                    tree=ET.parse(q).getroot()
                    if tree.tag in {'testsuite','testsuites'}:reports.append({'path':r['path'],'sha256':r['sha256'],'root_attributes':tree.attrib,'suites':[n.attrib for n in tree.iter('testsuite')],'cases':sum(1 for _ in tree.iter('testcase'))})
                except ET.ParseError:pass
            if 'trace' in p.name.lower() and p.suffix in {'.txt','.tsv','.csv'} and r['bytes']<20_000_000:
                lines=q.read_text(errors='replace').splitlines()
                if lines and 'task_id' in lines[0] and '\tstatus\t' in '\t'+lines[0]+'\t':
                    header=lines[0].split('\t'); pos=header.index('status');states=collections.Counter()
                    for line in lines[1:]:
                        fields=line.split('\t')
                        if len(fields)>pos:states[fields[pos]]+=1
                    traces.append({'path':r['path'],'sha256':r['sha256'],'states':dict(states),'scope':'historical task rows; not unique biological cases'})
    package_file.close()
    dump(a/'lockfiles.json',lockfiles)
    receipt=a/'snapshot/docs/tool-audit/evidence/post-fix-source-state.json'
    drift=[]
    if receipt.exists():
        for path,expected in json.loads(receipt.read_text()).get('source_sha256',{}).items():
            p=a/'snapshot'/path
            actual=digest(p) if p.is_file() else None
            if actual!=expected:drift.append({'path':path,'accepted_sha256':expected,'archived_sha256':actual})
    dump(a/'accepted-source-drift.json',drift)
    entries=json.loads((a/'test-entries.json').read_text())
    for e in entries:
        if e['path'].startswith('tests/') or (e['path'].startswith('modules/') and '/tests/' in e['path']):current.append(e)
    specs=a/'environment-specs';specs.mkdir(exist_ok=True)
    for prefix,record in envs.items():
        urls=[];missing=[]
        for p in sorted((a/'snapshot'/prefix/'conda-meta').glob('*.json')):
            data=json.loads(p.read_text());url=data.get('url')
            if url:urls.append(url+('#'+data['md5'] if data.get('md5') else ''))
            else:missing.append(p.name)
        filename=hashlib.sha256(prefix.encode()).hexdigest()+'.explicit.txt'
        (specs/filename).write_text('@EXPLICIT\n'+'\n'.join(urls)+'\n')
        record.update(explicit_spec='environment-specs/'+filename,packages_without_url=missing,
                      note='Conda packages only; pip distributions, platform and external tools require their separate locks/metadata')
    dump(a/'current-test-entries.json',current);dump(a/'environment-prefixes.json',list(envs.values()))
    dump(a/'models.json',models);dump(a/'junit-reports.json',reports);dump(a/'trace-reports.json',traces)
    dump(a/'index-summary.json',{'retained_by_root':dict(roots),'role_counts_overlapping':dict(categories),'current_entry_files':len(current),
         'current_python_test_definitions':sum(len(e['definitions']) for e in current),'conda_environment_prefixes':len(envs),
         'junit_reports':len(reports),'trace_reports':len(traces),'model_or_model_asset_files':len(models),
         'installed_python_distribution_metadata':package_count,'lockfiles':len(lockfiles),'accepted_source_drift':len(drift)})


def cleanup(root,a):
    if not json.loads((a/'summary.json').read_text())['capture_complete']:raise RuntimeError('capture incomplete')
    if not json.loads((a/'verification.json').read_text())['ok']:raise RuntimeError('archive not verified')
    targets=[]
    for p in (root/'results').iterdir():
        if p.name=='test-review-archive':continue
        if p.name=='tool-audit':
            targets.extend(q for q in p.iterdir() if q.name!='runtime' and not q.is_symlink())
        elif not p.is_symlink():targets.append(p)
    cache=root/'results/tool-audit/runtime/mamba-root/pkgs'
    if cache.is_dir():targets.append(cache)
    targets=sorted(targets); names=[p.relative_to(root).as_posix() for p in targets]
    counts=collections.Counter();logical=collections.Counter();omitted=collections.Counter();changes=[]
    name_set=set(names)
    def match(path):
        cache_name='results/tool-audit/runtime/mamba-root/pkgs'
        if path==cache_name or path.startswith(cache_name+'/'):return cache_name if cache_name in name_set else None
        parts=path.split('/')
        n='/'.join(parts[:3] if path.startswith('results/tool-audit/') else parts[:2])
        return n if n in name_set else None
    # Every retained result has already been content-verified. Ensure sources
    # did not change after capture before removing their original locations.
    for r in inventory(a):
        n=match(r['path'])
        if n is None:continue
        p=root/r['path'];counts[n]+=1;logical[n]+=r['bytes']
        if not r['retained']:omitted[n]+=1
        try:
            s=p.lstat()
            if (s.st_size,s.st_mtime_ns,s.st_ino)!=(r['bytes'],r['mtime_ns'],r['original_inode']):changes.append(r['path'])
        except OSError:changes.append(r['path'])
    actual_counts={}
    for p,n in zip(targets,names):
        if p.is_file() or p.is_symlink():actual_counts[n]=1
        else:
            total=0
            for base,dirs,files in os.walk(p,followlinks=False):
                total+=len(files)
                for d in dirs:
                    if (Path(base)/d).is_symlink():total+=1
            actual_counts[n]=total
        if actual_counts[n]!=counts[n]:changes.append(n+': directory membership changed')
    plan=[{'path':n,'entries':counts[n],'logical_bytes':logical[n],'metadata_only_reconstructible_entries':omitted[n],
           'action':'remove reconstructible package cache' if n.endswith('/mamba-root/pkgs') else 'replace verified historical result tree with relative archive link',
           'archive_target':None if n.endswith('/mamba-root/pkgs') else str(Path('snapshot')/n)} for n in names]
    dump(a/'cleanup-plan.json',{'targets':plan,'changed_since_capture':changes,'executed':False})
    if changes:raise RuntimeError('Sources changed; cleanup refused, inspect cleanup-plan.json')
    before=shutil.disk_usage(root).free;done=[]
    for p,n in zip(targets,names):
        if p.is_dir():shutil.rmtree(p)
        else:p.unlink()
        if n.endswith('/mamba-root/pkgs'):p.mkdir()
        else:p.symlink_to(os.path.relpath(a/'snapshot'/n,p.parent),target_is_directory=(a/'snapshot'/n).is_dir())
        done.append(n)
        dump(a/'cleanup-progress.json',{'completed':done,'free_before_bytes':before,'free_now_bytes':shutil.disk_usage(root).free})
    os.sync()
    after=shutil.disk_usage(root).free
    dump(a/'cleanup-result.json',{'completed':done,'target_count':len(done),'free_before_bytes':before,'free_after_bytes':after,
         'net_recovered_bytes':after-before,'logical_original_bytes_removed':sum(logical.values()),
         'warning':'CoW retained data still consumes disk; logical bytes removed are not actual reclaimed bytes. Installed dependency payloads within historical runs and package caches were not archived; metadata and detected model weights were retained. Runtime central environments and project test environment remain.'})


def restore(a,dest,prefix):
    if dest.exists():raise RuntimeError('restore destination must not exist')
    dest.mkdir(parents=True)
    original=json.loads((a/'metadata/capture.json').read_text())['original_root']
    selected=[]
    empty_file=a/'empty-directories.json'
    if empty_file.exists():
        for row in json.loads(empty_file.read_text()):
            if prefix and not (row['path']==prefix or row['path'].startswith(prefix+'/')):continue
            out=dest/row['path'];out.mkdir(parents=True,exist_ok=True);os.chmod(out,row['mode'])
    for r in inventory(a):
        if not r['retained'] or (prefix and not (r['path']==prefix or r['path'].startswith(prefix+'/'))):continue
        source=a/'snapshot'/r['path'];out=dest/r['path'];out.parent.mkdir(parents=True,exist_ok=True)
        if r['kind']=='file':
            shutil.copy2(source,out,follow_symlinks=False)
            if digest(out)!=r['sha256']:raise RuntimeError('restore checksum mismatch: '+r['path'])
            os.chmod(out,r['mode'])
            os.utime(out,ns=(r['mtime_ns'],r['mtime_ns']))
        else:
            target=r['target']
            if target.startswith(original+'/'):target=str(dest/target[len(original)+1:])
            out.symlink_to(target)
        selected.append(r['path'])
    dump(dest/'RESTORE_RECEIPT.json',{'files':len(selected),'prefix':prefix,'original_root':original,'note':'retained evidence only; rebuild metadata-only installed environments. External and originally broken links may remain unresolved.'})


def seal(a):
    rows=[]
    for p in sorted(a.rglob('*')):
        if 'snapshot' in p.relative_to(a).parts:continue
        if p.is_file() and p.name!='SHA256SUMS':rows.append(digest(p)+'  '+p.relative_to(a).as_posix())
    (a/'SHA256SUMS').write_text('\n'.join(rows)+'\n')


def deduplicate(a):
    if not json.loads((a/'verification.json').read_text())['ok']:raise RuntimeError('verification required')
    before=shutil.disk_usage(a).free;keepers={};verified=set();changes=[];already_shared=0
    for r in inventory(a):
        if not r['retained'] or r['kind']!='file' or r['bytes']<1024*1024:continue
        key=(r['sha256'],r['mode']);p=a/'snapshot'/r['path']
        if key not in keepers:keepers[key]=p;continue
        canonical=keepers[key]
        if p.stat().st_ino==canonical.stat().st_ino:already_shared+=1;continue
        if key not in verified:
            if digest(canonical)!=r['sha256']:raise RuntimeError('canonical changed: '+str(canonical))
            verified.add(key)
        if digest(p)!=r['sha256']:raise RuntimeError('duplicate changed: '+str(p))
        temporary=p.with_name(p.name+'.archive-dedup-tmp')
        os.link(canonical,temporary);os.replace(temporary,p)
        if p.stat().st_ino!=canonical.stat().st_ino:raise RuntimeError('dedup identity failure')
        changes.append({'path':r['path'],'canonical':canonical.relative_to(a/'snapshot').as_posix(),'bytes':r['bytes'],'sha256':r['sha256']})
    os.sync();after=shutil.disk_usage(a).free
    dump(a/'deduplication.json',{'threshold_bytes':1024*1024,'changes':changes,'files_relinked':len(changes),'already_shared':already_shared,
         'logical_duplicate_bytes':sum(r['bytes'] for r in changes),'free_before_bytes':before,'free_after_bytes':after,
         'net_recovered_bytes':after-before,'integrity':'both inputs SHA256 checked before each archive-only hardlink replacement; modes grouped; original per-path metadata remains in inventory'})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['index','cleanup','restore','seal','deduplicate'])
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--destination',type=Path);p.add_argument('--prefix',default='')
    args=p.parse_args();a=args.archive.resolve()
    if args.action=='index':index(a)
    elif args.action=='cleanup':cleanup(args.root.resolve(),a)
    elif args.action=='seal':seal(a)
    elif args.action=='deduplicate':deduplicate(a)
    elif args.destination is None:p.error('restore needs --destination')
    else:restore(a,args.destination.resolve(),args.prefix)


if __name__=='__main__':main()
