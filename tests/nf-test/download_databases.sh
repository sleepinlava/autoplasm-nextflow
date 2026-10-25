#!/usr/bin/env bash
# Download small/medium databases and tool assets for W3 real-node tests.
# Downloads are published only after transfer, digest and archive checks succeed.
# A recorded digest is a local replay lock, not an independent upstream checksum.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$ROOT/results/nf-test/databases"
ASSETS=""
while (($#)); do
    case "$1" in
        --outdir|--asset-list)
            (($# >= 2)) || { echo "Missing value for $1" >&2; exit 2; }
            if [[ "$1" == --outdir ]]; then OUT="$2"; else ASSETS="$2"; fi
            shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
mkdir -p "$OUT" || exit 1
MANIFEST="$OUT/manifest.txt"
[[ ! -L "$MANIFEST" && ( ! -e "$MANIFEST" || -f "$MANIFEST" ) ]] || {
    echo "Invalid manifest path: $MANIFEST" >&2; exit 1;
}
touch "$MANIFEST" || exit 1
PART=""
trap '[[ -z "$PART" ]] || rm -f -- "$PART"' EXIT

log() { printf '%s\n' "$*" | tee -a "$MANIFEST"; }

check_archive() {
    case "$1" in
        *.tar.gz|*.tar.xz|*.tar.bz2|*.tgz|*.tar) tar -tf "$2" >/dev/null ;;
        *.zip) unzip -tq "$2" >/dev/null ;;
        *) return 0 ;;
    esac
}

fetch() { # fetch <name> <url> <optional independent sha256>
    local name="$1" url="$2" expected="$3" recorded="" value actual size
    local file="$OUT/$name"
    # Compare the name literally: dots in asset names are not regex wildcards.
    value=$(awk -v name="$name" '$1 == "ARTIFACT" && $2 == name {
        hash=""; for (i=3; i<=NF; i++) if ($i ~ /^sha256=/) hash=substr($i,8);
        print hash == "" ? "INVALID" : hash
    }' "$MANIFEST") || return 1
    while IFS= read -r actual; do
        [[ -n "$actual" ]] || continue
        [[ "$actual" =~ ^[0-9a-f]{64}$ ]] || { echo "Invalid manifest digest for $name" >&2; return 1; }
        [[ -z "$recorded" || "$recorded" == "$actual" ]] || {
            echo "Conflicting manifest digests for $name" >&2; return 1;
        }
        recorded="$actual"
    done <<< "$value"
    [[ -z "$expected" || -z "$recorded" || "$expected" == "$recorded" ]] || {
        echo "Expected/recorded digest conflict for $name" >&2; return 1;
    }
    expected="${expected:-$recorded}"
    [[ ! -L "$file" && ( ! -e "$file" || -f "$file" ) ]] || {
        echo "Invalid artifact path: $name" >&2; return 1;
    }
    if [[ -e "$file" ]]; then
        [[ -s "$file" && -n "$expected" ]] || {
            echo "Unverified existing artifact: $name; supply an independent digest or remove it explicitly" >&2; return 1;
        }
        actual=$(sha256sum "$file" | cut -d' ' -f1) || return 1
        [[ "$actual" == "$expected" ]] || { echo "CORRUPT $name" >&2; return 1; }
        check_archive "$name" "$file" || return 1
        if [[ -n "$recorded" ]]; then log "== $name present, sha256 verified"; return $?; fi
    else
        log "== downloading $name" || return 1
        PART=$(mktemp "$OUT/.${name}.XXXXXX.part") || return 1
        if ! curl -fL --retry 3 --connect-timeout 30 -o "$PART" -- "$url"; then
            rm -f -- "$PART"; PART=""
            return 1
        fi
        [[ -s "$PART" ]] || { rm -f -- "$PART"; PART=""; echo "Empty download: $name" >&2; return 1; }
        actual=$(sha256sum "$PART" | cut -d' ' -f1) || return 1
        if [[ -n "$expected" && "$actual" != "$expected" ]] || ! check_archive "$name" "$PART"; then
            rm -f -- "$PART"; PART=""
            echo "Digest/archive validation failed: $name" >&2; return 1
        fi
        mv -- "$PART" "$file" || return 1
        PART=""
    fi
    size=$(stat -c %s "$file") || return 1
    log "ARTIFACT $name size=$size sha256=$actual url=$url"
}

default_assets() {
    # name, URL, optional independently verified SHA256 (TSV).
    cat <<'ASSET_LIST'
conjscan-2.1.0.tar.gz	https://github.com/macsy-models/CONJScan/archive/refs/tags/2.1.0.tar.gz
txsscan-1.1.4.tar.gz	https://github.com/macsy-models/TXSScan/archive/refs/tags/1.1.4.tar.gz
plasmidhostfinder-repo.tar.gz	https://bitbucket.org/deaytan/plasmid-host-prediction/get/bb9316d1.tar.gz
plasmidfinder-db-3.0.3.tar.gz	https://bitbucket.org/genomicepidemiology/plasmidfinder_db/get/plasmidfinder-3.0.3.tar.gz
dna_r10.4.1_e8.2_400bps_fast@v4.3.0.zip	https://cdn.oxfordnanoportal.com/software/analysis/dorado/dna_r10.4.1_e8.2_400bps_fast@v4.3.0.zip
mobsuite-data.tar.gz	https://zenodo.org/records/10304948/files/data.tar.gz
platon-db.tar.gz	https://zenodo.org/records/4066768/files/db.tar.gz
bakta-db-light.tar.xz	https://zenodo.org/record/14916843/files/db-light.tar.xz
checkm2-database.tar.gz	https://zenodo.org/record/14897628/files/checkm2_database.tar.gz
dorado-2.1.2-linux-x64.tar.gz	https://cdn.oxfordnanoportal.com/software/analysis/dorado-2.1.2-linux-x64.tar.gz
ASSET_LIST
}

names=(); urls=(); hashes=()
if [[ -n "$ASSETS" ]]; then
    exec 3< "$ASSETS" || exit 2
else
    exec 3< <(default_assets)
fi
# Validate the complete list before any network activity.
while IFS= read -r line <&3 || [[ -n "$line" ]]; do
    [[ -n "$line" && "$line" != \#* ]] || continue
    [[ "$line" == *$'\t'* ]] || { echo "Asset list requires TSV columns" >&2; exit 2; }
    name="${line%%$'\t'*}"; rest="${line#*$'\t'}"; hash=""
    if [[ "$rest" == *$'\t'* ]]; then url="${rest%%$'\t'*}"; hash="${rest#*$'\t'}"; else url="$rest"; fi
    [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._@+-]*$ && "$name" != manifest.txt &&
       "$url" =~ ^(https?|file)://[^[:space:]]+$ &&
       ( -z "$hash" || "$hash" =~ ^[0-9a-f]{64}$ ) ]] || {
        echo "Invalid asset list entry: $name" >&2; exit 2;
    }
    for previous in "${names[@]}"; do
        [[ "$name" != "$previous" ]] || { echo "Duplicate asset: $name" >&2; exit 2; }
    done
    names+=("$name"); urls+=("$url"); hashes+=("$hash")
done
exec 3<&-
((${#names[@]})) || { echo "Empty asset list" >&2; exit 2; }
failed=0
for i in "${!names[@]}"; do
    if ! fetch "${names[i]}" "${urls[i]}" "${hashes[i]}"; then
        log "FAILED ${names[i]} ${urls[i]}" || true
        ((failed+=1))
    fi
done
if ((failed)); then
    log "FAILED $failed of ${#names[@]} artifacts" || true
    exit 1
fi
log "ALL DONE" || exit 1
