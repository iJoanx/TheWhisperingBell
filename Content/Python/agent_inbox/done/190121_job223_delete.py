import unreal, traceback
out = []
eal = unreal.EditorAssetLibrary
ar = unreal.AssetRegistryHelpers.get_asset_registry()
F = "/Game/Sewers/Materials/"
instances = ["MI_SewerWater_Opaque", "MI_SewerWater_Masked", "MI_SewerWater_Translucent",
             "MI_SewerWaterV2_Masked", "MI_SewerWaterV2_Translucent",
             "MI_SewerWaterV3_Opaque", "MI_SewerWaterV3_Masked", "MI_SewerWaterV3_Translucent",
             "MI_SewerWaterV4_Opaque", "MI_SewerWaterV4_Masked", "MI_SewerWaterV4_Translucent",
             "MI_SewerWaterV5_Opaque", "MI_SewerWaterV5_Masked", "MI_SewerWaterV5_Translucent",
             "MI_SewerWaterSLW"]
masters = ["M_SewerWaterFlow", "M_SewerWaterDriftV3", "M_SewerWaterFlowV4", "M_SewerWaterFlowV5", "M_SewerWaterSLW", "M_SewerWater"]
opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
try:
    for group in (instances, masters):          # instances first, then the masters they used
        for n in group:
            p = F + n
            if not eal.does_asset_exist(p):
                out.append("missing (skipped) %s" % n); continue
            refs = [str(r) for r in (ar.get_referencers(p, opts) or []) if str(r) != p]
            if refs:
                out.append("KEPT %s - still used by %s" % (n, refs[:3])); continue
            out.append("deleted %s: %s" % (n, eal.delete_asset(p)))
except Exception:
    out.append(traceback.format_exc()[-1200:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump223.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
