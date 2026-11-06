import unreal, sys, pkgutil
print([n for n in dir(unreal) if "oolset" in n or "MCP" in n.upper() and len(n)<40][:60])
for m in list(sys.modules):
    if "toolset" in m.lower() or "mcp" in m.lower(): print("mod", m)
try:
    import editor_toolset; print("editor_toolset", editor_toolset.__file__)
except Exception as e: print("no editor_toolset", e)
# data layers
try:
    s = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for d in s.get_all_data_layers():
        a = None
        try: a = d.get_asset()
        except Exception: pass
        print("DLI", d.get_name(), type(d).__name__, "asset", a.get_path_name() if a else None, "rt" , d.get_editor_property("initial_runtime_state") if hasattr(d,"initial_runtime_state") else "")
except Exception as e: print("dl err", e)
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for a in ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine","DataLayerAsset")):
    print("DLA", a.package_name)
for n in ("BP_Master_PC","BP_WB_Sewer_Entry","BP_WB_Sewer_Exit"):
    f = unreal.ARFilter(recursive_paths=True, package_paths=["/Game"])
    for a in ar.get_assets(f):
        if str(a.asset_name) == n: print("BP", n, a.package_name)
