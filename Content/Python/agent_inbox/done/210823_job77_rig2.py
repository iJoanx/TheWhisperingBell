import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
ar = unreal.AssetRegistryHelpers.get_asset_registry()
opt = unreal.AssetRegistryDependencyOptions()
deps = [str(d) for d in ar.get_dependencies('/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed2', opt)]
out.append("ABP2 deps: %s" % deps)
cands = []
for d in deps:
    for ad in ar.get_assets_by_package_name(d):
        out.append("  %s : %s" % (d, ad.asset_class_path.asset_name))
        if 'ControlRig' in str(ad.asset_class_path.asset_name) or 'RigVM' in str(ad.asset_class_path.asset_name): cands.append(d)
ar_sm = ar.get_assets(unreal.ARFilter(package_paths=["/Game"], recursive_paths=True, class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "SkeletalMesh")]))
for ad in ar_sm:
    if 'Golkosh' in str(ad.asset_name):
        sm = ad.get_asset()
        def g(p):
            try: return sm.get_editor_property(p)
            except Exception: return "?"
        out.append("SM %s postAnim=%s phys=%s" % (ad.package_name, g('post_process_anim_blueprint'), g('physics_asset')))
        pp = g('post_process_anim_blueprint')
        if pp and pp != "?":
            pbp = pp.get_path_name().replace('_C', '').rsplit('.', 1)[0]
            for g_ in call('list_graphs', {'blueprint': {'refPath': pbp + '.' + pbp.split('/')[-1]}}):
                out.append("  PP graph %s: %s" % (g_['refPath'].split(':')[-1], [x['type_id'] for x in infos(nodes(g_['refPath']))][:30]))
for c in cands:
    rb = unreal.load_asset(c)
    out.append("== RIG %s %s" % (c, type(rb).__name__))
    try:
        ms = [rb.get_model()]
        try: ms = list(rb.get_all_models())
        except Exception: pass
        for m in ms:
            ns = m.get_nodes()
            titles = [n.get_node_title() for n in ns]
            out.append("  graph %s (%d): %s" % (m.get_name(), len(ns), titles[:80]))
    except Exception as e: out.append("  err %s" % e)
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump77.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
