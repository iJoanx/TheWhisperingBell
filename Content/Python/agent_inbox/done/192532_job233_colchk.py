import unreal
sm = unreal.load_asset("/Game/Sewers/Generated/SM_SewerNode_SL_303_Crossing")
n = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_simple_collision_count(sm) if sm else None
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump233.txt", "w").write("asset %s collision primitives: %s" % (sm.get_path_name() if sm else None, n))
print("ok")
