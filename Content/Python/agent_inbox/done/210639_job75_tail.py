import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
abps = set()
for name in ('BP_Master_PC', 'CBP_PC_GolKosh', 'CBP_PC_Hope'):
    cls = unreal.load_class(None, '/Game/ThirdPerson/Blueprints/%s.%s_C' % (name, name))
    cdo = unreal.get_default_object(cls)
    out.append("== %s" % name)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); L = unreal.SubobjectDataBlueprintFunctionLibrary
    bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/%s' % name)
    comps = []
    for hd in sub.k2_gather_subobject_data_for_blueprint(bp):
        o = L.get_object(L.get_data(hd))
        if isinstance(o, unreal.SkeletalMeshComponent): comps.append(o)
    for c in comps:
        def g(p):
            try: return c.get_editor_property(p)
            except Exception: return "?"
        ac = g('anim_class'); sm = g('skeletal_mesh_asset') if g('skeletal_mesh_asset') != "?" else g('skeletal_mesh')
        out.append("  SKM %s mesh=%s anim=%s physAsset=%s tickOpt=%s URO=%s simPhys=%s onlyOwnerSee=%s ownerNoSee=%s" % (c.get_name(), sm.get_name() if sm and sm != "?" else sm, ac.get_path_name() if ac and ac != "?" else ac, g('physics_asset_override'), g('visibility_based_anim_tick_option'), g('enable_update_rate_optimizations'), g('simulate_physics') if g('simulate_physics') != "?" else c.is_simulating_physics(), g('only_owner_see'), g('owner_no_see')))
        if ac and ac != "?": abps.add(ac.get_path_name().replace('_C', '').rsplit('.', 1)[0])
    # graph nodes mentioning physics/tail
    for g_ in call('list_graphs', {'blueprint': {'refPath': bp.get_path_name()}}):
        for x in infos(nodes(g_['refPath'])):
            t = x['type_id']
            if any(k in t for k in ('Physics', 'Simulate', 'Tail', 'Bone', 'Constraint', 'Cable', 'Teleport', 'SetAll')):
                out.append("   BPNODE %s %s" % (g_['refPath'].split(':')[-1], t))
for a in sorted(abps):
    out.append("== ANIMBP %s" % a)
    try:
        for g_ in call('list_graphs', {'blueprint': {'refPath': a + '.' + a.split('/')[-1]}}):
            ts = [x['type_id'] for x in infos(nodes(g_['refPath']))]
            interesting = [t for t in ts if any(k in t.lower() for k in ('rigid', 'dynamics', 'spring', 'kawaii', 'physics', 'ik', 'tail', 'chain', 'jiggle', 'modify', 'trail', 'copy', 'controlrig', 'pose', 'slot'))]
            out.append("  %s (%d nodes): %s" % (g_['refPath'].split(':')[-1], len(ts), interesting[:30]))
    except Exception as e: out.append("  err " + str(e)[:300])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump75.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
