import unreal
names = [a for a in dir(unreal) if a.startswith("GeometryScript")]
print(len(names))
print([a for a in names if "Library" in a or "Functions" in a])
for c in ["GeometryScriptLibrary_MeshBasicEditFunctions", "GeometryScript_MeshBasicEditFunctions"]:
    k = getattr(unreal, c, None)
    print(c, k, [x for x in dir(k) if "vertex" in x.lower()][:10] if k else None)
for cand in ["/Script/GeometryScriptingCore.GeometryScriptLibrary_MeshBasicEditFunctions"]:
    try:
        print(cand, unreal.load_class(None, cand))
    except Exception as e:
        print(cand, e)
pm = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
