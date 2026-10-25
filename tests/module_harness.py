"""Materialize a direct-module harness without changing a historical module ABI."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def render_module_harness(harness, include_path, module_source, helper):
    module_source = Path(module_source)
    module_file = module_source if module_source.suffix == '.nf' else module_source.with_suffix('.nf')
    text = Path(harness).read_text()
    quoted_include = repr(include_path)
    assert text.count(quoted_include) == 1, include_path
    text = text.replace(quoted_include, repr(str(module_file.with_suffix(''))))
    if 'autoplasm_helper_0' not in module_file.read_text():
        # Frozen original modules have their original number of inputs. Removing
        # only this helper argument keeps the original failing tool path intact.
        pattern = (r', Channel\.value\(file\("\$\{moduleDir\}/[^"\n]*/bin/'
                   + re.escape(helper) + r'", checkIfExists: true\)\)')
        text, count = re.subn(pattern, '', text)
        assert count == 1, (helper, count)
    # The generated workflow lives in its evidence directory, so moduleDir is
    # different from the checked-in harness directory.
    return text.replace('${moduleDir}/../../bin/', str(ROOT / 'bin') + '/')
