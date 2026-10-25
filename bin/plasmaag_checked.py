#!/usr/bin/env python3
"""Run the fixed PlasMAAG CLI while propagating its external child failures.

This guard does not certify the identity or biological meaning of products.
The workflow adapter must validate them separately before publishing results.
"""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import time

COMMIT = 'a6b39ac6e8e38ccc8419fc7b4a3f304b0f511803'
SOURCE_SHA256 = {'.git-blame-ignore-revs': '4836f21dd7e23fcefc2570803752c50edd3385fca3fd4f3d4d55a843f361b280', '.github/ISSUE_TEMPLATE.md': 'fab7fbace003f4b7e135fd6ea5321f64b8982a9c93b8f17070281dd4d1576ba1', '.github/workflows/cli_vamb.yml': '982b73c831277a59d9048fd16d53b2fe924bedfecfa3614734244054b6570c74', '.github/workflows/lint.yml': 'bc20136d753c1a0d2970c6d98bc5c5c8a87aef0c7f1783b9be866d44d5451645', '.github/workflows/snakemake_avamb.yml': '3c6c7e78973f0359330985f8dff12e48b76ea4c8104b06cc850737c3368857d5', '.github/workflows/unittest.yml': '70018181fb587e76bc93ec249a4c8ba88cb3be9aaabbc01dffb56c456c76abd7', '.gitignore': 'b9eae583d1ec2eeb83ca8196885594b1cd434bd612320687cc46dd21e79cf8da', '.readthedocs.yaml': '9b5d27141e91562e9abe01d81355d2d778eea983ec65b51784e6e6a275c6459b', 'CONTRIBUTING.md': '2cc7f879e75fb7e583b934c5ad4c81ae8e37ef75b55ff605557bf7c0ba8cadd0', 'LICENSE': 'ead0081181786d206f0d31b4f541a26ca707c8c765d152ddc99119081a1e48e4', 'MANIFEST.in': '03b0d2662e510d1ae86cb4cef8e053cd2ed61a8f4c1f52836ad69936e95a7562', 'PlasMAAG/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'PlasMAAG/__main__.py': '89cca0594e8b4cadf47c92807641472bc837e35fea0b9825fb2b18d110339f6f', 'PlasMAAG/click_file_types.py': 'e4b9699e14d33d5a7f9435510d748e527f4c6e019c53305c7d82a8c97d6203ed', 'PlasMAAG/command_line_runners.py': '84668d75411713c7376895fdb8b233d87be260bc61f4ad97243a0f2220d0ab62', 'PlasMAAG/environment.py': '3c13114d8a876f1df27ad194d30f9ccc765171724f1a9f01eafae7ac96af3389', 'PlasMAAG/richclick_options.py': '2a4156a62f09593fb82ebcd86a0a0f21746d329071f38493c419971ec1d580ae', 'README.md': '9a51d243c431d894d4e0d7dc688c05754e25d041dcd8d776c3a81dec3d1e9cf9', 'config/config.yaml': '4126075e5d8fcdd0ea3d8e9b9d0caf173a3e34edd2f71d73c036ec765c09a855', 'envs/PlasMAAG.yaml': '961eea8b92819850df4925f8ab620cd7977896deff11ddea4dd0cf99db2676e7', 'envs/genomad.yaml': 'ef6db79400746eefff6a4b88f947c92b2d35db87fdac1c1c1524bef97ba3f2c3', 'envs/node2vec.yaml': '59af7b1812a8e97d7271ca31053ae574a43f2d47a6d605790fd64f315be13437', 'envs/spades_env.yaml': '19bdf9109a1fc5787fff1aa649d6aa08573b3254b004a507afa774a99baf6dc7', 'envs/strobe_env.yaml': '31947db03f796f4341f2a47f4fa3f277b407dd54118711e6f9a91e943fdb905d', 'files_used_in_snakemake_workflow/circularisation.py': '4704d6100c2e13c0ea84b8f124d037a22dcf940c3d07f9bef38a652c65a34be9', 'files_used_in_snakemake_workflow/classify_bins_with_geNomad.py': '4ffbf07a37c83771545270f964df7913e037366c618bf4026a82eb8510b8c995', 'files_used_in_snakemake_workflow/classify_bins_with_geNomad_vir.py': '632a964447d4c319eec2fdbce914b3d3cfd8fe7caaf889d8bd948b3596915555', 'files_used_in_snakemake_workflow/concatenate.py': 'e0139bc3fae51c830ba4bf8ad21d2ad1f2f3d1a9a9f3ef29b3100bfb59c7efc4', 'files_used_in_snakemake_workflow/embeddings_to_neighs.py': '36a092c308aedd8655b148a94b56e5f3cae95f04f9e799ae404395e226ab9271', 'files_used_in_snakemake_workflow/fastnode2vec_args.py': '94b3b285ac3b25fbb21de84dcc80b3ca2464d2272b18efef7850c4ecdbfd7f44', 'files_used_in_snakemake_workflow/git_commit.py': 'b55d8b73ad8fd06692fdf82d0105720f04310aef04c6b8e50ff01938a06c90cb', 'files_used_in_snakemake_workflow/merge_assembly_alignment_graphs.py': 'bb2d516a73a64a6adb463bc8131e075256c44bfb0d85f1aa398c766f66242e1d', 'files_used_in_snakemake_workflow/merge_circular_plamb_clusters.py': '5118a6c97f614a575d8f61130c2576dbe2b646bfeed048ea0fba6f414a036b24', 'files_used_in_snakemake_workflow/process_blastout.py': '441c9453cd16a6c9a7ee051b583fb04c7328dafcc928b853e18373540159f64f', 'files_used_in_snakemake_workflow/process_gfa.py': 'c2968c487c4a540c6c54a9306cbf43dc69f842e2b93c707e64a15a57dd7c486b', 'files_used_in_snakemake_workflow/write_candidate_bins.py': '810c887a3d16ee5f86c937aa3efc43fc3b76983d2a021e5ea1c8fce9821296ab', 'files_used_in_snakemake_workflow/write_candidate_bins_virus.py': '61dc8b01e1532ecb5dfe4b7f3903c0e61e2748037b55a1556da8434367ef4dc3', 'pyproject.toml': 'e98ac16f6d022493b49b52b069d9b50c161d1d46fee7955632e32f6fdbc67544', 'reproducibility.md': 'e56e064e415de66d00a4588de8ea0921cee2f2899d70d75e12ac4ac51f7180a0', 'setup.cfg': '495a93232f65d12bf0f7e99ba064c88c409a8eba1f8d81b0d8cf199df17ab5d0', 'setup.py': 'b70473c60ddfc7954a0f90f7483f883bfcbd9cbccec805dfd84a23eda9a8938b', 'snakefile.smk': 'efdd98d38e39c5eb6575cc2f8423d6e7b8fbd8947abb5f45537ce130bcfa3152', 'snakefile_map_reads_to_contigs.smk': '8cdeb676ba4132e03a31b256d49f06ea60b03a3d830c16c9912a004f75e6ab31', 'snakefile_megahit.smk': '982d5ec9fb23c4f1b884b74c0678dcd3a87a0856c0401c2198c24dbc34935f04', 'src/_vambtools.pyx': 'cfca5ae68ae9d7a4de692d2709572e377eecd251953969ca7db217f83cb491e6', 'src/concatenate.py': '855d07d4610d21d03259fae5bcafd86140661e84d75e1fd2b1a3e2b16ca7dff5', 'src/create_fasta.py': '8ff26fafa8b2b90d4737b8f8bdc140f11a47fd75b76a798bef325c73e1864b5a', 'src/create_kernel.py': '9ef62aa7066ee959ce57d938cb8a69aa40200fc9aa8f628368e4d21b3e223b9f', 'test/data/aemb/6.aemb.tsv': '9e3a00c801919e08839d2a24b16c1d0ba76d4aeec482c49f44c3be01e823ba78', 'test/data/aemb/7.aemb.tsv': '1842cea6ea46bb825c8ad75ebab9ae273de908616ad4984e7b3a452697d6d02a', 'test/data/aemb/8.aemb.tsv': '534f98561ab20d26f227c9a038b28efced00a7abb9400c793f2b673255da4534', 'test/data/bam/10.bam': '37a147c0d69a2584930a3b97e1957bde73000887529201ad573f0b5a69df6753', 'test/data/bam/11.bam': 'b5f40ebc2e6b04e277784bc5003d5e6731d4ac247c8848992860a222425247bb', 'test/data/bam/12.bam': 'a996962ec314726de9465de3d2e35a91be272d314bede769dd397828ebb0fa35', 'test/data/fasta.fna': '8293616bf0b5b3d0533a424318b439d36c09f428767c44c208ce2b92ca1ab633', 'test/data/marker.fna': '43118b38e1815a731fdbf07483fd75151dcb052b1c9334b12079b2730cec177f', 'test/test_aamb_encode.py': 'bca7f59173b5133a63d591dd3e7d3dd86804f5d5f96e5dc697303fe59596496e', 'test/test_cluster.py': '9b5dec1e8b29a95acc9bfcc6bc27b37434bac649b7f8999b74633965d604f0a3', 'test/test_encode.py': '3a1413066f6ee33d45c6beee372629619566b699bf60efbb2ffdeb2bf1396980', 'test/test_parsebam.py': '05dd2bbd31f4f843938897088a05d0cadc96470d83167e3ec25b3a0eddc06a1c', 'test/test_parsecontigs.py': '093854b91c7f085174c3b04f234d7e261b54e82ec2ace24c5830ab722cddbdcc', 'test/test_parsemarkers.py': '468f44353b2a6ce35c30ba9030bf4f0ab32e5df221c1d11bfde953888c953ecd', 'test/test_reclustering.py': '0e99a2e18d39536bcf467eef06585aec1f93eecfc42672057f7cd76fbebc77d4', 'test/test_results.py': 'a14549f80039ec791d2968e9a1dbe9112361d1ba18b9ff61426ba935bee7eea4', 'test/test_semisupervised_encode.py': 'd49aeb1e70971a744e70325723471b2bb7967869c389661628baad11f3ed60a1', 'test/test_vambtools.py': 'cbf4685d94968199f6f435a779ba62b4afb70c66b41ad611396a7435c49126ef', 'test/testtools.py': '8426db93500d0de17623a81a6bef79876628706136cb5ee339382289863f990a', 'vamb/__init__.py': 'ea544ae2192b28a353f5feba6340ad2860b7b6524e449ecaf29d52be4e77fa8b', 'vamb/__main__.py': '848762a3f052a4bc9728aeeff35e1d93f111f0dd5ef4941eef926550254370bd', 'vamb/aamb_encode.py': '1dddc22148b6bdec3ca19fb494993c6350349c38d29477eb48b2b4fc0913fff1', 'vamb/cluster.py': 'dcbfdbde9916602585ea20852d4d3a3c0e04a30261c179580844f62bfb9a1185', 'vamb/encode.py': '7a3f7fcdafa85329b01c78f6a2c3611d13a8f9b2fec6502d5558a6482f297f5f', 'vamb/encode_n2v_asimetric.py': '0df435d887f4c064490d7a67deedfe7372659ea24780fe390c184d110eb8dac8', 'vamb/git_commit.py': '8599b355874ba6ec3e2137967d4572859e3623a414c5d50942f92c0489a281cb', 'vamb/hloss_misc.py': 'c65be789fdabd606e08b8739381f968f3e9f8ff73fcbfed16fe76632def7abcb', 'vamb/kernel.npz': '0a8383b6de8e7c0fb42162d6a0d1e63634e91a4fb9ad8200310ccad71ae9e7bb', 'vamb/marker.hmm': 'cd0c329c713e61e348629f3010d47dc9fadaaa08307c23a4dd696e29530f7707', 'vamb/parsebam.py': '4476443c07c47dabfc760513d9381ed62c7bad22ee1187d9efbeb0285ef6088d', 'vamb/parsecontigs.py': '13e474cd2ad76590d35926ceed501de099e9633bda066570dd2aa3c4b50e27da', 'vamb/parsemarkers.py': 'eaf4057f953c6483e383b9696e07cef8f6dd18009d19f334f2fe70e32a60613e', 'vamb/reclustering.py': 'bb2eb656a4ab2de5982f84dd02bce90f9e7a85771514e2906bb23d9b4c10f42d', 'vamb/semisupervised_encode.py': '150c9b082a7b97e2e54849f74d55c3b92610ccfa86dc42729688e8c8d9fb5f39', 'vamb/taxonomy.py': '2be959a54a6c7c9567e267cacb9148d5bb781f0411bd0bf4627f30190214dd2b', 'vamb/taxvamb_encode.py': '2e8c7351e332edf0b3692a3938d4162d6e1c9f4fb0d748d57530e45df006581e', 'vamb/vambtools.py': '71a8af44b760d4f680ef02d943b6a9456dfccec1acf52464da0ff5fc86444eb7'}


def verify_source(root):
    observed = {}
    for name, expected in SOURCE_SHA256.items():
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('Missing regular fixed PlasMAAG source: ' + name)
        observed[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed[name] != expected:
            raise ValueError('Unsupported PlasMAAG source: ' + name)
    return observed


def install_checked_runner(module, children):
    original = module.CliRunner.run

    def checked(self):
        if self.dry_run_command:
            return original(self)
        command = [str(x) for x in self._argument_holder]
        start = time.monotonic()
        result = subprocess.run(command)
        children.append(dict(command=command, exit_code=result.returncode,
                             elapsed_seconds=time.monotonic() - start))
        if result.returncode:
            raise subprocess.CalledProcessError(result.returncode, command)
        return None

    module.CliRunner.run = checked
    return original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--runtime-record', type=Path, required=True)
    parser.add_argument('--resume-private-source', action='store_true', help='Reuse only a fully verified existing private effective source')
    parser.add_argument('--genomad-splits', type=int, help='Explicit official geNomad memory partition option; leave native default when absent')
    parser.add_argument('tool_arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    arguments = args.tool_arguments
    if arguments[:1] == ['--']:
        arguments = arguments[1:]
    record = dict(source_commit=COMMIT, source_sha256={}, arguments=arguments, children=[],
                  scope='Fixed original CLI with checked external command boundary; product validation is separate')
    code = 1
    try:
        root = args.source.resolve()
        record['source_sha256'] = verify_source(root)
        distribution = importlib.metadata.distribution('PlasMAAG')
        if distribution.version != '1.0.2.dev142+ga6b39ac6e':
            raise ValueError('Unsupported installed PlasMAAG build version')
        installed = {}
        for name, expected in SOURCE_SHA256.items():
            if not name.endswith('.py') or not name.startswith(('vamb/', 'PlasMAAG/')):
                continue
            path = Path(distribution.locate_file(name))
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('Installed Python differs from fixed PlasMAAG source: ' + name)
            installed[name] = expected
        record['installed_python_source_sha256'] = installed
        extensions = [Path(distribution.locate_file(item)) for item in distribution.files
                      if str(item).startswith('vamb/_vambtools.') and str(item).endswith('.so')]
        if len(extensions) != 1 or not extensions[0].is_file():
            raise ValueError('Expected one same-build compiled VAMB extension')
        extension = extensions[0]
        record['compiled_extension'] = dict(original_path=str(extension), sha256=hashlib.sha256(extension.read_bytes()).hexdigest())
        # Keep the 85 upstream resources immutable. Compatibility pins and
        # optional memory partitions apply only to this task's private copy.
        effective = Path('.plasmaag_source').resolve()
        reuse = effective.exists()
        if reuse and not args.resume_private_source:
            raise ValueError('Private source already exists; explicit verified resume required')
        if not reuse:
            shutil.copytree(root, effective, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
        changes = {}
        original_environment = (root / 'envs/genomad.yaml').read_text()
        changes['envs/genomad.yaml'] = original_environment + '  - click==8.1.8\n  - rich-click==1.8.3\n'
        if args.genomad_splits is not None:
            if args.genomad_splits < 1:
                raise ValueError('geNomad splits must be positive')
            for name in ['snakefile.smk', 'snakefile_megahit.smk']:
                original_text = (root / name).read_text()
                old = 'genomad end-to-end --cleanup {input.contigs}'
                if original_text.count(old) != 1:
                    raise ValueError('Unexpected geNomad command in fixed Snakefile: ' + name)
                changes[name] = original_text.replace(old, 'genomad end-to-end --splits ' + str(args.genomad_splits) + ' --cleanup {input.contigs}')
        edits = []
        for name, changed in changes.items():
            target = effective / name
            if reuse:
                if target.read_text() != changed:
                    raise ValueError('Existing private deployment/resource patch differs: ' + name)
            else:
                target.write_text(changed)
            edits.append(dict(file=name, original_sha256=SOURCE_SHA256[name],
                              effective_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                              purpose='CLI dependency compatibility' if name.endswith('.yaml') else 'Explicit memory partitions'))
        for original_file in root.rglob('*'):
            relative = original_file.relative_to(root)
            if any(part in ['.git', '__pycache__'] for part in relative.parts) or original_file.suffix == '.pyc' or not original_file.is_file() or str(relative) in changes:
                continue
            copied = effective / relative
            if not copied.is_file() or hashlib.sha256(copied.read_bytes()).digest() != hashlib.sha256(original_file.read_bytes()).digest():
                raise ValueError('Private source differs from original runtime resource: ' + str(relative))
        record['resource_only_source_edits'] = [edit for edit in edits if edit['file'].endswith('.smk')]
        record['deployment_only_source_edits'] = [edit for edit in edits if edit['file'].endswith('.yaml')]
        record['reused_verified_private_source'] = reuse
        target_extension = effective / 'vamb' / extension.name
        if target_extension.is_file():
            if hashlib.sha256(target_extension.read_bytes()).digest() != hashlib.sha256(extension.read_bytes()).digest():
                raise ValueError('Private compiled VAMB extension differs from installed fixed build')
        else:
            shutil.copyfile(extension, target_extension)
        record['effective_source'] = str(effective)
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(effective))
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
        os.environ['PYTHONPATH'] = str(effective) + os.pathsep + os.environ.get('PYTHONPATH', '')
        cli = importlib.import_module('PlasMAAG.__main__')
        if Path(cli.__file__).resolve().parent != effective / 'PlasMAAG':
            raise ValueError('PlasMAAG CLI was loaded outside the fixed source')
        record['installed_version'] = importlib.metadata.version('PlasMAAG')
        if record['installed_version'] != '1.0.2.dev142+ga6b39ac6e':
            raise ValueError('Unsupported installed PlasMAAG build version')
        runners = importlib.import_module('PlasMAAG.command_line_runners')
        original = install_checked_runner(runners, record['children'])
        try:
            cli.main.main(args=arguments, prog_name='PlasMAAG', standalone_mode=False)
        finally:
            runners.CliRunner.run = original
        code = 0
    except Exception as error:
        record['error'] = str(error)
        print('PlasMAAG runtime violation: ' + str(error), file=sys.stderr)
    finally:
        record['exit_code'] = code
        args.runtime_record.write_text(json.dumps(record, indent=2) + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
