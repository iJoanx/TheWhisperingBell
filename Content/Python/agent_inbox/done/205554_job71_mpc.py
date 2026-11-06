import unreal, os, glob
ar = unreal.AssetRegistryHelpers.get_asset_registry()
opt = unreal.AssetRegistryDependencyOptions()
refs = ar.get_referencers("/Game/Level/Utility/PC_Adv_Data", opt)
print("referencers:", [str(r) for r in refs])
for r in refs:
    for ad in ar.get_assets_by_package_name(r):
        a = ad.get_asset()
        print("==", r, a.get_class().get_name())
        exprs = []
        try:
            ed = a.get_editor_only_data()
            exprs = list(ed.get_editor_property('expression_collection').get_editor_property('expressions'))
        except Exception as e:
            try: exprs = list(a.get_editor_property('expressions'))
            except Exception as e2: print("  no exprs", e, e2)
        for x in exprs:
            if isinstance(x, unreal.MaterialExpressionCollectionParameter):
                print("  CollectionParameter name=%s coll=%s" % (x.get_editor_property('parameter_name'), x.get_editor_property('collection')))
            elif x.get_class().get_name() == 'MaterialExpressionMaterialFunctionCall':
                print("  FunctionCall", x.get_editor_property('material_function'))
# original copy in Zippy?
for root in [r"C:\Users\Admin\Documents\Unreal Projects"]:
    for p in glob.glob(root + r"\**\PC_Adv_Data.uasset", recursive=True):
        print("copy:", p, os.path.getsize(p), os.path.getmtime(p))
    for p in glob.glob(root + r"\**\BP_PlaneOperator.uasset", recursive=True):
        print("bp copy:", p, os.path.getsize(p), os.path.getmtime(p))
