import inspect
from editor_toolset.toolsets.blueprint import BlueprintTools, NodeInfo, PinInfo
for n, f in inspect.getmembers(BlueprintTools):
    if n.startswith("_"): continue
    try: sig = str(inspect.signature(f))
    except Exception: sig = "?"
    print(n, sig[:300])
print("NodeInfo", [f for f in getattr(NodeInfo, "__dataclass_fields__", {})])
print("PinInfo", [f for f in getattr(PinInfo, "__dataclass_fields__", {})])
import editor_toolset.toolsets.blueprint_node as BN
print("bn", [n for n in dir(BN) if not n.startswith("_")])
