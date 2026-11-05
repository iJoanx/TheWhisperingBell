import unreal
EAL = unreal.EditorAssetLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("open level:", world.get_path_name())
pkg = world.get_outermost()
dirty = pkg.is_dirty() if hasattr(pkg, "is_dirty") else None
print("open level has unsaved changes:", dirty)
SRC, DST = "/Game/Sewers/Maps/SewerDefinitive", "/Game/Sewers/Maps/Sewers"
if EAL.does_asset_exist(SRC) and not EAL.does_asset_exist(DST):
    print("rename:", EAL.rename_asset(SRC, DST))
print("Sewers exists:", EAL.does_asset_exist(DST), " old exists:", EAL.does_asset_exist(SRC))
# redirectors left behind in the folder
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for a in ar.get_assets_by_path("/Game/Sewers/Maps", recursive=True):
    print("  in Maps:", a.asset_name, a.asset_class_path.asset_name if hasattr(a, "asset_class_path") else "")
