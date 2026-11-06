import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as BT
out = []
out.append("add_object_function_param doc: " + (BT.add_object_function_param.__doc__ or "")[:900])
out.append("add_object_variable doc: " + (BT.add_object_variable.__doc__ or "")[:700])
at = unreal.AssetToolsHelpers.get_asset_tools()
p = "/Game/__AgentTemp"
if unreal.EditorAssetLibrary.does_asset_exist(p + "/BP_DslTest"): unreal.EditorAssetLibrary.delete_asset(p + "/BP_DslTest")
f = unreal.BlueprintFactory(); f.set_editor_property("parent_class", unreal.Actor)
bp = at.create_asset("BP_DslTest", p, unreal.Blueprint, f)
B = bp.get_path_name()
EG = B + ":EventGraph"
try:
    call('write_graph_dsl', {'graph': {'refPath': EG}, 'code': '(event Custom|TestA\n  (Development|PrintString "a"))'})
    call('write_graph_dsl', {'graph': {'refPath': EG}, 'code': '(event Custom|TestB\n  (Development|PrintString "b"))'})
    out.append("after two writes:\n" + str(call('read_graph_dsl', {'graph': {'refPath': EG}})))
except Exception as e: out.append("dsl err " + str(e)[:600])
try:
    g = call('add_function_graph', {'blueprint': {'refPath': B}, 'graph_name': 'Fn1'})
    out.append("fn graph " + json.dumps(g))
    gr = g['refPath'] if isinstance(g, dict) else str(g)
    try:
        r = call('add_object_function_param', {'graph': {'refPath': gr}, 'param_name': 'Who', 'object_class': {'refPath': '/Script/Engine.Actor'}, 'input_param': True})
        out.append("objparam " + json.dumps(r))
    except Exception as e: out.append("objparam err " + str(e)[:900])
    call('add_function_param', {'graph': {'refPath': gr}, 'param_name': 'Flag', 'param_type': 'bool', 'input_param': True})
    call('write_graph_dsl', {'graph': {'refPath': gr}, 'code': '(fn Fn1 (Who Flag)\n  (if Flag\n    (Development|PrintString (Utilities|String|GetDisplayName Who))))'})
    out.append("fn:\n" + str(call('read_graph_dsl', {'graph': {'refPath': gr}})))
except Exception as e: out.append("fn err " + str(e)[:900])
for t in ['Actor|GetAllActorsOfClasswithTag', 'Rendering|SetVisibility', 'Rendering|Components|Light|SetCastShadows', 'Transformation|SetActorLocation', 'Math|Vector|Distance(Vector)', 'Utilities|Casting|CastToPawn', 'Pawn|GetController', 'Pawn|Possess', 'Transformation|GetActorTransform', 'Variables|Transformation|GetRootComponent']:
    try:
        r = tpins(EG, t)
        out.append("PINS %s in=%s out=%s" % (t, [(x['name'], x.get('type_id', x.get('type'))) for x in r['input_pins']], [(x['name'], x.get('type_id', x.get('type'))) for x in r['output_pins']]))
    except Exception as e: out.append("PINS %s err %s" % (t, str(e)[:200]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump61.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
