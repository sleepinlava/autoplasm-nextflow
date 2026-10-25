#!/usr/bin/env python3
"""Before/current native score-only contract; synthetic self-match is not host truth."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--before', type=Path, required=True)
    args = parser.parse_args()
    base = args.output.resolve(); base.mkdir(parents=True, exist_ok=False)
    rng = random.Random(390402026)
    dna = ''.join(rng.choices('ACGT', k=4000))
    fasta = base / 'plasmid.fa'; fasta.write_text('>self_math_control\n' + dna + '\n')
    mags = base / 'bins'; mags.mkdir()
    (mags / 'candidate.fna').write_text('>synthetic_chromosome\n' + dna + '\n')
    taxonomy = base / 'taxonomy.tsv'
    taxonomy.write_text('user_genome\tclassification\ncandidate\td__INTERFACE_MARKER\n')
    inputs = {str(p.relative_to(base)): sha(p) for p in [fasta, mags / 'candidate.fna', taxonomy]}
    sources = ['bin/sequence_similarity_link.R', 'modules/linking/sequence.nf',
               'subworkflows/host_linking.nf', 'tests/run_tetra_scores_only.py']
    hashes = {p: sha(ROOT / p) for p in sources}
    runs = []
    for name, old, cutoff in [('before', True, None), ('current', False, None),
                              ('legacy-zero', False, '0'), ('legacy-one', False, '1')]:
        folder = base / name; folder.mkdir()
        script = args.before.resolve() if old else ROOT / 'bin/sequence_similarity_link.R'
        cmd = ['Rscript', str(script), '--plasmid-contigs', str(fasta), '--host-genomes', str(mags),
               '--taxonomy', str(taxonomy), '--sample-id', 'A__B.v1', '--out', str(folder / 'links.tsv'),
               '--out-scores', str(folder / 'scores.tsv'), '--out-profile-status', str(folder / 'method.json')]
        if cutoff is not None: cmd += ['--min-similarity', cutoff]
        proc = subprocess.run(cmd, text=True, capture_output=True)
        (folder / 'stdout.log').write_text(proc.stdout); (folder / 'stderr.log').write_text(proc.stderr)
        assert proc.returncode == 0, proc.stderr
        scores = rows(folder / 'scores.tsv'); links = rows(folder / 'links.tsv')
        assert len(scores) == 1 and math.isclose(float(scores[0]['score']), 1, rel_tol=0, abs_tol=1e-12)
        assert scores[0]['sample_id'] == 'A__B.v1' and scores[0]['host_id'] == 'candidate'
        method = json.loads((folder / 'method.json').read_text())
        if old:
            assert len(links) == 1 and links[0]['evidence_type'] == 'sequence_similarity'
        else:
            assert scores[0]['score'] == runs[0]['scores'][0]['score'], 'Composition score changed'
            assert not links
            assert scores[0]['host_taxonomy'] == 'd__INTERFACE_MARKER'
            assert scores[0]['association_status'] == 'disabled_uncalibrated'
            assert 'threshold_pass' not in scores[0] and 'threshold' not in scores[0]
            assert method['host_links_enabled'] is False
            assert method['threshold_status'] == 'not_applied_uncalibrated'
            if cutoff is not None: assert 'deprecated and ignored' in proc.stderr
        runs.append({'case': name, 'command': cmd, 'exit_code': proc.returncode,
                     'scores': scores, 'links': links, 'method': method})
    assert inputs == {str(p.relative_to(base)): sha(p) for p in [fasta, mags / 'candidate.fna', taxonomy]}
    assert hashes == {p: sha(ROOT / p) for p in sources}
    payload = {'pass': True, 'runs': runs, 'source_sha256': hashes, 'inputs_sha256': inputs,
               'before_sha256': sha(args.before.resolve()),
               'limitations': ['Synthetic full-rank self-match is an exact mathematical control, not a known host assignment or host accuracy benchmark.',
                               'Score-only suppression is intentional after failed independent threshold acceptance; no scientific threshold is claimed valid.']}
    (base / 'run.json').write_text(json.dumps(payload, indent=2) + '\n')
    print('PASS: unchanged self-match score1; original link removed; legacy cutoffs0/1 cannot enable links')


if __name__ == '__main__':
    main()
