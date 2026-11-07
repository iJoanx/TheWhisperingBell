import sys, importlib, traceback
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    for pt in sb.PASSAGE_TYPES:
        out.append("ptype %s seg %s" % (pt, sb.PASSAGE_TYPES[pt].get("segment_length")))
        for e in (sb._uv_table(pt) or []):
            out.append("   edge %s -> %s  uv@0 %s  uv@400 %s  cell %s" % (e[0], e[1], tuple(tuple(round(c, 4) for c in p) for p in e[3]), tuple(tuple(round(c, 4) for c in p) for p in e[4]), e[5] if len(e) > 5 else None))
    base = unreal.load_asset("/Game/Level/Sewers/M_Master_Sewers")
    MEL = unreal.MaterialEditingLibrary
    for ex in MEL.get_material_expressions(base) if hasattr(MEL, "get_material_expressions") else []:
        if isinstance(ex, unreal.MaterialExpressionMaterialFunctionCall):
            f = ex.get_editor_property("material_function")
            out.append("func %s" % (f.get_path_name() if f else None))
            if f:
                try:
                    for e2 in MEL.get_material_function_expressions(f) if hasattr(MEL, "get_material_function_expressions") else []:
                        d = e2.get_class().get_name()
                        for prop in ("r", "const_a", "const_b", "coordinate_index", "input_name", "code"):
                            try: d += " %s=%s" % (prop, e2.get_editor_property(prop))
                            except Exception: pass
                        out.append("    " + d)
                except Exception as e:
                    out.append("    err %s" % e)
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump255.txt", "w", encoding="utf-8").write("\n".join(out))
