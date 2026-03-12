// Fill out your copyright notice in the Description page of Project Settings.


#include "TWBCharacterMovementComponent.h"

#include "GameFramework/Character.h"
#include "GameFramework/Controller.h"
#include "Components/CapsuleComponent.h"

#pragma region SavedMove

UTWBCharacterMovementComponent::FSavedMove_TWB::FSavedMove_TWB()
{
	Saved_bWantsToRun = 0;
	Saved_bWantsToSprint = 0;
}

bool UTWBCharacterMovementComponent::FSavedMove_TWB::CanCombineWith(const FSavedMovePtr& NewMove, ACharacter* InCharacter, float MaxDelta) const
{
	FSavedMove_TWB* NewTWBMove = static_cast<FSavedMove_TWB*>(NewMove.Get());

	if (Saved_bWantsToRun != NewTWBMove->Saved_bWantsToRun)
	{
		return false;
	}
	if (Saved_bWantsToSprint != NewTWBMove->Saved_bWantsToSprint)
	{
		return false;
	}

	return FSavedMove_Character::CanCombineWith(NewMove, InCharacter, MaxDelta);
}

void UTWBCharacterMovementComponent::FSavedMove_TWB::Clear()
{
	FSavedMove_Character::Clear();

	Saved_bWantsToRun = 0;
	Saved_bWantsToSprint = 0;
}

uint8 UTWBCharacterMovementComponent::FSavedMove_TWB::GetCompressedFlags() const
{
	uint8 Result = FSavedMove_Character::GetCompressedFlags();

	if (Saved_bWantsToRun) Result |= FLAG_Run;
	if (Saved_bWantsToSprint) Result |= FLAG_Sprint;
	return Result;
}

void UTWBCharacterMovementComponent::FSavedMove_TWB::SetMoveFor(ACharacter* C, float InDeltaTime, FVector const& NewAccel, FNetworkPredictionData_Client_Character& ClientData)
{
	FSavedMove_Character::SetMoveFor(C, InDeltaTime, NewAccel, ClientData);
	UTWBCharacterMovementComponent* CharacterMovement = Cast<UTWBCharacterMovementComponent>(C->GetCharacterMovement());
	Saved_bWantsToRun = CharacterMovement->Safe_bWantsToRun;
	Saved_bWantsToSprint = CharacterMovement->Safe_bWantsToSprint;
}

void UTWBCharacterMovementComponent::FSavedMove_TWB::PrepMoveFor(ACharacter* C)
{
	FSavedMove_Character::PrepMoveFor(C);
	UTWBCharacterMovementComponent* CharacterMovement = Cast<UTWBCharacterMovementComponent>(C->GetCharacterMovement());
	CharacterMovement->Safe_bWantsToRun = Saved_bWantsToRun;
	CharacterMovement->Safe_bWantsToSprint = Saved_bWantsToSprint;
}

#pragma endregion

#pragma region PredictionData

UTWBCharacterMovementComponent::UTWBCharacterMovementComponent()
{
	NavAgentProps.bCanCrouch = true;
}


UTWBCharacterMovementComponent::FNetworkPredictionData_Client_TWB::FNetworkPredictionData_Client_TWB(const UCharacterMovementComponent& ClientMovement)
	: Super(ClientMovement)
{
}

FSavedMovePtr UTWBCharacterMovementComponent::FNetworkPredictionData_Client_TWB::AllocateNewMove()
{
	return FSavedMovePtr(new FSavedMove_TWB());
}

#pragma endregion

#pragma region MovementOverrides

void UTWBCharacterMovementComponent::UpdateFromCompressedFlags(uint8 Flags)
{
	Super::UpdateFromCompressedFlags(Flags);

	Safe_bWantsToRun = (Flags & FSavedMove_TWB::FLAG_Run) != 0;
	Safe_bWantsToSprint = (Flags & FSavedMove_TWB::FLAG_Sprint) != 0;
}

FNetworkPredictionData_Client* UTWBCharacterMovementComponent::GetPredictionData_Client() const
{
	check(PawnOwner != nullptr);

	if (ClientPredictionData == nullptr)
	{
		UTWBCharacterMovementComponent* MutableThis = const_cast<UTWBCharacterMovementComponent*>(this);

		MutableThis->ClientPredictionData = new FNetworkPredictionData_Client_TWB(*this);
		MutableThis->ClientPredictionData->MaxSmoothNetUpdateDist = 92.f;
		MutableThis->ClientPredictionData->NoSmoothNetUpdateDist = 140.f;
	}
	return ClientPredictionData;
}

