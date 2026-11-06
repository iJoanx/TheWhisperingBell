import unreal, os
from editor_toolset.toolsets.blueprint import BlueprintTools as BT
out = []
try: out.append("=== DSL DOCS ===\n" + str(BT.get_graph_dsl_docs()))
except Exception as e: out.append("docs err %r" % e)
for bp in ['/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry',
           '/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Exit.BP_WB_Sewer_Exit',
           '/Game/ThirdPerson/Blueprints/BP_Master_PC.BP_Master_PC',
           '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle']:
    out.append("\n\n######## " + bp)
    b = unreal.load_asset(bp)
    try:
        gs = BT.list_graphs(b)
        out.append("graphs: %r" % (gs,))
    except Exception as e:
        out.append("list_graphs err %r" % e); gs = []
    try: out.append("vars: %r" % (BT.list_variables(b),))
    except Exception as e: out.append("vars err %r" % e)
    for g in (gs or []):
        try: out.append("\n--- %s\n%s" % (g.get_path_name() if hasattr(g, "get_path_name") else g, BT.read_graph_dsl(g)))
        except Exception as e: out.append("\n--- %r ERR %r" % (g, e))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump48.txt", "w", encoding="utf-8").write("\n".join(out))
print("written", sum(len(x) for x in out))
