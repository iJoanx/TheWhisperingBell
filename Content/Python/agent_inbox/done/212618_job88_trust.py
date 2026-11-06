import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
s = unreal.load_asset('/Game/Characters/Hope/Animations/Teleport/AS_TP_Dash')
s.modify()
s.set_editor_property('enable_root_motion', False)
s.set_editor_property('force_root_lock', True)
print("AS_TP_Dash root motion:", s.get_editor_property('enable_root_motion'), "force root lock:", s.get_editor_property('force_root_lock'))
for n in ('BP_Master_PC', 'CBP_PC_Hope', 'CBP_PC_GolKosh'):
    bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/%s' % n)
    bp.modify()
    cdo = unreal.get_default_object(unreal.load_class(None, '/Game/ThirdPerson/Blueprints/%s.%s_C' % (n, n)))
    cdo.modify()
    cmc = cdo.get_editor_property('character_movement')
    cmc.modify()
    cmc.set_editor_property('ignore_client_movement_error_checks_and_correction', True)
    cmc.set_editor_property('server_accept_client_authoritative_position', True)
for n in ('BP_Master_PC', 'CBP_PC_Hope', 'CBP_PC_GolKosh'):
    compile_bp('/Game/ThirdPerson/Blueprints/%s.%s' % (n, n))
for n in ('BP_Master_PC', 'CBP_PC_Hope', 'CBP_PC_GolKosh'):
    cmc = unreal.get_default_object(unreal.load_class(None, '/Game/ThirdPerson/Blueprints/%s.%s_C' % (n, n))).get_editor_property('character_movement')
    print(n, "after compile:", cmc.get_editor_property('ignore_client_movement_error_checks_and_correction'), cmc.get_editor_property('server_accept_client_authoritative_position'))
print("dirty content:", [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()][:20])
