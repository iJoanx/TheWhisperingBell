import sys, importlib, traceback
import unreal
out = []
MEL = unreal.MaterialEditingLibrary
try:
    top = unreal.load_asset('/Game/Sewers/Materials/MI_SewerWaterV2_Opaque')
    MEL.set_material_instance_vector_parameter_value(top, 'WaterColor', unreal.LinearColor(0.05, 0.055, 0.015, 1))
    MEL.set_material_instance_vector_parameter_value(top, 'RippleColor', unreal.LinearColor(0.12, 0.13, 0.05, 1))
    MEL.update_material_instance(top)
    out.append("top WaterColor=%s RippleColor=%s" % (MEL.get_material_instance_vector_parameter_value(top, 'WaterColor'), MEL.get_material_instance_vector_parameter_value(top, 'RippleColor')))
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_water_underside as swu
    importlib.reload(swu)
    made, inst, skipped = swu.run()
    out.append("underside components added: %d (%d instances), already there: %d" % (made, inst, skipped))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump215.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
