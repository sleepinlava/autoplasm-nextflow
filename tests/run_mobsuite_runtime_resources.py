#!/usr/bin/env python3
"""Real fixed MOB/BLAST readset controls and audit-only Nextflow cache experiment.

Uses existing complete references and pUTI89; no downloads, installers, synthetic
science, shared-database mutation or replacement of native resource selection.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--environment', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--fasta', type=Path, required=True)
    parser.add_argument('--nextflow', type=Path, required=True)
    args = parser.parse_args()
    out, prefix, database, fasta, nextflow = [p.resolve() for p in
        [args.out,args.environment,args.database,args.fasta,args.nextflow]]
    out.mkdir(parents=True, exist_ok=False)
    receipt = dict(schema_version=1, started=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                   commands=[], cache_phases=[], checks={}, limitations=[
        'Audit harness only: production pre-cache probe/context/pre-execution validation remain open.',
        'Single native fixed wheel environment; not OCI/provider/complete dependency acceptance.',
        'Full pUTI89 is a technical positive control, not an accuracy benchmark.',
        'Aliases and mutating filter_db are explicitly refused by the new inspector.',
        'Existing bacterial/plasmid sources; no claim of absence of all viral homology.'])

    def save():
        (out/'run.json').write_text(json.dumps(receipt,indent=2)+'\n')

    env = os.environ.copy()
    env['PATH'] = str(prefix/'bin') + os.pathsep + env['PATH']
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    private = out/'python'/'mob_suite'
    package = prefix/'lib/python3.10/site-packages/mob_suite'
    for source in sorted(package.rglob('*')):
        relative = source.relative_to(package)
        if source.is_file() and source.suffix in ['.py','.json'] and not {'tests','databases','__pycache__'}.intersection(relative.parts):
            target = private/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
    private_db = private/'databases'
    private_db.mkdir()
    for source in database.iterdir():
        if source.name == 'status.txt':
            shutil.copy2(source,private_db/source.name)
        else:
            (private_db/source.name).symlink_to(source)
    env['PYTHONPATH'] = str(private.parent)
    original = {p.name:sha(p) for p in sorted(database.iterdir()) if p.is_file()}
    receipt['original_database'] = dict(path=str(database),files=original)
    receipt['fixture'] = dict(path=str(fasta),sha256=sha(fasta),bytes=fasta.stat().st_size)
    receipt['sources'] = {str(p.relative_to(ROOT)):sha(p) for p in [
        ROOT/'bin/mobsuite_runtime_resources.py',ROOT/'bin/mobsuite_preflight.py',
        ROOT/'tests/run_mobsuite_runtime_resources.py',ROOT/'tests/nextflow/mobsuite_runtime_resources.nf',
        ROOT/'modules/nf-core/mobsuite/typer/main.nf',ROOT/'modules/nf-core/mobsuite/recon/main.nf']}
    save()

    def run(name,command,expected=0,cwd=ROOT):
        start = time.monotonic()
        with (out/(name+'.stdout')).open('w') as stdout, (out/(name+'.stderr')).open('w') as stderr:
            result = subprocess.run([str(x) for x in command],cwd=cwd,env=env,stdout=stdout,stderr=stderr)
        receipt['commands'].append(dict(name=name,argv=[str(x) for x in command],exit=result.returncode,
                                        seconds=round(time.monotonic()-start,3),expected=expected))
        save()
        if result.returncode != expected:
            raise AssertionError(f'{name}: exit {result.returncode}; see retained stdout/stderr')
        print(name+': expected exit '+str(expected),flush=True)

    python = prefix/'bin/python3'
    inspector = ROOT/'bin/mobsuite_runtime_resources.py'
    native = ['-i',str(fasta),'-o','unused','--sample_id','readset','-n','4']
    def inspect(name,tool='mob_recon',extra=(),expected=0,verify=None):
        command = [python,inspector,'--tool',tool,'--output',out/(name+'.json')]
        if verify: command += ['--verify',out/(verify+'.json')]
        run(name,[*command,'--',*native,*extra],expected)
        if expected:
            assert not (out/(name+'.json')).exists()
            return None
        return json.loads((out/(name+'.json')).read_text())

    try:
        default_recon = inspect('default-recon')
        default_typer = inspect('default-typer','mob_typer')
        assert default_recon['selection_branch'] == default_typer['selection_branch'] == 'default'
        explicit = inspect('explicit-recon',extra=['-d',str(database)])
        assert explicit['selection_branch'] == 'explicit'
        external = out/'external-clusters.txt'
        shutil.copy2(database/'clusters.txt',external)
        outside = inspect('external-meta',extra=['--plasmid_meta',str(external)])
        assert outside['selected_resources']['plasmid_meta']['location'] == str(external)
        stat = external.stat()
        data = external.read_bytes()
        with external.open('r+b') as stream:
            offset = data.index(b'\n')+1
            stream.seek(offset)
            stream.write(b'X' if data[offset:offset+1] != b'X' else b'Y')
        os.utime(external,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        inspect('external-meta-mutated',extra=['--plasmid_meta',str(external)],expected=2,verify='external-meta')
        external.write_bytes(data)
        restored = inspect('external-meta-restored',extra=['--plasmid_meta',str(external)],verify='external-meta')
        assert restored == outside
        inspect('filter-refused',extra=['--filter_db',str(fasta)],expected=2)
        # Real external BLAST volumes, built only from the complete positive
        # bacterial plasmid. This is a prefix-readset check, not filter science.
        filter_prefix = out/'external-filter'
        run('filter-makeblastdb',[prefix/'bin/makeblastdb','-in',fasta,'-dbtype','nucl','-out',filter_prefix])
        run('filter-mash',[prefix/'bin/mash','sketch','-o',filter_prefix,fasta])
        external_filter = inspect('external-genome-filter',extra=['--genome_filter_db_prefix',str(filter_prefix)])
        assert any(str(filter_prefix)+'.nsq' == key for key in external_filter['blast_databases']['genome_filter_db_prefix']['members'])
        binary = Path(str(filter_prefix)+'.nsq')
        binary_stat, binary_bytes = binary.stat(),binary.read_bytes()
        with binary.open('r+b') as stream:
            stream.seek(4)
            stream.write(bytes([binary_bytes[4] ^ 1]))
        os.utime(binary,ns=(binary_stat.st_atime_ns,binary_stat.st_mtime_ns))
        inspect('external-volume-mutated',extra=['--genome_filter_db_prefix',str(filter_prefix)],expected=2,verify='external-genome-filter')
        binary.write_bytes(binary_bytes)
        inspect('external-volume-restored',extra=['--genome_filter_db_prefix',str(filter_prefix)],verify='external-genome-filter')
        Path(str(filter_prefix)+'.nal').write_text('DBLIST '+str(filter_prefix)+'\n')
        inspect('alias-refused',extra=['--genome_filter_db_prefix',str(filter_prefix)],expected=2)
        Path(str(filter_prefix)+'.nal').unlink()
        receipt['checks']['native_readsets'] = True
        save()

        config = out/'native.config'
        # No environment creation: use the exact retained executable prefix.
        config.write_text("process.executor='local'\nprocess.cpus=4\nprocess.memory='8 GB'\n"+
                          "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"+
                          "trace.fields='task_id,hash,name,status,exit,workdir'\n")
        status = private_db/'status.txt'
        status_bytes,status_stat = status.read_bytes(),status.stat()
        baseline_reports = None
        for guarded in [False,True]:
            session = None
            family = 'candidate' if guarded else 'current'
            phases = ['cold','unchanged','mutated','restored']
            for phase in phases:
                mutated = bytes([status_bytes[0] ^ 1])+status_bytes[1:]
                status.write_bytes(mutated if phase == 'mutated' else status_bytes)
                os.utime(status,ns=(status_stat.st_atime_ns,status_stat.st_mtime_ns))
                name = family+'-'+phase
                command = [nextflow,'-log',out/(name+'.nextflow.log'),'-C',config,'run',
                           ROOT/'tests/nextflow/mobsuite_runtime_resources.nf','--fasta',fasta,
                           '--probe',str(guarded).lower(),'-work-dir',out/(family+'-work'),
                           '-with-trace',out/(name+'.trace.tsv'),'-ansi-log','false']
                if session: command += ['-resume',session]
                run(name,command)
                if session is None:
                    log = (out/(name+'.nextflow.log')).read_text()
                    session = re.search(r'Session UUID: ([0-9a-f-]+)',log).group(1)
                with (out/(name+'.trace.tsv')).open() as stream:
                    rows = list(csv.DictReader(stream,delimiter='\t'))
                consumers = [row for row in rows if 'MOBSUITE_' in row['name']]
                expected = 'COMPLETED' if phase == 'cold' or (guarded and phase == 'mutated') else 'CACHED'
                assert len(consumers) == 2 and all(row['status'] == expected for row in consumers), rows
                probes = [row for row in rows if 'MOB_RESOURCE_AUDIT_PROBE' in row['name']]
                assert (len(probes)==2 and all(row['status']=='COMPLETED' for row in probes)) if guarded else not probes
                reports = {}
                for row in consumers:
                    work = Path(row['workdir'])
                    if 'TYPER' in row['name']:
                        reports['typer'] = (work/'typer-native.txt').read_bytes()
                    else:
                        reports['recon'] = (work/'results/mobtyper_results.txt').read_bytes()
                        reports['plasmid'] = (work/'results/plasmid_AA337.fasta').read_bytes()
                if baseline_reports is None:
                    baseline_reports = reports
                    typer_rows = list(csv.DictReader(reports['typer'].decode().splitlines(),delimiter='\t'))
                    assert len(typer_rows)==1 and typer_rows[0]['rep_type(s)']=='IncFIA,IncFIB,rep_cluster_2131'
                    assert typer_rows[0]['predicted_mobility']=='conjugative'
                    fasta_dna = ''.join(line.strip() for line in fasta.read_text().splitlines() if not line.startswith('>'))
                    result_dna = ''.join(line.strip() for line in reports['plasmid'].decode().splitlines() if not line.startswith('>'))
                    assert result_dna == fasta_dna
                else:
                    assert reports == baseline_reports, name
                receipt['cache_phases'].append(dict(name=name,session=session,trace=str(out/(name+'.trace.tsv')),
                    consumer_status=expected,probe_tasks=len(probes),output_sha256={key:hashlib.sha256(value).hexdigest() for key,value in reports.items()},
                    interpretation='known stale-cache reproduction' if not guarded and phase=='mutated' else 'expected experiment behavior'))
                save()
        receipt['checks']['audit_only_cache_experiment'] = True
        receipt['checks']['original_database_unchanged'] = original == {p.name:sha(p) for p in sorted(database.iterdir()) if p.is_file()}
        assert receipt['checks']['original_database_unchanged']
        receipt['status'] = 'passed_bounded_experiment_production_gap_open'
    except BaseException as error:
        receipt['status'] = 'failed'
        receipt['error'] = str(error)
        raise
    finally:
        receipt['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        save()


if __name__ == '__main__':
    main()
