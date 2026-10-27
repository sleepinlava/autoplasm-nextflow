nextflow.enable.dsl=2
process MOBSUITE_SOFTWARE_READINESS {
    conda params.environment
    input:
    val(label)
    output:
    path('readiness.json'), emit: readiness
    script:
    """
    python3 - <<'PY'
import hashlib,importlib.metadata,json,pathlib,subprocess,sys
import mob_suite.mob_recon as recon
from mob_suite.version import __version__
from mob_suite.constants import default_database_dir
package=pathlib.Path(recon.__file__).parent
sources={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.rglob('*.py'))}
meta=[json.loads(p.read_text()) for p in (pathlib.Path(sys.prefix)/'conda-meta').glob('*.json')]
assert not any(p['name']=='mob_suite' for p in meta)
assert __version__==importlib.metadata.version('mob-suite')=='3.1.9'
assert sorted(p.name for p in pathlib.Path(default_database_dir).iterdir() if p.name!='__pycache__')==['__init__.py']
versions={name:subprocess.check_output([name,'--version'],text=True).strip() for name in ['mob_recon','mob_typer','mob_cluster','mob_init']}
assert all(v.endswith('3.1.9') for v in versions.values())
dist=importlib.metadata.distribution('mob-suite')
direct=json.loads(dist.read_text('direct_url.json'))
result=dict(prefix=sys.prefix,versions=versions,python_sources=sources,direct_url=direct,conda_packages=[{k:p[k] for k in ['name','version','build','url','sha256']} for p in meta],default_database_files=['__init__.py'],no_native_classification=True,scope='Actual environment creation and CLI version only; no mob_init scientific main/DB/sequence/model download.')
pathlib.Path('readiness.json').write_text(json.dumps(result,indent=2)+'\\n')
PY
    """
}
workflow {
    MOBSUITE_SOFTWARE_READINESS(Channel.value('software-only'))
}
