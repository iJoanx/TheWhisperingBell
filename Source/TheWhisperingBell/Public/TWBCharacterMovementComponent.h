#pragma once

#include "CoreMinimal.h"
#include "TWBCharacter.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TWBCharacterMovementComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FDashStartDelegate);

UENUM(BlueprintType)
enum ECustomMovementMode
{
	CMOVE_None			UMETA(Hidden),
	CMOVE_Slide			UMETA(DisplayName = "Slide"),
	CMOVE_MAX			UMETA(Hidden),
};


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
			FLAG_Custom_2		= 0x40,
			FLAG_Custom_3		= 0x80,
		};
		
		// Flags
		uint8 Saved_bPressedTWBJump:1;
		uint8 Saved_bWantsToSprint:1;

		// Other Variables
		uint8 Saved_bHadAnimRootMotion:1;
		uint8 Saved_bTransitionFinished:1;
		uint8 Saved_bPrevWantsToCrouch:1;


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
		FNetworkPredictionData_Client_TWB(const UCharacterMovementComponent& ClientMovement);

		typedef FNetworkPredictionData_Client_Character Super;

		virtual FSavedMovePtr AllocateNewMove() override;
	};

	// Parameters
		UPROPERTY(EditDefaultsOnly) float MaxSprintSpeed=750.f;

		// Slide
		UPROPERTY(EditDefaultsOnly) float MinSlideSpeed=400.f;
		UPROPERTY(EditDefaultsOnly) float MaxSlideSpeed=400.f;
		UPROPERTY(EditDefaultsOnly) float SlideEnterImpulse=400.f;
		UPROPERTY(EditDefaultsOnly) float SlideGravityForce=4000.f;
		UPROPERTY(EditDefaultsOnly) float SlideFrictionFactor=.06f;
		UPROPERTY(EditDefaultsOnly) float BrakingDecelerationSliding=1000.f;


	// Transient
		UPROPERTY(Transient) ATWBCharacter* TWBCharacterOwner;

		// Flags
		bool Safe_bWantsToSprint;

		bool Safe_bHadAnimRootMotion;
		bool Safe_bPrevWantsToCrouch;

		bool Safe_bTransitionFinished;
		TSharedPtr<FRootMotionSource_MoveToForce> TransitionRMS;
		FString TransitionName;
		UPROPERTY(Transient) UAnimMontage* TransitionQueuedMontage;
		float TransitionQueuedMontageSpeed;
		int TransitionRMS_ID;
	

	float AccumulatedClientLocationError=0.f;


	int TickCount=0;
	int CorrectionCount=0;
	int TotalBitsSent=0;
	
	// Delegates
public:
	UPROPERTY(BlueprintAssignable) FDashStartDelegate DashStartDelegate;

public:
	UTWBCharacterMovementComponent();

	void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	// Actor Component
protected:
	virtual void InitializeComponent() override;
	// Character Movement Component
public:
	virtual FNetworkPredictionData_Client* GetPredictionData_Client() const override;
	virtual bool CanCrouchInCurrentState() const override;
	virtual float GetMaxSpeed() const override;
	virtual float GetMaxBrakingDeceleration() const override;

	
protected:
	virtual void UpdateFromCompressedFlags(uint8 Flags) override;
	//virtual void OnClientCorrectionReceived(FNetworkPredictionData_Client_Character& ClientData, float TimeStamp, FVector NewLocation, FVector NewVelocity, UPrimitiveComponent* NewBase, FName NewBaseBoneName, bool bHasBase, bool bBaseRelativePosition, uint8 ServerMovementMode) override;
	virtual void OnClientCorrectionReceived(FNetworkPredictionData_Client_Character& ClientData, float TimeStamp, FVector NewLocation, FVector NewVelocity, UPrimitiveComponent* NewBase, FName NewBaseBoneName, bool bHasBase, bool bBaseRelativePosition, uint8 ServerMovementMode, FVector ServerGravityDirection) override;
public:
	virtual void UpdateCharacterStateBeforeMovement(float DeltaSeconds) override;
	virtual void UpdateCharacterStateAfterMovement(float DeltaSeconds) override;
protected:
	virtual void OnMovementUpdated(float DeltaSeconds, const FVector& OldLocation, const FVector& OldVelocity) override;
	virtual void PhysCustom(float deltaTime, int32 Iterations) override;
	virtual void OnMovementModeChanged(EMovementMode PreviousMovementMode, uint8 PreviousCustomMode) override;

	virtual bool ServerCheckClientError(float ClientTimeStamp, float DeltaTime, const FVector& Accel, const FVector& ClientWorldLocation, const FVector& RelativeClientLocation, UPrimitiveComponent* ClientMovementBase, FName ClientBaseBoneName, uint8 ClientMovementMode) override;

	FNetBitWriter TWBServerMoveBitWriter;
	
	virtual void CallServerMovePacked(const FSavedMove_Character* NewMove, const FSavedMove_Character* PendingMove, const FSavedMove_Character* OldMove) override;
	
	// Slide
private:
	void EnterSlide(EMovementMode PrevMode, ECustomMovementMode PrevCustomMode);
	void ExitSlide();
	bool CanSlide() const;
	void PhysSlide(float deltaTime, int32 Iterations);

	// Helpers
private:
	bool IsServer() const;
	float CapR() const;
	float CapHH() const;
	
	// Interface
public:
	UFUNCTION(BlueprintCallable) void SprintPressed();
	UFUNCTION(BlueprintCallable) void SprintReleased();

	UFUNCTION(BlueprintPure) bool IsCustomMovementMode(ECustomMovementMode InCustomMovementMode) const;
	UFUNCTION(BlueprintPure) bool IsMovementMode(EMovementMode InMovementMode) const;
	
};