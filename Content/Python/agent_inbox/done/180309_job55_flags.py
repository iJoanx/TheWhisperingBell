import unreal, json, asyncio, inspect
import toolset_registry._registry_interface as RI
def call(n, a, ts='editor_toolset.toolsets.object.ObjectTools'):
    r = RI.execute_tool(ts, n, a)
    if inspect.iscoroutine(r): r = asyncio.new_event_loop().run_until_complete(r)
    return r['returnValue'] if isinstance(r, dict) and 'returnValue' in r else r
reg = RI.get_toolset_registry()
s = json.loads(reg.get_toolset_json_schema('editor_toolset.toolsets.object.ObjectTools'))
print("ObjectTools tools:", [t.get('name') for t in s.get('tools', s if isinstance(s, list) else [])][:40] if isinstance(s, dict) else str(s)[:1500])
print(str(s)[:2500])
