// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TWBCharacterMovementComponent.generated.h"

UENUM(BlueprintType)
enum ETWBCustomMovementMode : uint8
{
	CMOVE_None UMETA(Hidden),
	CMOVE_Slide UMETA(DisplayName = "Slide"),
	CMOVE_MAX UMETA(Hidden),
};

UCLASS()
class THEWHISPERINGBELL_API UTWBCharacterMovementComponent : public UCharacterMovementComponent
{
	GENERATED_BODY()

#pragma region NetworkPrediction

	// Client prediction payload for sprint state.
	class FSavedMove_TWB : public FSavedMove_Character
	{
	public:
		enum CompressedFlags
		{
			FLAG_Sprint			= 0x10,
		};
		
		// Flags
		uint8 Saved_bWantsToSprint:1;


		FSavedMove_TWB();

		virtual bool CanCombineWith(const FSavedMovePtr& NewMove, ACharacter* InCharacter, float MaxDelta) const override;
		virtual void Clear() override;
		virtual uint8 GetCompressedFlags() const override;
		virtual void SetMoveFor(ACharacter* C, float InDeltaTime, FVector const& NewAccel, FNetworkPredictionData_Client_Character& ClientData) override;
		virtual void PrepMoveFor(ACharacter* C) override;
	};

	// Client-side move allocator for our saved-move type.
	class FNetworkPredictionData_Client_TWB : public FNetworkPredictionData_Client_Character
	{
	public:
		FNetworkPredictionData_Client_TWB(const UCharacterMovementComponent& ClientMovement);
		typedef FNetworkPredictionData_Client_Character Super;
		virtual FSavedMovePtr AllocateNewMove() override;
	};

#pragma endregion

private:
#pragma region Tuning

	// Movement tuning
	UPROPERTY(EditDefaultsOnly) float MaxSprintSpeed = 750.f;

	// Slide tuning
	UPROPERTY(EditDefaultsOnly) float MinSlideSpeed = 400.f;
	UPROPERTY(EditDefaultsOnly) float MaxSlideSpeed = 400.f;
	UPROPERTY(EditDefaultsOnly) float SlideEnterImpulse = 400.f;
	UPROPERTY(EditDefaultsOnly) float SlideGravityForce = 4000.f;
	UPROPERTY(EditDefaultsOnly) float SlideFrictionFactor = 0.06f;
	UPROPERTY(EditDefaultsOnly) float BrakingDecelerationSliding = 1000.f;

#pragma endregion

#pragma region RuntimeState

	// Runtime state
	bool Safe_bWantsToSprint = false;
	bool bSavedOrientRotationToMovement = true;
	bool bSavedUseControllerDesiredRotation = false;
	bool bHasSavedRotationPolicy = false;

#pragma endregion

public:
	UTWBCharacterMovementComponent();

#pragma region Overrides

	// UCharacterMovementComponent overrides
public:
	virtual FNetworkPredictionData_Client* GetPredictionData_Client() const override;
	virtual bool IsMovingOnGround() const override;
	virtual bool CanCrouchInCurrentState() const override;
	virtual float GetMaxSpeed() const override;
	virtual float GetMaxBrakingDeceleration() const override;

protected:
	virtual void UpdateFromCompressedFlags(uint8 Flags) override;
	virtual void UpdateCharacterStateBeforeMovement(float DeltaSeconds) override;
	virtual void OnMovementUpdated(float DeltaSeconds, const FVector& OldLocation, const FVector& OldVelocity) override;
	virtual void PhysCustom(float DeltaTime, int32 Iterations) override;
	virtual void OnMovementModeChanged(EMovementMode PreviousMovementMode, uint8 PreviousCustomMode) override;

#pragma endregion

private:
#pragma region SlideHelpers

	// Slide mode helpers
	void EnterSlide();
	void ExitSlide();
	bool CanSlide() const;
	void PhysSlide(float DeltaTime, int32 Iterations);

#pragma endregion

#pragma region InputAPI

	// Input/API surface
public:
	UFUNCTION(BlueprintCallable) void SprintPressed();
	UFUNCTION(BlueprintCallable) void SprintReleased();

	UFUNCTION(BlueprintCallable) void CrouchPressed();
	UFUNCTION(BlueprintCallable) void CrouchReleased();

	UFUNCTION(BlueprintPure) bool IsCustomMovementMode(ETWBCustomMovementMode InCustomMovementMode) const;
	UFUNCTION(BlueprintPure) bool IsMovementMode(EMovementMode InMovementMode) const;

#pragma endregion
};
