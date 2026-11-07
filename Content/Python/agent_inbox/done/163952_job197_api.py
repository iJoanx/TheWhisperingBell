import re, os
out = []
E = r"C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\Engine"
checks = [
 (E + r"\Classes\GameFramework\CharacterMovementComponent.h", [r".*ConstrainInputAcceleration.*", r".*CanEverSwim.*", r".*virtual void BeginPlay.*", r".*virtual void EndPlay.*", r".*GetMaxSpeed.*", r".*bool IsInWater.*"]),
 (E + r"\Classes\GameFramework\PawnMovementComponent.h", [r".*ConstrainInputAcceleration.*"]),
 (E + r"\Classes\GameFramework\NavMovementComponent.h", [r".*ConstrainInputAcceleration.*"]),
 (E + r"\Classes\Components\InstancedStaticMeshComponent.h", [r".*GetInstancesOverlapping.*", r".*bool GetInstanceTransform.*", r".*GetInstanceCount.*"]),
 (E + r"\Classes\Materials\MaterialParameterCollectionInstance.h", [r".*SetScalarParameterValue.*"]),
 (E + r"\Classes\Materials\MaterialParameterCollection.h", [r".*class .*UMaterialParameterCollection.*"]),
 (E + r"\Public\Subsystems\WorldSubsystem.h", [r".*OnWorldBeginPlay.*", r".*DoesSupportWorldType.*", r".*ShouldCreateSubsystem.*", r".*virtual void Initialize.*", r".*virtual void Deinitialize.*"]),
 (E + r"\Classes\GameFramework\PhysicsVolume.h", [r".*bWaterVolume.*", r".*FluidFriction.*", r".*TerminalVelocity.*", r".*Priority.*"]),
 (E + r"\Classes\Engine\World.h", [r".*LevelAddedToWorld.*", r".*LevelRemovedFromWorld.*", r".*GetParameterCollectionInstance.*"]),
]
for path, pats in checks:
    if not os.path.exists(path): out.append("MISSING " + path); continue
    s = open(path, encoding='utf-8', errors='ignore').read()
    for p in pats:
        ms = [m.group(0).strip()[:220] for m in re.finditer(p, s)][:4]
        out.append("%s :: %s" % (os.path.basename(path), ms))
cpp = E + r"\Private\Components\CharacterMovementComponent.cpp"
s = open(cpp, encoding='utf-8', errors='ignore').read()
for fn in ('FVector UCharacterMovementComponent::ConstrainInputAcceleration', 'void UCharacterMovementComponent::SetDefaultMovementMode', 'Buoyancy = '):
    i = s.find(fn); out.append("=== %s\n%s" % (fn, s[i:i+900] if i >= 0 else 'NOT FOUND'))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump197.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
