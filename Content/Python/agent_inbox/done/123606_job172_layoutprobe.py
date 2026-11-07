import unreal, importlib, pkgutil
out = []
import editor_toolset.toolsets as T
out.append("toolset modules: %s" % [m.name for m in pkgutil.iter_modules(T.__path__)])
for modname in ('blueprint_layout',):
    try:
        m = importlib.import_module('editor_toolset.toolsets.' + modname)
        for n in dir(m):
            o = getattr(m, n)
            if isinstance(o, type) and n.endswith('Tools'):
                out.append("CLASS %s" % n)
                for fn in dir(o):
                    if fn.startswith('_'): continue
                    f = getattr(o, fn)
                    out.append("== %s\n%s" % (fn, (getattr(f, '__doc__', '') or '').strip()[:1500]))
    except Exception as e: out.append("%s err %s" % (modname, e))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump172.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
