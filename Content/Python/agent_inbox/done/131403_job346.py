import unreal
out = []
try:
    t = unreal.load_asset('/Game/Houses/T_WardPalette')
    out.append("size %s x %s" % (t.blueprint_get_size_x(), t.blueprint_get_size_y()))
    task = unreal.AssetExportTask()
    task.object = t
    task.filename = r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\palette346.png"
    task.automated = True; task.prompt = False; task.replace_identical = True
    task.exporter = unreal.TextureExporterPNG()
    out.append("export %s" % unreal.Exporter.run_asset_export_task(task))
    m = unreal.load_asset('/Game/Houses/M_Houses_Master')
    for p in ('NumWards', 'SetsPerWard', 'TintStrength'):
        try: out.append("%s = %s" % (p, unreal.MaterialEditingLibrary.get_material_default_scalar_parameter_value(m, p)))
        except Exception as e: out.append(str(e)[:100])
except Exception:
    import traceback; out.append(traceback.format_exc()[-1200:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump346.txt", "w").write("\n".join(out))