bool UTWBCharacterMovementComponent::IsMovingOnGround() const
{
	return Super::IsMovingOnGround() || IsCustomMovementMode(CMOVE_Slide);
}

bool UTWBCharacterMovementComponent::CanCrouchInCurrentState() const
{
	return Super::CanCrouchInCurrentState() && IsMovingOnGround();
}

float UTWBCharacterMovementComponent::GetMaxSpeed() const
{
	if (MovementMode == MOVE_Walking && !IsCrouching())
	{
		if (Safe_bWantsToSprint && IsWithinSprintForwardCone())
		{
			return MaxSprintSpeed;
		}

		if (Safe_bWantsToRun || Safe_bWantsToSprint)
		{
			return MaxRunSpeed;
		}
	}

	if (MovementMode == MOVE_Custom && CustomMovementMode == CMOVE_Slide)
	{
		return MaxSlideSpeed;
	}

	return Super::GetMaxSpeed();
}

float UTWBCharacterMovementComponent::GetMaxBrakingDeceleration() const
{
	if (MovementMode == MOVE_Custom && CustomMovementMode == CMOVE_Slide)
	{
		return BrakingDecelerationSliding;
	}

	return Super::GetMaxBrakingDeceleration();
}

void UTWBCharacterMovementComponent::UpdateCharacterStateBeforeMovement(float DeltaSeconds)
{
	// While running or sprinting, crouch input should branch into slide instead of standard crouch.
	if (MovementMode == MOVE_Walking && bWantsToCrouch && (Safe_bWantsToRun || Safe_bWantsToSprint) && CanSlide())
	{
		SetMovementMode(MOVE_Custom, CMOVE_Slide);
	}
	else if (IsCustomMovementMode(CMOVE_Slide) && !bWantsToCrouch)
	{
		SetMovementMode(MOVE_Walking);
	}

	Super::UpdateCharacterStateBeforeMovement(DeltaSeconds);
}

void UTWBCharacterMovementComponent::OnMovementUpdated(float DeltaSeconds, const FVector& OldLocation, const FVector& OldVelocity)
{
	Super::OnMovementUpdated(DeltaSeconds, OldLocation, OldVelocity);

	if (IsCustomMovementMode(CMOVE_Slide))
	{
		ApplySlideViewYawLimit();
	}
}

void UTWBCharacterMovementComponent::PhysCustom(float DeltaTime, int32 Iterations)
{
	if (CustomMovementMode == CMOVE_Slide)
	{
		PhysSlide(DeltaTime, Iterations);
		return;
	}

	Super::PhysCustom(DeltaTime, Iterations);
}

void UTWBCharacterMovementComponent::OnMovementModeChanged(EMovementMode PreviousMovementMode, uint8 PreviousCustomMode)
{
	Super::OnMovementModeChanged(PreviousMovementMode, PreviousCustomMode);

	if (PreviousMovementMode == MOVE_Custom && PreviousCustomMode == CMOVE_Slide)
	{
		ExitSlide();
	}

	if (IsCustomMovementMode(CMOVE_Slide))
	{
		EnterSlide();
	}
}

#pragma endregion

#pragma region Slide

void UTWBCharacterMovementComponent::EnterSlide()
{
	bWantsToCrouch = true;
	if (!bHasSavedRotationPolicy)
	{
		bSavedOrientRotationToMovement = bOrientRotationToMovement;
		bSavedUseControllerDesiredRotation = bUseControllerDesiredRotation;
		bHasSavedRotationPolicy = true;
	}

	bUseControllerDesiredRotation = false;
	bOrientRotationToMovement = false;
	Velocity += Velocity.GetSafeNormal2D() * SlideEnterImpulse;
	FindFloor(UpdatedComponent->GetComponentLocation(), CurrentFloor, true, nullptr);
}

