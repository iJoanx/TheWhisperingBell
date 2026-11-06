import unreal
L = unreal.EditorLevelLibrary
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("world:", w.get_path_name())
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
print("loaded actors:", len(acts))
def g(o, p):
    try: return o.get_editor_property(p)
    except Exception as e: return "?"
dn = [a for a in acts if "DayNight" in a.get_class().get_name()]
for a in dn:
    print("DN:", a.get_actor_label(), a.get_path_name())
    for p in ("is_spatially_loaded","primary_actor_tick","b_replicates","net_load_on_client","runtime_grid"):
        print("  ", p, g(a, p))
    try: print("   data layers:", [str(x) for x in a.get_data_layer_assets()])
    except Exception as e: print("   dl err", e)
    for c in a.get_components_by_class(unreal.ActorComponent):
        cn = c.get_class().get_name()
        print("  COMP", c.get_name(), cn)
        props = {
         "DirectionalLightComponent": ["mobility","cast_shadows","dynamic_shadow_distance_movable_light","dynamic_shadow_cascades","distance_field_shadow_distance","b_use_ray_traced_distance_field_shadows","cast_ray_traced_shadow","shadow_cascade_distribution_exponent","far_shadow_cascade_count","forward_shading_priority","atmosphere_sun_light","cast_cloud_shadows","b_cast_volumetric_shadow","volumetric_scattering_intensity","intensity","light_source_angle"],
         "SkyLightComponent": ["mobility","b_real_time_capture","source_type","cast_shadows","b_lower_hemisphere_is_black","sky_distance_threshold","b_capture_emissive_only"],
         "ExponentialHeightFogComponent": ["b_enable_volumetric_fog","volumetric_fog_distance","volumetric_fog_extinction_scale"],
         "VolumetricCloudComponent": ["layer_bottom_altitude","layer_height","view_sample_count_scale","reflection_view_sample_count_scale","shadow_view_sample_count_scale","b_use_per_sample_atmospheric_light_transmittance"],
         "TimelineComponent": [],
         "StaticMeshComponent": ["mobility","cast_shadow","static_mesh"],
        }.get(cn, [])
        for p in props: print("     ", p, g(c, p))
# other sun/sky actors in level (duplicates?)
from collections import Counter
cnt = Counter(a.get_class().get_name() for a in acts)
for k in ("DirectionalLight","SkyLight","SkyAtmosphere","ExponentialHeightFog","VolumetricCloud","PostProcessVolume","LightmassImportanceVolume","WorldPartitionHLOD"):
    print("count", k, sum(v for n,v in cnt.items() if k in n))
# shadow casters
sm = 0; inst = 0; cast = 0; movable=0
for a in acts:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm += 1
        if g(c,"cast_shadow") is True: cast += 1
        if str(g(c,"mobility")).endswith("MOVABLE"): movable += 1
        if isinstance(c, unreal.InstancedStaticMeshComponent):
            try: inst += c.get_instance_count()
            except: pass
print("static mesh comps", sm, "casting", cast, "movable", movable, "instances", inst)
ws = w.get_world_settings()
for p in ("enable_world_partition_streaming",):
    print(p, g(ws,p))
for cv in ("r.Shadow.Virtual.Enable","r.DynamicGlobalIlluminationMethod","r.ReflectionMethod","r.Lumen.HardwareRayTracing","r.SkyLight.RealTimeReflectionCapture","r.VolumetricCloud","r.DistanceFields","wp.Runtime.EnableStreaming"):
    try: print(cv, unreal.SystemLibrary.get_console_variable_int_value(cv))
    except Exception as e: print(cv, "?")
print("top classes", cnt.most_common(15))
