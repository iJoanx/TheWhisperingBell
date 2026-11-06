import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal, json
out = []
A = '/Game/Characters/Golkosh/Meshes/Head/ABP_Post_Golkosh.ABP_Post_Golkosh'
out.append(dumpnodes(A + ':AnimGraph'))
for x in infos(nodes(A + ':AnimGraph')):
    if x['type_id'] in ('Animation|Dynamics|RigidBody', 'Animation|SkeletalControls|KawaiiPhysics'):
        r = x['node']['refPath']
        try:
            pl = call('list_properties', {'instance': {'refPath': r}}, OBT)
            out.append("PROPS %s: %s" % (x['type_id'], str(pl)[:600]))
            out.append("NODE %s" % str(getprops(r, ['Node']))[:6000])
        except Exception as e: out.append("err %s" % str(e)[:500])
out.append(str(call('read_graph_dsl', {'graph': {'refPath': A + ':EventGraph'}})))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump78.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
