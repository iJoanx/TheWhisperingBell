import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
H = '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.CBP_PC_Hope'
out = [dumpnodes(H + ':EventGraph')]
for g in ('Get Teleport Destination', 'Get Display Destination', 'Set Display Rotation'):
    pass
# defaults of vars
cdo = '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.Default__CBP_PC_Hope_C'
try: out.append("CDO " + str(getprops(cdo, ['TeleportRange', 'CanCast', 'Cast1', 'Cast2'])))
except Exception as e: out.append("cdo err " + str(e)[:300])
# montage info
m = unreal.load_asset('/Game/Characters/Hope/Animations/Teleport/AM_TP_Dash')
try:
    out.append("montage len=%.3f notifies=%s" % (m.get_play_length(), [(n.get_editor_property('notify_name'), round(n.get_editor_property('trigger_time_offset') if False else 0, 2), n.get_editor_property('notify').get_class().get_name() if n.get_editor_property('notify') else None) for n in m.get_editor_property('notifies')]))
except Exception as e: out.append("montage err %s" % e)
try:
    for n in m.get_editor_property('notifies'):
        out.append("  notify %s link_time? %s state=%s" % (n.get_editor_property('notify_name'), n.call_method('GetTime') if hasattr(n,'call_method') else '', n.get_editor_property('notify_state_class')))
except Exception as e: out.append("notify err %s" % e)
# who listens to montage notifies: anim BP of Hope
A = '/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed1.ABP_Unarmed1'
ev = [x['type_id'] for x in infos(nodes(A + ':EventGraph')) if 'Notify' in x['type_id'] or 'Teleport' in x['type_id'] or 'Custom' in x['type_id']]
out.append("ABP1 notify/teleport nodes: %s" % ev)
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump79.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
