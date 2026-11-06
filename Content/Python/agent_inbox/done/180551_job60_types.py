import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
EG = '/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry:EventGraph'
US = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle:UpdateSun'
GK = '/Game/ThirdPerson/Blueprints/CBP_PC_GolKosh.CBP_PC_GolKosh:EventGraph'
for g, fl in [(US, ["SetCastShadows", "GetForwardVector"]),
              (EG, ["ContainsDataLayer", "DataLayer", "ActorHasTag", "SetVisibility", "GetAllActorsOfClass", "IsLocallyControlled", "CastToPawn", "Distance", "GetWorldLocation", "ForEachLoop", "GetRootComponent", "SetActorLocation", "Boolean|NOT", "Vector|Distance", "FlowControl|Branch", "PostProcessVolume", "Settings|Set", "SetbEnabled"]),
              (GK, ["GetController", "GetActorTransform", "Possess", "CastToPlayerController"])]:
    for f in fl:
        try:
            r = types(g, f)
            ids = [x.get('type_id', x) if isinstance(x, dict) else x for x in (r or [])]
            out.append("Q %s | %s" % (f, ids[:30]))
        except Exception as e: out.append("Q %s ERR %s" % (f, str(e)[:200]))

open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump60.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
