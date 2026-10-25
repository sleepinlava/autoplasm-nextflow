#!/usr/bin/env python3
"""Verify the complete official PLASMe archive and build its full local indexes."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

SIZE=13632339031
MD5='b32263ad4fb20c04044700170b1609ef'


def digest(path,algorithm='sha256'):
    result=hashlib.new(algorithm)
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()


def extract(archive,directory):
    files=[]
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            path=PurePosixPath(member.filename)
            if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe archive member')
            target=directory.joinpath(*path.parts)
            if member.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():raise ValueError('Refusing to replace existing archive member: '+str(target))
            result=hashlib.sha256()
            with z.open(member) as source,target.open('xb') as output:
                for chunk in iter(lambda:source.read(1024*1024),b''):output.write(chunk);result.update(chunk)
            if target.stat().st_size!=member.file_size:raise ValueError('Incomplete archive member')
            files.append({'path':member.filename,'bytes':member.file_size,'crc32':hex(member.CRC),'sha256':result.hexdigest()})
    return files


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--python',type=Path,required=True)
    p.add_argument('--threads',type=int,default=2)
    a=p.parse_args();archive=a.archive.resolve();out=a.outdir.resolve();python=a.python.resolve()
    if out.exists():raise ValueError('Choose a new output directory')
    if a.threads<1:raise ValueError('threads must be positive')
    assert archive.stat().st_size==SIZE and digest(archive,'md5')==MD5
    archive_sha=digest(archive)
    out.mkdir(parents=True)
    print('Full archive size/upstream MD5 verified; extracting every member',flush=True)
    files=extract(archive,out);db=out/'DB'
    assert len(files)==41 and len(list((db/'trans_model').glob('*.pt')))==36
    nested=extract(db/'plsdb.zip',db)
    commands=[[str(python.parent/'diamond'),'makedb','--in','plsdb_Mar30.fna.aa','-d','plsdb_Mar30','-p',str(a.threads)],
              [str(python.parent/'makeblastdb'),'-in','plsdb_Mar30.fna','-dbtype','nucl','-out','plsdb_Mar30']]
    runs=[]
    for i,command in enumerate(commands):
        print('Building full',Path(command[0]).name,'index',flush=True)
        with (out/f'build-{i}.stdout').open('w') as stdout,(out/f'build-{i}.stderr').open('w') as stderr:
            result=subprocess.run(command,cwd=db,stdout=stdout,stderr=stderr)
        if result.returncode:raise RuntimeError('Database builder failed: '+str(command))
        runs.append({'command':command,'exit':result.returncode})
    indexes=[q for q in db.glob('plsdb_Mar30.*') if q.is_file() and q.suffix not in ['.zip','.fna','.aa','.p2a']]
    assert (db/'plsdb_Mar30.dmnd').stat().st_size>0
    for suffix in ['nin','nhr','nsq']:assert any(q.stat().st_size for q in db.glob('plsdb_Mar30*.'+suffix))
    receipt={'pass':True,'full_database':True,'zenodo_record':'8046934','archive_bytes':SIZE,'archive_md5':MD5,
             'archive_sha256':archive_sha,'archive_members':files,'nested_sequence_members':nested,
             'index_files':[{'path':q.name,'bytes':q.stat().st_size,'sha256':digest(q)} for q in indexes],
             'runs':runs,'database':str(db),'source_sha256':digest(Path(__file__).resolve()),
             'scope':'Complete official models/reference proteins/DNA; indexes built with pinned DIAMOND/BLAST; no model or biological accuracy claim'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Prepared full DB with36 models and full indexes:',db,flush=True)


if __name__=='__main__':main()
