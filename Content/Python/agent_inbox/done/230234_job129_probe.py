import unreal
from collections import Counter, defaultdict
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
def layers(a):
    try: return [x.get_name() for x in a.get_editor_property('data_layer_assets') if x]
    except Exception: return []
wb = [a for a in acts if 'EDL_TheWhisperingBell' in layers(a)]
z = [a for a in wb if abs(a.get_actor_location().x) < 0.5 and abs(a.get_actor_location().y) < 0.5]
meshes = {}
for a in z:
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if c and c.static_mesh: meshes[c.static_mesh.get_path_name()] = c.static_mesh
print("zero actors:", len(z), "unique meshes:", len(meshes))
sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
st = Counter()
for p, m in meshes.items():
    lods = m.get_num_lods() if hasattr(m, 'get_num_lods') else sme.get_lod_count(m)
    try: nan = m.get_editor_property('nanite_settings').get_editor_property('enabled')
    except Exception: nan = '?'
    bs = m.get_editor_property('body_setup')
    flag = str(bs.get_editor_property('collision_trace_flag')) if bs else 'nobody'
    try:
        ag = bs.get_editor_property('agg_geom'); counts = (len(ag.get_editor_property('box_elems')), len(ag.get_editor_property('sphere_elems')), len(ag.get_editor_property('sphyl_elems')), len(ag.get_editor_property('convex_elems')))
    except Exception as e: counts = ('?',)
    st[(lods, nan, flag.split('.')[-1], counts != (0, 0, 0, 0))] += 1
print("LODs / nanite / trace flag / has simple collision:", st.most_common())
rug_users = [(a.get_actor_label(), layers(a), a.get_actor_location()) for a in acts for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh and c.static_mesh.get_name() == 'WB_P_Rug']
print("WB_P_Rug users:", rug_users)
GS = [n for n in dir(unreal) if n.startswith('GeometryScript')]
print("geometry script libs:", [n for n in GS if any(k in n for k in ('Asset', 'Collision', 'Transform'))])
for lib in ('GeometryScript_Collision', 'GeometryScript_AssetUtils', 'GeometryScript_MeshTransforms'):
    L = getattr(unreal, lib, None)
    print(lib, [n for n in dir(L) if not n.startswith('_') and any(k in n for k in ('collision', 'static_mesh', 'translate', 'transform'))] if L else None)
vz = [a for a in z if a.get_actor_label() == 'WB_F3_Floor_Veranda']
for a in vz: print("veranda:", a.get_actor_transform())
