"""Apply the approved unknown-linear rule while retaining explicit topology."""
from Bio import SeqIO
from integron_finder.topology import Topology


def topology_plan(config):
    with open(config.replicon) as stream:
        records = list(SeqIO.parse(stream, 'fasta'))
    ids = [record.id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate IntegronFinder replicon identifier')
    command = 'lin' if config.linear else 'circ' if config.circular else None
    native = Topology(len(records), command, gembase=config.gembase, topology_file=config.topology_file)
    rows = []
    for record in records:
        if record.id.startswith('#') or any(c.isspace() for c in record.id):
            raise ValueError('Replicon identifier cannot be represented in topology file: ' + record.id)
        tokens = set(record.description.split()[1:])
        circular = bool(tokens & {'topology=circular', 'circular=true'})
        linear = bool(tokens & {'topology=linear', 'circular=false', 'not_circular'})
        if circular and linear:
            raise ValueError('Conflicting topology markers: ' + record.id)
        if record.id in native._topology_file:
            value, source = native[record.id], 'explicit_topology_file'
        elif command:
            value, source = command, 'explicit_cli'
        elif config.gembase:
            value, source = native[record.id], 'explicit_gembase_type'
        elif circular or linear:
            value, source = ('circ' if circular else 'lin'), 'explicit_header'
        else:
            value, source = 'lin', 'unknown_treated_as_linear'
        rows.append(dict(id=record.id, topology=value, source=source))
    return dict(policy='unknown_linear_v1', replicons=rows,
                content=''.join(row['id'] + ' ' + row['topology'] + '\n' for row in rows))
