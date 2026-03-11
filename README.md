# Oblivion GOTY Mac Installer (Steam Windows Edition)

A desktop GUI that automates the usual painful setup for running **The Elder Scrolls IV: Oblivion GOTY (2009)** from your Steam library on macOS.

## What it automates

1. Installs prerequisites:
   - Rosetta 2 (Apple Silicon only)
   - Homebrew (if missing)
   - `wine-stable`
   - `winetricks`
   - `steamcmd`
2. Downloads the Windows Steam build of Oblivion GOTY (`app_id=22330`) via SteamCMD.
3. Creates and configures a dedicated Wine prefix.
4. Installs common Oblivion runtime dependencies (`vcrun2008`, `d3dx9`, `xact`, `corefonts`).
5. Generates a launch script and can run the launcher directly from the app.

## Run

```bash
python3 app.py
```

## Usage

- Enter your Steam credentials.
- Optional: add Steam Guard code if prompted.
- Click buttons in order, or click **Run full setup**.

## Notes

- This app runs shell commands and may prompt for sudo during Homebrew/system setup.
- Steam Guard / account security prompts can still require user interaction in some cases.
- Tested workflow target: Apple Silicon + macOS with Wine under Rosetta.
