import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for n in ('CBP_Familiar_Bolita', 'BP_Master_Familiar'):
    hits = [a for a in ar.get_assets(unreal.ARFilter(package_paths=["/Game"], recursive_paths=True)) if str(a.asset_name) == n]
    for a in hits:
        p = str(a.package_name) + '.' + n
        out.append("######## " + p)
        try:
            cls = unreal.load_class(None, p + '_C'); cdo = unreal.get_default_object(cls)
            out.append("parent: %s" % cls.get_super_class().get_name() if hasattr(cls, 'get_super_class') else '')
            cmc = cdo.get_editor_property('character_movement') if hasattr(cdo, 'character_movement') else None
            if cmc: out.append("cmc %s default_land_mode=%s max_fly=%s" % (cmc.get_class().get_name(), cmc.get_editor_property('default_land_movement_mode'), cmc.get_editor_property('max_fly_speed')))
        except Exception as e: out.append("cdo err %s" % e)
        for g in call('list_graphs', {'blueprint': {'refPath': p}}):
            d = str(call('read_graph_dsl', {'graph': {'refPath': g['refPath']}}))
            out.append("--- %s\n%s" % (g['refPath'].split(':')[-1], d[:6000]))
# key mappings for E / Q
for ad in ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/EnhancedInput", "InputMappingContext")):
    if not str(ad.package_name).startswith("/Game"): continue
    imc = ad.get_asset()
    try:
        for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings"):
            k = str(m.get_editor_property("key").get_editor_property("key_name"))
            if k in ("E", "Q", "SpaceBar", "LeftControl", "C"): out.append("IMC %s %s -> %s" % (ad.package_name, k, m.get_editor_property("action").get_name()))
    except Exception as e: out.append("imc err %s" % e)
# window replication
for n in ('BP_WB_Window', 'BP_WB_Shutter1', 'BP_WB_Insidedoor', 'BP_WB_Sconce'):
    try:
        cdo = unreal.get_default_object(unreal.load_class(None, '/Game/Level/WhisperingBell/Blueprints/%s.%s_C' % (n, n)))
        rc = cdo.get_editor_property('root_component')
        out.append("%s replicates=%s replicate_movement=%s root=%s mobility=%s" % (n, cdo.get_editor_property('replicates'), cdo.get_editor_property('replicate_movement'), rc.get_class().get_name() if rc else None, rc.get_editor_property('mobility') if rc else None))
        try: out.append("   quantization: %s" % cdo.get_editor_property('replicated_movement').to_dict())
        except Exception as e: out.append("   rm err %s" % str(e)[:100])
    except Exception as e: out.append("%s err %s" % (n, str(e)[:120]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump137.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
