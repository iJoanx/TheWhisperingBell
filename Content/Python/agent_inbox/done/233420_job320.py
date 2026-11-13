import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
H = '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.CBP_PC_Hope'
bp = unreal.load_asset(H)
try:
    names = [str(n) for n in unreal.BlueprintEditorLibrary.list_graph_names(bp)]
except Exception as e:
    names = []; out.append("list_graph_names err " + str(e)[:300])
out.append("graphs: " + ", ".join(names))
for g in names:
    if 'eleport' in g or 'Trace' in g or 'Aim' in g:
        try: out.append("=== " + g + "\n" + str(call('read_graph_dsl', {'graph': {'refPath': H + ':' + g}})))
        except Exception as e: out.append("=== " + g + " err " + str(e)[:300])
try:
    d = str(call('read_graph_dsl', {'graph': {'refPath': H + ':EventGraph'}}))
    for key in ('Teleport', 'IA_Aim'):
        i = 0
        while True:
            i = d.find('(event', d.find(key, i) - 2000 if d.find(key, i) >= 0 else -1)
            break
    out.append("=== EventGraph (teleport-related sections)")
    # print whole event sections that mention teleport
    secs = d.split('\n(event')
    for s in secs:
        if 'eleport' in s or 'IA_Aim' in s: out.append('(event' + s[:6000])
except Exception as e: out.append("EG err " + str(e)[:300])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump320.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
