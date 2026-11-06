import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
dn = [a for a in acts if "DayNight" in a.get_class().get_name()][0]
def g(o, p):
    try: return o.get_editor_property(p)
    except Exception: return "?"
for c in dn.get_components_by_class(unreal.ActorComponent):
    cn = c.get_class().get_name()
    if cn in ("SkyLightComponent","ExponentialHeightFogComponent","DirectionalLightComponent","TimelineComponent"):
        names = [p for p in dir(c) if any(k in p for k in ("real_time","volumetric_fog","ray_traced","cast_volumetric","play_rate","timeline_length","looping","shadow_amount","contact_shadow","atmosphere_sun_light_index","transmission","cast_dynamic","static_shadow","affects_world"))]
        print(c.get_name(), cn)
        for p in names:
            if p.startswith("set_") or p.startswith("get_"): continue
            print("   ", p, g(c, p))
        if cn == "TimelineComponent":
            for f in ("get_play_rate","get_timeline_length","is_looping","is_playing"):
                try: print("   ", f, getattr(c, f)())
                except Exception as e: print("   ", f, "?")
# sewer share
sew = [a for a in acts if a.get_actor_label().startswith(("SL_","SewerNetwork"))]
comps=0; inst=0; cast=0; df=0
for a in sew:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        comps+=1
        if g(c,"cast_shadow") is True: cast+=1
        if g(c,"affect_distance_field_lighting") is True: df+=1
        if isinstance(c, unreal.InstancedStaticMeshComponent):
            try: inst+=c.get_instance_count()
            except: pass
print("sewer actors", len(sew), "smcomps", comps, "casting", cast, "dfaffect", df, "instances", inst)
# DL_Sewers runtime state
try:
    sub = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
    for d in sub.get_all_data_layers():
        print("DL", d.get_name(), "initial", g(d,"initial_runtime_state"), "type", g(d,"data_layer_type") if hasattr(d,"data_layer_type") else "", "loaded_in_editor", g(d,"is_loaded_in_editor"))
except Exception as e: print("dl err", e)
for cv in ("r.Shadow.CSMCaching","r.Shadow.DistanceFieldPenumbraSize","r.Lumen.DiffuseIndirect.Allow","r.Shadow.MaxCSMResolution","r.Shadow.RadiusThreshold","r.VolumetricFog","r.ShadowQuality","r.Lumen.SceneLightingForceFullUpdate"):
    try: print(cv, unreal.SystemLibrary.get_console_variable_int_value(cv), unreal.SystemLibrary.get_console_variable_float_value(cv))
    except Exception: print(cv,"?")
