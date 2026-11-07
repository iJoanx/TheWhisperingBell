import traceback
import unreal
out = []
try:
    sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_303_Crossing")
    seen = set()
    for i, m in enumerate(sm.static_materials):
        mi = m.material_interface
        out.append("slot %d %s -> %s" % (i, m.material_slot_name, mi.get_path_name() if mi else None))
        if not mi: continue
        base = mi.get_base_material()
        out.append("   base %s" % base.get_path_name())
        try:
            for p in unreal.MaterialEditingLibrary.get_texture_parameter_names(mi):
                tex = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mi, p) if isinstance(mi, unreal.MaterialInstance) else None
                out.append("   tex param %s = %s %s" % (p, tex.get_path_name() if tex else None, (tex.blueprint_get_size_x(), tex.blueprint_get_size_y()) if tex else ''))
        except Exception as e:
            out.append("   tex params err %s" % e)
        try:
            for p in unreal.MaterialEditingLibrary.get_scalar_parameter_names(mi):
                out.append("   scalar %s = %s" % (p, unreal.MaterialEditingLibrary.get_material_instance_scalar_value(mi, p) if isinstance(mi, unreal.MaterialInstance) else '?'))
        except Exception as e:
            out.append("   scalar err %s" % e)
        if base.get_path_name() in seen: continue
        seen.add(base.get_path_name())
        try:
            texs = unreal.MaterialEditingLibrary.get_used_textures(base)
            for t in texs:
                out.append("   used tex %s %dx%d filter %s" % (t.get_path_name(), t.blueprint_get_size_x(), t.blueprint_get_size_y(), t.get_editor_property("filter")))
        except Exception as e:
            out.append("   used tex err %s" % e)
        # expressions in the base material
        try:
            exprs = unreal.MaterialEditingLibrary.get_material_expressions(base) if hasattr(unreal.MaterialEditingLibrary, "get_material_expressions") else []
        except Exception:
            exprs = []
        for ex in exprs:
            desc = ex.get_class().get_name()
            extra = ''
            for prop in ("coordinate_index", "u_tiling", "v_tiling", "r", "const_a", "const_b", "parameter_name", "default_value", "texture"):
                try:
                    v = ex.get_editor_property(prop)
                    extra += " %s=%s" % (prop, v.get_path_name() if hasattr(v, 'get_path_name') else v)
                except Exception:
                    pass
            out.append("     expr %s%s" % (desc, extra))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump253.txt", "w", encoding="utf-8").write("\n".join(out))
