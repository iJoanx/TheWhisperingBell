import json, os
import inspect
import toolset_registry._registry_interface as RI, editor_toolset.toolsets.programmatic as PG
print(inspect.signature(RI.execute_tool), inspect.signature(PG.execute_tool))
execute_tool = PG.execute_tool
T = 'editor_toolset.toolsets.blueprint.BlueprintTools.'
def call(n, a):
    r = execute_tool(T + n, json.dumps(a))
    return r['returnValue'] if isinstance(r, dict) and 'returnValue' in r else r
outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else ".", "")
out = []
try: out.append("=== DSL DOCS ===\n" + str(call('get_graph_dsl_docs', {})))
except Exception as e: out.append("docs err %s" % e)
for bp in ['/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry',
           '/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Exit.BP_WB_Sewer_Exit',
           '/Game/ThirdPerson/Blueprints/BP_Master_PC.BP_Master_PC',
           '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle']:
    out.append("\n\n######## " + bp)
    try:
        gs = call('list_graphs', {'blueprint': {'refPath': bp}})
        out.append("graphs: " + json.dumps(gs)[:3000])
        try: out.append("vars: " + json.dumps(call('list_variables', {'blueprint': {'refPath': bp}}))[:4000])
        except Exception as e: out.append("vars err %s" % e)
        refs = []
        def walk(x):
            if isinstance(x, dict):
                if 'refPath' in x: refs.append(x['refPath'])
                for v in x.values(): walk(v)
            elif isinstance(x, list):
                for v in x: walk(v)
        walk(gs)
        for g in refs:
            try: out.append("\n--- " + g + "\n" + str(call('read_graph_dsl', {'graph': {'refPath': g}})))
            except Exception as e: out.append("\n--- " + g + " ERR " + str(e)[:300])
    except Exception as e:
        out.append("ERR %s" % e)
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump45.txt", "w", encoding="utf-8").write("\n".join(out))
print("written", sum(len(x) for x in out))
