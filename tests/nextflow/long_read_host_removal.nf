nextflow.enable.dsl=2
include { LONG_READ_HOST_REMOVAL } from '../../subworkflows/long_read_host_removal'

// Read-only downstream observer, not an assembler or a host classifier.
process OBSERVE_LONG_READS {
    input:
    tuple val(meta), path(reads)
    output:
    path "${meta.id}.observed.json"
    script:
    def encodedMeta = groovy.json.JsonOutput.toJson(meta).bytes.encodeBase64().toString()
    """
    python3 - '${encodedMeta}' ${reads} <<'PY'
import base64,gzip,json,sys
from pathlib import Path
meta=json.loads(base64.b64decode(sys.argv[1]))
path=Path(sys.argv[2])
with (gzip.open(path,'rt') if path.suffix.lower()=='.gz' else path.open()) as handle:
    lines=handle.read().splitlines()
assert len(lines)%4==0
records={}
for i in range(0,len(lines),4):
    assert lines[i].startswith('@') and lines[i+2]=='+'
    assert len(lines[i+1])==len(lines[i+3])
    name=lines[i][1:].split()[0]
    assert name not in records
    records[name]=[lines[i+1],lines[i+3]]
Path(meta['id']+'.observed.json').write_text(json.dumps({'meta':meta,'records':records}))
PY
    """
}

workflow {
    ids = params.fixture_case == 'mixed' ? ['A', 'B', 'C'] : ['Z']
    reads = Channel.fromList(ids).map { sid ->
        def reference = sid == 'C' ? null : "${params.fixture_dir}/host ${sid == 'B' ? 'B' : 'A'}.fasta"
        tuple([id:sid, group:'preserved_group', host_reference:reference],
              file("${params.fixture_dir}/${sid} input.fastq.gz", checkIfExists:true))
    }
    LONG_READ_HOST_REMOVAL(reads, params.preset)
    OBSERVE_LONG_READS(LONG_READ_HOST_REMOVAL.out.reads)
}
