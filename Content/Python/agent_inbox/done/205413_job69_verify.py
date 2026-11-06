import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
for bp in ['/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry', '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle',
           '/Game/ThirdPerson/Blueprints/CBP_PC_GolKosh.CBP_PC_GolKosh', '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.CBP_PC_Hope', '/Game/ThirdPerson/Blueprints/BP_Master_PC.BP_Master_PC']:
    try: compile_bp(bp); out.append("compiled OK " + bp.split('.')[-1])
    except Exception as e: out.append("COMPILE FAIL %s: %s" % (bp.split('.')[-1], str(e)[:700]))
US = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle:UpdateSun'
sw = pin(US + '.K2Node_CallFunction_11', 'then', 'out')
nx = [info(c['node']['refPath'])['type_id'] for c in sw.get('connected_pins') or []]
out.append("after sun SetWorldRotation -> %s" % nx)
# sewer shafts near each entry drop point
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
nodes_ = [a for a in acts if a.get_actor_label().startswith('SL_')]
for a in acts:
    if a.get_class().get_name() == 'BP_WB_Sewer_Entry_C':
        cap = [c for c in a.get_components_by_class(unreal.CapsuleComponent) if c.get_name() == 'Capsule'][0].get_world_location()
        best = min(nodes_, key=lambda n: (n.get_actor_location() - cap).length())
        d = best.get_actor_location() - cap
        hit = unreal.SystemLibrary.line_trace_single(a, cap, cap - unreal.Vector(0, 0, 500), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        hr = hit.to_tuple() if hit else None
        floor = (hr[4].z if hr and hr[0] else None)
        actor = (hr[9].get_actor_label() if hr and hr[0] and hr[9] else None)
        out.append("%s drop=%s nearest=%s (%.0f cm away, dz=%.0f) floor_below=%s on %s" % (a.get_actor_label(), [round(v) for v in (cap.x, cap.y, cap.z)], best.get_actor_label(), d.length(), d.z, None if floor is None else round(floor), actor))
print("\n".join(out))
