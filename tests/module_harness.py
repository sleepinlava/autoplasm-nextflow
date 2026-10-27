"""Materialize a direct-module harness without changing a historical module ABI."""
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parents[1]


def run_session_uuid(run_name, directory=ROOT):
    """Bind a recovery check to the one actual session created by its cold run."""
    matches = [fields[5] for line in (Path(directory) / '.nextflow/history').read_text().splitlines()
               if len(fields := line.split('\t')) >= 6 and fields[2] == run_name]
    if len(matches) != 1:
        raise ValueError('Expected one exact Nextflow session for ' + run_name + ': ' + repr(matches))
    return str(uuid.UUID(matches[0]))


def render_module_harness(harness, include_path, module_source, helper):
    module_source = Path(module_source)
    module_file = module_source if module_source.suffix == '.nf' else module_source.with_suffix('.nf')
    text = Path(harness).read_text()
    quoted_include = repr(include_path)
    assert text.count(quoted_include) == 1, include_path
    text = text.replace(quoted_include, repr(str(module_file.with_suffix(''))))
    source = module_file.read_text()
    if '_identity)' not in source:
        # Historical modules retain their original resource ABI, even when the
        # current harness carries explicit content identities.
        text = text.replace('Channel.value(resourceInput(params.card))',
                            'Channel.value(file(params.card, checkIfExists: true))')
        text = text.replace('Channel.value(resourceInput(null))', '[]')
        text = text.replace("Channel.value(taggedResourceInput([id:'EXPLICIT_INTERFACE_FIXTURE'], params.gtdbtk_db))",
                            "Channel.value([[id:'EXPLICIT_INTERFACE_FIXTURE'],file(params.gtdbtk_db,checkIfExists:true)])")
    if 'autoplasm_helper_0' not in source:
        # Frozen original modules have their original number of inputs. Removing
        # only this helper argument keeps the original failing tool path intact.
        pattern = (r', Channel\.value\(file\("\$\{moduleDir\}/[^"\n]*/bin/'
                   + re.escape(helper) + r'", checkIfExists: true\)\)')
        text, count = re.subn(pattern, '', text)
        assert count == 1, (helper, count)
    # The generated workflow lives in its evidence directory, so moduleDir is
    # different from the checked-in harness directory.
    return text.replace('${moduleDir}/../../bin/', str(ROOT / 'bin') + '/').replace(
        "'../../lib/resource_inputs'", repr(str(ROOT / 'lib/resource_inputs')))
