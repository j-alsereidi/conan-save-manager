# Conan Exiles Save Manager

Swap between multiple Conan Exiles server saves without keeping separate full installs. The server itself is several GB but the actual save data is usually under a few hundred MB, so this just swaps that folder instead of duplicating everything.

This is intended to be a companion program for the Dedicated Server Launcher utility. Download V1.9.4 here: https://forums.funcom.com/t/conan-exiles-dedicated-server-launcher-official-version-1-9-4-beta-1-9-7/21699

Only tested on Windows 10.

## Setup

Download `ConanSaveManager.exe` from [Releases](../../releases) and put it in the same directory as your `DedicatedServerLauncher.exe`, for example:

```
C:ExilesServer\
  ConanSaveManager.exe
  DedicatedServerLauncher1904.exe
  DedicatedServerLauncher\
    ConanExilesDedicatedServer\
      ConanSandbox\
        Saved\
```

`Worlds\` and `Backups\` get created automatically on first run.

If you already have a save in `Saved\`, the app will ask you to name it on first launch so it doesn't get overwritten.

## What it does

- Lists your worlds, pick one and hit Load & Launch
- Manual backups, timestamped, per world
- Syncs `Saved\` back into the right world folder on startup, in case the server was still running when you last closed the app

## Building it yourself

Alternatively, you can build from source with pyinstaller:

```bat
pip install pyinstaller
pyinstaller --onefile --windowed --name "ConanSaveManager" src/conan_manager.py
```

Not affiliated with Funcom. Back up your saves before use.