void UTWBCharacterMovementComponent::ExitSlide()
{
	// Do not clear crouch intent here; let input release decide.
	// This avoids stand-up/slide flicker when slide ends due to MinSlideSpeed.
	if (bHasSavedRotationPolicy)
	{
		bOrientRotationToMovement = bSavedOrientRotationToMovement;
		bUseControllerDesiredRotation = bSavedUseControllerDesiredRotation;
		bHasSavedRotationPolicy = false;
	}
	else
	{
		bOrientRotationToMovement = true;
		bUseControllerDesiredRotation = false;
	}

	// Restore upright capsule orientation with a stable planar heading.
	FVector Forward2D = UpdatedComponent->GetForwardVector();
	Forward2D.Z = 0.f;
	if (Forward2D.IsNearlyZero())
	{
		Forward2D = CharacterOwner ? CharacterOwner->GetActorForwardVector() : FVector::ForwardVector;
		Forward2D.Z = 0.f;
	}
	if (Forward2D.IsNearlyZero())
	{
		Forward2D = FVector::ForwardVector;
	}

	const float UprightYaw = Forward2D.GetSafeNormal2D().Rotation().Yaw;
	const FRotator UprightRotation(0.f, UprightYaw, 0.f);
	FHitResult Hit;
	SafeMoveUpdatedComponent(FVector::ZeroVector, UprightRotation.Quaternion(), false, Hit);
}

bool UTWBCharacterMovementComponent::CanSlide() const
{
	if (!bCanSlide || !CharacterOwner || !UpdatedComponent)
	{
		return false;
	}

	const FVector Start = UpdatedComponent->GetComponentLocation();
	const float CapsuleHalfHeight = CharacterOwner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FVector End = Start + CapsuleHalfHeight * 2.5f * FVector::DownVector;
	FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(TWB_CanSlide), false, CharacterOwner);
	const bool bValidSurface = GetWorld()->LineTraceTestByProfile(Start, End, TEXT("BlockAll"), QueryParams);
	const bool bEnoughSpeed = Velocity.SizeSquared2D() > FMath::Square(MinSlideSpeed);

	return bValidSurface && bEnoughSpeed;
}

