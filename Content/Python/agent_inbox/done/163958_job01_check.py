import unreal, sys
ar = unreal.AssetRegistryHelpers.get_asset_registry()
print("project:", unreal.Paths.get_project_file_path())
print("geometry script:", hasattr(unreal, "GeometryScript_MeshBasicEditFunctions") or hasattr(unreal, "GeometryScriptLibrary_MeshBasicEditFunctions"))
for m in ["sewer_tools", "walls_spline", "door_wrap", "agent_bridge"]:
    print("module", m, m in sys.modules)
missing = {}
for root in ["/Game/Sewers", "/Game/Walls", "/Game/Level/Sewers"]:
    for a in ar.get_assets_by_path(root, recursive=True):
        pkg = str(a.package_name)
        opts = unreal.AssetRegistryDependencyOptions(True, True, False, False, False)
        for d in ar.get_dependencies(pkg, opts) or []:
            d = str(d)
            if d.startswith("/Script") or d.startswith("/Engine"):
                continue
            if not unreal.EditorAssetLibrary.does_asset_exist(d) and not ar.get_assets_by_package_name(d):
                missing.setdefault(d, []).append(pkg)
print("assets in Sewers:", len(ar.get_assets_by_path("/Game/Sewers", recursive=True)), "Walls:", len(ar.get_assets_by_path("/Game/Walls", recursive=True)))
print("MISSING deps:", len(missing))
for d, users in sorted(missing.items()):
    print("  ", d, "<-", users[:4], "(%d)" % len(users))
for p in ["/Game/Level/WhisperingBell/Blueprints/BPI_Interactable"]:
    print(p, unreal.EditorAssetLibrary.does_asset_exist(p))
for a in ar.get_assets_by_path("/Game", recursive=True):
    n = str(a.asset_name)
    if n in ("BP_Master_PC", "BPI_Interactable"):
        print("found", n, a.package_name)
print("current level:", unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name())
