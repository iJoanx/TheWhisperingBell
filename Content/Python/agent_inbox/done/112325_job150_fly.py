import unreal
cdo = unreal.get_default_object(unreal.load_class(None, '/Game/ThirdPerson/Blueprints/CBP_Familiar_Bolita.CBP_Familiar_Bolita_C'))
for p in ('use_controller_rotation_pitch', 'use_controller_rotation_yaw', 'use_controller_rotation_roll'):
    print(p, cdo.get_editor_property(p))
cmc = cdo.get_editor_property('character_movement')
for p in ('max_fly_speed', 'braking_deceleration_flying', 'max_acceleration', 'orient_rotation_to_movement', 'use_controller_desired_rotation', 'rotation_rate'):
    try: print(p, cmc.get_editor_property(p))
    except Exception as e: print(p, '?')
bs = unreal.load_asset('/Game/Characters/Bolita/Meshes/BS_Bolita_Flight')
for p in ('interpolation_param', 'target_weight_interpolation_speed_per_sec', 'axis_to_scale_animation'):
    try: print(p, bs.get_editor_property(p))
    except Exception as e: print(p, '?', str(e)[:60])
try:
    for s in bs.get_editor_property('sample_data'):
        print("sample", s.get_editor_property('animation').get_name() if s.get_editor_property('animation') else None, s.get_editor_property('sample_value'))
except Exception as e: print("samples ?", str(e)[:100])
try: print("params", [ (x.get_editor_property('display_name'), x.get_editor_property('min'), x.get_editor_property('max')) for x in bs.get_editor_property('blend_parameters')])
except Exception as e: print("params ?", str(e)[:100])
