// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "TWBWaterSubsystem.generated.h"

class UStaticMeshComponent;
class UPrimitiveComponent;
class APhysicsVolume;
class ULevel;

UENUM(BlueprintType)
enum class ETWBWaterType : uint8
{
	NoWater UMETA(DisplayName = "None"),
	Sea,
	Sewage
};

USTRUCT(BlueprintType)
struct FTWBWaterQuery
{
	GENERATED_BODY()

	// Which water was found (NoWater = none here).
	UPROPERTY(BlueprintReadOnly, Category = "Water")
	ETWBWaterType Type = ETWBWaterType::NoWater;

	// World Z of the water surface straight above (or below) the queried location.
	UPROPERTY(BlueprintReadOnly, Category = "Water")
	float SurfaceZ = 0.f;

	// How far the location is under the surface. Negative = above it.
	UPROPERTY(BlueprintReadOnly, Category = "Water")
	float Depth = 0.f;

	bool IsValid() const { return Type != ETWBWaterType::NoWater; }
};

/**
 * Knows where the water is. Any static mesh component tagged "Water_Sea" or "Water_Sewage"
 * counts as a water surface: its top face (which may be tilted) is the waterline, and
 * everything below it inside its outline is water. Instanced components are checked per instance.
 * Swimming (TWBCharacterMovementComponent) and the underwater look both ask this.
 * In the editor it also drives the underwater look from the viewport camera, so it previews without PIE.
 */
UCLASS()
class THEWHISPERINGBELL_API UTWBWaterSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	static const FName SeaTag;
	static const FName SewageTag;
	static const FName UndersideTag;

	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;

	// Ticking (editor preview of the underwater look)
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual bool IsTickableInEditor() const override { return true; }

	/**
	 * Finds the water surface at Location.
	 * MaxAbove: how far above the surface the location may be and still count.
	 * SeaMaxDepth / SewageMaxDepth: how far below a surface still counts as inside that water.
	 */
	FTWBWaterQuery FindWater(const FVector& Location, float MaxAbove, float SeaMaxDepth, float SewageMaxDepth);

	UFUNCTION(BlueprintCallable, Category = "Water", meta = (DisplayName = "Find Water At"))
	FTWBWaterQuery FindWaterAt(FVector Location, float MaxAbove = 0.f, float SeaMaxDepth = 100000.f, float SewageMaxDepth = 400.f)
	{
		return FindWater(Location, MaxAbove, SeaMaxDepth, SewageMaxDepth);
	}

	/**
	 * Sewer water seen from below (components tagged Water_Underside) is hidden in game and only drawn
	 * near a camera that is under the sewage, so its water pass costs nothing the rest of the time.
	 * Called every frame by the local player's movement component; it only changes visibility when needed.
	 */
	void UpdateUndersides(const FVector& CameraLocation, bool bCameraUnderSewage);

	/** The (invisible, brushless) water volume the movement component reports while swimming in this water type. */
	APhysicsVolume* GetWaterVolume(ETWBWaterType Type);

private:
	struct FSurface
	{
		TWeakObjectPtr<UStaticMeshComponent> Component;
		ETWBWaterType Type = ETWBWaterType::NoWater;
		FBox LocalBox = FBox(ForceInit);
		bool bInstanced = false;
	};

	TArray<FSurface> Surfaces;
	TArray<TWeakObjectPtr<UPrimitiveComponent>> Undersides;
	TSet<TWeakObjectPtr<UPrimitiveComponent>> ShownUndersides;
	double LastUndersideUpdate = -1000.0;
	static constexpr float UndersideShowRadius = 4000.f;
	FDelegateHandle LevelAddedHandle;

	UPROPERTY(Transient)
	TObjectPtr<APhysicsVolume> SeaVolume;

	UPROPERTY(Transient)
	TObjectPtr<APhysicsVolume> SewageVolume;

	double LastEditorRebuildTime = -1000.0;
	float LastEditorSea = -1.f;
	float LastEditorSewage = -1.f;

	void RebuildAllSurfaces();
	void TickEditorPreview();
	void AddActorSurfaces(AActor* Actor);
	void OnLevelAdded(ULevel* Level, UWorld* World);
	APhysicsVolume* SpawnWaterVolume();

	static bool TestSurface(const FTransform& SurfaceTransform, const FBox& LocalBox, const FVector& Location,
		float MaxAbove, float MaxDepth, float& OutSurfaceZ);
};
