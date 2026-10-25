#!/usr/bin/env python3
"""Execute fixed gplas with checked children and explicit final-product checks."""
import argparse
import csv
import difflib
import hashlib
import json
import math
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_nodes(graph):
    nodes = {}
    for line in Path(graph).read_text().splitlines():
        fields = line.split('\t')
        if fields[0] != 'S':
            continue
        if len(fields) < 4 or fields[1] in nodes or not re.fullmatch(r'[0-9]+', fields[1]):
            raise ValueError('Invalid or duplicate native GFA segment')
        dna = fields[2]
        if not re.fullmatch(r'[ACGTRYSWKMBDHVNacgtryswkmbdhvn]+', dna):
            raise ValueError('Native GFA must contain explicit DNA')
        header = 'S%s_%s_%s' % (fields[1], fields[3], fields[4] if len(fields) > 4 else '')
        nodes[fields[1]] = {'header': header, 'dna': dna.upper()}
    if not nodes:
        raise ValueError('Native GFA has no segments')
    return nodes


def fasta(path):
    result, name, sequence = {}, None, []
    for line in Path(path).read_text().splitlines():
        if line.startswith('>'):
            if name is not None:
                result[name] = ''.join(sequence).upper()
            name = line[1:]
            if not name or name in result:
                raise ValueError('Empty or repeated bin FASTA ID')
            sequence = []
        elif line.strip():
            if name is None:
                raise ValueError('Bin FASTA DNA precedes its header')
            sequence.append(line.strip())
    if name is not None:
        if name in result:
            raise ValueError('Repeated bin FASTA ID')
        result[name] = ''.join(sequence).upper()
    return result


def table(path, header):
    lines = Path(path).read_text().splitlines()
    actual_header = shlex.split(lines[0]) if lines else []
    if len(actual_header) != len(header) or set(actual_header) != set(header):
        raise ValueError('Unexpected native gplas table schema: ' + str(path))
    rows = []
    for line in lines[1:]:
        fields = shlex.split(line)
        if len(fields) != len(header):
            raise ValueError('Malformed native gplas row')
        rows.append(dict(zip(actual_header, fields)))
    return rows


def validate_products(graph, directory, name):
    nodes = native_nodes(graph)
    directory = Path(directory)
    rows = table(directory / (name + '_results.tab'),
                 ['number', 'Contig_name', 'Prob_Chromosome', 'Prob_Plasmid', 'Prediction', 'length', 'coverage', 'Bin'])
    membership = table(directory / (name + '_bins.tab'), ['number', 'Bin'])
    expected, keys = {}, set()
    for row in rows:
        node, group = row['number'], row['Bin']
        if node not in nodes or not re.fullmatch(r'(?:[1-9][0-9]*|Isolated_[1-9][0-9]*|Unbinned|Repeat_like)', group):
            raise ValueError('Unknown graph node or bin in final results')
        if (node, group) in keys:
            raise ValueError('Duplicate final node/bin membership')
        keys.add((node, group))
        original = nodes[node]
        if row['Contig_name'] != original['header'] or row['length'] != str(len(original['dna'])):
            raise ValueError('Final result identity or length differs from GFA')
        for column in ['Prob_Chromosome', 'Prob_Plasmid', 'coverage']:
            value = float(row[column])
            if not math.isfinite(value) or value < 0 or (column != 'coverage' and value > 1):
                raise ValueError('Nonfinite or out-of-domain final score: ' + column)
        if row['Prediction'] not in ['Plasmid', 'Repeat']:
            raise ValueError('Unexpected gplas output classification')
        expected.setdefault(group, {})[original['header']] = original['dna']
    actual_keys = [(row['number'], row['Bin']) for row in membership]
    if len(actual_keys) != len(set(actual_keys)) or set(actual_keys) != keys:
        raise ValueError('Final results and bin membership disagree')
    products = {}
    for group, sequences in expected.items():
        path = directory / (name + '_bin_' + group + '.fasta')
        if fasta(path) != sequences:
            raise ValueError('Final bin FASTA DNA or membership differs from GFA/results')
        products[path.name] = sha(path)
    actual_names = {p.name for p in directory.glob(name + '_bin_*.fasta')}
    if actual_names != set(products):
        raise ValueError('Unexpected final bin FASTA files')
    if not rows:
        raise ValueError('Native gplas returned no final membership despite plasmid seeds')
    resolved = [group for group in expected if group not in ['Unbinned', 'Repeat_like']]
    return {'state': 'bins_found' if resolved else 'unresolved_nodes_only', 'memberships': len(keys), 'bins': len(resolved),
            'connected_components': sum(group.isdecimal() for group in expected),
            'isolated_candidates': sum(group.startswith('Isolated_') for group in expected),
            'unbinned_memberships': sum(group == 'Unbinned' for node, group in keys),
            'repeat_like_memberships': sum(group == 'Repeat_like' for node, group in keys),
            'overlapping_repeat_nodes_allowed': True, 'final_fasta_sha256': products,
            'results_sha256': sha(directory / (name + '_results.tab')),
            'membership_sha256': sha(directory / (name + '_bins.tab'))}


