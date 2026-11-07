import importlib, inspect, pkgutil, re, sys
out = []
import editor_toolset.toolsets.blueprint as B
mods = [B]
if hasattr(B, '__path__'):
    for s in pkgutil.walk_packages(B.__path__, B.__name__ + '.'):
        try: mods.append(importlib.import_module(s.name))
        except Exception as e: out.append("imp err %s %s" % (s.name, e))
for m in mods:
    try: src = inspect.getsource(m)
    except Exception: continue
    i = src.find('def arrange_nodes')
    if i >= 0:
        out.append("FOUND in %s file %s" % (m.__name__, getattr(m, '__file__', '')))
        out.append(src[i-300:i+2200])
    for mm in re.finditer(r".*arrange_nodes.*", src):
        out.append("%s: %s" % (m.__name__, mm.group(0).strip()[:200]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump176.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
