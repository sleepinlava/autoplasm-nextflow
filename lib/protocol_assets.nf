/* Stage imported helper dependencies too: edits must invalidate cached tasks. */
def protocolAssets(root, executable) {
    def names = executable.endsWith('.R') ? [executable] :
        [executable, 'protocol_catalogue.py', 'build_shared_catalogue.py']
    if (executable == 'ancombc2_plasmid.R') names += ['statistics_input_contract.R','statistics_design.R','ancombc2_compat.R']
    return names.unique().collect { file("${root}/${it}",checkIfExists:true) }
}
