import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
for n in ('BP_Master_PC', 'CBP_PC_Hope', 'CBP_PC_GolKosh'):
    bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/%s' % n); bp.modify()
    cdo = unreal.get_default_object(unreal.load_class(None, '/Game/ThirdPerson/Blueprints/%s.%s_C' % (n, n))); cdo.modify()
    cmc = cdo.get_editor_property('character_movement'); cmc.modify()
    cmc.set_editor_property('ignore_client_movement_error_checks_and_correction', True)
    cmc.set_editor_property('server_accept_client_authoritative_position', True)
for n in ('BP_Master_PC', 'CBP_PC_Hope', 'CBP_PC_GolKosh'):
    compile_bp('/Game/ThirdPerson/Blueprints/%s.%s' % (n, n))
    cmc = unreal.get_default_object(unreal.load_class(None, '/Game/ThirdPerson/Blueprints/%s.%s_C' % (n, n))).get_editor_property('character_movement')
    print(n, cmc.get_editor_property('ignore_client_movement_error_checks_and_correction'), cmc.get_editor_property('server_accept_client_authoritative_position'))
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("editor world:", w.get_path_name() if w else None, "PIE running:", unreal.EditorLevelLibrary.get_game_world() is not None)
