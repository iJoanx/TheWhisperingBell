import unreal
for c in ["BlueprintEditorLibrary", "KismetEditorUtilities", "EditorUtilityLibrary"]:
    k = getattr(unreal, c, None)
    print(c, [x for x in dir(k) if "nterface" in x] if k else None)
bp = unreal.load_asset("/Game/Walls/BP_WallSpline")
for p in ["implemented_interfaces"]:
    try:
        print(p, bp.get_editor_property(p))
    except Exception as e:
        print(p, "ERR", e)
pc = unreal.load_asset("/Game/ThirdPerson/Blueprints/BP_Master_PC")
try:
    print("PC interfaces", pc.get_editor_property("implemented_interfaces"))
except Exception as e:
    print("ERR", e)
# who implements BPI_Interactable
ar = unreal.AssetRegistryHelpers.get_asset_registry()
refs = ar.get_referencers("/Game/Level/WhisperingBell/Blueprints/BPI_Interactable", unreal.AssetRegistryDependencyOptions(True, True, True, True, True))
print("BPI referencers:", [str(r) for r in refs])
