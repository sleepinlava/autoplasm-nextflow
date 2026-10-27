#!/usr/bin/env python3
"""Independent Python oracle and actual Nextflow content-cache controls.

Synthetic resource bytes plus a native cat reader; no classifier/biology claim.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def oracle(root):
    if root.is_file():paths=[root]
    else:paths=[Path(parent)/name for parent,dirs,names in os.walk(root,followlinks=True) for name in names]
    # Java String.compareTo sorts UTF-16 code units, independent of locale.
    paths.sort(key=lambda p:str(p.relative_to(root)).encode('utf-16-be'))
    digest=hashlib.sha256();total=0
    for path in paths:
        relative='' if path==root else str(path.relative_to(root))
        size=path.stat().st_size;total+=size
        for value in [relative,str(size),sha(path)]:digest.update(value.encode());digest.update(b'\0')
    file_digest=digest.hexdigest()
    entries=[root] if root.is_file() else [root]+[Path(parent)/name for parent,dirs,names in os.walk(root,followlinks=True) for name in dirs+names]
    entries.sort(key=lambda p:('' if p==root else str(p.relative_to(root))).encode('utf-16-be'))
    layout=hashlib.sha256()
    bits={'OWNER_READ':stat.S_IRUSR,'OWNER_WRITE':stat.S_IWUSR,'OWNER_EXECUTE':stat.S_IXUSR,
          'GROUP_READ':stat.S_IRGRP,'GROUP_WRITE':stat.S_IWGRP,'GROUP_EXECUTE':stat.S_IXGRP,
          'OTHERS_READ':stat.S_IROTH,'OTHERS_WRITE':stat.S_IWOTH,'OTHERS_EXECUTE':stat.S_IXOTH}
    for path in entries:
        mode=path.stat().st_mode
        fields=['' if path==root else str(path.relative_to(root)), 'directory' if path.is_dir() else 'file',
                os.readlink(path) if path!=root and path.is_symlink() else '',
                ','.join(sorted(name for name,bit in bits.items() if mode&bit))]
        for value in fields:layout.update(value.encode());layout.update(b'\0')
    layout.update(file_digest.encode())
    return {'schema_version':2,'algorithm':'sha256-files-v1-layout-posix-v2',
            'file_count':len(paths),'entry_count':len(entries),'bytes':total,'sha256':layout.hexdigest()}


def run(base,nextflow):
    source={p:sha(ROOT/p) for p in ['lib/ResourceIdentity.groovy','tests/nextflow/resource_identity.nf','tests/run_resource_identity.py']}
    fixture=base/"fixtures with space's";fixture.mkdir()
    tree=fixture/'base';tree.mkdir();(tree/'nested').mkdir()
    (tree/'signal.txt').write_bytes(b'old\n');(tree/'.hidden').write_bytes(b'hidden\n')
    (tree/'nested/signal.txt').write_bytes(b'different basename peer\n')
    (tree/'large.bin').write_bytes(bytes(range(256))*(8192)+b'ending')
    for name in ['α.model','😀.model','\ue000.model','line\nbreak.model','tab\treturn\r.model','literal[glob]*?.model']:(tree/name).write_text(name+'\n')
    cases=[{'id':'base','root':str(tree)}]
    for name in ['identical','changed_same_stats','mtime_only','tail_changed','renamed','hidden_added','deleted','empty_dir_added','executable_changed']:
        path=fixture/name;shutil.copytree(tree,path)
        if name=='changed_same_stats':
            target=path/'signal.txt';stamp=target.stat();target.write_bytes(b'new\n');os.utime(target,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        elif name=='mtime_only':os.utime(path/'signal.txt',ns=(1_000_000_000,1_000_000_000))
        elif name=='tail_changed':
            with (path/'large.bin').open('r+b') as stream:stream.seek(-1,2);stream.write(b'X')
        elif name=='renamed':(path/'nested/signal.txt').rename(path/'nested/renamed.txt')
        elif name=='hidden_added':(path/'.new-hidden').write_text('new hidden model\n')
        elif name=='empty_dir_added':(path/'empty-dir').mkdir()
        elif name=='executable_changed':(path/'signal.txt').chmod(0o755)
        elif name=='deleted':(path/'nested/signal.txt').unlink()
        cases.append({'id':name,'root':str(path)})
    alias=fixture/'root_alias';alias.symlink_to(tree,target_is_directory=True);cases.append({'id':'root_alias','root':str(alias)})
    empty=fixture/'empty';empty.mkdir();cases.append({'id':'empty_directory','root':str(empty)})
    single=fixture/'single';single.write_bytes(b'');cases.append({'id':'empty_file','root':str(single)})
    link_tree=fixture/'links';link_tree.mkdir();(link_tree/'file_link').symlink_to(tree/'signal.txt');(link_tree/'dir_link').symlink_to(tree/'nested',target_is_directory=True)
    cases.append({'id':'symlink_members','root':str(link_tree)})
    for name in ['symlink_retarget_a','symlink_retarget_b']:
        path=fixture/name;path.mkdir()
        target=fixture/(name+'.target');target.write_bytes(b'identical target content\n')
        (path/'linked').symlink_to(target)
        cases.append({'id':name,'root':str(path)})
    for name in ['broken_link','link_cycle','fifo']:
        path=fixture/name;path.mkdir()
        if name=='broken_link':(path/'bad').symlink_to(path/'missing')
        elif name=='link_cycle':(path/'cycle').symlink_to(path,target_is_directory=True)
        else:os.mkfifo(path/'fifo')
        cases.append({'id':name,'root':str(path),'expected_error':True})
    cases.extend([
        {'id':'outside_member','root':str(tree),'members':[str(single)]},
        {'id':'duplicate_member','root':str(tree),'members':[str(tree/'signal.txt')]*2},
        {'id':'directory_member','root':str(tree),'members':[str(tree/'nested')]},
    ])
    props=base/'properties';props.mkdir();(props/'params.json').write_text(json.dumps({'mode':'properties','cases':cases})+'\n')
    config=base/'native.config';config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='256 MB'\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
    def execute(folder,params,resume=None):
        (folder/'params.json').write_text(json.dumps(params)+'\n')
        command=[nextflow,'-C',str(config),'run',str(ROOT/'tests/nextflow/resource_identity.nf'),'-params-file',str(folder/'params.json'),
                 '-work-dir',str(base/'work'),'-with-trace',str(folder/'trace.tsv'),'-ansi-log','false','-name','resource_identity_'+folder.name]
        if resume:command+=['-resume',resume]
        result=subprocess.run(command,cwd=base,capture_output=True,text=True,timeout=180)
        (folder/'stdout').write_text(result.stdout);(folder/'stderr').write_text(result.stderr)
        assert result.returncode==0,result.stdout+result.stderr
        return command,result.stdout
    command,text=execute(props,{'mode':'properties','cases':cases})
    observed={row['case']:row for row in [json.loads(line.split('=',1)[1]) for line in text.splitlines() if line.startswith('IDENTITY_CONTROL=')]}
    assert len(observed)==len(cases)==22
    for row in cases:
        if row.get('expected_error'):assert 'error' in observed[row['id']],row['id']
        elif 'members' in row:assert observed[row['id']]['error']=='IllegalArgumentException'
        else:assert observed[row['id']]['identity']==oracle(Path(row['root'])),row['id']
    assert observed['base']['identity']==observed['identical']['identity']==observed['mtime_only']['identity']==observed['root_alias']['identity']
    for name in ['changed_same_stats','tail_changed','renamed','hidden_added','deleted','empty_dir_added','executable_changed']:assert observed[name]['identity']!=observed['base']['identity']
    assert observed['symlink_retarget_a']['identity']!=observed['symlink_retarget_b']['identity']
    resource=base/'resource';resource.mkdir();signal=resource/'signal.txt';signal.write_bytes(b'old\n');stamp=signal.stat();rootstamp=resource.stat()
    records=[];uuid=None;scripts=set()
    for case in ['cold','unchanged','changed','restored','hidden_added','hidden_removed','newline_added','newline_changed','newline_removed','empty_dir_added','empty_dir_removed','mode_changed','mode_restored','link_added','link_target_changed','link_removed']:
        folder=base/case;folder.mkdir()
        if case in ['changed','restored']:
            signal.write_bytes(b'new\n' if case=='changed' else b'old\n');os.utime(signal,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        if case=='hidden_added':(resource/'.hidden').write_bytes(b'not consumed by cat but part of declared resource\n')
        if case=='hidden_removed':(resource/'.hidden').unlink()
        if case=='newline_added':(resource/'line\nbreak').write_bytes(b'old\n')
        if case=='newline_changed':
            member=resource/'line\nbreak';before=member.stat();member.write_bytes(b'new\n');os.utime(member,ns=(before.st_atime_ns,before.st_mtime_ns))
        if case=='newline_removed':(resource/'line\nbreak').unlink()
        if case=='empty_dir_added':(resource/'empty').mkdir()
        if case=='empty_dir_removed':(resource/'empty').rmdir()
        if case in ['mode_changed','mode_restored']:signal.chmod(0o755 if case=='mode_changed' else 0o644)
        if case=='link_added':
            (base/'external-target').write_bytes(b'old\n');(resource/'linked').symlink_to(base/'external-target')
        if case=='link_target_changed':
            member=base/'external-target';before=member.stat();member.write_bytes(b'new\n');os.utime(member,ns=(before.st_atime_ns,before.st_mtime_ns))
        if case=='link_removed':(resource/'linked').unlink()
        os.utime(resource,ns=(rootstamp.st_atime_ns,rootstamp.st_mtime_ns))
        command,text=execute(folder,{'mode':'cache','resource':str(resource)},uuid)
        tasks=list(csv.DictReader((folder/'trace.tsv').open(),delimiter='\t'));assert len(tasks)==1
        expected='COMPLETED' if case in ['cold','changed','hidden_added','newline_added','newline_changed','empty_dir_added','mode_changed','link_added','link_target_changed'] else 'CACHED'
        assert tasks[0]['status']==expected,tasks
        row,=[json.loads(line.split('=',1)[1]) for line in text.splitlines() if line.startswith('CACHE_CONTROL=')]
        assert row['identity']==oracle(resource) and row['observed']==('new\n' if case=='changed' else 'old\n')
        scripts.add(sha(Path(tasks[0]['workdir'])/'.command.sh'))
        if uuid is None:uuid=next(line.split('\t')[5] for line in reversed((base/'.nextflow/history').read_text().splitlines()) if '\tresource_identity_cold\t' in line)
        records.append({'case':case,'command':command,'tasks':tasks,'observed':row})
        print(case,expected,flush=True)
    assert len(scripts)==1,'The reader script must stay identical; cache invalidation comes from the identity input.'
    assert all(sha(ROOT/p)==h for p,h in source.items())
    (base/'run.json').write_text(json.dumps({'pass':True,'source_sha256':source,'source_unchanged':True,
        'property_cases':len(cases),'property_results':observed,'runs':records,'reader_script_sha256':next(iter(scripts)),
        'scope':'Actual Groovy fingerprint implementation vs independent Python oracle; synthetic byte fixtures and native cat cache observer only, not biological tools/model accuracy/OCI/cloud.'},indent=2,ensure_ascii=False)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--work-dir',required=True)
    parser.add_argument('--nextflow',default=str(ROOT/'results/tool-audit/runtime/bin/nextflow'))
    args=parser.parse_args();base=Path(args.work_dir).resolve();base.mkdir(parents=True,exist_ok=False);run(base,args.nextflow)
