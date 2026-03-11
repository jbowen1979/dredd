#!/usr/bin/env python3
import os
import platform
import queue
import shlex
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

APP_DIR = Path.home() / ".oblivion-mac"
PREFIX = APP_DIR / "prefix"
STEAM_EXE = APP_DIR / "SteamSetup.exe"
OBLIVION_APP_ID = "22330"


class InstallerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Oblivion GOTY 2009 Installer + Launcher (macOS)")
        self.geometry("900x620")

        self.log_queue = queue.Queue()
        self.running = False

        self._build_ui()
        self.after(100, self._drain_log_queue)

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        header = ttk.Label(
            self,
            text="One-click setup for Steam Windows Oblivion on macOS",
            font=("SF Pro", 16, "bold"),
        )
        header.pack(anchor="w", **pad)

        note = ttk.Label(
            self,
            text=(
                "This tool sets up Wine + Steam (Windows) and launches Oblivion GOTY Edition (AppID 22330).\n"
                "You must own the game on Steam. First launch requires login inside Steam."
            ),
            foreground="#333333",
        )
        note.pack(anchor="w", **pad)

        controls = ttk.Frame(self)
        controls.pack(fill="x", **pad)

        self.btn_prepare = ttk.Button(controls, text="1) Prepare Mac Environment", command=self.prepare_env)
        self.btn_prepare.grid(row=0, column=0, sticky="ew", **pad)

        self.btn_install_steam = ttk.Button(controls, text="2) Install Steam (Windows)", command=self.install_steam)
        self.btn_install_steam.grid(row=0, column=1, sticky="ew", **pad)

        self.btn_launch_steam = ttk.Button(controls, text="3) Launch Steam", command=self.launch_steam)
        self.btn_launch_steam.grid(row=1, column=0, sticky="ew", **pad)

        self.btn_install_game = ttk.Button(controls, text="4) Install Oblivion GOTY", command=self.install_game)
        self.btn_install_game.grid(row=1, column=1, sticky="ew", **pad)

        self.btn_play = ttk.Button(controls, text="5) Play Oblivion", command=self.play_game)
        self.btn_play.grid(row=2, column=0, sticky="ew", **pad)

        self.btn_all = ttk.Button(controls, text="Run Full Automated Setup", command=self.full_setup)
        self.btn_all.grid(row=2, column=1, sticky="ew", **pad)

        for i in range(2):
            controls.columnconfigure(i, weight=1)

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=10, pady=4)

        self.log = tk.Text(self, wrap="word", height=24)
        self.log.pack(fill="both", expand=True, padx=10, pady=6)
        self.log.configure(state="disabled")

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _drain_log_queue(self):
        try:
            while True:
                self._append_log(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def _set_running(self, value):
        self.running = value
        buttons = [
            self.btn_prepare,
            self.btn_install_steam,
            self.btn_launch_steam,
            self.btn_install_game,
            self.btn_play,
            self.btn_all,
        ]
        for btn in buttons:
            btn["state"] = "disabled" if value else "normal"
        if value:
            self.progress.start(10)
        else:
            self.progress.stop()

    def run_task(self, fn):
        if self.running:
            return

        def wrapped():
            self._set_running(True)
            try:
                fn()
                self.log_queue.put("\n✅ Task completed.\n")
            except Exception as exc:
                self.log_queue.put(f"\n❌ Error: {exc}\n")
                messagebox.showerror("Task failed", str(exc))
            finally:
                self._set_running(False)

        threading.Thread(target=wrapped, daemon=True).start()

    def _run(self, cmd, allow_fail=False):
        self.log_queue.put(f"$ {cmd}")
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            executable="/bin/bash",
        )
        assert proc.stdout
        for line in proc.stdout:
            self.log_queue.put(line.rstrip())
        code = proc.wait()
        if code != 0 and not allow_fail:
            raise RuntimeError(f"Command failed ({code}): {cmd}")

    def _ensure_dirs(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)

    def prepare_env(self):
        self.run_task(self._prepare_env_impl)

    def _prepare_env_impl(self):
        if platform.system() != "Darwin":
            raise RuntimeError("This installer only supports macOS.")

        self._ensure_dirs()
        self.log_queue.put(f"Architecture: {platform.machine()}")

        self._run("xcode-select -p", allow_fail=True)
        self._run("xcode-select --install", allow_fail=True)

        if subprocess.call("command -v brew >/dev/null 2>&1", shell=True) != 0:
            self.log_queue.put("Homebrew not found; installing Homebrew...")
            self._run('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
        else:
            self.log_queue.put("Homebrew already installed.")

        self._run("brew update")
        self._run("brew install --cask xquartz")
        self._run("brew install --cask --no-quarantine wine-stable")
        self._run("brew install winetricks cabextract")

        self.log_queue.put("Environment prep complete.")

    def install_steam(self):
        self.run_task(self._install_steam_impl)

    def _install_steam_impl(self):
        self._ensure_dirs()
        self._run(f"mkdir -p {shlex.quote(str(PREFIX))}")
        self._run(f"curl -L -o {shlex.quote(str(STEAM_EXE))} https://cdn.cloudflare.steamstatic.com/client/installer/SteamSetup.exe")
        self._run(f"WINEPREFIX={shlex.quote(str(PREFIX))} wineboot -u")
        self._run(f"WINEPREFIX={shlex.quote(str(PREFIX))} winetricks -q corefonts vcrun2019", allow_fail=True)
        self._run(f"WINEPREFIX={shlex.quote(str(PREFIX))} wine {shlex.quote(str(STEAM_EXE))} /S")
        self.log_queue.put("Steam Windows client installed in Wine prefix.")

    def launch_steam(self):
        self.run_task(self._launch_steam_impl)

    def _launch_steam_impl(self):
        steam_path = PREFIX / "drive_c/Program Files (x86)/Steam/Steam.exe"
        if not steam_path.exists():
            raise RuntimeError("Steam is not installed yet. Run step 2 first.")
        self._run(f"WINEPREFIX={shlex.quote(str(PREFIX))} wine {shlex.quote(str(steam_path))}")

    def install_game(self):
        self.run_task(self._install_game_impl)

    def _install_game_impl(self):
        steam_path = PREFIX / "drive_c/Program Files (x86)/Steam/Steam.exe"
        if not steam_path.exists():
            raise RuntimeError("Steam is not installed yet. Run step 2 first.")

        self.log_queue.put("Opening Steam and requesting Oblivion install...")
        self._run(
            f"WINEPREFIX={shlex.quote(str(PREFIX))} wine {shlex.quote(str(steam_path))} -applaunch {OBLIVION_APP_ID}",
            allow_fail=True,
        )
        self.log_queue.put("If Steam asked for login/guard, complete that and click Install in Steam UI.")

    def play_game(self):
        self.run_task(self._play_game_impl)

    def _play_game_impl(self):
        steam_path = PREFIX / "drive_c/Program Files (x86)/Steam/Steam.exe"
        if not steam_path.exists():
            raise RuntimeError("Steam is not installed yet.")
        self._run(f"WINEPREFIX={shlex.quote(str(PREFIX))} wine {shlex.quote(str(steam_path))} -applaunch {OBLIVION_APP_ID}")

    def full_setup(self):
        self.run_task(self._full_setup_impl)

    def _full_setup_impl(self):
        self._prepare_env_impl()
        self._install_steam_impl()
        self.log_queue.put("Launching Steam for first-time login + installation...")
        self._install_game_impl()


if __name__ == "__main__":
    app = InstallerGUI()
    app.mainloop()
