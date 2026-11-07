import unreal
out = []
for n in dir(unreal):
    if 'GeometryScript' in n or 'MeshNormals' in n:
        cls = getattr(unreal, n)
        hits = [f for f in dir(cls) if 'flip' in f.lower() or 'reverse' in f.lower() or 'invert' in f.lower()]
        if hits: out.append("%s: %s" % (n, hits))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump220.txt", "w", encoding="utf-8").write("\n".join(out) or "none")
print("ok")
