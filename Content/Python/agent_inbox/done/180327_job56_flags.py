import unreal, json, asyncio, inspect
import toolset_registry._registry_interface as RI
from editor_toolset.toolsets.object import ObjectTools as OT
def call(n, a, ts='editor_toolset.toolsets.object.ObjectTools'):
    r = RI.execute_tool(ts, n, a)
    if inspect.iscoroutine(r): r = asyncio.new_event_loop().run_until_complete(r)
    return r['returnValue'] if isinstance(r, dict) and 'returnValue' in r else r
print([n for n in dir(OT) if not n.startswith("_") and n not in dir(unreal.Object)])
for n in ("get_properties","set_properties","list_properties","get_property_names"):
    f = getattr(OT, n, None)
    if f: print("==", n, (f.__doc__ or "")[:900])
G = '/Game/ThirdPerson/Blueprints/'
for p in [G+'CBP_PC_GolKosh.CBP_PC_GolKosh:EventGraph.K2Node_CustomEvent_4', G+'CBP_PC_GolKosh.CBP_PC_GolKosh:EventGraph.K2Node_CustomEvent_5']:
    for args in ({'instance': {'refPath': p}, 'property_names': ['FunctionFlags']}, {'instance': {'refPath': p}}):
        try:
            print(p.split('.')[-1], json.dumps(call('get_properties', args))[:1500]); break
        except Exception as e: print("err", str(e)[:400])
