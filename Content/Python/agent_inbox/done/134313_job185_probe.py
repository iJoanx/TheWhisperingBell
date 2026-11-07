import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
G = '/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry:ApplySewerView'
for f in ('SetVisibility', 'GetRootComponent', 'GetIsReplicated', 'SetHiddenInGame', 'GetComponentsByClass', 'IsVisible'):
    try: out.append("%s -> %s" % (f, [x.get('type_id') if isinstance(x, dict) else x for x in types(G, f)][:12]))
    except Exception as e: out.append("%s ERR %s" % (f, str(e)[:200]))
world = unreal.EditorLevelLibrary.get_editor_world()
for a in unreal.GameplayStatics.get_all_actors_with_tag(world, 'RDL_Sky'):
    out.append("ACTOR %s (%s)" % (a.get_name(), a.get_class().get_name()))
    for c in a.get_components_by_class(unreal.SceneComponent):
        try: out.append("   %-30s %-28s visible=%s hiddenInGame=%s" % (c.get_name(), c.get_class().get_name(), c.get_editor_property('visible'), c.get_editor_property('hidden_in_game')))
        except Exception as e: out.append("   %s err %s" % (c.get_name(), e))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump185.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
