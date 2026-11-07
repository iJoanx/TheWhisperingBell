import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
bp = '/Game/ThirdPerson/Blueprints/BP_Master_PC.BP_Master_PC'
for g in call('list_graphs', {'blueprint': {'refPath': bp}}):
    try: d = str(call('read_graph_dsl', {'graph': {'refPath': g['refPath']}}))
    except Exception as e: out.append("err %s %s" % (g['refPath'], e)); continue
    for blk in d.split("\n\n"):
        if 'Interact' in blk:
            out.append("--- %s\n%s" % (g['refPath'].split(':')[-1], blk[:4000]))
world = unreal.EditorLevelLibrary.get_editor_world()
for tag in ('RDL_Sky', 'RDL_Sewers'):
    acts = unreal.GameplayStatics.get_all_actors_with_tag(world, tag)
    rep = [a.get_name() for a in acts if a.get_editor_property('replicates')]
    out.append("%s: %d actors; replicated: %s" % (tag, len(acts), rep[:40]))
    out.append("  classes: %s" % sorted({a.get_class().get_name() for a in acts})[:40])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump184.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