void UTWBCharacterMovementComponent::PhysSlide(float DeltaTime, int32 Iterations)
{
	if (DeltaTime < MIN_TICK_TIME)
	{
		return;
	}

	if (!CanSlide())
	{
		SetMovementMode(MOVE_Walking);
		StartNewPhysics(DeltaTime, Iterations);
		return;
	}

	bJustTeleported = false;
	bool bCheckedFall = false;
	bool bTriedLedgeMove = false;
	float RemainingTime = DeltaTime;

	while ((RemainingTime >= MIN_TICK_TIME) &&
		(Iterations < MaxSimulationIterations) &&
		CharacterOwner &&
		(CharacterOwner->Controller || bRunPhysicsWithNoController || (CharacterOwner->GetLocalRole() == ROLE_SimulatedProxy)))
	{
		Iterations++;
		bJustTeleported = false;

		const float TimeTick = GetSimulationTimeStep(RemainingTime, Iterations);
		RemainingTime -= TimeTick;

		UPrimitiveComponent* const OldBase = GetMovementBase();
		const FVector PreviousBaseLocation = (OldBase != nullptr) ? OldBase->GetComponentLocation() : FVector::ZeroVector;
		const FVector OldLocation = UpdatedComponent->GetComponentLocation();
		const FFindFloorResult OldFloor = CurrentFloor;

		MaintainHorizontalGroundVelocity();
		const FVector OldVelocity = Velocity;

		FVector SlopeForce = CurrentFloor.HitResult.Normal;
		SlopeForce.Z = 0.f;
		Velocity += SlopeForce * SlideGravityForce * TimeTick;

		// Ignore player input during slide: no strafe and no forward acceleration influence.
		Acceleration = FVector::ZeroVector;
		CalcVelocity(TimeTick, GroundFriction * SlideFrictionFactor, false, GetMaxBrakingDeceleration());

		const FVector MoveVelocity = Velocity;
		const FVector Delta = TimeTick * MoveVelocity;
		const bool bZeroDelta = Delta.IsNearlyZero();
		FStepDownResult StepDownResult;
		const bool bFloorWalkable = CurrentFloor.IsWalkableFloor();

		if (bZeroDelta)
		{
			RemainingTime = 0.f;
		}
		else
		{
			MoveAlongFloor(MoveVelocity, TimeTick, &StepDownResult);

			if (IsFalling())
			{
				const float DesiredDist = Delta.Size();
				if (DesiredDist > KINDA_SMALL_NUMBER)
				{
					const float ActualDist = (UpdatedComponent->GetComponentLocation() - OldLocation).Size2D();
					RemainingTime += TimeTick * (1.f - FMath::Min(1.f, ActualDist / DesiredDist));
				}

				StartNewPhysics(RemainingTime, Iterations);
				return;
			}
			else if (IsSwimming())
			{
				StartSwimming(OldLocation, OldVelocity, TimeTick, RemainingTime, Iterations);
				return;
			}
		}

		if (StepDownResult.bComputedFloor)
		{
			CurrentFloor = StepDownResult.FloorResult;
		}
		else
		{
			FindFloor(UpdatedComponent->GetComponentLocation(), CurrentFloor, bZeroDelta, nullptr);
		}

		const bool bCheckLedges = !CanWalkOffLedges();
		if (bCheckLedges && !CurrentFloor.IsWalkableFloor())
		{
			const FVector NewDelta = bTriedLedgeMove ? FVector::ZeroVector : GetLedgeMove(OldLocation, Delta, OldFloor);
			if (!NewDelta.IsZero())
			{
				RevertMove(OldLocation, OldBase, PreviousBaseLocation, OldFloor, false);
				bTriedLedgeMove = true;
				Velocity = NewDelta / TimeTick;
				RemainingTime += TimeTick;
				continue;
			}

			const bool bMustJump = bZeroDelta || (OldBase == nullptr || (!OldBase->IsQueryCollisionEnabled() && MovementBaseUtility::IsDynamicBase(OldBase)));
			if ((bMustJump || !bCheckedFall) && CheckFall(OldFloor, CurrentFloor.HitResult, Delta, OldLocation, RemainingTime, TimeTick, Iterations, bMustJump))
			{
				return;
			}

			bCheckedFall = true;
			RevertMove(OldLocation, OldBase, PreviousBaseLocation, OldFloor, true);
			RemainingTime = 0.f;
			break;
		}
		else
		{
			if (CurrentFloor.IsWalkableFloor())
			{
				if (ShouldCatchAir(OldFloor, CurrentFloor))
				{
					HandleWalkingOffLedge(OldFloor.HitResult.ImpactNormal, OldFloor.HitResult.Normal, OldLocation, TimeTick);
					if (IsMovingOnGround())
					{
						StartFalling(Iterations, RemainingTime, TimeTick, Delta, OldLocation);
					}
					return;
				}

				AdjustFloorHeight();
				SetBase(CurrentFloor.HitResult.Component.Get(), CurrentFloor.HitResult.BoneName);
			}
			else if (CurrentFloor.HitResult.bStartPenetrating && RemainingTime <= 0.f)
			{
				FHitResult Hit(CurrentFloor.HitResult);
				Hit.TraceEnd = Hit.TraceStart + FVector(0.f, 0.f, MAX_FLOOR_DIST);
				const FVector RequestedAdjustment = GetPenetrationAdjustment(Hit);
				ResolvePenetration(RequestedAdjustment, Hit, UpdatedComponent->GetComponentQuat());
				bForceNextFloorCheck = true;
			}

			if (IsSwimming())
			{
				StartSwimming(OldLocation, Velocity, TimeTick, RemainingTime, Iterations);
				return;
			}

			if (!CurrentFloor.IsWalkableFloor() && !CurrentFloor.HitResult.bStartPenetrating)
			{
				const bool bMustJump = bJustTeleported || bZeroDelta || (OldBase == nullptr || (!OldBase->IsQueryCollisionEnabled() && MovementBaseUtility::IsDynamicBase(OldBase)));
				if ((bMustJump || !bCheckedFall) && CheckFall(OldFloor, CurrentFloor.HitResult, Delta, OldLocation, RemainingTime, TimeTick, Iterations, bMustJump))
				{
					return;
				}
				bCheckedFall = true;
			}
		}

		if (IsMovingOnGround() && bFloorWalkable)
		{
			if (!bJustTeleported && !HasAnimRootMotion() && !CurrentRootMotion.HasOverrideVelocity() && TimeTick >= MIN_TICK_TIME)
			{
				Velocity = (UpdatedComponent->GetComponentLocation() - OldLocation) / TimeTick;
				MaintainHorizontalGroundVelocity();
			}
		}

		if (UpdatedComponent->GetComponentLocation() == OldLocation)
		{
			RemainingTime = 0.f;
			break;
		}
	}

	FHitResult Hit;
	FVector FloorNormal = CurrentFloor.IsWalkableFloor() ? CurrentFloor.HitResult.Normal : FVector::UpVector;
	if (FloorNormal.IsNearlyZero())
	{
		FloorNormal = FVector::UpVector;
	}

	// Keep forward on the tangent plane so we tilt with slopes but do not twist unpredictably.
	FVector SlideForward = FVector::VectorPlaneProject(Velocity, FloorNormal).GetSafeNormal();
	if (SlideForward.IsNearlyZero())
	{
		SlideForward = FVector::VectorPlaneProject(UpdatedComponent->GetForwardVector(), FloorNormal).GetSafeNormal();
	}
	if (SlideForward.IsNearlyZero())
	{
		SlideForward = UpdatedComponent->GetForwardVector().GetSafeNormal();
	}

	const FQuat NewRotation = FRotationMatrix::MakeFromXZ(SlideForward, FloorNormal).ToQuat();
	SafeMoveUpdatedComponent(FVector::ZeroVector, NewRotation, false, Hit);
}

