import unreal
out = []
at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
D = "/Game/Water"
if not eal.does_directory_exist(D): eal.make_directory(D)

# ---------- parameter collection
mpc_path = D + "/MPC_Water"
mpc = unreal.load_asset(mpc_path) if eal.does_asset_exist(mpc_path) else at.create_asset("MPC_Water", D, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
params = []
for n in ("SeaUnderwater", "SewageUnderwater", "UnderwaterDepth"):
    p = unreal.CollectionScalarParameter(); p.set_editor_property("parameter_name", n); p.set_editor_property("default_value", 0.0)
    params.append(p)
existing = [str(p.get_editor_property("parameter_name")) for p in mpc.get_editor_property("scalar_parameters")]
if sorted(existing) != sorted(["SeaUnderwater", "SewageUnderwater", "UnderwaterDepth"]):
    mpc.set_editor_property("scalar_parameters", params)
out.append("MPC params: %s" % [str(p.get_editor_property("parameter_name")) for p in mpc.get_editor_property("scalar_parameters")])

def build(name, amount_param, tint, water_color, density, wobble):
    path = D + "/" + name
    if eal.does_asset_exist(path):
        m = unreal.load_asset(path); MEL.delete_all_material_expressions(m)
    else:
        m = at.create_asset(name, D, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS)
    try: m.set_editor_property("blendable_location", unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_DOF)
    except Exception as e: out.append("blendable_location: %s" % e)
    X = lambda cls, x, y: MEL.create_material_expression(m, cls, x, y)
    C = MEL.connect_material_expressions
    def const(v, x, y):
        e = X(unreal.MaterialExpressionConstant, x, y); e.set_editor_property("r", v); return e
    def mul(a, b, x, y, bconst=None):
        e = X(unreal.MaterialExpressionMultiply, x, y); C(a, "", e, "A")
        if bconst is not None: e.set_editor_property("const_b", bconst)
        else: C(b, "", e, "B")
        return e
    def add(a, b, x, y):
        e = X(unreal.MaterialExpressionAdd, x, y); C(a, "", e, "A"); C(b, "", e, "B"); return e
    def mask(src, r, g, x, y):
        e = X(unreal.MaterialExpressionComponentMask, x, y)
        e.set_editor_property("r", r); e.set_editor_property("g", g); e.set_editor_property("b", False); e.set_editor_property("a", False)
        C(src, "", e, ""); return e
    # how much of the effect (0 = off, 1 = camera under this water)
    amount = X(unreal.MaterialExpressionCollectionParameter, -1600, -300)
    amount.set_editor_property("collection", mpc); amount.set_editor_property("parameter_name", amount_param)
    # gentle wobble of the screen
    uv = X(unreal.MaterialExpressionTextureCoordinate, -1600, 0)
    t = X(unreal.MaterialExpressionTime, -1600, 150)
    sx = X(unreal.MaterialExpressionSine, -1000, 0); C(add(mul(mask(uv, False, True, -1400, 0), None, -1250, 0, 30.0), mul(t, None, -1250, 120, 1.5), -1100, 50), "", sx, "")
    cy = X(unreal.MaterialExpressionCosine, -1000, 200); C(add(mul(mask(uv, True, False, -1400, 200), None, -1250, 200, 25.0), mul(t, None, -1250, 320, 1.2), -1100, 250), "", cy, "")
    off = X(unreal.MaterialExpressionAppendVector, -850, 100); C(sx, "", off, "A"); C(cy, "", off, "B")
    offs = mul(mul(off, None, -700, 100, wobble), amount, -550, 100)
    uvd = add(uv, offs, -400, 50)
    scene = X(unreal.MaterialExpressionSceneTexture, -250, 0)
    scene.set_editor_property("scene_texture_id", unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    C(uvd, "", scene, "UVs")
    sc = mask(scene, True, True, -50, 0); sc.set_editor_property("b", True)
    # depth fog towards the water colour
    depth = X(unreal.MaterialExpressionSceneTexture, -700, 450)
    depth.set_editor_property("scene_texture_id", unreal.SceneTextureId.PPI_SCENE_DEPTH)
    dr = mask(depth, True, False, -500, 450)
    dd = mul(dr, None, -350, 450, density)
    one_plus = X(unreal.MaterialExpressionAdd, -200, 450); C(dd, "", one_plus, "A"); one_plus.set_editor_property("const_b", 1.0)
    inv = X(unreal.MaterialExpressionDivide, -50, 450); inv.set_editor_property("const_a", 1.0); C(one_plus, "", inv, "B")
    fog = X(unreal.MaterialExpressionOneMinus, 100, 450); C(inv, "", fog, "")
    tintc = X(unreal.MaterialExpressionConstant3Vector, 100, 150); tintc.set_editor_property("constant", unreal.LinearColor(*tint, 1.0))
    tinted = mul(sc, tintc, 250, 50)
    wc = X(unreal.MaterialExpressionConstant3Vector, 250, 300); wc.set_editor_property("constant", unreal.LinearColor(*water_color, 1.0))
    fogged = X(unreal.MaterialExpressionLinearInterpolate, 450, 150); C(tinted, "", fogged, "A"); C(wc, "", fogged, "B"); C(fog, "", fogged, "Alpha")
    final = X(unreal.MaterialExpressionLinearInterpolate, 650, 0); C(sc, "", final, "A"); C(fogged, "", final, "B"); C(amount, "", final, "Alpha")
    MEL.connect_material_property(final, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    out.append("%s built (%d expressions)" % (name, MEL.get_num_material_expressions(m)))
    return m

sea_m = build("M_PP_Underwater_Sea", "SeaUnderwater", (0.55, 0.85, 0.9), (0.015, 0.09, 0.12), 0.0008, 0.0025)
sew_m = build("M_PP_Underwater_Sewage", "SewageUnderwater", (0.7, 0.75, 0.45), (0.05, 0.055, 0.015), 0.006, 0.0035)

# ---------- two unbound post-process volumes, one per data layer
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
dls = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
def inst_for(asset_path):
    a = unreal.load_asset(asset_path)
    for d in dls.get_all_data_layers():
        try:
            if d.get_asset() == a: return d
        except Exception: pass
for label, mat, layer in (("PPV_Underwater_Sea", sea_m, "/Game/Levels/DataLayers/RDL_Sea"), ("PPV_Underwater_Sewage", sew_m, "/Game/Levels/DataLayers/RDL_Sewers")):
    ppv = next((a for a in eas.get_all_level_actors() if a.get_actor_label() == label), None)
    if ppv is None:
        ppv = eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
        ppv.set_actor_label(label)
    ppv.set_folder_path("Water")
    ppv.set_editor_property("unbound", True)
    ppv.set_editor_property("priority", 10.0)
    s = ppv.get_editor_property("settings")
    wb = unreal.WeightedBlendables(); wbl = unreal.WeightedBlendable(); wbl.set_editor_property("weight", 1.0); wbl.set_editor_property("object", mat)
    wb.set_editor_property("array", [wbl]); s.set_editor_property("weighted_blendables", wb)
    ppv.set_editor_property("settings", s)
    if ppv.get_editor_property("is_spatially_loaded"): ppv.set_editor_property("is_spatially_loaded", False)
    inst = inst_for(layer)
    r = dls.add_actors_to_data_layer([ppv], inst) if inst else None
    out.append("%s: unbound=%s blendables=%d layer=%s added=%s" % (label, ppv.get_editor_property("unbound"), len(ppv.get_editor_property("settings").get_editor_property("weighted_blendables").get_editor_property("array")), layer.split('/')[-1], r))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump199.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
