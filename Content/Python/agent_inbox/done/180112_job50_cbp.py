import unreal, json, asyncio, inspect
import toolset_registry._registry_interface as RI
def call(n, a, ts='editor_toolset.toolsets.blueprint.BlueprintTools'):
    r = RI.execute_tool(ts, n, a)
    if inspect.iscoroutine(r): r = asyncio.new_event_loop().run_until_complete(r)
    return r['returnValue'] if isinstance(r, dict) and 'returnValue' in r else r
out = []
for n in ("CBP_PC_GolKosh", "CBP_PC_Hope"):
    bp = "/Game/ThirdPerson/Blueprints/%s.%s" % (n, n)
    b = unreal.load_asset(bp)
    out.append("######## %s parent=%s" % (bp, b.get_editor_property("parent_class").get_path_name()))
    gs = call('list_graphs', {'blueprint': {'refPath': bp}})
    out.append("graphs " + json.dumps(gs))
    out.append("vars " + json.dumps(call('list_variables', {'blueprint': {'refPath': bp}})))
    for g in gs:
        g = g['refPath']
        out.append("--- DSL " + g + "\n" + str(call('read_graph_dsl', {'graph': {'refPath': g}})))
        nodes = [r['refPath'] for r in call('find_nodes', {'graph': {'refPath': g}, 'title': '', 'entry_points_only': False})]
        ii = call('get_node_infos', {'nodes': [{'refPath': r} for r in nodes]})
        for x in ii:
            pins = []
            for p in x['input_pins'] + x['output_pins']:
                conn = [c['node']['refPath'].split('.')[-1] + ":" + c.get('name', c.get('pin_name', '?')) for c in p.get('connected_pins', [])] if p.get('connected_pins') else []
                dv = p.get('default_value', '')
                pins.append("%s%s%s%s" % (p['name'], "=" + str(dv) if dv not in ('', None) else "", "->" + ",".join(conn) if conn else "", ""))
            out.append("  NODE %s [%s] %s | %s" % (x['node']['refPath'].split(':')[-1], x['type_id'], x.get('title', ''), " ; ".join(pins)))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump50.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok", len(out))