void UTWBCharacterMovementComponent::ApplySlideViewYawLimit() const
{
	if (!CharacterOwner || !CharacterOwner->Controller || !UpdatedComponent || !CharacterOwner->IsLocallyControlled())
	{
		return;
	}

	FRotator ControlRotation = CharacterOwner->Controller->GetControlRotation();
	const float SlideFacingYaw = UpdatedComponent->GetComponentRotation().Yaw;
	const float RawYawOffset = FMath::FindDeltaAngleDegrees(SlideFacingYaw, ControlRotation.Yaw);
	const float LimitedYawOffset = FMath::Clamp(RawYawOffset, -SlideViewYawLimitDegrees, SlideViewYawLimitDegrees);

	ControlRotation.Yaw = FRotator::NormalizeAxis(SlideFacingYaw + LimitedYawOffset);
	CharacterOwner->Controller->SetControlRotation(ControlRotation);
}

#pragma endregion

#pragma region Input

void UTWBCharacterMovementComponent::RunPressed()
{
	Safe_bWantsToRun = true;
}

void UTWBCharacterMovementComponent::RunReleased()
{
	Safe_bWantsToRun = false;
}

void UTWBCharacterMovementComponent::SprintPressed()
{
	Safe_bWantsToSprint = true;
}

void UTWBCharacterMovementComponent::SprintReleased()
{
	Safe_bWantsToSprint = false;
}

void UTWBCharacterMovementComponent::CrouchPressed()
{
	// Priority rule: crouch while running/sprinting => slide.
	const bool bWantsSlideFromRun = IsMovementMode(MOVE_Walking) && (Safe_bWantsToRun || Safe_bWantsToSprint) && CanSlide();
	bWantsToCrouch = true;

	if (bWantsSlideFromRun)
	{
		if (!IsCustomMovementMode(CMOVE_Slide))
		{
			SetMovementMode(MOVE_Custom, CMOVE_Slide);
		}
		return;
	}
}

void UTWBCharacterMovementComponent::CrouchReleased()
{
	// Hold-crouch behavior: releasing crouch always clears crouch intent.
	bWantsToCrouch = false;
}

#pragma endregion

#pragma region Helpers

bool UTWBCharacterMovementComponent::IsCustomMovementMode(ETWBCustomMovementMode InCustomMovementMode) const
{
	return MovementMode == MOVE_Custom && CustomMovementMode == InCustomMovementMode;
}

bool UTWBCharacterMovementComponent::IsMovementMode(EMovementMode InMovementMode) const
{
	return MovementMode == InMovementMode;
}

bool UTWBCharacterMovementComponent::IsWithinSprintForwardCone() const
{
	const FVector Input2D = Acceleration.GetSafeNormal2D();
	if (Input2D.IsNearlyZero())
	{
		return false;
	}

	FVector Forward2D = UpdatedComponent ? UpdatedComponent->GetForwardVector() : FVector::ForwardVector;
	Forward2D.Z = 0.f;
	Forward2D = Forward2D.GetSafeNormal();
	if (Forward2D.IsNearlyZero())
	{
		return false;
	}

	constexpr float SprintMinDot = 0.5f; // cos(60 deg)
	return FVector::DotProduct(Input2D, Forward2D) >= SprintMinDot;
}

#pragma endregion
