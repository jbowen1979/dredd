# Oblivion GOTY One-Click for macOS

This repo is set up so you can **download it and double-click one file**.

## Do this

1. Download/extract this folder.
2. Double-click **`Oblivion-OneClick.command`**.
3. Enter Steam login in the window.
4. Click **Install + Play**.

The app will automatically:
- install Rosetta (Apple Silicon), Homebrew, Wine, Winetricks, SteamCMD
- download Oblivion GOTY (Steam App ID `22330`) from your account
- configure a Wine prefix + required runtime packages
- generate `Play-Oblivion.command` inside the game folder
- launch Oblivion Launcher

## If macOS blocks opening

- Right click `Oblivion-OneClick.command` -> **Open** -> **Open**.
- Or run once in Terminal:
  ```bash
  xattr -d com.apple.quarantine Oblivion-OneClick.command
  ```

## Notes

- First run can take a while (downloads + setup).
- Steam Guard may still be required depending on account security.
