process PROTOCOL_STRAIN_PROFILE {
    tag { meta.id }
    label 'process_high'
    conda "${projectDir}/envs/instrain.yml"
    publishDir "${params.outdir}/08_epidemiology/instrain", mode: params.publish_dir_mode
    cache 'deep'
    input:
    tuple val(meta), path(bam)
    path catalogue
    path mags
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    tuple val(meta), path("${meta.id}"), emit: profile
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" "${meta.id}.${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 - '${catalogue}' '${mags}' <<'PY'
from pathlib import Path
import sys
from protocol_catalogue import rows
eligible={r['mag_id'] for r in rows(Path(sys.argv[2])/'strain_eligible_mags.tsv')}
with open('scaffold_to_bin.tsv','w') as out:
    for r in rows(Path(sys.argv[2])/'scaffold_to_bin.tsv'):
        if r['mag_id'] in eligible:out.write(r['contig_id']+'\\tM:'+r['mag_id']+'\\n')
    for r in rows(Path(sys.argv[1])/'features.tsv'):
        if r['is_plasmid']=='1':out.write(r['feature_id']+'\\tP:'+r['feature_id']+'\\n')
PY
    samtools index '${bam}'
    inStrain profile '${bam}' '${catalogue}/reference.fasta' -o '${meta.id}' \\
      -s scaffold_to_bin.tsv -p ${task.cpus} --min_cov ${params.protocol_strain_min_coverage}
    cp scaffold_to_bin.tsv '${meta.id}/scaffold_to_bin.tsv'
    python3 -c "from importlib.metadata import version; print(version('inStrain'))" > '${meta.id}/autoplasm_version.txt'
    printf 'sample_id\\tbam_name\\n%s\\t%s\\n' '${meta.id}' '${bam.name}' > '${meta.id}/sample_identity.tsv'
    """
}
process PROTOCOL_STRAIN_COMPARE {
    label 'process_high'
    conda "${projectDir}/envs/instrain.yml"
    publishDir "${params.outdir}/08_epidemiology/instrain", mode: params.publish_dir_mode
    cache 'deep'
    input:
    path profiles,stageAs:'profiles??/*'
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('strain_compare'), emit: comparisons
    script:
    def dirs=(profiles instanceof List ? profiles : [profiles]).collect { "'${it}'" }.join(' ')
    def firstProfile=(profiles instanceof List ? profiles : [profiles])[0]
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    inStrain compare -i ${dirs} -o strain_compare -p ${task.cpus} \\
      -s '${firstProfile}/scaffold_to_bin.tsv' \\
      --min_cov ${params.protocol_strain_min_coverage} --breadth ${params.protocol_min_breadth}
    python3 - ${dirs} <<'PYCODE'
import sys
from pathlib import Path
from protocol_catalogue import rows
from build_shared_catalogue import write_tsv
records=[r for p in sys.argv[1:] for r in rows(Path(p)/'sample_identity.tsv')]
write_tsv(Path('strain_compare/sample_identity.tsv'),['sample_id','bam_name'],([r['sample_id'],r['bam_name']] for r in records))
PYCODE
    """
}
