import re, os, glob
out = []
E = r"C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\Engine"
s = open(E + r"\Classes\GameFramework\CharacterMovementComponent.h", encoding='utf-8', errors='ignore').read()
for p in (r".*ShouldRemainVertical.*", r".*virtual void TickComponent.*", r".*UpdateCharacterStateBeforeMovement.*"):
    out.append(str([m.group(0).strip() for m in re.finditer(p, s)]))
s2 = open(E + r"\Classes\AI\Navigation\NavigationTypes.h", encoding='utf-8', errors='ignore').read() if os.path.exists(E + r"\Classes\AI\Navigation\NavigationTypes.h") else ''
out.append("bCanSwim in NavigationTypes: %s" % [m.group(0).strip() for m in re.finditer(r".*bCanSwim.*", s2)][:3])
for f in glob.glob(E + r"\**\MaterialParameterCollectionInstance.h", recursive=True)[:3]: out.append("MPCI header: " + f)
for f in glob.glob(E + r"\**\NavMovementComponent.h", recursive=True)[:2]:
    t = open(f, encoding='utf-8', errors='ignore').read()
    out.append("NavMovement %s CanEverSwim: %s" % (f, [m.group(0).strip() for m in re.finditer(r".*CanEverSwim.*", t)][:2]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump198.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
