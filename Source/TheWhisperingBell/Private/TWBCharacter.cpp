// Fill out your copyright notice in the Description page of Project Settings.


#include "TWBCharacter.h"
#include <TWBCharacterMovementComponent.h>

// Sets default values
ATWBCharacter::ATWBCharacter(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer.SetDefaultSubobjectClass<UTWBCharacterMovementComponent>(ACharacter::CharacterMovementComponentName))
{
	TWBCharacterMovementComponent = Cast<UTWBCharacterMovementComponent>(GetCharacterMovement());
 	// Set this character to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;

}

bool ATWBCharacter::CanJumpInternal_Implementation() const
{
	if (TWBCharacterMovementComponent && TWBCharacterMovementComponent->IsCustomMovementMode(CMOVE_Slide))
	{
		return JumpIsAllowedInternal();
	}

	return Super::CanJumpInternal_Implementation();
}

// Called when the game starts or when spawned
void ATWBCharacter::BeginPlay()
{
	Super::BeginPlay();
	
}

// Called every frame
void ATWBCharacter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

}

// Called to bind functionality to input
void ATWBCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

}
