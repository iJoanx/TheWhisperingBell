// Fill out your copyright notice in the Description page of Project Settings.

#include "TheWhisperingBell.h"

#include "Containers/Ticker.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/GameUserSettings.h"
#include "Misc/ConfigCacheIni.h"
#include "Modules/ModuleManager.h"

namespace
{
	constexpr float TargetInternalHeight = 960.0f;
	constexpr TCHAR UserRenderSettingsSection[] = TEXT("WhisperingBell.RenderSettings");
	constexpr TCHAR RetroScaleInitializedKey[] = TEXT("bRetro960ScaleInitialized");
}

class FTheWhisperingBellModule final : public FDefaultGameModuleImpl
{
public:
	void StartupModule() override
	{
		TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
			FTickerDelegate::CreateRaw(this, &FTheWhisperingBellModule::TrySetRetroScreenPercentage), 0.25f);
	}

	void ShutdownModule() override
	{
		FTSTicker::RemoveTicker(TickerHandle);
	}

private:
	bool TrySetRetroScreenPercentage(float DeltaTime)
	{
		if (bApplied)
		{
			return false;
		}

		bool bAlreadyInitialized = false;
		if (GConfig && GConfig->GetBool(UserRenderSettingsSection, RetroScaleInitializedKey,
			bAlreadyInitialized, GGameUserSettingsIni) && bAlreadyInitialized)
		{
			bApplied = true;
			return false;
		}

		if (!GEngine || !GEngine->GameViewport || !GEngine->GameViewport->Viewport)
		{
			return true;
		}

		UWorld* World = GEngine->GameViewport->GetWorld();
		if (!World || !World->HasBegunPlay() || (World->WorldType != EWorldType::Game && World->WorldType != EWorldType::PIE))
		{
			return true;
		}

		const int32 ViewportHeight = GEngine->GameViewport->Viewport->GetSizeXY().Y;
		if (ViewportHeight <= 0)
		{
			return true;
		}

		const float ScreenPercentage = 100.0f * TargetInternalHeight / static_cast<float>(ViewportHeight);
		if (UGameUserSettings* Settings = GEngine->GetGameUserSettings())
		{
			Settings->SetResolutionScaleValueEx(ScreenPercentage);
			Settings->ApplySettings(false);

			if (GConfig)
			{
				GConfig->SetBool(UserRenderSettingsSection, RetroScaleInitializedKey, true, GGameUserSettingsIni);
				GConfig->Flush(false, GGameUserSettingsIni);
			}

			bApplied = true;
			UE_LOG(LogTemp, Log, TEXT("Initial retro render scale set to %.1f%% for %d-pixel viewport height (target %d)."),
				ScreenPercentage, ViewportHeight, static_cast<int32>(TargetInternalHeight));
			return false;
		}
		return true;
	}

	FTSTicker::FDelegateHandle TickerHandle;
	bool bApplied = false;
};

IMPLEMENT_PRIMARY_GAME_MODULE(FTheWhisperingBellModule, TheWhisperingBell, "TheWhisperingBell");

