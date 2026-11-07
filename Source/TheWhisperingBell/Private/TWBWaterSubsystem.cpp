// Fill out your copyright notice in the Description page of Project Settings.

#include "TWBWaterSubsystem.h"

#include "EngineUtils.h"
#include "Engine/Level.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "GameFramework/PhysicsVolume.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"

#if WITH_EDITOR
#include "LevelEditorViewport.h"
#endif

const FName UTWBWaterSubsystem::SeaTag(TEXT("Water_Sea"));
const FName UTWBWaterSubsystem::SewageTag(TEXT("Water_Sewage"));
const FName UTWBWaterSubsystem::UndersideTag(TEXT("Water_Underside"));

bool UTWBWaterSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE || WorldType == EWorldType::Editor;
}

void UTWBWaterSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	// World Partition cells and data layers stream in as levels; pick up their water as they arrive.
	LevelAddedHandle = FWorldDelegates::LevelAddedToWorld.AddUObject(this, &UTWBWaterSubsystem::OnLevelAdded);
}

void UTWBWaterSubsystem::Deinitialize()
{
	FWorldDelegates::LevelAddedToWorld.Remove(LevelAddedHandle);
	Surfaces.Reset();
	Super::Deinitialize();
}

void UTWBWaterSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);

	RebuildAllSurfaces();

	SeaVolume = SpawnWaterVolume();
	SewageVolume = SpawnWaterVolume();
}

void UTWBWaterSubsystem::RebuildAllSurfaces()
{
	Surfaces.Reset();
	Undersides.Reset();
	ShownUndersides.Reset();
	if (UWorld* World = GetWorld())
	{
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			AddActorSurfaces(*It);
		}
	}
}

TStatId UTWBWaterSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UTWBWaterSubsystem, STATGROUP_Tickables);
}

void UTWBWaterSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	const UWorld* World = GetWorld();
	if (World && World->WorldType == EWorldType::Editor)
	{
		TickEditorPreview();
	}
}

void UTWBWaterSubsystem::TickEditorPreview()
{
#if WITH_EDITOR
	UWorld* World = GetWorld();
	if (!World || !GCurrentLevelEditingViewportClient)
	{
		return;
	}

	// Water gets placed, moved and streamed while editing: rescan every couple of seconds.
	const double Now = FPlatformTime::Seconds();
	if (Now - LastEditorRebuildTime > 2.0)
	{
		LastEditorRebuildTime = Now;
		RebuildAllSurfaces();
	}

	static const FSoftObjectPath CollectionPath(TEXT("/Game/Water/MPC_Water.MPC_Water"));
	UMaterialParameterCollection* Collection = Cast<UMaterialParameterCollection>(CollectionPath.TryLoad());
	UMaterialParameterCollectionInstance* Parameters = Collection ? World->GetParameterCollectionInstance(Collection) : nullptr;
	if (!Parameters)
	{
		return;
	}

	const FTWBWaterQuery CameraWater = FindWater(GCurrentLevelEditingViewportClient->GetViewLocation(), 0.f, 100000.f, 400.f);
	const bool bUnder = CameraWater.IsValid() && CameraWater.Depth > 0.f;
	const float Sea = (bUnder && CameraWater.Type == ETWBWaterType::Sea) ? 1.f : 0.f;
	const float Sewage = (bUnder && CameraWater.Type == ETWBWaterType::Sewage) ? 1.f : 0.f;
	if (Sea != LastEditorSea || Sewage != LastEditorSewage)
	{
		Parameters->SetScalarParameterValue(TEXT("SeaUnderwater"), Sea);
		Parameters->SetScalarParameterValue(TEXT("SewageUnderwater"), Sewage);
		LastEditorSea = Sea;
		LastEditorSewage = Sewage;
	}
	Parameters->SetScalarParameterValue(TEXT("UnderwaterDepth"), bUnder ? CameraWater.Depth : 0.f);
#endif
}

void UTWBWaterSubsystem::OnLevelAdded(ULevel* Level, UWorld* World)
{
	if (!Level || World != GetWorld())
	{
		return;
	}
	for (AActor* Actor : Level->Actors)
	{
		AddActorSurfaces(Actor);
	}
}

