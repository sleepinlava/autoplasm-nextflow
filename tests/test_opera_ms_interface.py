"""Original OPERA-MS wrapper contract using a Perl interface observer, not an assembler."""
import os
import gzip
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
OBSERVER = r'''# Interface observer only: no assembly algorithm or real reads.
use strict;
use warnings;
use File::Path qw(make_path);
my %args = @ARGV;
open(my $called, '>', 'observer_called.txt') or die $!;
print $called "Interface observer only\n";
close($called);
open(my $input, '<', $args{'--long-read'}) or die $!;
local $/;
my $long_input = <$input>;
close($input);
die "expected uncompressed exact long-read input" unless $long_input eq "\@interface\nACGT\n+\nIIII\n";
my $out = $args{'--out-dir'};
my ($mode) = $args{'--short-read1'} =~ /^(\w+)\.R1/;
die "unrecognized interface observer mode" unless defined($mode);
make_path("$out/intermediate_files/opera_long_read/GF3");
make_path("$out/intermediate_files/coverage_estimation");
open(my $diagnostic, '>', "$out/intermediate_files/coverage_estimation/short_read_analysis.err") or die $!;
print $diagnostic "samtools: bgzf.c:142: bgzf_open: Assertion `compressBound(0xff00) < 0x10000' failed.\n" if $mode eq 'aborted';
close($diagnostic);
sub write_fasta {
    my ($path, $id, $seq) = @_;
    open(my $fh, '>', $path) or die $!;
    print $fh ">$id\n$seq\n";
    close($fh);
}
if ($mode eq 'both' || $mode eq 'final' || $mode eq 'aborted') {
    write_fasta("$out/contigs.fasta", 'final_product', 'ACGTTGCA');
}
if ($mode eq 'both' || $mode eq 'intermediate') {
    write_fasta("$out/intermediate_files/opera_long_read/GF3/contigs.fa", 'intermediate', 'TTTTAAAA');
}
if ($mode eq 'decoy') {
    make_path("$out/other");
    write_fasta("$out/other/contigs.fasta", 'decoy', 'CCCCGGGG');
}
if ($mode eq 'empty') {
    open(my $fh, '>', "$out/contigs.fasta") or die $!;
    close($fh);
}
'''


class OperaInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nextflow = shutil.which('nextflow')
        if not cls.nextflow:
            raise unittest.SkipTest('Nextflow required for original-wrapper interface checks')

    def run_case(self, mode, succeeds, compression=None):
        base = Path(tempfile.mkdtemp(prefix='opera-interface-'))
        self.addCleanup(lambda: shutil.rmtree(base) if not os.environ.get('AUTOPLASM_KEEP_INTERFACE') else None)
        scripts = base/'observer-bin';scripts.mkdir()
        # Deliberately only on PATH, never staged into the task directory.
        (scripts/'OPERA-MS.pl').write_text(OBSERVER)
        (scripts/'OPERA-MS.pl').chmod(0o755)
        for suffix in ['R1', 'R2', 'long']:
            (base/f'{mode}.{suffix}.fastq').write_text('@interface\nACGT\n+\nIIII\n')
        long_reads = base/f'{mode}.long.fastq'
        if compression:
            long_reads = base/f'{mode}.long reads.fastq.{"GZ" if compression == "GZ" else "gz"}'
            long_reads.write_bytes(b'broken gzip' if compression == 'corrupt' else gzip.compress(b'@interface\nACGT\n+\nIIII\n'))
        input_hashes = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in base.glob('*.fastq*')}
        harness = base/'probe.nf'
        harness.write_text(f'''nextflow.enable.dsl = 2
include {{ OPERA_MS }} from '{ROOT}/modules/assembly/opera_ms'
workflow {{
 OPERA_MS(Channel.of(tuple([id:'S1'],file('{base}/{mode}.R1.fastq'),file('{base}/{mode}.R2.fastq'),file('{long_reads}'))))
}}
''')
        config=base/'config'
        config.write_text(f'''params.outdir = '{base}/out'
params.publish_dir_mode = 'copy'
process.executor = 'local'
process.cpus = 1
process.memory = '1 GB'
conda.enabled = false
docker.enabled = false
singularity.enabled = false
''')
        command=[self.nextflow,'-C',str(config),'run',str(harness),'-work-dir',str(base/'work'),'-with-trace',str(base/'trace.tsv'),'-ansi-log','false']
        env=os.environ.copy();env['PATH']=str(scripts)+':'+env['PATH']
        result=subprocess.run(command,env=env,text=True,capture_output=True)
        (base/'stdout.log').write_text(result.stdout);(base/'stderr.log').write_text(result.stderr)
        (base/'command.txt').write_text(repr(command)+'\n')
        print(f'OPERA_INTERFACE_ARTIFACT {mode} {base} exit={result.returncode}',flush=True)
        output=base/'out/02_assembly/opera_ms/S1.opera_ms.contigs.fasta'
        self.assertEqual(input_hashes, {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in input_hashes})
        if succeeds:
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(output.read_text(),'>final_product\nACGTTGCA\n')
        else:
            self.assertNotEqual(result.returncode,0)
            errors='\n'.join(p.read_text() for p in (base/'work').rglob('.command.err'))
            expected = 'gzip:' if compression == 'corrupt' else 'OPERA-MS internal process failure' if mode == 'aborted' else 'OPERA-MS final assembly missing or empty'
            self.assertIn(expected,errors)
            if compression == 'corrupt':
                self.assertFalse(list((base/'work').rglob('observer_called.txt')))
            self.assertFalse(output.exists())

    def test_final_over_intermediate(self):
        self.run_case('both',True)

    def test_final_only(self):
        self.run_case('final',True)

    def test_intermediate_is_not_final(self):
        self.run_case('intermediate',False)

    def test_arbitrary_decoy_is_not_final(self):
        self.run_case('decoy',False)

    def test_empty_final_is_rejected(self):
        self.run_case('empty',False)

    def test_gzip_long_read_with_space_in_name(self):
        self.run_case('both',True,'gz')

    def test_uppercase_gzip_long_read(self):
        self.run_case('both',True,'GZ')

    def test_corrupt_gzip_fails_before_observer(self):
        self.run_case('both',False,'corrupt')

    def test_fatal_internal_diagnostic_rejects_final_fasta(self):
        self.run_case('aborted',False)


if __name__ == '__main__':
    unittest.main()
