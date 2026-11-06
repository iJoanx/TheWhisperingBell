import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
A = '/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed3.ABP_Unarmed3'
g = [x['refPath'] for x in call('list_graphs', {'blueprint': {'refPath': A}}) if x['refPath'].endswith('.Fly')][0]
print(g)
print(dumpnodes(g))
bs = unreal.load_asset('/Game/Characters/Bolita/Animations/BS_Bolita_Flight') if unreal.EditorAssetLibrary.does_asset_exist('/Game/Characters/Bolita/Animations/BS_Bolita_Flight') else None
if bs is None:
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    for a in ar.get_assets(unreal.ARFilter(package_paths=["/Game"], recursive_paths=True)):
        if str(a.asset_name) == 'BS_Bolita_Flight': bs = a.get_asset(); print("bs at", a.package_name)
if bs:
    for i in (0, 1):
        try:
            p = bs.get_blend_parameter(i) if hasattr(bs, 'get_blend_parameter') else None
            print("axis", i, p.to_dict() if p else None)
        except Exception as e: print("axis", i, "?", e)
    try: print("blend params", [x.to_dict() for x in bs.get_editor_property('blend_parameters')])
    except Exception as e: print("bp err", str(e)[:150])
print("users of ABP_Unarmed3:", [str(r) for r in unreal.AssetRegistryHelpers.get_asset_registry().get_referencers('/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed3', unreal.AssetRegistryDependencyOptions())])
