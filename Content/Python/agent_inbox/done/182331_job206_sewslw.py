import unreal, traceback
out = []
MEL = unreal.MaterialEditingLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
try:
    mi = unreal.load_asset('/Game/Sewers/Materials/MI_SewerWaterV2_Opaque')
    old = mi.get_editor_property('parent')
    out.append("MI parent: %s" % old.get_path_name())
    texs = MEL.get_used_textures(old)
    out.append("textures used by old master: %s" % [t.get_path_name() for t in texs])
    for fn, getter in (('scalar', MEL.get_scalar_parameter_names), ('vector', MEL.get_vector_parameter_names), ('texture', MEL.get_texture_parameter_names)):
        try: out.append("%s params: %s" % (fn, [str(n) for n in getter(old)]))
        except Exception as e: out.append("%s params err %s" % (fn, e))
    normal = next((t for t in texs if any(k in t.get_name().lower() for k in ('normal', '_n', 'nrm'))), None)
    out.append("chosen normal: %s" % (normal.get_path_name() if normal else None))

    D = '/Game/Water'; name = 'M_SewageWater_SLW'; path = D + '/' + name
    if eal.does_asset_exist(path): eal.delete_asset(path)
    m = at.create_asset(name, D, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('two_sided', True)
    X = lambda cls, x, y: MEL.create_material_expression(m, cls, x, y)
    C = MEL.connect_material_expressions
    def vparam(n, v, x, y):
        e = X(unreal.MaterialExpressionVectorParameter, x, y); e.set_editor_property('parameter_name', n); e.set_editor_property('default_value', unreal.LinearColor(*v)); return e
    def sparam(n, v, x, y):
        e = X(unreal.MaterialExpressionScalarParameter, x, y); e.set_editor_property('parameter_name', n); e.set_editor_property('default_value', v); return e
    # colours matched to the sewage underwater post-process (murky green-brown)
    base = vparam('BaseColor', (0.05, 0.055, 0.015, 1), -600, -300)
    rough = sparam('Roughness', 0.12, -600, -150)
    spec = sparam('Specular', 0.4, -600, -60)
    MEL.connect_material_property(base, '', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(spec, '', unreal.MaterialProperty.MP_SPECULAR)
    if normal:
        pan = X(unreal.MaterialExpressionPanner, -900, 100)
        pan.set_editor_property('speed_x', 0.0); pan.set_editor_property('speed_y', -0.05)
        tc = X(unreal.MaterialExpressionTextureCoordinate, -1100, 100); tc.set_editor_property('u_tiling', 2.0); tc.set_editor_property('v_tiling', 2.0)
        C(tc, '', pan, 'Coordinate')
        ts = X(unreal.MaterialExpressionTextureSample, -650, 100); ts.set_editor_property('texture', normal)
        ts.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        C(pan, '', ts, 'UVs')
        flat = X(unreal.MaterialExpressionConstant3Vector, -650, 300); flat.set_editor_property('constant', unreal.LinearColor(0, 0, 1, 1))
        strength = sparam('NormalStrength', 0.35, -650, 400)
        lerp = X(unreal.MaterialExpressionLinearInterpolate, -350, 150); C(flat, '', lerp, 'A'); C(ts, 'RGB', lerp, 'B'); C(strength, '', lerp, 'Alpha')
        MEL.connect_material_property(lerp, '', unreal.MaterialProperty.MP_NORMAL)
    wo = X(unreal.MaterialExpressionSingleLayerWaterMaterialOutput, 0, 500)
    scat = vparam('ScatteringCoefficients', (0.10, 0.11, 0.03, 1), -400, 450)
    absb = vparam('AbsorptionCoefficients', (1.2, 1.0, 2.5, 1), -400, 600)
    phase = sparam('PhaseG', 0.2, -400, 750)
    behind = sparam('ColorScaleBehindWater', 0.35, -400, 850)
    for e, pin in ((scat, 'Scattering Coefficients'), (absb, 'Absorption Coefficients'), (phase, 'PhaseG'), (behind, 'ColorScaleBehindWater')):
        try: C(e, '', wo, pin)
        except Exception as ex: out.append("connect %s failed: %s" % (pin, ex))
    MEL.recompile_material(m)
    out.append("built %s with %d expressions" % (path, MEL.get_num_material_expressions(m)))
    # point the sewage instance at it (keeps the per-instance two-sided override); old master untouched
    mi.set_editor_property('parent', m)
    MEL.update_material_instance(mi)
    out.append("MI parent now: %s; two-sided override kept: %s" % (mi.get_editor_property('parent').get_path_name(), mi.get_editor_property('base_property_overrides').get_editor_property('two_sided')))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump206.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
