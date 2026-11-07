import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
ar = unreal.AssetRegistryHelpers.get_asset_registry()
assets = ar.get_assets(unreal.ARFilter(package_paths=['/Game/ThirdPerson', '/Game/Characters'], recursive_paths=True, class_paths=[unreal.TopLevelAssetPath('/Script/Engine', 'Blueprint')]))
for a in assets:
    bp = str(a.package_name) + '.' + str(a.asset_name)
    try: gs = call('list_graphs', {'blueprint': {'refPath': bp}})
    except Exception: continue
    for g in gs:
        try: d = str(call('read_graph_dsl', {'graph': {'refPath': g['refPath']}}))
        except Exception: continue
        for blk in d.split("\n\n"):
            if 'Interact' in blk:
                out.append("--- %s :: %s\n%s" % (a.asset_name, g['refPath'].split(':')[-1], blk[:3500]))
# which actors carry the sewer/sky tags and do they replicate
for tag in ('RDL_Sky', 'RDL_Sewers'):
    acts = unreal.GameplayStatics.get_all_actors_with_tag(unreal.EditorLevelLibrary.get_editor_world(), tag)
    rep = [a.get_name() for a in acts if a.get_editor_property('replicates')]
    out.append("%s: %d actors, replicated ones: %s" % (tag, len(acts), rep[:30]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump183.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
