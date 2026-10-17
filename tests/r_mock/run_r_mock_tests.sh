#!/usr/bin/env bash
# Mock-data smoke tests for the R analysis scripts in bin/.
#
# Generates a tiny synthetic dataset (6 samples, 2 groups, 2 contigs, 1
# plasmid) under a temp dir and runs every bin/*.R script against it,
# asserting exit codes and key output content. Complements the unit tests in
# tests/test_*.py (which pin error paths and edge cases).
#
# Usage: bash tests/r_mock/run_r_mock_tests.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BIN="$ROOT/bin"
WORK="$(mktemp -d /tmp/r_mock.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

PASS=0
FAIL=0
check() { # check <label> <condition...>
  local label="$1"; shift
  if "$@"; then PASS=$((PASS + 1)); echo "ok   - $label"; else FAIL=$((FAIL + 1)); echo "FAIL - $label"; fi
}
check_grep() { # check_grep <label> <file> <pattern>
  local label="$1" file="$2" pattern="$3"
  if grep -qF -- "$pattern" "$file" 2>/dev/null; then PASS=$((PASS + 1)); echo "ok   - $label"; else FAIL=$((FAIL + 1)); echo "FAIL - $label (missing '$pattern' in $file)"; fi
}

SAMPLES="S1 S2 S3 S4 S5 S6"

# ---------- shared mock inputs ----------
# CoverM-style per-sample tables (Contig / Length / Count Mean / RPKM / TPM)
i=0
for s in $SAMPLES; do
  i=$((i + 1))
  { printf 'Contig\tLength\tCount Mean\tRPKM\tTPM\n'
    printf 'plasmid_1\t5000\t%s\t%s\t%s\n' "$((10 * i))" "$((20 + i))" "$((30 + i))"
    printf 'chrom_1\t50000\t%s\t%s\t%s\n' "$((100 - i))" "$((50 + i))" "$((60 + i))"
  } > "${s}.coverm.tsv"
done
# Metadata: two groups of three
{ printf 'sample_id\tgroup\n'
  printf 'S1\tcase\nS2\tcase\nS3\tcase\nS4\tctrl\nS5\tctrl\nS6\tctrl\n'
} > metadata.tsv
# MetaPhlAn-style species profiles (abundance tracks the plasmid coverage)
i=0
for s in $SAMPLES; do
  i=$((i + 1))
  { printf '#mpa_v31_CHOCOPhlAn_201901\n'
    printf 'clade_name\tncbi_tax_id\trelative_abundance\tadditional_species\n'
    printf 'k__Bacteria|p__Firmicutes|g__Host|s__Host_exemplar\t2|123|999\t%s\t\n' "$((10 * i)).0"
  } > "${s}.metaphlan.tsv"
