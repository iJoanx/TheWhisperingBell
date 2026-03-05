// Fill out your copyright notice in the Description page of Project Settings.


#include "TWBCharacterMovementComponent.h"
#include "GameFramework/Character.h"

class TWBCharacterMovementComponent
{
};

bool UTWBCharacterMovementComponent::FSavedMove_TWB::CanCombineWith(const FSavedMovePtr& NewMove, ACharacter* InCharacter, float MaxDelta) const
{
	FSavedMove_TWB* NewTWBMove = static_cast<FSavedMove_TWB*>(NewMove.Get());

	if (Saved_bWantsToSprint != NewTWBMove->Saved_bWantsToSprint)
	{
		return false;
	}

	return FSavedMove_Character::CanCombineWith(NewMove, InCharacter, MaxDelta);
}

void UTWBCharacterMovementComponent::FSavedMove_TWB::Clear()
{
	FSavedMove_Character::Clear();

	Saved_bWantsToSprint = 0;
}

uint8 UTWBCharacterMovementComponent::FSavedMove_TWB::GetCompressedFlags() const
{
	uint8 Result = Super::GetCompressedFlags();

	if (Saved_bWantsToSprint) 
	{
		Result |= FLAG_Custom_0;
	}
	return Result;
}

void UTWBCharacterMovementComponent::FSavedMove_TWB::SetMoveFor(ACharacter* C, float InDeltaTime, FVector const& NewAccel, FNetworkPredictionData_Client_Character& ClientData)
{
	FSavedMove_Character::SetMoveFor(C, InDeltaTime, NewAccel, ClientData);
	UTWBCharacterMovementComponent* CharacterMovement = Cast<UTWBCharacterMovementComponent>(C->GetCharacterMovement());
	Saved_bWantsToSprint = CharacterMovement->Safe_bWantsToSprint;
}

void UTWBCharacterMovementComponent::FSavedMove_TWB::PrepMoveFor(ACharacter* C)
{
	Super::PrepMoveFor(C);
	UTWBCharacterMovementComponent* CharacterMovement = Cast<UTWBCharacterMovementComponent>(C->GetCharacterMovement());
	CharacterMovement->Safe_bWantsToSprint = Saved_bWantsToSprint;
}


UTWBCharacterMovementComponent::UTWBCharacterMovementComponent()
{
}


UTWBCharacterMovementComponent::FNetworkPredictionData_Client_TWB::FNetworkPredictionData_Client_TWB(const UCharacterMovementComponent& ClientMovement)
	: Super(ClientMovement)
{
}

FSavedMovePtr UTWBCharacterMovementComponent::FNetworkPredictionData_Client_TWB::AllocateNewMove()
{
	return FSavedMovePtr(new FSavedMove_TWB);
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

void UTWBCharacterMovementComponent::UpdateFromCompressedFlags(uint8 Flags)
{

	Super::UpdateFromCompressedFlags(Flags);
	Safe_bWantsToSprint = (Flags & FSavedMove_TWB::FLAG_Custom_0) != 0;
}

void UTWBCharacterMovementComponent::OnMovementUpdated(float DeltaTime, const FVector& OldLocation, const FVector& OldVelocity)
{
	Super::OnMovementUpdated(DeltaTime, OldLocation, OldVelocity);
	if (MovementMode == MOVE_Walking)
	{
		if (Safe_bWantsToSprint)
		{
			MaxWalkSpeed = Sprint_MaxWalkSpeed;
		}
		else
		{
			MaxWalkSpeed = Walk_MaxWalkSpeed;
		}
	}
}

void UTWBCharacterMovementComponent::SprintPressed()
{
	Safe_bWantsToSprint = true;
}

void UTWBCharacterMovementComponent::SprintReleased()
{
	Safe_bWantsToSprint = false;
}
