import unreal
out = []
D = r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\\"
try:
    arr = unreal.load_asset('/Game/Houses/HouseArray').get_editor_property('source_textures')
    cb = (5 * 4 + 1) * 15
    for s in (cb + 0, cb + 3, cb + 6, cb + 7, cb + 8):
        t = arr[s]
        out.append("slice %d = %s" % (s, t.get_path_name() if t else None))
        if t:
            task = unreal.AssetExportTask()
            task.object = t; task.filename = D + "slice353_%d.png" % s
            task.automated = True; task.prompt = False; task.replace_identical = True
            task.exporter = unreal.TextureExporterPNG()
            out.append("  export %s" % unreal.Exporter.run_asset_export_task(task))
except Exception:
    import traceback; out.append(traceback.format_exc()[-1200:])
open(D + "dump353.txt", "w").write("\n".join(out))
