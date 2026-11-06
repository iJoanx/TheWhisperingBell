import unreal, inspect
from editor_toolset.toolsets.blueprint import BlueprintTools as BT
names = [n for n in dir(BT) if not n.startswith('_') and n not in dir(unreal.Object)]
print(names)
for n in names:
    if any(k in n for k in ('dup', 'copy', 'paste', 'rpc', 'replic', 'flag', 'net', 'event')):
        print("==", n, (getattr(BT, n).__doc__ or "")[:600])
import toolset_registry._registry_interface as RI
reg = RI.get_toolset_registry()
from editor_toolset.toolsets.object import ObjectTools as OT
print("OT:", [n for n in dir(OT) if not n.startswith('_') and n not in dir(unreal.Object)])