def repaired_source(text):
    patched = text
    for suffix in ['results', 'bins']:
        old = 'shutil.move("results/{args.name}_' + suffix + '_no_repeats.tab", "results/{args.name}_' + suffix + '.tab")'
        new = 'shutil.move(f"results/{args.name}_' + suffix + '_no_repeats.tab", f"results/{args.name}_' + suffix + '.tab")'
        if patched.count(old) != 1:
            raise ValueError('Unexpected fixed gplas no-repeat move statement')
        patched = patched.replace(old, new)
    return patched


def stage_input(source, name):
    target = Path(name)
    if target.exists():
        if target.samefile(source):
            return
        raise ValueError('Native gplas local input name already exists: ' + name)
    shutil.copyfile(source, target)


def effective_source(root):
    """Use a private copy: explicit headers also parse zero-row repeat tables."""
    target = Path('effective-source').resolve()
    if target.exists():
        raise ValueError('Effective gplas source directory already exists')
    changes = []
    readers = {'gplas/scripts/' + name + '.R' for name in
               ['gplas_paths', 'gplas_paths_bold', 'gplas_coocurrence', 'gplas_coocurrence_final']}
    for key in SOURCE_SHA256:
        path = target / key
        path.parent.mkdir(parents=True, exist_ok=True)
        original = (root / key).read_bytes()
        data = original
        if key == 'gplas/gplas.py':
            data = repaired_source(original.decode()).encode()
        elif key in readers:
            old = 'repeats_graph <- read.table(file = path_graph_repeats)'
            text = original.decode()
            if text.count(old) != 1:
                raise ValueError('Unexpected fixed repeat-table reader: ' + key)
            data = text.replace(old, old[:-1] + ', header = TRUE)').encode()
        path.write_bytes(data)
        if data != original:
            changes.append({'path': key, 'original_sha256': hashlib.sha256(original).hexdigest(),
                            'effective_sha256': sha(path),
                            'diff': ''.join(difflib.unified_diff(original.decode().splitlines(True), data.decode().splitlines(True),
                                                              fromfile='original/' + key, tofile='effective/' + key))})
    return target, changes


