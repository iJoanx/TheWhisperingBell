import unreal, collections
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump345.txt", "w", encoding="utf-8").write("\n".join(out))
GA, GQ = unreal.GeometryScript_AssetUtils, unreal.GeometryScript_MeshQueries
PATCHED = set()
for l in open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump342.txt").read().splitlines() + open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump341.txt").read().splitlines():
    if l.startswith('WROTE '): PATCHED.add(l.split()[1].rstrip(':'))
def rand_of(sm):
    dm = unreal.DynamicMesh()
    GA.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    xs, ys = collections.Counter(), []
    n = GQ.get_num_triangle_i_ds(dm)
    for t in range(0, n, max(1, n // 30)):
        u = [x for x in GQ.get_triangle_u_vs(dm, 5, t) if isinstance(x, unreal.Vector2D)]
        if u: xs[int(round(u[0].x))] += 1; ys.append(round(1.0 - u[0].y, 3))
    return dict(xs), (min(ys), max(ys)) if ys else None
try:
    sel = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
    out.append("selected: %s" % [a.get_actor_label() for a in sel])
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    assets = ar.get_assets_by_path('/Game/Houses/Meshes', recursive=True)
    names = sorted(str(a.asset_name) for a in assets if str(a.asset_name).startswith('SM_Towers'))
    for n in names:
        x, r = rand_of(unreal.load_asset('/Game/Houses/Meshes/' + n))
        out.append("%s %s code %s rand %s" % ("PATCHED" if n in PATCHED else "orig   ", n, x, r))
    hs = sorted(str(a.asset_name) for a in assets if str(a.asset_name).startswith('SM_Houses'))[::200]
    for n in hs:
        x, r = rand_of(unreal.load_asset('/Game/Houses/Meshes/' + n))
        out.append("house   %s code %s rand %s" % (n, x, r))
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