void UTWBWaterSubsystem::AddActorSurfaces(AActor* Actor)
{
	if (!IsValid(Actor))
	{
		return;
	}

	TInlineComponentArray<UStaticMeshComponent*> Components(Actor);
	for (UStaticMeshComponent* Component : Components)
	{
		if (!Component || !Component->GetStaticMesh())
		{
			continue;
		}

		if (Component->ComponentHasTag(UndersideTag))
		{
			if (!Undersides.Contains(Component))
			{
				Undersides.Add(Component);
				// In game they start hidden; the editor keeps showing them.
				const UWorld* World = GetWorld();
				if (World && World->IsGameWorld())
				{
					Component->SetVisibility(false);
				}
			}
			continue;
		}

		ETWBWaterType Type = ETWBWaterType::NoWater;
		if (Component->ComponentHasTag(SeaTag))
		{
			Type = ETWBWaterType::Sea;
		}
		else if (Component->ComponentHasTag(SewageTag))
		{
			Type = ETWBWaterType::Sewage;
		}
		if (Type == ETWBWaterType::NoWater)
		{
			continue;
		}

		const bool bAlreadyKnown = Surfaces.ContainsByPredicate([Component](const FSurface& S) { return S.Component.Get() == Component; });
		if (bAlreadyKnown)
		{
			continue;
		}

		FSurface& Surface = Surfaces.AddDefaulted_GetRef();
		Surface.Component = Component;
		Surface.Type = Type;
		Surface.LocalBox = Component->GetStaticMesh()->GetBoundingBox();
		Surface.bInstanced = Component->IsA<UInstancedStaticMeshComponent>();
	}
}

void UTWBWaterSubsystem::UpdateUndersides(const FVector& CameraLocation, bool bCameraUnderSewage)
{
	if (!bCameraUnderSewage)
	{
		// Left the water: hide what was shown (only ever the few pieces near the camera).
		for (const TWeakObjectPtr<UPrimitiveComponent>& Weak : ShownUndersides)
		{
			if (UPrimitiveComponent* Component = Weak.Get())
			{
				Component->SetVisibility(false);
			}
		}
		ShownUndersides.Reset();
		return;
	}

	// Under the sewage: keep the pieces around the camera drawn, refreshed a few times a second.
	const double Now = FPlatformTime::Seconds();
	if (Now - LastUndersideUpdate < 0.25 && ShownUndersides.Num() > 0)
	{
		return;
	}
	LastUndersideUpdate = Now;

	const float RadiusSquared = FMath::Square(UndersideShowRadius);
	for (int32 Index = Undersides.Num() - 1; Index >= 0; --Index)
	{
		const TWeakObjectPtr<UPrimitiveComponent> Weak = Undersides[Index];
		UPrimitiveComponent* Component = Weak.Get();
		if (!Component)
		{
			Undersides.RemoveAtSwap(Index);
			ShownUndersides.Remove(Weak);
			continue;
		}
		const bool bNear = Component->Bounds.GetBox().ComputeSquaredDistanceToPoint(CameraLocation) <= RadiusSquared;
		const bool bShown = ShownUndersides.Contains(Weak);
		if (bNear && !bShown)
		{
			Component->SetVisibility(true);
			ShownUndersides.Add(Weak);
		}
		else if (!bNear && bShown)
		{
			Component->SetVisibility(false);
			ShownUndersides.Remove(Weak);
		}
	}
}

APhysicsVolume* UTWBWaterSubsystem::SpawnWaterVolume()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return nullptr;
	}

	// A brushless physics volume: it never contains anything by itself, the movement component
	// hands it out while the character is inside a water surface so the engine's swimming runs.
	FActorSpawnParameters Params;
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	APhysicsVolume* Volume = World->SpawnActor<APhysicsVolume>(APhysicsVolume::StaticClass(), FTransform::Identity, Params);
	if (Volume)
	{
		Volume->bWaterVolume = true;
		Volume->SetActorEnableCollision(false);
	}
	return Volume;
}

APhysicsVolume* UTWBWaterSubsystem::GetWaterVolume(ETWBWaterType Type)
{
	TObjectPtr<APhysicsVolume>& Volume = (Type == ETWBWaterType::Sewage) ? SewageVolume : SeaVolume;
	if (Type == ETWBWaterType::NoWater)
	{
		return nullptr;
	}
	if (!IsValid(Volume))
	{
		Volume = SpawnWaterVolume();
	}
	return Volume;
}

