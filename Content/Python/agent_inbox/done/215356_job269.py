import traceback, collections
import unreal
out = []
try:
    def key_of(mesh_name, xf):
        l = xf.translation; r = xf.rotation.rotator(); s = xf.scale3d
        return (mesh_name.replace("_Underside", ""), round(l.x, 0), round(l.y, 0), round(l.z, 0),
                round(r.roll, 0) % 360, round(r.pitch, 0) % 360, round(r.yaw, 0) % 360, round(s.x, 2), round(s.y, 2), round(s.z, 2))
    sets = {"Water_Sewage": collections.Counter(), "Water_Underside": collections.Counter(), "Water_Sea": collections.Counter()}
    where = collections.defaultdict(list)
    ncomp = collections.Counter()
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        for comp in a.get_components_by_class(unreal.StaticMeshComponent):
            tags = [str(t) for t in comp.component_tags]
            tag = next((t for t in sets if t in tags), None)
            if not tag:
                continue
            ncomp[tag] += 1
            sm = comp.static_mesh
            name = sm.get_name() if sm else "None"
            if isinstance(comp, unreal.InstancedStaticMeshComponent):
                for i in range(comp.get_instance_count()):
                    xf = comp.get_instance_transform(i, True)
                    k = key_of(name, xf)
                    sets[tag][k] += 1
                    if len(where[(tag, k)]) < 4: where[(tag, k)].append("%s/%s#%d" % (a.get_actor_label(), comp.get_name(), i))
            else:
                k = key_of(name, comp.get_world_transform())
                sets[tag][k] += 1
                if len(where[(tag, k)]) < 4: where[(tag, k)].append("%s/%s" % (a.get_actor_label(), comp.get_name()))
    for tag, cnt in sets.items():
        dups = {k: v for k, v in cnt.items() if v > 1}
        out.append("%s: %d components, %d pieces, %d distinct, %d spots duplicated (%d extra copies)" % (tag, ncomp[tag], sum(cnt.values()), len(cnt), len(dups), sum(v - 1 for v in dups.values())))
        for k, v in list(dups.items())[:25]:
            out.append("   x%d %s at %s  -> %s" % (v, k[0], k[1:4], where[(tag, k)]))
    top, und = sets["Water_Sewage"], sets["Water_Underside"]
    missing = [k for k in top if k not in und]
    orphan = [k for k in und if k not in top]
    out.append("sewage tops without an underside: %d; undersides without a top: %d" % (len(missing), len(orphan)))
    for k in orphan[:20]: out.append("   orphan underside %s at %s -> %s" % (k[0], k[1:4], where[("Water_Underside", k)]))
    for k in missing[:20]: out.append("   top without underside %s at %s -> %s" % (k[0], k[1:4], where[("Water_Sewage", k)]))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump269.txt", "w", encoding="utf-8").write("\n".join(out))
