import importlib, inspect, re
m = importlib.import_module('editor_toolset.toolsets.blueprint_layout')
src = inspect.getsource(m.GraphFormatter)
out = [src[:1500]]
for mm in re.finditer(r"\n    def (\w+)\(([^)]*)\)[^:]*:\n(\s+\"\"\"[\s\S]*?\"\"\")?", src):
    out.append("def %s(%s)\n%s" % (mm.group(1), mm.group(2), (mm.group(3) or '')[:600]))
# find who uses GraphFormatter
import editor_toolset.toolsets.blueprint as B
for name in ('blueprint', 'blueprint_dsl', 'blueprint_node'):
    try:
        s = inspect.getsource(importlib.import_module('editor_toolset.toolsets.' + name))
        for mm in re.finditer(r".*GraphFormatter.*|.*def \w*(layout|format|arrange)\w*\(.*", s, re.I):
            out.append("%s: %s" % (name, mm.group(0).strip()[:200]))
    except Exception as e: out.append("%s src err %s" % (name, e))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump174.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