def run(args):
    record = {'source_commit': '00cf37bec5e44b05ee30c8a4c99e987abbbb4c4f', 'children': [],
              'scope': 'checked subprocess exits; two filename interpolations and four repeat-table header reads repaired; algorithms/defaults unchanged'}
    original_run, original_argv = subprocess.run, sys.argv
    try:
        root = Path(args.source).resolve()
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', args.name) or args.name in ['.', '..']:
            raise ValueError('Unsafe native gplas output name')
        if any(ch.isspace() for ch in str(root) + str(Path.cwd())):
            raise ValueError('Fixed gplas shell commands require source/work paths without whitespace')
        actual = {key: sha(root / key) for key in SOURCE_SHA256}
        if actual != SOURCE_SHA256:
            raise ValueError('Unsupported gplas source or generated version file')
        if Path('results').exists() or Path('gplas_input').exists():
            raise ValueError('Native gplas requires a fresh working directory')
        graph = Path(args.graph).resolve()
        predictions = Path(args.predictions).resolve()
        nodes = native_nodes(graph)
        with predictions.open(newline='') as stream:
            reader = csv.DictReader(stream, delimiter='\t')
            if reader.fieldnames != ['Prob_Chromosome', 'Prob_Plasmid', 'Prediction', 'Contig_name', 'Contig_length']:
                raise ValueError('Expected typed graph-node prediction table')
            calls = list(reader)
        if not any(v['Prediction'] == 'Plasmid' for v in calls):
            raise ValueError('No plasmid seeds: use the explicit pre-analysis state, not native gplas')
        # Fixed local names also keep user paths out of upstream shell strings.
        stage_input(graph, 'input.gfa')
        stage_input(predictions, 'input.prediction.tab')
        effective, changes = effective_source(root)
        source = effective / 'gplas/gplas.py'
        patched = source.read_text()
        record.update(source_sha256=actual, graph_sha256=sha(graph), predictions_sha256=sha(predictions),
                      source_repairs=changes)
        def checked(*pos, **kw):
            command = pos[0] if pos else kw.get('args')
            child = {'command': command}
            record['children'].append(child)
            result = original_run(*pos, **kw)
            child['exit_code'] = result.returncode
            if result.returncode:
                raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)
            return result
        sys.path.insert(0, str(effective))
        sys.argv = ['gplas', '-i', 'input.gfa', '-c', 'predict', '-n', args.name,
                    '-P', 'input.prediction.tab', '-k']
        record['native_argv'] = sys.argv[:]
        subprocess.run = checked
        try:
            exec(compile(patched, str(source), 'exec'), {'__file__': str(source), '__name__': 'gplas.gplas', '__package__': 'gplas'})
        except SystemExit as error:
            record['native_exit_code'] = error.code
            if error.code not in [None, 0]:
                raise
        finally:
            subprocess.run = original_run
            sys.argv = original_argv
        raw = fasta(Path('gplas_input') / (args.name + '_raw_nodes.fasta'))
        if raw != {v['header']: v['dna'] for v in nodes.values()}:
            raise ValueError('Native extraction differs from input graph nodes')
        calibration = table(Path('coverage') / (args.name + '_estimation.txt'), ['x'])
        if len(calibration) != 1:
            raise ValueError('Expected one native coverage-variation estimate')
        spread = float(calibration[0]['x'])
        if not math.isfinite(spread) or spread <= 0:
            raise ValueError('Native coverage variation is unassessed or zero; no calibrated graph reconstruction')
        record['coverage_standard_deviation'] = spread
        record['products'] = validate_products(graph, 'results', args.name)
        if {key: sha(root / key) for key in SOURCE_SHA256} != actual:
            raise ValueError('Native gplas modified its source files')
        return 0
    except BaseException as error:
        record['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        subprocess.run = original_run
        sys.argv = original_argv
        Path(args.record).write_text(json.dumps(record, indent=2) + '\n')


# Fixed archive blobs plus its independently generated SCM version file.
SOURCE_SHA256 = {'.gitignore': '1887af9c0de504316526962d54e29c5cdc88ebfc33f1312d80435b9b7fd193e9', 'LICENSE': 'f7b0c116c798a2682bf37c345f6ee38ef8843d3cf02b1744a767c8a1f034c0e3', 'README.md': '3f33e86a0d5c14b02500b35e7bd2351036d731ab453a9f9eada2344c7cac5187', 'checklist.md': 'a5f86176f623d0a5d418942928837e18e92211ad16f431a8c42aa3fdd88fff90', 'citation.cff': '311b64a8faca73afb17a19559d13cfa7250334c76b65db0d8f4e3ed5b7acf96b', 'envs/gplas.yaml': '07dd4e306bf640971b5acdf54f38c1d5553a80134abc7adb6b100184293cd00c', 'envs/plasflow.yaml': '33af0f667093765cc95895073765f4d06a584503d5d19730d24c041c7f84c832', 'envs/requirements.txt': 'df0692aa6f7b52c59ad137fc434bc46e40dca6da0e6db768b447b19c2331480c', 'envs/spec-snakemake.txt': '48d9d9b7f58fb35331c2f465135219bd78bb1e5dd886c2fd0fd95c1d059f848a', 'figures/bandage_path.jpg': 'de8a7ecd47f8cdfe5dc09da9bbcc7e10b7abf79d7719d5811093747a186cf9bc', 'figures/logo.png': '0ded69c7b6f3db44c97fd066868cf4b536ad5071b54f1812f1ae2fae4cd74634', 'figures/logo.txt': '3da6c8d2f2414b1ed678110ea85566c0737025670916450c33ec50c013586ea6', 'figures/my_isolate_plasmidome_network.png': '722f15c4db868c72829203a26c68cb053f9e582756871de296190f2dfacb3aa1', 'gplas/.gitkeep': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'gplas/envs/plasflow.yaml': '6130d669bb1bfba6512fa879b3d8814ee77ffa08f3db49e387e8ffe0991ec204', 'gplas/envs/quast.yaml': '5ced15314151bedd34d87e51d95e8e81b9b80c0aa6947882285652782622b07f', 'gplas/envs/r_packages.yaml': '6a0eca23e5c44121bb884500d79f02ee5ad2b6cf140e28762faca3bdfc251796', 'gplas/envs/snakemake.yaml': 'c8f6c801bd89cf558e3553ed853b817570f6c4a80b14be56599ec9badbdd2f17', 'gplas/figures/bandage_path.jpg': '09d3dfa0a401c7a463ae7fa073f9bfcb28d3eae1866767adb7666b99f72536f2', 'gplas/figures/logo.png': '3832c5294ac5bcede38c7c970ba40735042900fc9d28340728fc3bc81d95963a', 'gplas/figures/logo.txt': '3da6c8d2f2414b1ed678110ea85566c0737025670916450c33ec50c013586ea6', 'gplas/figures/my_isolate_plasmidome_network.png': 'a670cc339fc12346ff5806a0ce7c4f555cc196f568290f594129449e0465d01b', 'gplas/gplas.py': '54d43047fd578098fca3a8d75f1f5b60679713113547f7630502fbbc9df8cbd8', 'gplas/independent_prediction/test_ecoli_plasmid_prediction.tab': '6b216097e52c4a23789d9fb5457407eaab84f37b04230ce5c7e11d7b69753846', 'gplas/scripts/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'gplas/scripts/check_independent_prediction_format.R': 'dc4ca99748fe912570eca97aa46a0841e49ce17a17820d89c5619f735e0d08e4', 'gplas/scripts/gplas_coocurrence.R': '664086c79e4be43035f7c9da66db552974827c7ffd4931f93e2504d8b069a708', 'gplas/scripts/gplas_coocurrence_final.R': '62bc873af98bced9e6bd9393afe9ec234025d9864f4bf2d6344d0632b14546d5', 'gplas/scripts/gplas_coocurrence_repeats.R': '51afbd53a8fb03151ff05a1e9cabb75ab17fc6fb1a97b1a070dc5c484830e564', 'gplas/scripts/gplas_coverage.R': '568bc745e7fa4f67477f06f9cbacc94a2bbbf6d7709b4037568c0adc5bbb3b8e', 'gplas/scripts/gplas_evaluation.R': '3149d99b8cbdc831edff45501e039b9a199c4cfff884b94c93ea05fba096291a', 'gplas/scripts/gplas_paths.R': '8da1ee8378e35536c8b911c65bd8048a83e6fb4d54a0ed730df607bb78787e0f', 'gplas/scripts/gplas_paths_bold.R': '73223e677aeb2123b700668ce052716a9bbd370446f0f349051935bc6aa0a814', 'gplas/scripts/gplas_paths_repeats.R': '6a545ad32babd76ff8add003f9f4fd22dc242f937e6034dedfa5cccd574e335e', 'gplas/scripts/remove_intermediate_files.sh': '78a028308a00198013a8b785cd0897d01364c79721331bf71d6d0a97254d55e9', 'gplas/snakefiles/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'gplas/snakefiles/mlplasmidssnake.smk': '36685c753e06287170e4946c6bdc910a335b0169d79d651505e18032d1e4aa57', 'gplas/snakefiles/mlplasmidssnake.smk~': 'a17e29e798e4094733e5c3e3e353521ba7e3f1d80046b787ef0ab4fd131b0240', 'gplas/snakefiles/otherclassifiers.smk': '037003fde6086c788893949e7730ac93ad3273e92691a807ac78514c02234a6d', 'gplas/snakefiles/plasflowsnake.smk': '337ed2c1aebbd45a5fdd18b7c2358003ff4353b4379df2efd6c0ee69f17e44dc', 'setup.py': 'b4f3675edcb37f5b04e3d8d648e3f9e648a54f61c6868c794f09535c9cfb71c2', 'test/abaumannii_graph.gfa': '153d3deecd0a6141448b258b9be567f5570316dbef8c91c439d6639da6a59c8e', 'test/faecium_graph.gfa': '6f567269bf0e517526beb7e3f2463cd5cdb0b376d4b706dbb06e73ec67bb6064', 'test/faecium_reference.fasta': '17cc9cd7a76f59e4969784dccbc21fcf4c6e326c4e32ac198b7b10f3defa9434', 'test/test_ecoli.gfa': '4c25a91f80de04bc6fca57d0ce11631b9c73ef8779cd95c4aaac5f6875d5f126', 'gplas/version.py': 'cb250eef19b07c62b18de8a7d405b6b29c4bea0def1cd5e1fc9c0f087172e4c4'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['source', 'graph', 'predictions', 'name', 'record']:
        parser.add_argument('--' + key, required=True)
    run(parser.parse_args())
