import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
ar = unreal.AssetRegistryHelpers.get_asset_registry()
print("BP referencers:", [str(r) for r in ar.get_referencers("/Game/Level/Utility/BP_PlaneOperator", unreal.AssetRegistryDependencyOptions())])
print("placed in _WP:", [a.get_actor_label() for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_class().get_name() == 'BP_PlaneOperator_C'])
M = '/Game/Level/Utility/PC_Adv_Data.PC_Adv_Data'
m = unreal.load_asset(M)
m.modify()
vp = []
for n, v in (("PlaneLocation", unreal.LinearColor(0, 0, 0, 0)), ("PlaneNormal", unreal.LinearColor(0, 0, 1, 0))):
    p = unreal.CollectionVectorParameter()
    p.set_editor_property('parameter_name', n); p.set_editor_property('default_value', v)
    vp.append(p)
m.set_editor_property('vector_parameters', vp)
print("MPC now:", [str(x.get_editor_property('parameter_name')) for x in m.get_editor_property('vector_parameters')])
P = '/Game/Level/Utility/BP_PlaneOperator.BP_PlaneOperator'
for g in (P + ':UserConstructionScript', P + ':EventGraph'):
    for nn, name in (('K2Node_CallMaterialParameterCollectionFunction_1', 'PlaneLocation'), ('K2Node_CallMaterialParameterCollectionFunction_0', 'PlaneNormal')):
        r = g + '.' + nn
        setv(pin(r, 'Collection', 'in'), M)
        setv(pin(r, 'ParameterName', 'in'), name)
try: compile_bp(P); print("compile OK")
except Exception as e: print("compile FAIL", str(e)[:800])
