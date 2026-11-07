import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
paths = {'BP_Master_PC': '/Game/ThirdPerson/Blueprints/BP_Master_PC.BP_Master_PC'}
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for nm in ('CBP_PC_Hope', 'CBP_PC_GolKosh'):
    for a in ar.get_assets(unreal.ARFilter(package_paths=['/Game/ThirdPerson', '/Game/Characters'], recursive_paths=True)):
        if str(a.asset_name) == nm: paths[nm] = str(a.package_name) + '.' + nm
flags = ('ignore_client_movement_error_checks_and_correction', 'server_accept_client_authoritative_position', 'network_always_replicate_transform_update_timestamp')
for nm, p in paths.items():
    cls = unreal.load_object(None, p + '_C')
    cdo = unreal.get_default_object(cls)
    cmc = cdo.get_editor_property('character_movement')
    vals = {}
    for f in flags:
        try: vals[f] = cmc.get_editor_property(f)
        except Exception as e: vals[f] = 'n/a'
    out.append("%s CMC %s" % (nm, vals))
# Hope's teleport events
hp = paths.get('CBP_PC_Hope')
if hp:
    for g in call('list_graphs', {'blueprint': {'refPath': hp}}):
        try: d = str(call('read_graph_dsl', {'graph': {'refPath': g['refPath']}}))
        except Exception: continue
        for blk in d.split("\n\n"):
            if 'Teleport' in blk or 'DoTeleport' in blk:
                out.append("--- Hope %s\n%s" % (g['refPath'].split(':')[-1], blk[:2500]))
gm = unreal.EditorLevelLibrary.get_editor_world().get_world_settings().get_editor_property('default_game_mode')
out.append("GameMode override: %s" % gm)
if gm:
    try: out.append("default pawn: %s" % unreal.get_default_object(gm).get_editor_property('default_pawn_class'))
    except Exception as e: out.append("pawn err %s" % e)
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump188.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
