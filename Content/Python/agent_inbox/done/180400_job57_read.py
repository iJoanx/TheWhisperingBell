import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
G = '/Game/ThirdPerson/Blueprints/'
for p in [G+'CBP_PC_GolKosh.CBP_PC_GolKosh:EventGraph.K2Node_CustomEvent_4', G+'CBP_PC_GolKosh.CBP_PC_GolKosh:EventGraph.K2Node_CustomEvent_5']:
    try: out.append(p + " " + str(getprops(p, ['FunctionFlags', 'CustomFunctionName'])))
    except Exception as e: out.append("err " + str(e)[:300])
mpc = G + 'BP_Master_PC.BP_Master_PC:EventGraph'
for n in nodes(mpc):
    i = info(n)
    if 'Custom|' in i['type_id']:
        try: out.append(i['type_id'] + " " + str(getprops(n, ['FunctionFlags'])))
        except Exception as e: out.append("err " + str(e)[:200])
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
out.append("DN CDO repl " + str(getprops(DN.replace('BP_DayNightCycle.BP_DayNightCycle', 'BP_DayNightCycle.Default__BP_DayNightCycle_C'), ['bReplicates'])))
out.append("=== UpdateSun\n" + dumpnodes(DN + ':UpdateSun'))
E = '/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry'
out.append("=== Entry EventGraph\n" + dumpnodes(E + ':EventGraph'))
out.append("Entry CDO " + str(getprops('/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.Default__BP_WB_Sewer_Entry_C', ['bReplicates'])))
# entry components (SCS)
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
bp = unreal.load_asset(E)
hs = sub.k2_gather_subobject_data_for_blueprint(bp)
for hd in hs:
    d = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(hd)
    o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)
    extra = ""
    if isinstance(o, unreal.PrimitiveComponent):
        extra = " profile=%s rel=%s ext=%s" % (o.get_collision_profile_name(), o.get_editor_property('relative_location'), o.get_editor_property('box_extent') if isinstance(o, unreal.BoxComponent) else "")
        if isinstance(o, unreal.BoxComponent):
            r = []
            for ch in range(0, 8):
                try: r.append(str(o.get_collision_response_to_channel(unreal.CollisionChannel.cast(ch))))
                except Exception: pass
            extra += " resp=" + ",".join(x.split('.')[-1] for x in r) + " enabled=" + str(o.get_collision_enabled())
    out.append("COMP %s %s%s" % (unreal.SubobjectDataBlueprintFunctionLibrary.get_variable_name(d), o.get_class().get_name() if o else None, extra))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump57.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