bool UTWBWaterSubsystem::TestSurface(const FTransform& SurfaceTransform, const FBox& LocalBox, const FVector& Location,
	float MaxAbove, float MaxDepth, float& OutSurfaceZ)
{
	// Inside the surface's outline (in its own, possibly tilted, space)?
	const FVector Local = SurfaceTransform.InverseTransformPosition(Location);
	constexpr float EdgeSlack = 10.f;
	if (Local.X < LocalBox.Min.X - EdgeSlack || Local.X > LocalBox.Max.X + EdgeSlack ||
		Local.Y < LocalBox.Min.Y - EdgeSlack || Local.Y > LocalBox.Max.Y + EdgeSlack)
	{
		return false;
	}

	const FVector Up = SurfaceTransform.GetUnitAxis(EAxis::Z);
	if (Up.Z < 0.2f)
	{
		return false; // a wall or an upside-down plane, not a waterline
	}

	// The waterline is the top face of the mesh. Measure straight up from the location to that (tilted) plane.
	const FVector PointOnSurface = SurfaceTransform.TransformPosition(FVector(Local.X, Local.Y, LocalBox.Max.Z));
	const float Rise = FVector::DotProduct(PointOnSurface - Location, Up) / Up.Z;
	if (Rise > MaxDepth || Rise < -MaxAbove)
	{
		return false;
	}

	OutSurfaceZ = Location.Z + Rise;
	return true;
}

FTWBWaterQuery UTWBWaterSubsystem::FindWater(const FVector& Location, float MaxAbove, float SeaMaxDepth, float SewageMaxDepth)
{
	FTWBWaterQuery Result;
	float BestRise = TNumericLimits<float>::Max();

	auto Consider = [&](ETWBWaterType Type, float SurfaceZ)
	{
		const float Rise = SurfaceZ - Location.Z;
		// The nearest surface wins, so a tunnel under another tunnel uses its own water.
		if (Rise < BestRise)
		{
			BestRise = Rise;
			Result.Type = Type;
			Result.SurfaceZ = SurfaceZ;
			Result.Depth = Rise;
		}
	};

	for (int32 Index = Surfaces.Num() - 1; Index >= 0; --Index)
	{
		const FSurface& Surface = Surfaces[Index];
		const UStaticMeshComponent* Component = Surface.Component.Get();
		if (!Component)
		{
			Surfaces.RemoveAtSwap(Index); // its level streamed out
			continue;
		}

		const float MaxDepth = (Surface.Type == ETWBWaterType::Sea) ? SeaMaxDepth : SewageMaxDepth;
		const FBox WorldBox = Component->Bounds.GetBox();
		if (Location.X < WorldBox.Min.X || Location.X > WorldBox.Max.X ||
			Location.Y < WorldBox.Min.Y || Location.Y > WorldBox.Max.Y ||
			Location.Z > WorldBox.Max.Z + MaxAbove || Location.Z < WorldBox.Min.Z - MaxDepth)
		{
			continue;
		}

		float SurfaceZ = 0.f;
		if (Surface.bInstanced)
		{
			const UInstancedStaticMeshComponent* Instanced = static_cast<const UInstancedStaticMeshComponent*>(Component);
			const FBox Probe(Location - FVector(50.f, 50.f, MaxAbove), Location + FVector(50.f, 50.f, MaxDepth));
			for (const int32 InstanceIndex : Instanced->GetInstancesOverlappingBox(Probe, true))
			{
				FTransform InstanceTransform;
				if (Instanced->GetInstanceTransform(InstanceIndex, InstanceTransform, true) &&
					TestSurface(InstanceTransform, Surface.LocalBox, Location, MaxAbove, MaxDepth, SurfaceZ))
				{
					Consider(Surface.Type, SurfaceZ);
				}
			}
		}
		else if (TestSurface(Component->GetComponentTransform(), Surface.LocalBox, Location, MaxAbove, MaxDepth, SurfaceZ))
		{
			Consider(Surface.Type, SurfaceZ);
		}
	}

	return Result;
}
