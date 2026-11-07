import unreal, re
out = []
world = unreal.EditorLevelLibrary.get_editor_world()
# engine swim API (read-only)
hdr = r"C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\Engine\Classes\GameFramework\CharacterMovementComponent.h"
try:
    src = open(hdr, encoding='utf-8', errors='ignore').read()
    for pat in (r".*ImmersionDepth.*", r".*FindWaterLine.*", r".*PhysSwimming.*", r".*virtual .*Swim.*", r".*StartSwimming.*", r".*GetPhysicsVolume.*", r".*IsInWater.*", r".*Buoyancy.*", r".*MaxSwimSpeed.*", r".*bWaterVolume.*", r".*UpdateCharacterStateAfterMovement.*", r".*virtual void TickComponent.*"):
        for m in re.finditer(pat, src): out.append("CMC.h: " + m.group(0).strip()[:200])
except Exception as e: out.append("hdr err %s" % e)
for h2 in (r"C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\Engine\Classes\GameFramework\MovementComponent.h",):
    try:
        s2 = open(h2, encoding='utf-8', errors='ignore').read()
        for pat in (r".*GetPhysicsVolume.*", r".*IsInWater.*"):
            for m in re.finditer(pat, s2): out.append("MC.h: " + m.group(0).strip()[:200])
    except Exception as e: out.append("hdr2 err %s" % e)
cpp = r"C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\Engine\Private\Components\CharacterMovementComponent.cpp"
try:
    s3 = open(cpp, encoding='utf-8', errors='ignore').read()
    for fn in ('void UCharacterMovementComponent::PhysSwimming', 'float UCharacterMovementComponent::Swim(', 'void UCharacterMovementComponent::StartSwimming', 'FVector UCharacterMovementComponent::FindWaterLine', 'float UCharacterMovementComponent::ImmersionDepth'):
        i = s3.find(fn)
        out.append("=== %s\n%s" % (fn, s3[i:i+2600] if i >= 0 else 'NOT FOUND'))
except Exception as e: out.append("cpp err %s" % e)
# water surface candidates
dls = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
def is_water_mat(m):
    try:
        base = m.get_base_material() if hasattr(m, 'get_base_material') else m
        sm = base.get_editor_property('shading_model')
        return 'SINGLE_LAYER_WATER' in str(sm)
    except Exception: return False
rows = []
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    comps = a.get_components_by_class(unreal.StaticMeshComponent)
    for c in comps:
        mats = c.get_materials()
        nm = (a.get_actor_label() + ' ' + a.get_name()).lower()
        if any(is_water_mat(m) for m in mats if m) or any(k in nm for k in ('water', 'sea', 'ocean', 'sewage')):
            mesh = c.static_mesh
            lb = mesh.get_bounding_box() if mesh else None
            try: layers = [l.get_data_layer_short_name() if hasattr(l, 'get_data_layer_short_name') else str(l) for l in dls.get_actor_data_layers(a)] if hasattr(dls, 'get_actor_data_layers') else []
            except Exception as e: layers = ['err']
            try: layers = [str(x) for x in a.get_editor_property('data_layer_assets')] or layers
            except Exception: pass
            t = c.get_world_transform()
            rows.append("%s | label=%s | comp=%s | mesh=%s | loc=%s | rot=%s | scale=%s | localbox=%s | coll=%s/%s | mats=%s | layers=%s | tags=%s" % (
                a.get_name(), a.get_actor_label(), c.get_name(), mesh.get_name() if mesh else None,
                tuple(round(v) for v in (t.translation.x, t.translation.y, t.translation.z)),
                tuple(round(v, 1) for v in (t.rotation.rotator().roll, t.rotation.rotator().pitch, t.rotation.rotator().yaw)),
                tuple(round(v, 2) for v in (t.scale3d.x, t.scale3d.y, t.scale3d.z)),
                (tuple(round(v) for v in (lb.min.x, lb.min.y, lb.min.z)), tuple(round(v) for v in (lb.max.x, lb.max.y, lb.max.z))) if lb else None,
                c.get_collision_profile_name(), c.get_collision_enabled(),
                [m.get_name() for m in mats if m], layers, [str(x) for x in a.tags]))
out.append("WATER CANDIDATES (%d):" % len(rows))
out.extend(rows[:300])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump194.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
