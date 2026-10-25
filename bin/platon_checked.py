#!/usr/bin/env python3
"""Run fixed Platon1.7 with audited calls and four summary-log repairs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import difflib
import gzip
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1048576), b''): h.update(data)
    return h.hexdigest()


def fingerprint(directory):
    return {str(p.relative_to(directory)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
            for p in sorted(directory.rglob('*')) if p.is_file()}


def fasta(path):
    from Bio import SeqIO
    records = {}
    with Path(path).open() as stream:
        for record in SeqIO.parse(stream, 'fasta'):
            if record.id in records: raise ValueError('Duplicate FASTA ID: ' + record.id)
            if '/' in record.id or '\\' in record.id:
                raise ValueError('Platon uses contig IDs as filenames; path separators are unsupported: ' + record.id)
            if not len(record.seq): raise ValueError('Empty FASTA sequence: ' + record.id)
            records[record.id] = str(record.seq)
    return records


class ChildAudit:
    def __init__(self):
        self.commands = []
        self.futures = []
        self.original_run = subprocess.run

    @staticmethod
    def empty_annotation_query(command):
        # Platon calls these four HMM searches even when its RDS prefilter
        # leaves no proteins. Such a query provides no annotation evidence.
        if not command or Path(command[0]).name != 'hmmsearch': return False
        query = Path(command[-1])
        return query.name == 'proteins-filtered.faa' and query.is_file() and query.stat().st_size == 0

    def run(self, *args, **kwargs):
        raw = args[0] if args else kwargs.get('args')
        command = [str(v) for v in raw] if isinstance(raw, (list, tuple)) else [str(raw)]
        empty_query = self.empty_annotation_query(command)
        record = {'command': command, 'cwd': str(kwargs['cwd']) if kwargs.get('cwd') else None,
                  'empty_annotation_query': empty_query}
        self.commands.append(record)
        try:
            result = self.original_run(*args, **kwargs)
            record['exit_code'] = result.returncode
            if result.returncode:
                stderr = result.stderr
                if isinstance(stderr, bytes): stderr = stderr.decode(errors='replace')
                record['stderr'] = str(stderr or '')[-32768:]
            return result
        except BaseException as error:
            record['error'] = type(error).__name__ + ': ' + str(error)
            if isinstance(error, subprocess.CalledProcessError): record['exit_code'] = error.returncode
            raise

    def failures(self):
        children = [v for v in self.commands if ('error' in v or v.get('exit_code') != 0)
                    and not v['empty_annotation_query']]
        workers = []
        for future in self.futures:
            try:
                error = future.exception()
                if error is not None: workers.append(type(error).__name__ + ': ' + str(error))
            except BaseException as error:
                workers.append(type(error).__name__ + ': ' + str(error))
        return children, workers


def executor(audit):
    class AuditedExecutor(ThreadPoolExecutor):
        def submit(self, *args, **kwargs):
            future = super().submit(*args, **kwargs)
            audit.futures.append(future)
            return future
    return AuditedExecutor


def repair_no_hit_logging(program):
    """Repair four pinned summary log statements; no search/filter code changes."""
    module = program.pf
    source = Path(module.__file__).read_text()
    patched = source
    definitions = [('search_amr_genes', 'AMRs', 'AMRs', 'amr_hits'),
                   ('search_replication_genes', 'rep genes', 'rep-genes', 'replication_hits'),
                   ('search_mobilization_genes', 'mob genes', 'mob-genes', 'mobilization_hits'),
                   ('search_conjugation_genes', 'conj genes', 'conj-genes', 'conjugation_hits')]
    for _, label, count_label, key in definitions:
        old = "    log.info('%s: contig=%%s, # %s=%%s', contig['id'], len(contig['%s']))" % (label, count_label, key)
        if patched.count(old) != 1: raise ValueError('Unexpected fixed Platon summary log: ' + label)
        patched = patched.replace(old, "    log.info('%s: # hits=%%d', len(hits))" % label)
    namespace = {'__name__': 'platon_no_hit_logging_compat'}
    exec(compile(patched, 'platon_no_hit_logging_compat.py', 'exec'), namespace)
    for name, _, _, _ in definitions: setattr(module, name, namespace[name])
    return {'scope': 'four summary logging statements only; search commands, thresholds, hit parsing and classification unchanged',
            'original_sha256': hashlib.sha256(source.encode()).hexdigest(),
            'effective_sha256': hashlib.sha256(patched.encode()).hexdigest(),
            'diff': ''.join(difflib.unified_diff(source.splitlines(True), patched.splitlines(True),
                                              fromfile='original/functions.py', tofile='effective/functions.py'))}


def validate_outputs(prefix, records, eligible, header):
    table, plasmids, details = [Path(prefix + suffix) for suffix in ['.tsv', '.plasmid.fasta', '.json']]
    synthesized = False
    if not eligible:
        # Fixed upstream exits0 before creating products when every record is
        # outside its length domain. This is explicitly NOT an assessed negative.
        if any(p.exists() for p in [table, plasmids, details]):
            raise ValueError('Unexpected products for Platon all-length-filtered exit')
        table.write_text(header + '\n'); plasmids.write_text(''); details.write_text('{}')
        synthesized = True
    with table.open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if reader.fieldnames != header.split('\t'): raise ValueError('Unexpected Platon TSV schema')
        rows = list(reader)
    predicted = fasta(plasmids)
    with details.open() as stream: annotated = json.load(stream)
    ids = [v['ID'] for v in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(predicted) or set(ids) != set(annotated):
        raise ValueError('Platon TSV/FASTA/JSON IDs disagree or repeat')
    counts = {'# ORFs': 'orfs', 'Inc Type(s)': 'inc_types', '# Replication': 'replication_hits',
              '# Mobilization': 'mobilization_hits', '# OriT': 'orit_hits',
              '# Conjugation': 'conjugation_hits', '# AMRs': 'amr_hits',
              '# rRNAs': 'rrnas', '# Plasmid Hits': 'plasmid_hits'}
    for row in rows:
        cid = row['ID']; obj = annotated[cid]
        if cid not in eligible or predicted[cid] != records[cid] or obj['sequence'] != records[cid]:
            raise ValueError('Platon output DNA or eligible ID differs from source: ' + cid)
        if int(row['Length']) != len(records[cid]) or obj['length'] != len(records[cid]):
            raise ValueError('Platon output length differs from source: ' + cid)
        score = float(row['RDS'])
        if not math.isfinite(score) or score != float(f"{obj['protein_score']:3.1f}"):
            raise ValueError('Platon RDS TSV/JSON mismatch: ' + cid)
        if row['Circular'] != ('yes' if obj['is_circular'] else 'no'):
            raise ValueError('Platon circularity TSV/JSON mismatch: ' + cid)
        for column, key in counts.items():
            if int(row[column]) != len(obj[key]): raise ValueError('Platon annotation count mismatch: ' + column)
    if not synthesized:
        chromosomes = fasta(Path(prefix + '.chromosome.fasta'))
        if chromosomes != {k: v for k, v in records.items() if k not in predicted}:
            raise ValueError('Platon non-positive FASTA does not partition the original records')
    return {'state': 'not_assessed_length_filter' if synthesized else 'plasmids_found' if rows else 'no_plasmids',
            'input_contigs': len(records), 'eligible_contigs': len(eligible), 'plasmid_count': len(rows),
            'plasmid_ids': ids, 'not_assessed_ids': [k for k in records if k not in eligible],
            'compatibility_empty_products': synthesized,
            'interpretation': 'non-positive or length-filtered records are not independent chromosome identification'}


def run(args):
    if not args.prefix or Path(args.prefix).name != args.prefix or any(c in args.prefix for c in '\t\r\n'):
        raise ValueError('Platon prefix must be one filename component')
    if args.threads < 1: raise ValueError('Platon threads must be positive')
    if Path(args.record).exists(): raise ValueError('Platon runtime record already exists')
    metadata = {'sample_id': args.prefix, 'method': 'fixed Platon1.7 default accuracy + meta; four zero-hit summary logs repaired, scientific search/filter code unchanged',
                'commands': [], 'worker_errors': []}
    audit = ChildAudit()
    try:
        program = importlib.import_module('platon.platon')
        package = Path(program.__file__).parent
        installed = {p.name: sha(p) for p in package.glob('*.py')}
        if installed != SOURCE_SHA256: raise ValueError('Unsupported Platon source; expected fixed1.7 commit3cce2dd2')
        metadata['zero_hit_logging_repair'] = repair_no_hit_logging(program)
        constants = importlib.import_module('platon.constants')
        metadata.update(source_commit='3cce2dd295348e25be4b5bd64f3622c2603d6ba0', source_sha256=installed,
                        python_executable=sys.executable, python_version=sys.version)
        raw = Path(args.assembly).read_bytes()
        compressed = raw[:2] == b'\x1f\x8b' or str(args.assembly).lower().endswith('.gz')
        decoded = gzip.decompress(raw) if compressed else raw
        staged = Path('platon.input.fasta')
        if staged.exists(): raise ValueError('Platon normalized input already exists')
        staged.write_bytes(decoded)
        records = fasta(staged)
        if not records: raise ValueError('Platon input has no FASTA records')
        eligible = {k for k, v in records.items() if constants.MIN_CONTIG_LENGTH <= len(v) < constants.MAX_CONTIG_LENGTH}
        metadata.update(input_sha256=hashlib.sha256(raw).hexdigest(), decoded_input_sha256=hashlib.sha256(decoded).hexdigest(),
                        input_lengths={k: len(v) for k, v in records.items()},
                        database=fingerprint(Path(args.database)), eligible_ids=sorted(eligible), threads=args.threads)
        if not metadata['database']: raise ValueError('Platon database has no files')
        previous_argv = sys.argv
        previous_executor = program.ThreadPoolExecutor
        sys.argv = ['platon', '--meta', '--threads', str(args.threads), '--db', args.database,
                    '--output', '.', '--prefix', args.prefix, str(staged)]
        metadata['native_arguments'] = sys.argv[:]
        native_exit = 0
        try:
            subprocess.run = audit.run
            program.ThreadPoolExecutor = executor(audit)
            try: program.main()
            except SystemExit as error:
                native_exit = error.code if isinstance(error.code, int) else 0 if error.code is None else 1
                if error.code: metadata['native_exit_message'] = str(error.code)
        finally:
            subprocess.run = audit.original_run
            program.ThreadPoolExecutor = previous_executor
            sys.argv = previous_argv
        failed, workers = audit.failures()
        metadata.update(native_exit_code=native_exit, failed_children=failed, worker_errors=workers)
        if native_exit or failed or workers:
            raise ValueError('Platon analysis failed; native exit=%s, failed children=%d, failed workers=%d' % (native_exit, len(failed), len(workers)))
        state = validate_outputs(args.prefix, records, eligible, constants.HEADER)
        metadata['database_unchanged'] = metadata['database'] == fingerprint(Path(args.database))
        if not metadata['database_unchanged']: raise ValueError('Platon database changed during analysis')
        Path(args.prefix + '.platon_state.json').write_text(json.dumps({'sample_id': args.prefix, **state}, indent=2) + '\n')
        metadata['state'] = state
        return 0
    except BaseException as error:
        metadata['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        metadata['commands'] = audit.commands
        Path(args.record).write_text(json.dumps(metadata, indent=2) + '\n')


# Seven unchanged installed Python blobs from official v1.7.
SOURCE_SHA256 = {'__init__.py': 'a16912eb40daa3e4a477f70b4ad09c5a3831d24522073e35c9077c1ffc3ef17f', 'config.py': '08cafcd82ae82919486cfc0d16f4ce27f76bf8cc2cc911d258078c95b04180c3', 'constants.py': 'c50858a69de0692db5192773ee6e3ec29d618434aa33c8af6d1fb66d5f5af4ad', 'db.py': '7f866b114e9c2d953d706f51a2f0e05b37dbbdbf0592a72dc78b8d7855c38cc1', 'functions.py': '3e266e78b1c17e5565540c6195af494eaf9b481a1bd98dad451ab48b3f86c151', 'platon.py': '7bbc328b177f5348e1b136199794e471c61e0f69c44f13f1303c8e1d0866a250', 'utils.py': '6a63a6663fec73f164c0a4c8b40a04b40ec33444b3b9623ff87ada8d7419480c'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['assembly', 'database', 'prefix', 'record']: parser.add_argument('--' + flag, required=True)
    parser.add_argument('--threads', type=int, required=True)
    try: raise SystemExit(run(parser.parse_args()))
    except (ValueError, OSError, ImportError, KeyError) as error:
        print('Platon checked runtime: ' + str(error), file=sys.stderr); raise SystemExit(1)
