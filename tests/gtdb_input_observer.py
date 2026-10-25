#!/usr/bin/env python3
"""Input-only observer: real installed GTDB parser/selector, no taxonomy model.

The caller supplies a tiny, explicitly fake reference-name fixture. Construction
of OptionsParser and the classification workflow are intentionally not run.
Summary classifications below are observer markers, never biological results.
"""
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys


def main():
    if sys.argv[1:] == ['--version']:
        return subprocess.run([str(Path(sys.executable).with_name('gtdbtk')), '--version']).returncode
    from gtdbtk.cli import get_main_parser
    from gtdbtk.main import OptionsParser
    from gtdbtk.biolib_lite.seq_io import read_fasta
    import gtdbtk
    import gtdbtk.cli
    import gtdbtk.main
    assert gtdbtk.__version__ == '2.7.2'
    args = get_main_parser().parse_args(sys.argv[1:])
    assert args.subparser_name == 'classify_wf'
    print('NATIVE_GTDB_SELECTION_REACHED', flush=True)
    selector = object.__new__(OptionsParser)
    selector.logger = logging.getLogger('timestamp')
    selector.warnings = logging.getLogger('warnings')
    genomes, tables = selector._genomes_to_process(args.genome_dir, args.batchfile, args.extension)
    if os.environ.get('GTDB_INPUT_OBSERVER_FAIL') == '1':
        raise RuntimeError('EXPLICIT_GTDB_INPUT_OBSERVER_FAILURE')
    out = Path(args.out_dir);(out/'classify').mkdir(parents=True)
    rows = []
    for genome_id, filename in sorted(genomes.items()):
        records = read_fasta(filename)
        rows.append({'genome_id':genome_id,'selected_path':filename,
            'file_sha256':hashlib.sha256(Path(filename).read_bytes()).hexdigest(),
            'records':{name:{'length':len(dna),'DNA_sha256':hashlib.sha256(dna.encode()).hexdigest()} for name,dna in records.items()}})
    result={'scope':'REAL_PARSER_AND_GENOME_SELECTION_ONLY;NO_TAXONOMY_MODEL',
        'version':gtdbtk.__version__,'extension':args.extension,'genome_dir':args.genome_dir,
        'genomes':rows,'reference_names':'EXPLICIT_INTERFACE_FIXTURE_NOT_A_GTDATABASE',
        'initialization':'OptionsParser.__init__ bypassed; no data-package compatibility or classification run',
        'installed_source_sha256':{name:hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for name,module in [('gtdbtk.cli',gtdbtk.cli),('gtdbtk.main',gtdbtk.main)]}}
    (out/'input_selection.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'classify'/f'{args.prefix}.bac120.summary.tsv').write_text('user_genome\tclassification\n'+''.join(row['genome_id']+'\tINTERFACE_OBSERVER_NOT_TAXONOMY\n' for row in rows))
    (out/'gtdbtk.log').write_text('REAL_INPUT_SELECTION_ONLY; NO_CLASSIFICATION\n')
    (out/'gtdbtk.warnings.log').write_text('FAKE_REFERENCE_NAME_FIXTURE; NO_CLASSIFICATION\n')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        print(f'GTDB input observer: {type(error).__name__}: {error}',file=sys.stderr)
        raise SystemExit(2)
