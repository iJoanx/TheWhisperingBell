import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal, traceback
out = []
eal = unreal.EditorAssetLibrary
def safe(f):
    try: return f()
    except Exception as e: return "ERR %s" % str(e)[:150]
for p in ('/Game/Water/M_SewageWater_SLW', '/Game/Water/M_SewerWaterFlow_SLW', '/Game/Water/MPC_Water', '/Game/Water/M_PP_Underwater_Sea', '/Game/Water/M_PP_Underwater_Sewage', '/Game/Levels/DataLayers/RDL_Sea', '/Game/Levels/DataLayers/RDL_Walls'):
    out.append("%-45s exists=%s" % (p, eal.does_asset_exist(p)))
mi = unreal.load_asset('/Game/Sewers/Materials/MI_SewerWaterV2_Opaque')
out.append("sewage MI parent: %s" % safe(lambda: mi.get_editor_property('parent').get_path_name()))
out.append("sewage MI two-sided override: %s" % (safe(lambda: (mi.get_editor_property('base_property_overrides').get_editor_property('override_two_sided'), mi.get_editor_property('base_property_overrides').get_editor_property('two_sided'))),))
out.append("sewage MI WaterColor: %s" % safe(lambda: unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mi, 'WaterColor')))
par = safe(lambda: mi.get_editor_property('parent'))
if not isinstance(par, str):
    out.append("parent shading: %s" % safe(lambda: str(par.get_base_material().get_editor_property('shading_model'))))
sea = unreal.load_asset('/Game/Level/Streets/Materials/M_Master_Water_Inst')
out.append("sea MI two-sided override: %s" % safe(lambda: sea.get_editor_property('base_property_overrides').get_editor_property('two_sided')))
world = unreal.EditorLevelLibrary.get_editor_world()
for tag in ('RDL_Sea', 'RDL_Walls', 'RDL_Sewers', 'RDL_Sky'):
    out.append("actors tagged %s: %d" % (tag, len(unreal.GameplayStatics.get_all_actors_with_tag(world, tag))))
n_sew = n_nocoll = 0
for a in unreal.GameplayStatics.get_all_actors_with_tag(world, 'RDL_Sewers'):
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if unreal.Name('Water_Sewage') in list(c.component_tags):
            n_sew += 1
            if c.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION: n_nocoll += 1
out.append("sewage water comps tagged: %d, no-collision: %d" % (n_sew, n_nocoll))
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    if a.get_actor_label() in ('WaterdeepWater', 'PPV_Underwater_Sea', 'PPV_Underwater_Sewage'):
        if a.get_actor_label() == 'WaterdeepWater':
            c = a.get_components_by_class(unreal.StaticMeshComponent)[0]
            out.append("sea plane tags=%s coll=%s" % ([str(t) for t in c.component_tags], c.get_collision_enabled()))
        else:
            out.append("%s present, blendables=%d" % (a.get_actor_label(), len(a.get_editor_property('settings').get_editor_property('weighted_blendables').get_editor_property('array'))))
G = '/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry:ApplySewerView'
d = str(call('read_graph_dsl', {'graph': {'refPath': G}}))
out.append("ApplySewerView: tags %s, collision toggles %d" % ([t for t in ('RDL_Sewers', 'RDL_Sky', 'RDL_Sea', 'RDL_Walls') if t in d], d.count('SetActorEnableCollision')))
u = str(call('read_graph_dsl', {'graph': {'refPath': G.replace('ApplySewerView', 'UseEntry')}}))
out.append("UseEntry locally-controlled teleport: %s" % ('IsLocallyControlled' in u and 'SetActorLocation' in u))
out.append("C++ built (TWBWaterSubsystem class present): %s" % hasattr(unreal, 'TWBWaterSubsystem'))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump209.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
