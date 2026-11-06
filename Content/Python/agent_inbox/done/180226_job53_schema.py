import unreal, json, asyncio, inspect
import toolset_registry._registry_interface as RI
print([n for n in dir(RI) if not n.startswith("_")])
for fn in ("describe_toolset","get_toolset","list_tools","describe_tool","get_tool_schema","get_tool_definitions"):
    if hasattr(RI, fn): print("has", fn, inspect.signature(getattr(RI, fn)))
def call(n, a, ts='editor_toolset.toolsets.blueprint.BlueprintTools'):
    r = RI.execute_tool(ts, n, a)
    if inspect.iscoroutine(r): r = asyncio.new_event_loop().run_until_complete(r)
    return r['returnValue'] if isinstance(r, dict) and 'returnValue' in r else r
G = '/Game/ThirdPerson/Blueprints/CBP_PC_GolKosh.CBP_PC_GolKosh:EventGraph'
for nm in ("K2Node_CustomEvent_4", "K2Node_CustomEvent_5"):
    i = call('get_node_infos', {'nodes': [{'refPath': '/Game/ThirdPerson/Blueprints/CBP_PC_GolKosh.CBP_PC_GolKosh:EventGraph.' + nm}]})[0]
    print(nm, json.dumps({k: v for k, v in i.items() if k not in ('input_pins', 'output_pins')})[:1500])
    o = unreal.load_object(None, '/Game/ThirdPerson/Blueprints/CBP_PC_GolKosh.CBP_PC_GolKosh:EventGraph.' + nm)
    print("  obj", o, [p for p in dir(o) if 'flag' in p.lower() or 'replic' in p.lower() or 'net' in p.lower()])
    for p in ("function_flags","custom_function_name","b_call_in_editor"):
        try: print("   ", p, o.get_editor_property(p))
        except Exception as e: print("   ", p, "?", str(e)[:80])
