import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal, toolset_registry._registry_interface as RI
reg = RI.get_toolset_registry()
print("toolsets:", [n for n in dir(reg) if not n.startswith('_')][:30])
try: print("names:", reg.get_toolset_names() if hasattr(reg, 'get_toolset_names') else reg.list_toolsets())
except Exception as e: print("list err", e)
import pkgutil, editor_toolset.toolsets as T
print("toolset modules:", [m.name for m in pkgutil.iter_modules(T.__path__)])
W = unreal.load_asset('/Game/Menus/WB_SetTime')
print("widget bp:", W, type(W).__name__)
try:
    wt = W.get_editor_property('widget_tree'); print("widget_tree", wt)
except Exception as e: print("no widget_tree prop:", str(e)[:100])
cls = unreal.load_class(None, '/Game/Menus/WB_SetTime.WB_SetTime_C')
cdo = unreal.get_default_object(cls)
print("vars:", call('list_variables', {'blueprint': {'refPath': '/Game/Menus/WB_SetTime.WB_SetTime'}}))
