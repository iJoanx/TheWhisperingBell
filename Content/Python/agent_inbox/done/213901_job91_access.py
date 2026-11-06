import re
def access_at(path, needle):
    L = open(path, encoding="utf-8", errors="ignore").read().splitlines()
    idx = [i for i, l in enumerate(L) if needle in l]
    for i in idx:
        acc = None
        for j in range(i, -1, -1):
            m = re.match(r"\s*(public|protected|private)\s*:", L[j])
            if m: acc = m.group(1); break
            if re.match(r"\s*(class|struct)\s+\w+.*:\s*public", L[j]) and j < i - 1: break
        print(path.split('\\')[-1], i + 1, acc, L[i].strip()[:120])
E = r"C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\Engine"
access_at(E + r"\Classes\Components\SkeletalMeshComponent.h", "uint8 bOnlyAllowAutonomousTickPose")
access_at(E + r"\Classes\GameFramework\CharacterMovementComponent.h", "virtual void TickCharacterPose(")
access_at(E + r"\Classes\GameFramework\Character.h", "bool IsPlayingRootMotion(")
