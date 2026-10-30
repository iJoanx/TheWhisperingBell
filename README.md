# The Whispering Bell

![Project Logo](TheWhisperingBell.png)

## Overview
**The Whispering Bell** is an Unreal Engine 5 project. Based on the project structure and source code, it appears to be a 3D action/adventure game featuring custom character movement logic. The project utilizes a stylized medieval aesthetic and includes various environment maps such as Sewers, Streets, and a main "TheWhisperingBell" map.

## Tech Stack
- **Game Engine:** [Unreal Engine 5.8](https://www.unrealengine.com/)
- **Programming Language:** C++ (C++20 supported by UE 5.8)
- **Target Platform:** Windows
- **Build System:** Unreal Build Tool (UBT)

## Requirements
- **Operating System:** Windows 10/11
- **Unreal Engine:** Version 5.8
- **IDE:** [Visual Studio 2022](https://visualstudio.microsoft.com/) (with C++ Game Development workload) or [JetBrains Rider](https://www.jetbrains.com/rider/)
- **Version Control:** Git (with Git LFS for large assets)

## Setup and Run

### 1. Clone the Repository
```bash
git clone <repository-url>
cd TheWhisperingBell
```

### 2. Generate Project Files
Right-click `TheWhisperingBell.uproject` and select **Generate Visual Studio project files**. 
Alternatively, use the command line (adjusting paths for your UE5 installation):
```powershell
& "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe" -projectfiles -project="C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\TheWhisperingBell.uproject" -game -rocket -progress
```

### 3. Build the Project
Open `TheWhisperingBell.sln` or `TheWhisperingBell.slnx` in Visual Studio or Rider and build the solution in **Development Editor** configuration.

### 4. Launch the Editor
Double-click `TheWhisperingBell.uproject` or launch the project directly from your IDE.

## Project Structure
- **`Source/`**: Contains C++ source code.
  - `TheWhisperingBell/`: Main module code.
    - `Public/TWBCharacter.h`: Character class definition.
    - `Public/TWBCharacterMovementComponent.h`: Custom movement logic.
- **`Content/`**: Project assets (Blueprints, Maps, Models, Textures, Audio).
  - `Maps/`: Level files (e.g., `TheWhisperingBell.umap`).
- **`Config/`**: Configuration files (`.ini`) for engine, game, and input settings.
- **`Plugins/`**: Project-specific plugins.
- **`Binaries/` & `Intermediate/`**: Compiled binaries and temporary build files (ignored by Git).

## Scripts
Unreal Engine projects typically use standard UBT and UAT scripts. 
- **Generate Files:** `UnrealBuildTool.exe -projectfiles`
- **Build:** `UnrealBuildTool.exe TheWhisperingBellEditor Win64 Development`
- **Cook Content:** `RunUAT.bat BuildCookRun ...`

## Environment Variables
- `UE_SDKS_ROOT` (Optional): If using custom SDK locations.
- Standard Unreal Engine environment variables apply for specialized build environments.

## Tests
The project can be tested using the **Unreal Automation Tool**:
1. Open the **Session Frontend** in the Unreal Editor.
2. Navigate to the **Automation** tab.
3. Run project-specific tests under the `TheWhisperingBell` namespace.
- **TODO:** Implement more comprehensive C++ unit tests using the `SPEC` macro.

## License
- **TODO:** Add a LICENSE file to the root directory.
(Check with project owners for specific licensing terms).

## Notes
- The project includes several plugins like `SunPosition`, `ModelingToolsEditorMode`, and `ModelContextProtocol`.
- Custom character movement is a core part of the gameplay implementation (`TWBCharacterMovementComponent`).
