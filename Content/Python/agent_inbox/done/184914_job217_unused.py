import unreal, re
out = []
ar = unreal.AssetRegistryHelpers.get_asset_registry()
builder = open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\sewer_builder.py", encoding="utf-8", errors="ignore").read()
scripts = builder
for extra in ("sewer_water_underside.py", "sewer_setup.py", "sewer_tools.py", "sewer_water3.py"):
    try: scripts += open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\\" + extra, encoding="utf-8", errors="ignore").read()
    except Exception: pass
opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True, include_searchable_names=False, include_soft_management_references=False, include_hard_management_references=False)
for folder in ("/Game/Sewers/Materials", "/Game/Water"):
    assets = ar.get_assets(unreal.ARFilter(package_paths=[folder], recursive_paths=True))
    for a in sorted(assets, key=lambda x: str(x.asset_name)):
        cls = str(a.asset_class_path.asset_name) if hasattr(a, 'asset_class_path') else str(a.asset_class)
        if cls not in ("Material", "MaterialInstanceConstant"): continue
        pkg = str(a.package_name)
        refs = [str(r) for r in (ar.get_referencers(pkg, opts) or []) if str(r) != pkg]
        in_script = str(a.asset_name) in scripts
        out.append("%-5s %-40s %-26s referenced by %2d assets%s  %s" % ("USED" if refs else "free", str(a.asset_name), cls, len(refs),
                   "  + named in a Python script" if in_script else "", ", ".join(r.split('/')[-1] for r in refs[:4])))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump217.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
