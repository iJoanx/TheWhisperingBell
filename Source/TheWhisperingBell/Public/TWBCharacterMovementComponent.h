// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TWBCharacterMovementComponent.generated.h"

UCLASS()
class THEWHISPERINGBELL_API UTWBCharacterMovementComponent : public UCharacterMovementComponent
{
	GENERATED_BODY()

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

	class FNetworkPredictionData_Client_TWB : public FNetworkPredictionData_Client_Character
	{
	public:
		// Make the constructor public so it can be called from UTWBCharacterMovementComponent
		FNetworkPredictionData_Client_TWB(const UCharacterMovementComponent& ClientMovement);
		typedef FNetworkPredictionData_Client_Character Super;
		virtual FSavedMovePtr AllocateNewMove() override;
	};

// Parameters
	UPROPERTY(EditDefaultsOnly) float MaxSprintSpeed = 750.f;

	// Flags
	bool Safe_bWantsToSprint;

public:
	UTWBCharacterMovementComponent();
	
	// Character Movement Component
public:
	virtual FNetworkPredictionData_Client* GetPredictionData_Client() const override;
	virtual float GetMaxSpeed() const override;

protected:
	virtual void UpdateFromCompressedFlags(uint8 Flags) override;
	
	// Interface
public:
	UFUNCTION(BlueprintCallable) void SprintPressed();
	UFUNCTION(BlueprintCallable) void SprintReleased();
};
