import unreal, sys
for n in dir(unreal):
    try: o = getattr(unreal, n)
    except Exception: continue
    if isinstance(o, type):
        for m in ("execute_tool", "call_tool", "invoke_tool"):
            if hasattr(o, m): print("class", n, m)
for name, mod in list(sys.modules.items()):
    if mod and ("toolset" in name or "mcp" in name.lower()):
        for m in ("execute_tool","call_tool","invoke_tool"):
            if hasattr(mod, m): print("mod", name, m)
import editor_toolset.toolsets.blueprint as B
print(B.BlueprintTools, type(B.BlueprintTools), B.BlueprintTools.__mro__ if hasattr(B.BlueprintTools,"__mro__") else "")
print((B.BlueprintTools.read_graph_dsl.__doc__ or "")[:1500])
print((B.BlueprintTools.write_graph_dsl.__doc__ or "")[:1500])
print((B.BlueprintTools.get_graph_dsl_docs.__doc__ or "")[:500])
