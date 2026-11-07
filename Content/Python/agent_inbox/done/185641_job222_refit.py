import sys, importlib, traceback
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_water_underside as swu
    importlib.reload(swu)
    fixed, inst = swu.refit()
    out.append("refitted %d components (%d instances); turned-over meshes made/used: %d" % (fixed, inst, len(swu._FLIPPED)))
    sample = unreal.load_asset(swu.MESH_FOLDER + "/SM_SewerHubWaterV2_SL_303_Crossing_Underside")
    if sample:
        b = sample.get_bounding_box()
        out.append("SL_303 underside mesh z %.1f..%.1f" % (b.min.z, b.max.z))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump222.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