done
# Sequences (generated in R for non-periodic, deterministic content):
# plasmid_1 = 1200 bp random + its first 24 bp repeated at the end (a DTR);
# chrom_1   = independent 1600 bp random (no terminal repeat).
mkdir -p mag_bins
Rscript - <<'RS'
set.seed(42)
rand_seq <- function(n) paste(sample(c("A", "C", "G", "T"), n, replace = TRUE), collapse = "")
p1_core <- rand_seq(1200)
plasmid_1 <- paste0(p1_core, substr(p1_core, 1, 24))
chrom_1 <- rand_seq(1600)
writeLines(c(paste0(">plasmid_1\n", plasmid_1), paste0(">chrom_1\n", chrom_1)), "assembly.fasta")
writeLines(paste0(">plasmid_1\n", plasmid_1), "S1.plasmid_contigs.fasta")
writeLines(paste0(">bin_contig\n", plasmid_1), "mag_bins/bin.1.fa")
RS
# Detection-tool mock tables for the consensus
printf 'seq_name\tplasmid_score\nplasmid_1\t0.97\n' > genomad.tsv
printf 'contig_id\tclassification\tplasmid_score\nplasmid_1\tplasmid\t0.9\nchrom_1\tchromosome\t0.05\n' > S1.plasme.tsv
printf 'contig_id\tscore\nplasmid_1\t0.8\n' > S1.platon.tsv
# MAG taxonomy for the sequence linker (mag_bins/bin.1.fa written above)
printf 'user_genome\tclassification\nbin.1.fa\td__Bacteria;p__Firmicutes\n' > taxonomy.tsv
# Long-read SAM: 3 bridging reads (primary -> plasmid_1, supplementary -> chrom_1)
{ printf '@HD\tVN:1.6\tSO:unsorted\n@SQ\tSN:plasmid_1\tLN:1224\n@SQ\tSN:chrom_1\tLN:1600\n'
  for i in 1 2 3; do
    printf 'read%s\t0\tplasmid_1\t1\t60\t100M\t*\t0\t0\t%s\t%s\n' "$i" "$(printf 'A%.0s' {1..100})" "$(printf 'I%.0s' {1..100})"
    printf 'read%s\t2048\tchrom_1\t1\t60\t100M\t*\t0\t0\t%s\t%s\n' "$i" "$(printf 'T%.0s' {1..100})" "$(printf 'I%.0s' {1..100})"
  done
} > alignments.sam

echo "## mock inputs ready in $WORK"

# ---------- 1. merge_abundance.R ----------
Rscript "$BIN/merge_abundance.R" --tables S1.coverm.tsv S2.coverm.tsv S3.coverm.tsv S4.coverm.tsv S5.coverm.tsv S6.coverm.tsv \
  --sample-ids $SAMPLES --mapper mock --out merged_contigs.tsv 2>merge.err
check "merge_abundance exits 0" test $? -eq 0
check "merged rows = 12" bash -c 'test $(($(wc -l < merged_contigs.tsv) - 1)) -eq 12'
check_grep "merged keeps TPM string" merged_contigs.tsv $'chrom_1	S6	56	66'

# ---------- 2. diversity.R ----------
Rscript "$BIN/diversity.R" --abundance merged_contigs.tsv --metadata metadata.tsv \
  --out-metrics diversity_metrics.tsv --out-beta bray_curtis_matrix.tsv 2>diversity.err
check "diversity exits 0" test $? -eq 0
check "4 metrics x 6 samples = 24 rows" bash -c 'test $(($(wc -l < diversity_metrics.tsv) - 1)) -eq 24'
check_grep "richness metric" diversity_metrics.tsv $'S1	richness	2	case'
check_grep "simpson metric" diversity_metrics.tsv $'	simpson	'
check_grep "pielou metric" diversity_metrics.tsv $'	pielou	'
check "beta matrix 7x7" bash -c 'test $(wc -l < bray_curtis_matrix.tsv) -eq 7'
Rscript "$BIN/diversity.R" --abundance merged_contigs.tsv --metadata metadata.tsv \
  --beta-normalization tss --out-metrics div_tss.tsv --out-beta beta_tss.tsv 2>/dev/null
check "diversity --beta-normalization tss exits 0" test $? -eq 0

# ---------- 3. differential_abundance.R ----------
Rscript "$BIN/differential_abundance.R" --abundance merged_contigs.tsv --metadata metadata.tsv \
  --min-replicates 3 --out differential_abundance.tsv 2>diff.err
check "differential_abundance exits 0" test $? -eq 0
check "1 pair x 2 contigs = 2 rows" bash -c 'test $(($(wc -l < differential_abundance.tsv) - 1)) -eq 2'
check_grep "Welch method label" differential_abundance.tsv "internal_effect_size"

# ---------- 4. network_prepare.R ----------
Rscript "$BIN/network_prepare.R" --abundance merged_contigs.tsv --out fastspar_input.tsv 2>network.err
check "network_prepare exits 0" test $? -eq 0
check_grep "FastSpar header" fastspar_input.tsv "#OTU ID"
check "prevalence filter keeps 2 contigs" bash -c 'test $(($(wc -l < fastspar_input.tsv) - 1)) -eq 2'

