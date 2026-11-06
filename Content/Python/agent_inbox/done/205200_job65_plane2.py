import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
P = '/Game/Level/Utility/BP_PlaneOperator.BP_PlaneOperator'
for g in (P + ':UserConstructionScript', P + ':EventGraph'):
    print("=== ", g); print(dumpnodes(g))
m = unreal.load_asset('/Game/Level/Utility/PC_Adv_Data')
print("MPC vectors:", [str(v.get_editor_property('parameter_name')) for v in m.get_editor_property('vector_parameters')])
print("MPC scalars:", [str(v.get_editor_property('parameter_name')) for v in m.get_editor_property('scalar_parameters')])
import os
print("mpc file mtime", os.path.getmtime(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Level\Utility\PC_Adv_Data.uasset"), os.path.getmtime(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Level\Utility\BP_PlaneOperator.uasset"))
