import unreal
out = []
for n in dir(unreal):
    if n.startswith('GeometryScript_'):
        cls = getattr(unreal, n)
        hits = [f for f in dir(cls) if any(k in f for k in ('index_list', 'triangle_id', 'triangle_i_d', 'triangle_positions', 'max_triangle', 'triangle_count', 'num_triangle'))]
        if hits: out.append("%s: %s" % (n, hits))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump227.txt", "w", encoding="utf-8").write("\n".join(out) or "none")
print("ok")