# ---------- 5. deseq2_plasmid.R ----------
# DESeq2 needs enough features and real within-group variance; generate 40
# plasmids x 6 samples of Poisson counts with a group effect in R.
Rscript - <<'RS'
set.seed(7)
samples <- c("S1", "S2", "S3", "S4", "S5", "S6")
group <- ifelse(samples %in% c("S1", "S2", "S3"), "case", "ctrl")
rows <- c("plasmid_id\tsample_id\traw_count\tcoverage")
for (p in seq_len(40)) {
  for (i in seq_along(samples)) {
    lambda <- if (group[i] == "case") 100 + p * 10 else 10 + p * 2
    n <- rpois(1, lambda)
    rows <- c(rows, sprintf("pl_%d\t%s\t%d\t%d", p, samples[i], n, n))
  }
}
writeLines(rows, "deseq2_abundance.tsv")
RS
Rscript "$BIN/deseq2_plasmid.R" --abundance deseq2_abundance.tsv --metadata metadata.tsv \
  --output differential_plasmids.tsv 2>deseq2.err
check "deseq2_plasmid exits 0" test $? -eq 0
check_grep "DESeq2 method label" differential_plasmids.tsv "DESeq2"
check_grep "group contrast" differential_plasmids.tsv $'	case	ctrl	'

# ---------- 6. coabundance_link.R ----------
Rscript "$BIN/coabundance_link.R" --plasmid-abundance merged_contigs.tsv \
  --host-profiles S1.metaphlan.tsv S2.metaphlan.tsv S3.metaphlan.tsv S4.metaphlan.tsv S5.metaphlan.tsv S6.metaphlan.tsv \
  --host-sample-ids $SAMPLES --method pearson --min-correlation 0.9 --out coabundance_links.tsv 2>coab.err
check "coabundance_link exits 0" test $? -eq 0
check_grep "correlated host link" coabundance_links.tsv "s__Host_exemplar"
check_grep "significance fields" coabundance_links.tsv "pvalue="
check_grep "jaccard field" coabundance_links.tsv "jaccard="

# ---------- 7. sequence_similarity_link.R ----------
Rscript "$BIN/sequence_similarity_link.R" --plasmid-contigs S1.plasmid_contigs.fasta \
  --host-genomes mag_bins --taxonomy taxonomy.tsv --sample-id S1 \
  --min-similarity 0.7 --out sequence_links.tsv 2>seq.err
check "sequence_similarity_link exits 0" test $? -eq 0
check_grep "identical sequence links to bin.1" sequence_links.tsv $'	bin.1	'
check_grep "taxonomy attached" sequence_links.tsv "d__Bacteria"
check_grep "TETRA method label" sequence_links.tsv "method=tetra_zscore"

# ---------- 8. longread_bridge_link.R ----------
Rscript "$BIN/longread_bridge_link.R" --sam alignments.sam --plasmid-contigs S1.plasmid_contigs.fasta \
  --assembly assembly.fasta --sample-id S1 --out longread_links.tsv 2>longread.err
check "longread_bridge_link (SAM) exits 0" test $? -eq 0
check_grep "bridge link score 3" longread_links.tsv $'plasmid_1	chrom_1	S1	long_read_bridge	3	'
check_grep "strength/rank fields" longread_links.tsv "strength="
# BAM input parity (convert with Rsamtools itself; no samtools needed)
Rscript -e 'suppressPackageStartupMessages(library(Rsamtools)); asBam("alignments.sam", "alignments", overwrite = TRUE)' 2>/dev/null
Rscript "$BIN/longread_bridge_link.R" --sam alignments.bam --plasmid-contigs S1.plasmid_contigs.fasta \
  --assembly assembly.fasta --sample-id S1 --out longread_links_bam.tsv 2>/dev/null
check "longread_bridge_link (BAM) exits 0" test $? -eq 0
check "SAM and BAM outputs identical" bash -c 'cmp -s longread_links.tsv longread_links_bam.tsv'

