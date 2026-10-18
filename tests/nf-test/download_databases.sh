#!/usr/bin/env bash
# Download small/medium databases and tool assets for W3 real-node tests.
# Every artifact gets size + sha256 recorded in manifest.txt (for lock entries).
# Artifacts live in results/nf-test/databases/ (home disk, survives reboot).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$ROOT/results/nf-test/databases"
mkdir -p "$OUT"
cd "$OUT"
touch manifest.txt

fetch() { # fetch <name> <url>
    local name="$1" url="$2"
    local file="$OUT/$name"
    if [ -s "$file" ]; then
        # Re-verify existing artifacts against the recorded sha256.
        local recorded
        recorded=$(grep -m1 "^ARTIFACT $name " manifest.txt | sed 's/.*sha256=\([0-9a-f]*\).*/\1/')
        if [ -n "$recorded" ]; then
            local actual
            actual=$(sha256sum "$file" | cut -d' ' -f1)
            if [ "$actual" != "$recorded" ]; then
                echo "CORRUPT $name (recorded $recorded != actual $actual)" | tee -a manifest.txt
                return 1
            fi
            echo "== $name present, sha256 verified" | tee -a manifest.txt
            return 0
        fi
        echo "== $name already present (no manifest entry to verify)" | tee -a manifest.txt
    else
        echo "== downloading $name" | tee -a manifest.txt
        if ! curl -fL --retry 3 --connect-timeout 30 -o "$file" "$url"; then
            echo "FAILED $name $url" | tee -a manifest.txt
            rm -f "$file"
            return 1
        fi
    fi
    local size sha
    size=$(stat -c %s "$file")
    sha=$(sha256sum "$file" | cut -d' ' -f1)
    echo "ARTIFACT $name size=$size sha256=$sha url=$url" | tee -a manifest.txt
}

fetch conjscan-2.1.0.tar.gz   https://github.com/macsy-models/CONJScan/archive/refs/tags/2.1.0.tar.gz
fetch txsscan-1.1.4.tar.gz    https://github.com/macsy-models/TXSScan/archive/refs/tags/1.1.4.tar.gz
fetch plasmidhostfinder-repo.tar.gz https://bitbucket.org/deaytan/plasmid-host-prediction/get/bb9316d1.tar.gz
fetch plasmidfinder-db-3.0.3.tar.gz https://bitbucket.org/genomicepidemiology/plasmidfinder_db/get/plasmidfinder-3.0.3.tar.gz
fetch 'dna_r10.4.1_e8.2_400bps_fast@v4.3.0.zip' 'https://cdn.oxfordnanoportal.com/software/analysis/dorado/dna_r10.4.1_e8.2_400bps_fast@v4.3.0.zip'
fetch mobsuite-data.tar.gz    https://zenodo.org/records/10304948/files/data.tar.gz
fetch platon-db.tar.gz        https://zenodo.org/records/4066768/files/db.tar.gz
fetch bakta-db-light.tar.xz   https://zenodo.org/record/14916843/files/db-light.tar.xz
fetch checkm2-database.tar.gz https://zenodo.org/record/14897628/files/checkm2_database.tar.gz
fetch dorado-2.1.2-linux-x64.tar.gz https://cdn.oxfordnanoportal.com/software/analysis/dorado-2.1.2-linux-x64.tar.gz
echo "ALL DONE" | tee -a manifest.txt
