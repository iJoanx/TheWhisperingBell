import unreal, importlib, pkgutil, inspect
out = []
m = importlib.import_module('editor_toolset.toolsets.blueprint_layout')
out.append("dir: %s" % [n for n in dir(m) if not n.startswith('__')])
if hasattr(m, '__path__'):
    for s in pkgutil.iter_modules(m.__path__):
        out.append("sub %s" % s.name)
        try:
            sm = importlib.import_module('editor_toolset.toolsets.blueprint_layout.' + s.name)
            for n in dir(sm):
                o = getattr(sm, n)
                if isinstance(o, type) and getattr(o, '__module__', '').startswith('editor_toolset'):
                    out.append(" CLASS %s.%s" % (sm.__name__, n))
                    for fn in dir(o):
                        if fn.startswith('_'): continue
                        out.append(" == %s: %s" % (fn, (getattr(getattr(o, fn), '__doc__', '') or '').strip()[:1200]))
        except Exception as e: out.append(" err %s" % e)
try:
    src = inspect.getsource(m)
    out.append("SRC:\n" + src[:3000])
except Exception as e: out.append("src err %s" % e)
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump173.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
