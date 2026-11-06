import unreal, json, asyncio, inspect
import toolset_registry._registry_interface as RI
BPT = 'editor_toolset.toolsets.blueprint.BlueprintTools'
OBT = 'editor_toolset.toolsets.object.ObjectTools'
def call(n, a, ts=BPT):
    r = RI.execute_tool(ts, n, a)
    if inspect.iscoroutine(r): r = asyncio.new_event_loop().run_until_complete(r)
    return r['returnValue'] if isinstance(r, dict) and 'returnValue' in r else r
def infos(refs): return call('get_node_infos', {'nodes': [{'refPath': r} for r in refs]})
def info(ref): return infos([ref])[0]
def nodes(graph): return [r['refPath'] for r in call('find_nodes', {'graph': {'refPath': graph}, 'title': '', 'entry_points_only': False})]
def pin(ref, name, d):
    i = info(ref)
    for p in (i['input_pins'] if d == 'in' else i['output_pins']):
        if p['name'] == name: return p
    raise RuntimeError('no pin %s on %s: %s' % (name, ref, [p['name'] for p in (i['input_pins'] if d == 'in' else i['output_pins'])]))
def connect(o, i): call('connect_pins', {'output_pin': o['pin_id'], 'input_pin': i['pin_id']})
def node(graph, t, x, y): return call('create_node', {'graph': {'refPath': graph}, 'type_id': t, 'pos': {'x': x, 'y': y}})['refPath']
def setv(p, v): call('set_pin_value', {'pin': p['pin_id'], 'value': str(v)})
def getprops(ref, names): return call('get_properties', {'instance': {'refPath': ref}, 'properties': names}, OBT)
def setprops(ref, d): return call('set_properties', {'instance': {'refPath': ref}, 'values': json.dumps(d)}, OBT)
def compile_bp(bp): return call('compile_blueprint', {'blueprint': {'refPath': bp}, 'warnings_as_errors': False})
def types(graph, f): return call('find_node_types', {'graph': {'refPath': graph}, 'type_id_filter': f, 'context_pins': []})
def tpins(graph, t): return call('get_node_type_pins', {'graph': {'refPath': graph}, 'type_id': t})
def dumpnodes(graph):
    out = []
    for x in infos(nodes(graph)):
        ps = []
        for p in x['input_pins'] + x['output_pins']:
            c = p.get('connected_pins') or []
            ps.append(p['name'] + ("=" + str(p.get('default_value')) if p.get('default_value') not in (None, '') else "") + ("->" + ",".join(cc['node']['refPath'].split('.')[-1] for cc in c) if c else ""))
        out.append("  %s [%s] %s" % (x['node']['refPath'].split(':')[-1], x['type_id'], " ; ".join(ps)))
    return "\n".join(out)
