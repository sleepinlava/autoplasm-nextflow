"""Independent finite-window/Markov oracle for the published 256-word TETRA math.

This is a numeric contract test, not a host association accuracy benchmark.
"""
import collections
import csv
import itertools
import math
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'bin/sequence_similarity_link.R'
WORDS = {k: [''.join(x) for x in itertools.product('ACGT', repeat=k)] for k in [2, 3, 4]}


def rc(sequence):
    return sequence.translate(str.maketrans('ACGTN', 'TGCAN'))[::-1]


def counts(records, width):
    counter = collections.Counter()
    for record in records:
        clean = ''.join(c if c in 'ACGTN' else 'N' for c in record.upper())
        for strand in [clean, rc(clean)]:
            for start in range(len(strand) - width + 1):
                word = strand[start:start + width]
                if all(c in 'ACGT' for c in word): counter[word] += 1
    return {word: counter[word] for word in WORDS[width]}


def zscores(records):
    di, tri, tetra = [counts(records, k) for k in [2, 3, 4]]
    result = {}
    for word in WORDS[4]:
        denominator = di[word[1:3]]
        if not denominator: result[word] = None; continue
        left, right = tri[word[:3]], tri[word[1:]]
        expected = left * right / denominator
        variance = expected * (denominator - left) * (denominator - right) / denominator ** 2
        result[word] = (tetra[word] - expected) / math.sqrt(variance) if variance > 0 else None
    return result


def pearson(a, b):
    if any(x is None for x in list(a.values()) + list(b.values())): return None
    left = [a[w] for w in WORDS[4]]; right = [b[w] for w in WORDS[4]]
    ml = sum(left) / 256; mr = sum(right) / 256
    vl = sum((x - ml) ** 2 for x in left); vr = sum((x - mr) ** 2 for x in right)
    if not vl or not vr: return None
    return sum((x - ml) * (y - mr) for x, y in zip(left, right)) / math.sqrt(vl * vr)


class TetraMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); cls.base = Path(cls.temp.name)
        rng = random.Random(390402026)
        seq = ''.join(rng.choices('ACGT', weights=[.35, .15, .2, .3], k=4000))
        varied = ''.join(rng.choice('ACGT') if rng.random() < .18 else c for c in seq)
        cls.records = {'full': [seq], 'changed': [varied], 'reverse': [rc(seq)],
            'split': [seq[:1999], seq[1999:]], 'reordered': [seq[1999:], seq[:1999]],
            'ambiguous': [seq[:2000] + 'NRY-' + seq[2000:]],
            'broken': [seq[:2000], seq[2000:]], 'short': ['ACGT', 'AT', 'CG'],
            'homopolymer': ['A' * 1200], 'periodic': ['ACGT' * 300], 'empty': []}
        for name, seqs in cls.records.items():
            (cls.base / (name + '.fa')).write_text(''.join(f'>r{i}\n{s}\n' for i, s in enumerate(seqs)))
        probe = cls.base / 'probe.R'
        probe.write_text('''args <- commandArgs(TRUE)
e <- parse(args[1]); for (x in e[-length(e)]) eval(x)
root <- args[2]
for (name in c("full","changed","reverse","split","reordered","ambiguous","broken","short","homopolymer","periodic","empty")) {
  sequences <- vapply(read_fasta(file.path(root,paste0(name,".fa"))), function(r) r$seq, character(1))
  z <- tetra_zscores(sequences)
  write.table(data.frame(word=names(z),z=z),file.path(root,paste0(name,".z.tsv")),sep="\\t",quote=FALSE,row.names=FALSE,na="NA")
  for (space in list(SPACE2,SPACE3,SPACE4)) {
    n <- strand_counts(sequences,space)
    write.table(data.frame(word=names(n),count=n),file.path(root,paste0(name,".",space$width,".tsv")),sep="\\t",quote=FALSE,row.names=FALSE)
  }
}
''')
        result = subprocess.run(['Rscript', str(probe), str(SCRIPT), str(cls.base)], text=True, capture_output=True)
        if result.returncode: raise AssertionError(result.stderr)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def rcounts(self, name, width):
        with (self.base / f'{name}.{width}.tsv').open() as f:
            return {r['word']: int(r['count']) for r in csv.DictReader(f, delimiter='\t')}

    def rz(self, name):
        with (self.base / f'{name}.z.tsv').open() as f:
            return {r['word']: None if r['z'] == 'NA' else float(r['z']) for r in csv.DictReader(f, delimiter='\t')}

    def test_every_legal_window_both_strands_and_all_ordered_words(self):
        for name, records in self.records.items():
            for width in [2, 3, 4]: self.assertEqual(self.rcounts(name, width), counts(records, width), (name, width))

    def test_full_256_zscores_against_independent_scalar_formula(self):
        for name, records in self.records.items():
            actual, expected = self.rz(name), zscores(records)
            self.assertEqual(len(actual), 256)
            for word, value in expected.items():
                if value is None: self.assertIsNone(actual[word], (name, word))
                else: self.assertAlmostEqual(actual[word], value, places=9, msg=(name, word))

    def test_palindromes_are_counted_on_each_strand(self):
        self.assertEqual(self.rcounts('short', 4)['ACGT'], 2)
        self.assertEqual(self.rcounts('short', 2)['AT'], 2)
        self.assertEqual(self.rcounts('short', 2)['CG'], 4)

    def test_sequence_end_windows_and_short_records(self):
        self.assertEqual(sum(self.rcounts('full', 4).values()), 2 * (4000 - 3))
        self.assertEqual(sum(self.rcounts('split', 4).values()), 2 * (4000 - 6))
        self.assertEqual(sum(self.rcounts('short', 4).values()), 2)
        self.assertEqual(sum(self.rcounts('empty', 4).values()), 0)

    def test_fragment_boundaries_exclude_six_junction_windows(self):
        full, split = self.rcounts('full', 4), self.rcounts('split', 4)
        self.assertEqual(sum(full.values()) - sum(split.values()), 6)
        self.assertTrue(any(full[w] != split[w] for w in WORDS[4]))
        # Reordering independent contigs cannot alter any count or z-score.
        self.assertEqual(split, self.rcounts('reordered', 4))
        self.assertEqual(self.rz('split'), self.rz('reordered'))

    def test_strand_invariance_and_ambiguity_breaks_windows(self):
        self.assertEqual(self.rz('full'), self.rz('reverse'))
        for width in [2, 3, 4]: self.assertEqual(self.rcounts('ambiguous', width), self.rcounts('broken', width))

    def test_undefined_profiles_are_not_numeric_zero_similarities(self):
        self.assertIsNone(pearson(self.rz('homopolymer'), self.rz('full')))
        self.assertIsNone(pearson(self.rz('periodic'), self.rz('periodic')))

    def test_full_vector_pearson_independent_and_self_match(self):
        self.assertAlmostEqual(pearson(self.rz('full'), self.rz('reverse')), 1, places=12)
        expected = pearson(zscores(self.records['full']), zscores(self.records['changed']))
        self.assertAlmostEqual(pearson(self.rz('full'), self.rz('changed')), expected, places=12)
        self.assertLess(expected, .7)


if __name__ == '__main__': unittest.main()
