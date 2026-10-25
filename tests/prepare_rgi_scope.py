#!/usr/bin/env python3
"""Prepare locked full CARD fixtures for native RGI scope tests, without downloading data."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile

LOCK = Path(__file__).with_name('rgi-database-scope.lock.json')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(output, prefix, archives, plasmid):
    lock = json.loads(LOCK.read_text())
    for version, archive in archives.items():
        if sha(archive) != lock['archives'][version]['sha256']:
            raise ValueError('CARD archive checksum mismatch: ' + str(archive))
    if sha(plasmid) != lock['plasmid']['sha256']:
        raise ValueError('Plasmid fixture checksum mismatch: ' + str(plasmid))
    output.mkdir(parents=True)  # Never overwrite an earlier test preparation.
    env = os.environ.copy()
    env['PATH'] = str(prefix / 'bin') + ':' + env['PATH']
    env['MPLCONFIGDIR'] = str(output / 'mpl')
    commands = []

    def run(name, command, cwd, environment=env):
        result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True)
        (output / (name + '.stdout.log')).write_text(result.stdout)
        (output / (name + '.stderr.log')).write_text(result.stderr)
        commands.append({'name': name, 'command': command, 'cwd': str(cwd), 'exit': result.returncode})
        if result.returncode:
            raise RuntimeError(name + ' failed; see retained logs at ' + str(output))
        return result.stdout.strip()

    if run('version', ['rgi', 'main', '--version'], output) != lock['tool_version']:
        raise ValueError('Native RGI version does not match the test lock')
    data = {}
    for version, archive in archives.items():
        path = output / ('card-' + version)
        path.mkdir()
        with tarfile.open(archive) as bundle:
            # Read only card.json; never extract arbitrary archive paths.
            member = next(m for m in bundle.getmembers() if m.name.lstrip('./') == 'card.json')
            raw = bundle.extractfile(member).read()
        data[version] = json.loads(raw)
        if data[version]['_version'] != version:
            raise ValueError('Unexpected internal CARD version')
        (path / 'card.json').write_bytes(raw)
        run('annotation-' + version, ['rgi', 'card_annotation', '-i', 'card.json'], path)
    model = lock['new_model_id']
    if model in data['3.2.8']:
        raise ValueError('Counterfactual model unexpectedly exists in old CARD')
    record = data['3.3.0'][model]
    if record['ARO_name'] != lock['new_model_name']:
        raise ValueError('Model name no longer matches the lock')
    sequences = record['model_sequences']['sequence'][lock['new_sequence_id']]
    (output / 'VIM77.fasta').write_text('>VIM77_reference\n' + sequences['dna_sequence']['sequence'] + '\n')
    (output / 'VIM77.protein.fasta').write_text('>VIM77_reference\n' + sequences['protein_sequence']['sequence'] + '\n')
    shutil.copyfile(plasmid, output / 'NC_020818.1.fasta')
    global_dir = output / 'global-3.2.8'
    global_dir.mkdir()
    global_env = env.copy()
    global_env.update(DB_PATH=str(global_dir), DATA_PATH=str(global_dir))
    old = output / 'card-3.2.8'
    run('global-load', ['rgi', 'load', '--card_json', str(old / 'card.json'),
                        '--card_annotation', str(old / 'card_database_v3.2.8.fasta'),
                        '--card_annotation_all_models', str(old / 'card_database_v3.2.8_all.fasta')], global_dir, global_env)
    # Build a real, usable global index rather than an invalid dummy database.
    run('global-query', ['rgi', 'main', '--input_type', 'protein', '--input_sequence', str(output / 'VIM77.protein.fasta'),
                         '--output_file', str(output / 'global-control'), '--threads', '1'], output, global_env)
    receipt = {'commands': commands, 'lock_sha256': sha(LOCK),
               'fixture_sha256': {str(p.relative_to(output)): sha(p) for p in output.rglob('*') if p.is_file() and p.suffix in ['.json', '.fasta']},
               'limitations': ['exact reference/database identity controls, not AMR performance or clinical truth']}
    (output / 'preparation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--card-330-archive', type=Path, required=True)
    parser.add_argument('--card-328-archive', type=Path, required=True)
    parser.add_argument('--plasmid-fasta', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.output_dir.resolve(), args.prefix.resolve(),
            {'3.3.0': args.card_330_archive.resolve(), '3.2.8': args.card_328_archive.resolve()}, args.plasmid_fasta.resolve())
