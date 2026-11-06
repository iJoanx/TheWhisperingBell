import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()
p = "/Game/__AgentTemp"
if unreal.EditorAssetLibrary.does_asset_exist(p + "/BP_EvTest"): unreal.EditorAssetLibrary.delete_asset(p + "/BP_EvTest")
f = unreal.BlueprintFactory(); f.set_editor_property("parent_class", unreal.Actor)
bp = at.create_asset("BP_EvTest", p, unreal.Blueprint, f)
B = bp.get_path_name(); EG = B + ":EventGraph"
# test 1: DSL custom event with typed usage
try:
    call('write_graph_dsl', {'graph': {'refPath': EG}, 'code': '(event Custom|T1 (Hour Day Year)\n  (Development|PrintString (Utilities|String|ToString(Float) Hour)))'})
    print("T1:", [(x['type_id'], [(q['name'], q.get('type_id', q.get('type'))) for q in x['output_pins']]) for x in infos(nodes(EG)) if 'T1' in x['type_id']])
except Exception as e: print("T1 err", str(e)[:400])
# test 2: dispatcher signature + Assign
try:
    d = call('add_event_dispatcher', {'blueprint': {'refPath': B}, 'name': 'OnSetTimeSig'})
    dg = d['refPath'] if isinstance(d, dict) else str(d)
    call('add_function_param', {'graph': {'refPath': dg}, 'param_name': 'Hour', 'param_type': 'float', 'input_param': True})
    call('add_function_param', {'graph': {'refPath': dg}, 'param_name': 'Day', 'param_type': 'int', 'input_param': True})
    call('add_function_param', {'graph': {'refPath': dg}, 'param_name': 'Year', 'param_type': 'int', 'input_param': True})
    compile_bp(B)
    ids = [x.get('type_id', x) if isinstance(x, dict) else x for x in types(EG, 'OnSetTimeSig')]
    print("T2 types:", ids)
    for t in ids:
        if 'Assign' in t:
            n = node(EG, t, 0, 600)
            print("T2 created", n)
    print("T2 nodes:", [(x['node']['refPath'].split('.')[-1], x['type_id'], [q['name'] for q in x['output_pins']]) for x in infos(nodes(EG))])
except Exception as e: print("T2 err", str(e)[:600])
