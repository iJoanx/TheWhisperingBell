import unreal, collections
import sewer_builder as sb
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("level:", w.get_path_name())
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
labels = collections.Counter(a.get_actor_label() for a in acts)
print("actors:", len(acts))
print("network actors:", labels.get(sb.NETWORK_LABEL, 0))
dup = {k: v for k, v in labels.items() if v > 1}
print("duplicate labels:", len(dup), list(dup.items())[:20])
cls = collections.Counter(a.get_class().get_name() for a in acts)
print("classes:", cls.most_common(15))
# same-place duplicates of static mesh actors / nodes
pos = collections.defaultdict(list)
for a in acts:
    l = a.get_actor_location()
    pos[(round(l.x), round(l.y), round(l.z), a.get_class().get_name())].append(a.get_actor_label())
same = [(k, v) for k, v in pos.items() if len(v) > 1]
print("actors stacked on the same spot (same class):", len(same))
for k, v in same[:15]:
    print("  ", k, v[:4])
for a in acts:
    if a.get_actor_label() == sb.NETWORK_LABEL:
        hs = a.get_components_by_class(unreal.InstancedStaticMeshComponent)
        names = collections.Counter(c.get_name().rsplit("_", 1)[0] for c in hs)
        tot = sum(c.get_instance_count() for c in hs)
        print("network", a.get_name(), "ism comps:", len(hs), "instances:", tot)
        print("   comp kinds:", names.most_common(12))
