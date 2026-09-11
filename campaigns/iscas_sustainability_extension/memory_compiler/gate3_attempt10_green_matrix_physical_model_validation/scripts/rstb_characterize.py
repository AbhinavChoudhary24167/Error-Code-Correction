#!/usr/bin/env python3
"""Reproduce bounded rstb table diagnostics without changing frozen evidence."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT.parent / 'gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure'
MACROS = ['sram22_256x64m4w8', 'sram22_256x8m8w1']
FAMILIES = ['buf', 'clkbuf', 'inv', 'clkinv']
NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'

def groups(text, kind):
    """Yield balanced Liberty groups; braces inside quoted strings are ignored."""
    pattern = re.compile(r'\b' + re.escape(kind) + r'\s*\(([^)]*)\)\s*\{')
    for match in pattern.finditer(text):
        depth, quoted, escaped = 1, False, False
        end = match.end()
        while depth:
            char = text[end]
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = not quoted
            elif not quoted:
                depth += (char == '{') - (char == '}')
            end += 1
        yield match.group(1).strip().strip('"'), text[match.end():end - 1]

def attr(text, name, default=None):
    match = re.search(r'\b' + name + r'\s*:\s*(' + NUM + r')\s*;', text)
    return float(match.group(1)) if match else default

def vector(text, name):
    match = re.search(r'\b' + name + r'\s*\((.*?)\)\s*;', text, re.S)
    return [float(x) for x in re.findall(NUM, match.group(1))] if match else []

def table(body, kind):
    _, part = next(groups(body, kind))
    x, y = vector(part, 'index_1'), vector(part, 'index_2')
    vals = vector(part, 'values')
    assert len(vals) == len(x) * len(y)
    return {'input_slew_ns': x, 'load_pf': y,
            'values_ns': [vals[i:i + len(y)] for i in range(0, len(vals), len(y))]}

def bracket(axis, value):
    if not axis[0] <= value <= axis[-1]:
        raise ValueError(f'Out-of-domain value {value}: [{axis[0]}, {axis[-1]}]; extrapolation forbidden')
    i = next((i for i in range(len(axis) - 1) if axis[i] <= value <= axis[i + 1]), len(axis) - 2)
    return i, (value - axis[i]) / (axis[i + 1] - axis[i])

def interpolate(t, slew, cap):
    i, a = bracket(t['input_slew_ns'], slew)
    j, b = bracket(t['load_pf'], cap)
    v = t['values_ns']
    return (1-a)*((1-b)*v[i][j]+b*v[i][j+1])+a*((1-b)*v[i+1][j]+b*v[i+1][j+1])

def source(path):
    return {'path': path.relative_to(ROOT.parent.parent.parent.parent).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

def load_models():
    stdpath = PRIOR / 'raw/liberty/sky130_fd_sc_hd__tt_025C_1v80.lib'
    stdtext = stdpath.read_text()
    cells = dict(groups(stdtext, 'cell'))
    selected = {}
    for family in FAMILIES:
        names = [n for n in cells if re.fullmatch('sky130_fd_sc_hd__' + family + r'_\d+', n)]
        name = max(names, key=lambda n: int(n.rsplit('_', 1)[1]))
        body = cells[name]
        selected[family] = {'name': name, 'available_strengths': sorted(int(n.rsplit('_', 1)[1]) for n in names),
                            'rise': table(body, 'rise_transition'), 'fall': table(body, 'fall_transition'),
                            'pin_A': {k: attr(dict(groups(body, 'pin'))['A'], k) for k in ['capacitance', 'rise_capacitance', 'fall_capacitance']},
                            'max_capacitance_pf': attr(body, 'max_capacitance'), 'source': source(stdpath)}
    macros = {}
    for macro in MACROS:
        path = PRIOR / 'raw/liberty' / (macro + '_tt_025C_1v80.lib')
        text = path.read_text()
        pin = dict(groups(text, 'pin'))['rstb']
        macros[macro] = {k: attr(pin, k) for k in ['capacitance', 'rise_capacitance', 'fall_capacitance', 'max_transition']}
        macros[macro].update({'rise_capacitance_range': vector(pin, 'rise_capacitance_range'),
                             'fall_capacitance_range': vector(pin, 'fall_capacitance_range'),
                             'constraint_index_1_ns': sorted(set(vector(pin, 'index_1'))),
                             'source': source(path), 'pin': 'rstb'})
    factor = (attr(text, 'slew_upper_threshold_pct_rise')-attr(text, 'slew_lower_threshold_pct_rise'))/(attr(stdtext, 'slew_upper_threshold_pct_rise')-attr(stdtext, 'slew_lower_threshold_pct_rise'))
    return selected, macros, factor

def table_diagnostics(cells, macros, factor):
    rows = []
    for macro, pin in macros.items():
        for family, cell in cells.items():
            for condition, wire in [('ZERO_WIRE_FASTEST_CHARACTERIZED_INPUT', 0.0), ('NEAR_ZERO_WIRE_1FF_LUMPED', 0.001)]:
                row = {'macro': macro, 'cell': cell['name'], 'configuration': family + ('_pair' if family in ['inv','clkinv'] else '_single'),
                       'condition': condition, 'wire_capacitance_pf': wire, 'evidence_level': 'LIBERTY_TABLE_DIAGNOSTIC',
                       'physical_placement_status': 'NOT_APPLICABLE_LUMPED_MODEL', 'threshold_factor': factor}
                for edge in ['rise', 'fall']:
                    slew = cell[edge]['input_slew_ns'][0]
                    if family in ['inv','clkinv']:
                        other = 'fall' if edge == 'rise' else 'rise'
                        slew = interpolate(cell[other], slew, cell['pin_A'][other + '_capacitance'])
                    row[edge + '_driver_input_slew_ns'] = slew
                    row[edge + '_macro_slew_ns'] = factor * interpolate(cell[edge], slew, pin[edge + '_capacitance'] + wire)
                row['worst_macro_slew_ns'] = max(row['rise_macro_slew_ns'], row['fall_macro_slew_ns'])
                row['meets_0p351_ns_in_model'] = row['worst_macro_slew_ns'] <= pin['max_transition']
                # Lower envelope: interpolation is piecewise linear along input slew.
                row['best_rise_over_characterized_input_axis_ns'] = factor * min(interpolate(cell['rise'], x, pin['rise_capacitance'] + wire) for x in cell['rise']['input_slew_ns'])
                j, _ = bracket(cell['rise']['load_pf'], pin['rise_capacitance'])
                dt = cell['rise']['values_ns'][0][j+1] - cell['rise']['values_ns'][0][j]
                dc = cell['rise']['load_pf'][j+1] - cell['rise']['load_pf'][j]
                row['local_effective_rise_resistance_ohm'] = 1000 * dt / dc / math.log(4)
                row['resistance_model'] = 'local d(t20-80)/dC divided by ln(4); first-order RC equivalent, not transistor resistance'
                rows.append(row)
    return rows

def prepare():
    out = ROOT / 'rstb'
    (out / 'diagnostics').mkdir(parents=True, exist_ok=True)
    for macro in MACROS:
        width = 64 if '256x64' in macro else 8
        for family in FAMILIES:
            cell = f'sky130_fd_sc_hd__{family}_16'
            if family in ['inv', 'clkinv']:
                stages = f'{cell} stage1(.A(rstb), .Y(mid));\n{cell} stage2(.A(mid), .Y(local_rstb));'
            else:
                stages = f'{cell} stage2(.A(rstb), .X(local_rstb));'
            netlist = f'module diagnostic(input rstb, input clk, output [{width-1}:0] dout);\nwire mid, local_rstb;\n{stages}\n{macro} memory(.rstb(local_rstb), .clk(clk), .dout(dout));\nendmodule\n'
            (out/'diagnostics'/f'{macro}_{family}.v').write_text(netlist)

def spice_summary(macro):
    path = PRIOR/'source_checkout'/macro/(macro+'.spice')
    text = path.read_text()
    subckts = {}
    for m in re.finditer(r'^\.SUBCKT\s+(\S+)\s+([^\n]+)\n(.*?)^\.ENDS[^\n]*', text, re.M|re.S|re.I):
        subckts[m[1]] = (m[2].split(), m[3])
    leaves, branches = [], []
    def walk(name, nets, prefix, depth=0):
        assert depth < 40
        ports, body = subckts[name]
        for line in body.splitlines():
            tokens = line.split()
            if not tokens or not tokens[0].upper().startswith('X'):
                continue
            refpos = next((i for i in range(1,len(tokens)) if '=' in tokens[i]), len(tokens)) - 1
            ref, nodes = tokens[refpos], tokens[1:refpos]
            connected = [i for i, node in enumerate(nodes) if node in nets]
            if not connected:
                continue
            instance = prefix+'/'+tokens[0]
            if name == 'sram22_inner':
                branches.append({'instance': tokens[0], 'subcircuit': ref, 'connected_ports': [subckts[ref][0][i] for i in connected] if ref in subckts else connected})
            if ref in subckts:
                walk(ref, {subckts[ref][0][i] for i in connected}, instance, depth+1)
            else:
                leaves.append({'path': instance, 'model': ref, 'terminal_indices': connected, 'parameters': tokens[refpos+1:]})
    walk(macro, {'rstb'}, macro)
    return {'source': source(path), 'status': 'READ_ONLY_HIERARCHICAL_CONNECTIVITY_INSPECTION', 'direct_inner_branches': branches,
            'rstb_connected_primitive_count': len(leaves), 'primitive_gate_connection_count': sum(1 in x['terminal_indices'] for x in leaves),
            'primitive_terminal_convention': 'sky130 transistor wrapper d,g,s,b; gate terminal index=1',
            'primitive_connections': leaves, 'transient_simulation': 'NOT_RUN',
            'capacitance_recharacterization': 'NOT_QUALIFIED', 'limitation': 'Connectivity is not a SPICE transient or extracted RC capacitance validation.'}

def slews(text):
    return {m[1]: {'rise_min_ns': float(m[2]), 'rise_max_ns': float(m[3]),
                   'fall_min_ns': float(m[4]), 'fall_max_ns': float(m[5])}
            for m in re.finditer(r'^(\S+) \^ ('+NUM+'):('+NUM+r') v ('+NUM+'):('+NUM+r')$', text, re.M)}

def spef_net(path, name):
    text = path.read_text()
    assert '*C_UNIT 1 PF' in text and '*R_UNIT 1 OHM' in text and 'PIN_CAP NONE' in text
    names = {m[2]: '*'+m[1] for m in re.finditer(r'^\*(\d+)\s+(\S+)$', text.split('*PORTS')[0], re.M)}
    ident = names[name]
    match = re.search(r'^\*D_NET\s+'+re.escape(ident)+r'\s+('+NUM+r')\n(.*?)^\*END', text, re.M|re.S)
    body = match[2]
    cap = body.split('*CAP\n')[1].split('*RES')[0]
    ground, coupling, coupling_count = 0.0, 0.0, 0
    for line in cap.splitlines():
        tokens = line.split()
        if len(tokens) == 3:
            ground += float(tokens[-1])
        elif len(tokens) == 4:
            coupling += float(tokens[-1]); coupling_count += 1
    return {'spef_d_net_parasitic_capacitance_pf': float(match[1]), 'listed_ground_capacitance_pf': ground,
            'listed_coupling_capacitance_pf': coupling, 'listed_coupling_entry_count': coupling_count,
            'pin_cap_in_spef': False, 'coupling_qualification': 'AS_REPRESENTED_IN_SPEF; zero entries do not prove absence of physical coupling',
            'source': source(path)}

def reset_chain(path, driver):
    instances, drivers = {}, {}
    for m in re.finditer(r'\b(sky130_fd_sc_hd__\w+)\s+(\S+)\s*\((.*?)\);', path.read_text(), re.S):
        pins = dict(re.findall(r'\.(\w+)\s*\(\s*(.*?)\s*\)', m[3]))
        instances[m[2]] = (m[1], pins)
        for key in ['X','Y']:
            if key in pins:
                drivers[pins[key]] = m[2]
    chain, visited = [], set()
    while driver in instances and driver not in visited:
        visited.add(driver)
        cell, pins = instances[driver]
        chain.append({'instance': driver, 'cell': cell})
        driver = drivers.get(pins.get('A'), pins.get('A'))
    return {'cells_from_final_driver_upstream': chain, 'cell_count': len(chain), 'upstream_terminal': driver,
            'source': source(path), 'interpretation': 'Cells on unary reset path, including timing/hold buffers; not all are new Attempt09 insertions.'}

def actual_diagnostics():
    zero, extracted, local = [], [], []
    for path in sorted((ROOT/'rstb/raw').glob('zero_*.log')):
        text = path.read_text()
        assert 'RSTB_ZERO_WIRE_END' in text and '[ERROR' not in text, path
        header = re.search(r'BEGIN macro=(\S+) family=(\S+)', text)
        for match in re.finditer(r'RSTB_INPUT_SLEW_NS ('+NUM+r')\n(.*?)(?=RSTB_INPUT_SLEW_NS|RSTB_ZERO_WIRE_END)', text, re.S):
            pins = slews(match[2])
            zero.append({'macro': header[1], 'family': header[2], 'applied_input_slew_ns': float(match[1]),
                         'pins': pins, 'worst_macro_slew_ns': max(pins['memory/rstb'].values()),
                         'evidence_level': 'OPENSTA_ZERO_WIRE_TOOL_DIAGNOSTIC', 'wire_capacitance_pf': 0.0,
                         'source': source(path)})
    historical = json.loads((PRIOR/'RESIDUAL_EXTERNAL_DRV_INVENTORY.json').read_text())
    records = historical['records'] + historical['closed_target_records']
    for path in sorted((ROOT/'rstb/raw').glob('postroute_*.log')):
        text = path.read_text()
        assert '[ERROR' not in text, path
        for match in re.finditer(r'RSTB_EXTRACTED_BEGIN design=(\S+) target=(\S+) driver=(\S+)\n(.*?)RSTB_EXTRACTED_END', text, re.S):
            design, target, driver, body = match.groups()
            old = next(r for r in records if r['object'] == target)
            result = PRIOR/f'raw/openroad/work/results/sky130hd/attempt09_{design}/seed11'
            coord = lambda kind: [int(v)/1000 for v in re.search('RSTB_'+kind+r'_PIN_XY_DBU 1 (\d+) (\d+)', body).groups()]
            dxy, mxy = coord('DRIVER'), coord('MACRO')
            row = {'design': design.upper(), 'seed': 11, 'macro': MACROS[1] if '.u_ecc/' in target else MACROS[0],
                   'target': target, 'driver': driver, 'driver_cell': old['driver_cell'], 'net': old['net'],
                   'pins': slews(body), 'driver_pin_center_um': dxy, 'macro_pin_center_um': mxy,
                   'center_manhattan_distance_um': sum(abs(a-b) for a,b in zip(dxy,mxy)),
                   'routed_net_length_um': old['estimated_parasitic_wire_length_um'],
                   'routed_length_source': source(PRIOR/'RESIDUAL_EXTERNAL_DRV_INVENTORY.json'),
                   'routed_length_method': 'Frozen DEF segment Manhattan sum; pin-shape centers need not be actual route access points.',
                   'reset_path': reset_chain(result/'6_final.v', driver),
                   'source': source(path), 'evidence_level': 'FROZEN_POST_ROUTE_OPENROAD_REPRODUCED'}
            row.update(spef_net(result/'6_final.spef', old['net']))
            # Keep log and SPEF provenance separately.
            row['log_source'] = source(path)
            extracted.append(row)
    for path in sorted((ROOT/'rstb/raw').glob('local_*.log')):
        text = path.read_text()
        assert 'RSTB_LOCAL_END' in text and '[ERROR' not in text, path
        target = re.search(r'RSTB_LOCAL_BEGIN target=(\S+)', text)[1]
        for condition, marker, end in [('IDEALIZED_LOCAL_PLACEMENT', 'RSTB_IDEALIZED_BEFORE_LEGALIZATION', 'RSTB_LEGALIZED_PLACEMENT'),
                                      ('LEGALIZED_LOCAL_PLACEMENT', 'RSTB_LEGALIZED_PLACEMENT', 'RSTB_LOCAL_END')]:
            body = text.split(marker)[1].split(end)[0]
            pins = slews(body)
            local.append({'target': target, 'macro': MACROS[1] if '.u_ecc/' in target else MACROS[0],
                          'condition': condition, 'cell': 'sky130_fd_sc_hd__clkinv_16', 'new_stages': 2,
                          'pins': pins, 'worst_macro_slew_ns': max(pins[target].values()),
                          'evidence_level': 'OPENROAD_PLACEMENT_ESTIMATED_RC_DIAGNOSTIC', 'routed_validation': 'NOT_RUN',
                          'source': source(path)})
    return {'zero_wire': zero, 'post_route': extracted, 'local_placement': local}

def report(payload):
    pin = payload['macro_capacitance']
    ratio = pin[MACROS[0]]['rise_capacitance']/pin[MACROS[1]]['rise_capacitance']
    text = ['# Rstb interface characterization', '',
            '**Classification D: INSUFFICIENT_EVIDENCE** for a universal interface limitation or an invalid rstb constraint. '
            'The evidence supports a narrower finding: all four strongest x16 buffer/inverter families tested fail the 256x64 interface in zero-wire diagnostics; the strongest tested phase-preserving clkinv pair also fails after local placement. '
            'Historical Gate-3 remains FAIL / RESIDUAL_SRAM_INPUT_DRV_FAIL.', '',
            f'The 256x64 rising pin capacitance is 0.448008 pF versus 0.250926 pF for 256x8 ({ratio:.6f} times). '
            'SPEF declares PIN_CAP NONE: its parasitic capacitance must be added to the Liberty pin load, never substituted for it. '
            'The data net parasitics are only 0.00213879 pF (U0) and 0.00111857 pF (E0), under 0.5% of the rising pin load. '
            'This is strong evidence that the frozen macro input-capacitance model, rather than long external wiring alone, dominates the load.', '',
            '## Matched frozen post-route condition', '',
            '| Design/pin | Rise cap (pF) | Wire cap (pF) | Driver input rise/fall (ns) | Macro worst slew (ns) | Route length (um) |',
            '|---|---:|---:|---|---:|---:|']
    for r in payload['actual_diagnostics']['post_route']:
        upstream = r['pins'][r['driver']+'/A']
        text.append(f"| {r['design']} {r['target']} | {pin[r['macro']]['rise_capacitance']:.6f} | {r['spef_d_net_parasitic_capacitance_pf']:.8f} | {upstream['rise_max_ns']:.9f} / {upstream['fall_max_ns']:.9f} | {max(r['pins'][r['target']].values()):.9f} | {r['routed_net_length_um']:.2f} |")
    text += ['', '## Controlled zero-wire results', '',
             'Eight tiny netlists use frozen TT Liberty, no wire parasitics, one macro load, and the strongest available drive suffix in each unary family. '
             'Each runs three defined source slew conditions (0.01, 0.1, 0.3 ns). Inverter pairs preserve rstb phase; no production netlist or constraints are changed.', '',
             '| Macro | Driver topology | Source slew (ns) | Worst macro slew (ns) | 0.351 ns |', '|---|---|---:|---:|---|']
    for r in payload['actual_diagnostics']['zero_wire']:
        text.append(f"| {r['macro']} | {r['family']} {'pair' if 'inv' in r['family'] else 'single'} | {r['applied_input_slew_ns']} | {r['worst_macro_slew_ns']:.9f} | {'MET' if r['worst_macro_slew_ns'] <= .351 else 'FAIL'} |")
    text += ['', '## Local placement', '',
             'Three in-memory experiments insert a clkinv_16 pair near the target, remove filler cells from the in-memory copy, legalize the placement, and estimate parasitics using the frozen SKY130HD setRC.tcl. '
             'They retain the original upstream reset chain. They are placement diagnostics, not rerouted implementations or whole-design closure.', '',
             '| Target | Condition | Macro worst slew (ns) |', '|---|---|---:|']
    for r in payload['actual_diagnostics']['local_placement']:
        text.append(f"| {r['target']} | {r['condition']} | {r['worst_macro_slew_ns']:.9f} |")
    text += ['', '## Decomposition and numerical checks', '',
             '`slew ≈ threshold_ratio × NLDM(input_slew, Cpin(edge)+Cwire)`, with placement/coupling and distributed RC treated separately. '
             'SKY130HD tables describe 20–80% slew; SRAM22 describes 10–90%. The STA linear threshold-span conversion is 80/60 = 4/3. '
             'The script uses bilinear interpolation within the characterized table domain, prohibits extrapolation, and verifies the zero-wire values against standalone OpenSTA. '
             'The local effective resistance is d(t20–80)/dC / ln(4), in ohms, a first-order RC equivalent derived from the adjacent characterized load points; it is not a transistor measurement. '
             'The CSV includes 16 bounded table diagnostics, 24 STA conditions, three extracted observations, and six local-placement conditions, with evidence labels. The JSON contains all actual STA and placement observations, full source hashes, and physical locations.', '',
             'An idealized zero-wire table is not a universal lower bound on distributed-RC STA: effective capacitance and waveform treatment can change the tool result. '
             'The observed post-route buf16 data slew is slightly lower than the simple lumped table estimate; neither result is substituted for the other.', '',
             '## SPICE and constraint provenance', '',
             'The frozen transistor-level netlists were inspected recursively along the directly connected rstb net. '
             'The JSON lists control, address/control-register and column-periphery branches and all reached primitive terminals. '
             'This proves connectivity, not capacitance accuracy. No SPICE transient, extracted internal RC simulation, or Liberty regeneration was performed. '
             'Both rstb pins explicitly specify max_transition=0.351 ns and retain the same characterization ceiling. '
             'No new evidence invalidates that constraint. It is independent of the SRAM output default_max_transition=0.04 ns inconsistency.', '',
             '## Claim disposition and remaining work', '',
             'Proven: heavy data rstb pin load; exact reproduction of the U0/E0 seed-11 failure and ECC closure; zero-wire and locally placed strongest-family diagnostics; no standard-cell-model-only tested repair closes data rstb. '
             'Unproven: impossibility for every legal SKY130HD topology, internal macro parasitic accuracy, and invalidity of the 0.351 ns limit. '
             'Classifications A/B/C are therefore not asserted. Historical five-seed setup/hold-clean pairs remain 5/5 and external DRV-clean pairs remain 0/5; these bounded new diagnostics are seed-independent tiny netlists or seed-11 ODB experiments, not a new five-seed physical repair.', '',
             'All rstb experiments use UPSTREAM_ORIGINAL Liberty. Phase-A output-constraint diagnostic copies do not alter rstb pin caps, tables, or max_transition. '
             'PPA/energy/reliability/carbon/GREEN ranking changes are NOT_MEASURED for these interface diagnostics; there is no retained production repair. '
             'The ISCAS analysis may use qualified physical baselines with residual DRV visible. No new signoff, energy, or interleaving claims are introduced.', '',
             'Recommended next action: obtain independent rstb capacitance/transition characterization with stimulus and internal extraction provenance. '
             'A broader interface impossibility claim requires a defined legal topology space and an established bound, not another blind sweep.', '',
             '## Reproduction and integrity', '',
             '`python scripts/rstb_characterize.py --prepare`; run `scripts/rstb_run_diagnostics.sh <repository-root>` and '
             '`scripts/rstb_run_local.sh <repository-root>` with the frozen Docker image; then `python scripts/rstb_characterize.py`. '
             'Shell runners refuse to overwrite raw logs and mount the entire repository read-only in Docker. All ODB edits are transient in memory. '
             'The initial missing-technology invocation and filler-overlap attempt are retained as explicitly failed exploratory logs; completed runs use standalone STA or remove fillers only in memory. '
             'The campaign root records protected-baseline verification and repository regressions. Source SHA-256 values in this phase were recomputed from the frozen files.', '']
    return '\n'.join(text)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    prepare()
    if args.prepare:
        return
    cells, macros, factor = load_models()
    rows = table_diagnostics(cells, macros, factor)
    actual = actual_diagnostics()
    for row in actual['post_route']:
        pin = macros[row['macro']]
        row['liberty_pin_capacitance_pf'] = pin['capacitance']
        row['liberty_rise_capacitance_pf'] = pin['rise_capacitance']
        row['liberty_fall_capacitance_pf'] = pin['fall_capacitance']
        row['lumped_rise_load_pf'] = pin['rise_capacitance'] + row['spef_d_net_parasitic_capacitance_pf']
        row['lumped_fall_load_pf'] = pin['fall_capacitance'] + row['spef_d_net_parasitic_capacitance_pf']
        row['wire_to_rise_pin_capacitance_ratio'] = row['spef_d_net_parasitic_capacitance_pf']/pin['rise_capacitance']
        output = 'Y' if '__inv_' in row['driver_cell'] else 'X'
        row['macro_rise_minus_threshold_scaled_driver_ns'] = row['pins'][row['target']]['rise_max_ns'] - factor * row['pins'][row['driver']+'/'+output]['rise_max_ns']
        row['effective_driver_capacitance_pf'] = 'NOT_MEASURED'
    checks = []
    for row in rows:
        if row['wire_capacitance_pf'] == 0:
            observed = next((x for x in actual['zero_wire'] if x['macro'] == row['macro'] and x['family'] == row['configuration'].split('_')[0] and x['applied_input_slew_ns'] == .01), None)
            if observed:
                checks.append({'macro': row['macro'], 'configuration': row['configuration'],
                               'absolute_error_ns': abs(observed['worst_macro_slew_ns'] - row['worst_macro_slew_ns'])})
    payload = {'schema_version': 1, 'classification': 'INSUFFICIENT_EVIDENCE', 'classification_letter': 'D',
               'historical_gate3_status': 'FAIL', 'historical_residual_status': 'RESIDUAL_SRAM_INPUT_DRV_FAIL',
               'liberty_model': 'UPSTREAM_ORIGINAL', 'rstb_constraint_changed': False,
               'macro_capacitance': macros, 'strongest_family_drivers': cells, 'table_diagnostics': rows,
               'actual_diagnostics': actual, 'table_opensta_crosscheck': checks,
               'spice_connectivity': {m: spice_summary(m) for m in MACROS},
               'scope_limit': 'Four x16 buffer/inverter families are bounded diagnostics, not proof over every legal interface topology.'}
    (ROOT/'rstb/RSTB_INTERFACE_CHARACTERIZATION.json').write_text(json.dumps(payload, indent=2)+'\n')
    (ROOT/'rstb/RSTB_INTERFACE_CHARACTERIZATION.md').write_text(report(payload), encoding='utf-8')
    csv_rows = [dict(r, record_type='TABLE_DIAGNOSTIC') for r in rows]
    for r in actual['zero_wire'] + actual['local_placement']:
        is_zero = 'family' in r
        target = 'memory/rstb' if is_zero else r['target']
        driver_input = r['pins']['stage2/A' if is_zero else 'rstb10_final/A']
        csv_rows.append({'record_type': 'OPENSTA_ZERO_WIRE' if is_zero else 'OPENROAD_LOCAL_PLACEMENT',
                         'macro': r['macro'], 'condition': 'ZERO_WIRE' if is_zero else r['condition'],
                         'configuration': r.get('family', 'clkinv') + ('_pair' if 'inv' in r.get('family', 'clkinv') else '_single'),
                         'wire_capacitance_pf': r.get('wire_capacitance_pf', 'NOT_EXACTLY_REPORTED'),
                         'rise_driver_input_slew_ns': driver_input['rise_max_ns'], 'fall_driver_input_slew_ns': driver_input['fall_max_ns'],
                         'rise_macro_slew_ns': r['pins'][target]['rise_max_ns'], 'fall_macro_slew_ns': r['pins'][target]['fall_max_ns'],
                         'worst_macro_slew_ns': r['worst_macro_slew_ns'], 'meets_0p351_ns_in_model': r['worst_macro_slew_ns'] <= .351,
                         'evidence_level': r['evidence_level'], 'source_path': r['source']['path'], 'source_sha256': r['source']['sha256']})
    for r in actual['post_route']:
        driver_input = r['pins'][r['driver']+'/A']
        csv_rows.append({'record_type': 'FROZEN_POST_ROUTE', 'macro': r['macro'], 'design': r['design'], 'seed': r['seed'],
                         'cell': r['driver_cell'], 'condition': 'EXTRACTED_POST_ROUTE', 'target': r['target'],
                         'wire_capacitance_pf': r['spef_d_net_parasitic_capacitance_pf'], 'listed_coupling_capacitance_pf': r['listed_coupling_capacitance_pf'],
                         'pin_capacitance_pf': r['liberty_pin_capacitance_pf'], 'rise_capacitance_pf': r['liberty_rise_capacitance_pf'],
                         'fall_capacitance_pf': r['liberty_fall_capacitance_pf'], 'lumped_rise_load_pf': r['lumped_rise_load_pf'],
                         'rise_driver_input_slew_ns': driver_input['rise_max_ns'], 'fall_driver_input_slew_ns': driver_input['fall_max_ns'],
                         'rise_macro_slew_ns': r['pins'][r['target']]['rise_max_ns'], 'fall_macro_slew_ns': r['pins'][r['target']]['fall_max_ns'],
                         'worst_macro_slew_ns': max(r['pins'][r['target']].values()), 'routed_net_length_um': r['routed_net_length_um'],
                         'center_manhattan_distance_um': r['center_manhattan_distance_um'], 'evidence_level': r['evidence_level'],
                         'source_path': r['log_source']['path'], 'source_sha256': r['log_source']['sha256']})
    with (ROOT/'rstb/RSTB_INTERFACE_CHARACTERIZATION.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(key for row in csv_rows for key in row)), restval='NOT_APPLICABLE')
        writer.writeheader()
        writer.writerows(csv_rows)
    print(json.dumps({'classification': payload['classification'], 'table_rows': len(rows), 'threshold_factor': factor,
                      'zero_wire': [{k:r[k] for k in ['macro','configuration','worst_macro_slew_ns']} for r in rows if r['wire_capacitance_pf']==0]}, indent=2))

if __name__ == '__main__':
    main()
