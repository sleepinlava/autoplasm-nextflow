#!/usr/bin/env bash
# Source this before running nf-test suites: . tests/nf-test/env.sh
# Java 21 + Nextflow + nf-test runtime + tool paths.
# Podman on SELinux hosts needs bind mounts relabelled; bin/podman here is a
# shim that appends :z to -v/--volume specs and execs the real podman.
#
# 2026-10-17: /tmp is a small tmpfs that was wiped by a reboot; the runtime
# (nextflow launcher, nf-test 0.9.5) now lives in results/nf-test/runtime/
# and native tool execution has moved to podman containers (images persist
# in ~/.local/share/containers).

_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
_runtime="$_root/results/nf-test/runtime"

# Nextflow 26.10.0 accepts Java 17-24; the host default may be newer (mise 27).
_java21="$HOME/.local/share/mise/installs/java/21.0.12+101.0.LTS"
if [ -x "$_java21/bin/java" ]; then
    export JAVA_HOME="$_java21"
fi
export NXF_VER="${NXF_VER:-26.10.0}"
export NFT_BIN="${NFT_BIN:-$_runtime/nf-test}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$_root/results/nf-test/uv-cache}"

_path_add=("$_runtime" "$_runtime/bin" "$JAVA_HOME/bin")
# OPERA-MS (v0.8.3, built from source; OPERA-MS.pl locates siblings by its own dir).
[ -d "$_root/results/nf-test/opera-ms-src" ] && _path_add+=("$_root/results/nf-test/opera-ms-src")
# uv-locked Python tools: genomad, quast.py, multiqc.
[ -d "$_root/tests/nf-test/.venv/bin" ] && _path_add+=("$_root/tests/nf-test/.venv/bin")
# Pipeline R/bin scripts: process-level tests launch scripts whose projectDir
# is not the repo root, so Nextflow would not add the repo bin/ itself.
_path_add+=("$_root/bin")
# SELinux podman shim (harmless when SELinux is permissive/disabled).
if command -v getenforce >/dev/null && [ "$(getenforce)" = "Enforcing" ]; then
    _path_add=("$_root/tests/nf-test/bin" "${_path_add[@]}")
fi

for ((i=${#_path_add[@]}-1; i>=0; i--)); do
    PATH="${_path_add[$i]}:$PATH"
done
export PATH

# Keep work dirs and caches on the home disk, not the small /tmp tmpfs.
export NXF_WORK="${NXF_WORK:-$_root/results/nf-test/nxf-work}"
