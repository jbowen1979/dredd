# Oblivion GOTY 2009 Mac One-Click Installer GUI

This project provides a macOS GUI app (`app.py`) that automates the setup required to run **The Elder Scrolls IV: Oblivion GOTY Edition (2009)** from your Windows Steam library on macOS.

## What it automates

- macOS environment preparation
  - Homebrew install/update
  - XQuartz install
  - Wine + winetricks install
- Windows Steam setup inside a dedicated Wine prefix (`~/.oblivion-mac/prefix`)
- Launching Steam and triggering Oblivion install/play (`AppID 22330`)

## Usage

```bash
python3 app.py
```

Then click **Run Full Automated Setup**.

## Notes

- You must own Oblivion on Steam.
- On first run, you still need to complete Steam login / Steam Guard in the Steam window.
- The game can require tweaks depending on macOS version, Apple Silicon translation behavior, and GPU driver compatibility in Wine.
- This tool is designed to reduce manual setup as much as possible in one GUI.
