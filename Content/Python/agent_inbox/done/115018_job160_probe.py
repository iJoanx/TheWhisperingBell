import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal, inspect
from editor_toolset.toolsets.blueprint import BlueprintTools as BT
out = []
for n in ("add_variable",):
    f = getattr(BT, n, None)
    out.append("===== %s %s\n%s" % (n, "", (f.__doc__ or "").strip()[:2000]))
G = '/Game/Menus/WB_SetTime.WB_SetTime:EventGraph'
for flt in ('EventTick', 'GetWidgetfromName', 'CastToTextBlock', 'IsValidIndex', 'ToText(String)', 'SetText(Text)', 'Array|Get', 'Array|Length'):
    try:
        r = types(G, flt)
        out.append("%s -> %s" % (flt, [x.get('type_id') if isinstance(x, dict) else x for x in r][:12]))
    except Exception as e: out.append("%s ERR %s" % (flt, str(e)[:300]))
try: out.append("props %s" % getprops('/Game/Menus/WB_SetTime.WB_SetTime:WidgetTree.MonthText', ['bIsVariable']))
except Exception as e: out.append("getprops err %s" % str(e)[:300])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump160.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
