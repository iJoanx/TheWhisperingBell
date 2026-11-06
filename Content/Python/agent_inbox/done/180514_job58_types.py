import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
EG = '/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry:EventGraph'
US = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle:UpdateSun'
GK = '/Game/ThirdPerson/Blueprints/CBP_PC_GolKosh.CBP_PC_GolKosh:EventGraph'
for g, fl in [(US, ["SetCastShadows", "GetForwardVector"]),
              (EG, ["ContainsDataLayer", "DataLayer", "ActorHasTag", "SetVisibility", "GetAllActorsOfClass", "IsLocallyControlled", "CastToPawn", "Distance", "GetWorldLocation", "ForEachLoop", "GetRootComponent", "SetActorLocation", "Boolean|NOT", "Vector|Distance", "FlowControl|Branch", "PostProcessVolume", "Settings|Set", "SetbEnabled"]),
              (GK, ["GetController", "GetActorTransform", "Possess", "CastToPlayerController"])]:
    for f in fl:
        try:
            r = types(g, f)
            ids = [x.get('type_id', x) if isinstance(x, dict) else x for x in (r or [])]
            out.append("Q %s | %s" % (f, ids[:25]))
        except Exception as e: out.append("Q %s ERR %s" % (f, str(e)[:200]))
sub = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
out.append("DLES " + str([n for n in dir(sub) if not n.startswith('_')]))
out.append("DLI " + str([n for n in dir(unreal.DataLayerInstanceWithAsset) if not n.startswith('_')]))
out.append("DCP " + str([n for n in dir(unreal.DataLayerCreationParameters) if not n.startswith('_')]))
ppv = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if isinstance(a, unreal.PostProcessVolume)]
for a in ppv:
    out.append("PPV %s %s unbound=%s tags=%s layers=%s" % (a.get_actor_label(), a.get_path_name(), a.get_editor_property('unbound'), a.tags, [x.get_name() for x in a.get_editor_property('data_layer_assets') if x]))
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    L = [x.get_name() for x in a.get_editor_property('data_layer_assets') if x]
    if 'DL_Sky' in L: out.append("SKY %s %s spatial=%s" % (a.get_actor_label(), a.get_class().get_name(), a.get_editor_property('is_spatially_loaded')))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump58.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