# ---------- 9. plasmid_consensus.R ----------
Rscript "$BIN/plasmid_consensus.R" --assembly assembly.fasta --genomad-summary genomad.tsv \
  --extra S1.plasme.tsv --extra S1.platon.tsv --method weighted_vote --sample-id S1 \
  --out-fasta plasmids.fasta --out-predictions predictions.tsv --out-consensus consensus.tsv 2>consensus.err
check "plasmid_consensus exits 0" test $? -eq 0
check_grep "consensus call" consensus.tsv $'plasmid_1	S1	plasmid'
check_grep "ensemble column genomad" consensus.tsv $'genomad	plasme	plasx	platon	scapp'
check_grep "plasmid fasta written" plasmids.fasta ">plasmid_1"

# ---------- 10. plasmid_structure.R ----------
Rscript "$BIN/plasmid_structure.R" --contigs assembly.fasta --sample-id S1 \
  --out plasmid_structure.tsv 2>structure.err
check "plasmid_structure exits 0" test $? -eq 0
check_grep "DTR detected as circular" plasmid_structure.tsv $'	plasmid_1	1224	true	24	dtr	'
check_grep "linear contig not circular" plasmid_structure.tsv $'	chrom_1	1600	false	0	none	'

# ---------- 11. plasmid_catalog_prepare.R ----------
cp S1.plasmid_contigs.fasta S2.plasmid_contigs.fasta
Rscript "$BIN/plasmid_catalog_prepare.R" --contigs S1.plasmid_contigs.fasta S2.plasmid_contigs.fasta \
  --out catalog.fasta 2>catalog.err
check "plasmid_catalog_prepare exits 0" test $? -eq 0
check_grep "sample-prefixed header S1" catalog.fasta ">S1|plasmid_1"
check_grep "sample-prefixed header S2" catalog.fasta ">S2|plasmid_1"
Rscript "$BIN/plasmid_catalog_prepare.R" --contigs S1.plasmid_contigs.fasta --min-length 2000 \
  --out catalog_minlen.fasta 2>catalog_minlen.err 1>catalog_minlen.out
check "catalog --min-length exits 0" test $? -eq 0
check_grep "short contigs skipped" catalog_minlen.out "skipped 1 shorter than 2000 bp"

# ---------- 12. generate_report.R ----------
mkdir -p results/04_plasmid_detection/consensus results/04_plasmid_detection/structure results/11_diversity
cp plasmids.fasta results/04_plasmid_detection/consensus/S1.plasmid_contigs.fasta
cp consensus.tsv results/04_plasmid_detection/consensus/S1.plasmid_consensus.tsv
cp plasmid_structure.tsv results/04_plasmid_detection/structure/S1.plasmid_structure.tsv
Rscript "$BIN/generate_report.R" --outdir results --platform illumina \
  --project-name mock_run --template "$ROOT/assets/plasmid_report.Rmd" --out-prefix . 2>report.err
check "generate_report exits 0" test $? -eq 0
check_grep "report title" report.md "# AutoPlasm report — mock_run"
check_grep "detection table row" report.md "| S1 | 1 | 1 |"
check_grep "diversity section checked" report.md '- [x] `11_diversity`'
check_grep "html report" report.html "<!DOCTYPE html>"
check_grep "template-rendered html (pandoc table)" report.html "<table"
check_grep "methods written" methods.md "# Methods"
check_grep "data layer json" report_data.json '"project_name": "mock_run"'
# fallback path without --template
mkdir -p fallback && Rscript "$BIN/generate_report.R" --outdir results --platform illumina \
  --project-name mock_run --out-prefix fallback 2>/dev/null
check "generate_report fallback exits 0" test $? -eq 0
check_grep "fallback html" fallback/report.html "<pre>"

echo
echo "## r_mock: $PASS passed, $FAIL failed"
test "$FAIL" -eq 0
