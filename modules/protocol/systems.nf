process MOBMESS_SYSTEMS {
    label 'process_high'
    conda "${projectDir}/envs/mobmess.yml"
    publishDir "${params.outdir}/09_comparative/mobmess", mode: params.publish_dir_mode
    cache 'deep'
    input:
    path catalogue
    path complete_ids
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('systems'), emit: systems
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    mkdir native
    python3 - '${catalogue}' '${complete_ids}' <<'PY'
import sys
from pathlib import Path
from protocol_catalogue import rows
known = {r['plasmid_id'] for r in rows(Path(sys.argv[1])/'structure.tsv') if r['completeness'] in ('independently_supported','predicted_near_complete')}
ids = {r['plasmid_id'] for r in rows(Path(sys.argv[1])/'structure.tsv')}
if not known <= ids: raise ValueError('complete_ids contains IDs absent from the frozen catalogue')
with open('complete.tsv','w') as f:
    for fid in sorted(ids): f.write(fid+'\\t'+str(fid in known)+'\\n')
PY
    if [ -s '${catalogue}/plasmids.fasta' ] && grep -q 'True' complete.tsv; then
        mobmess systems --sequences '${catalogue}/plasmids.fasta' --complete complete.tsv \\
            --output native/mobmess --threads ${task.cpus}
    fi
    python3 analysis_code/protocol_systems.py normalize --native native --catalogue '${catalogue}' --output systems
    cp -r native systems/
    python3 -c "import importlib.metadata; print(importlib.metadata.version('mobmess'))" > systems/version.txt
    """
}
process SYSTEM_ABUNDANCE {
    label 'process_single'
    conda "${projectDir}/envs/catalogue.yml"
    container 'python:3.12-slim'
    publishDir "${params.outdir}/tables", mode: params.publish_dir_mode
    cache 'deep'
    input:
    path abundance
    path systems
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('system_abundance.tsv'), emit: abundance
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/protocol_systems.py aggregate --abundance '${abundance}' --systems '${systems}' --output system_abundance.tsv
    """
}
