import os, re
root = r"C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\Engine"
files = [r"Private\Components\CharacterMovementComponent.cpp", r"Classes\Components\SkeletalMeshComponent.h", r"Private\Character.cpp", r"Classes\GameFramework\CharacterMovementComponent.h", r"Private\Components\SkeletalMeshComponent.cpp"]
for f in files:
    p = os.path.join(root, f)
    try: L = open(p, encoding="utf-8", errors="ignore").read().splitlines()
    except Exception as e: print("missing", f); continue
    for i, l in enumerate(L):
        if re.search(r"bOnlyAllowAutonomousTickPose|TickCharacterPose\(|bServerAcceptClientAuthoritativePosition|ListenServerNetworkSimulatedSmooth|bEnableServerDualMoveScopedMovementUpdates|bWasSimulatingRootMotion|bAutonomousTickPose", l):
            ctx = " | ".join(x.strip() for x in L[max(0, i-2):i+3])
            print("%s:%d  %s" % (f.split('\\')[-1], i+1, ctx[:420]))
