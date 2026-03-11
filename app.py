#!/usr/bin/env python3
"""Oblivion GOTY (Steam Windows) one-click setup + launcher for macOS."""

from __future__ import annotations

import os
import platform
import queue
import shlex
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "Oblivion GOTY Mac Installer"
APP_ID = "22330"  # The Elder Scrolls IV: Oblivion GOTY (2009) Steam app id
DEFAULT_GAME_DIR = Path.home() / "Games" / "OblivionGOTY"
DEFAULT_PREFIX = Path.home() / ".oblivion-wineprefix"


@dataclass
class StepResult:
    name: str
    ok: bool


class InstallerGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x700")

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.game_dir = tk.StringVar(value=str(DEFAULT_GAME_DIR))
        self.prefix_dir = tk.StringVar(value=str(DEFAULT_PREFIX))
        self.steam_user = tk.StringVar()
        self.steam_pass = tk.StringVar()
        self.steam_guard = tk.StringVar()

        self.status_var = tk.StringVar(value="Idle")

        self._build_ui()
        self.after(120, self._drain_logs)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(root, text=APP_TITLE, font=("SF Pro", 17, "bold"))
        title.pack(anchor="w")
        subtitle = ttk.Label(
            root,
            text=(
                "Automates dependency install, Steam depot download, Wine prefix setup, "
                "and launching Oblivion GOTY on macOS."
            ),
        )
        subtitle.pack(anchor="w", pady=(0, 10))

        form = ttk.LabelFrame(root, text="Configuration", padding=10)
        form.pack(fill=tk.X)

        self._row(form, 0, "Steam username", ttk.Entry(form, textvariable=self.steam_user, width=36))
        self._row(form, 1, "Steam password", ttk.Entry(form, textvariable=self.steam_pass, show="*", width=36))
        self._row(form, 2, "Steam Guard code (optional)", ttk.Entry(form, textvariable=self.steam_guard, width=20))

        self._dir_row(form, 3, "Install directory", self.game_dir)
        self._dir_row(form, 4, "Wine prefix", self.prefix_dir)

        btns = ttk.Frame(root)
        btns.pack(fill=tk.X, pady=10)
        ttk.Button(btns, text="1) Install prerequisites", command=self.install_prereqs).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btns, text="2) Download Oblivion", command=self.download_game).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btns, text="3) Configure Wine", command=self.configure_wine).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btns, text="4) Launch game", command=self.launch_game).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btns, text="Run full setup", command=self.full_setup).pack(side=tk.LEFT)

        stat = ttk.Frame(root)
        stat.pack(fill=tk.X)
        ttk.Label(stat, text="Status:").pack(side=tk.LEFT)
        ttk.Label(stat, textvariable=self.status_var).pack(side=tk.LEFT, padx=6)

        log_frame = ttk.LabelFrame(root, text="Log", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _row(self, parent: ttk.Frame, i: int, label: str, widget: ttk.Widget) -> None:
        ttk.Label(parent, text=label).grid(row=i, column=0, sticky="w", padx=(0, 10), pady=6)
        widget.grid(row=i, column=1, sticky="ew", pady=6)
        parent.columnconfigure(1, weight=1)

    def _dir_row(self, parent: ttk.Frame, i: int, label: str, var: tk.StringVar) -> None:
        frame = ttk.Frame(parent)
        entry = ttk.Entry(frame, textvariable=var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame, text="Browse", command=lambda: self._choose_dir(var)).pack(side=tk.LEFT, padx=(8, 0))
        self._row(parent, i, label, frame)

    def _choose_dir(self, var: tk.StringVar) -> None:
        selected = filedialog.askdirectory(initialdir=var.get() or str(Path.home()))
        if selected:
            var.set(selected)

    def _append_log(self, line: str) -> None:
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)

    def _drain_logs(self) -> None:
        while not self.log_queue.empty():
            self._append_log(self.log_queue.get_nowait())
        self.after(120, self._drain_logs)

    def _run_async(self, title: str, func) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo(APP_TITLE, "A task is already running. Please wait.")
            return

        def _target() -> None:
            self.status_var.set(title)
            try:
                func()
            except Exception as exc:  # noqa: BLE001
                self.log_queue.put(f"ERROR: {exc}")
                self.status_var.set("Failed")
                return
            self.status_var.set("Done")

        self.worker = threading.Thread(target=_target, daemon=True)
        self.worker.start()

    def _run_cmd(self, cmd: str, *, env: dict[str, str] | None = None) -> int:
        self.log_queue.put(f"$ {cmd}")
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            self.log_queue.put(line.rstrip())
        return proc.wait()

    def _ensure_dirs(self) -> None:
        Path(self.game_dir.get()).mkdir(parents=True, exist_ok=True)
        Path(self.prefix_dir.get()).mkdir(parents=True, exist_ok=True)

    def install_prereqs(self) -> None:
        self._run_async("Installing prerequisites", self._install_prereqs_sync)

    def _install_prereqs_sync(self) -> None:
        self._ensure_dirs()
        cmds: list[str] = []

        if platform.machine() == "arm64":
            cmds.append("/usr/sbin/softwareupdate --install-rosetta --agree-to-license || true")

        cmds.extend(
            [
                "command -v brew >/dev/null || /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"",
                "brew update",
                "brew install --cask --no-quarantine wine-stable",
                "brew install winetricks steamcmd",
            ]
        )

        for cmd in cmds:
            code = self._run_cmd(cmd)
            if code != 0:
                raise RuntimeError(f"Command failed ({code}): {cmd}")

        self.log_queue.put("Prerequisite installation complete.")

    def download_game(self) -> None:
        self._run_async("Downloading Oblivion via SteamCMD", self._download_game_sync)

    def _download_game_sync(self) -> None:
        self._ensure_dirs()
        user = self.steam_user.get().strip()
        passwd = self.steam_pass.get().strip()
        if not user or not passwd:
            raise RuntimeError("Steam username and password are required to download via SteamCMD.")

        install_dir = shlex.quote(self.game_dir.get())
        login = f"+login {shlex.quote(user)} {shlex.quote(passwd)}"
        if self.steam_guard.get().strip():
            login = f"+set_steam_guard_code {shlex.quote(self.steam_guard.get().strip())} {login}"

        cmd = (
            "steamcmd "
            "+@sSteamCmdForcePlatformType windows "
            f"+force_install_dir {install_dir} "
            f"{login} "
            f"+app_update {APP_ID} validate +quit"
        )
        code = self._run_cmd(cmd)
        if code != 0:
            raise RuntimeError("SteamCMD failed. Recheck credentials and Steam Guard code.")

        self.log_queue.put("Oblivion download complete.")

    def configure_wine(self) -> None:
        self._run_async("Configuring Wine prefix", self._configure_wine_sync)

    def _configure_wine_sync(self) -> None:
        self._ensure_dirs()
        env = dict(os.environ)
        env["WINEPREFIX"] = self.prefix_dir.get()

        commands = [
            "WINEARCH=win64 wineboot -u",
            "winetricks -q vcrun2008 d3dx9 xact corefonts",
        ]
        for cmd in commands:
            code = self._run_cmd(cmd, env=env)
            if code != 0:
                raise RuntimeError(f"Wine configuration failed: {cmd}")

        launcher = Path(self.game_dir.get()) / "launch_oblivion.command"
        launcher.write_text(
            "#!/bin/bash\n"
            f"export WINEPREFIX={shlex.quote(self.prefix_dir.get())}\n"
            f'cd {shlex.quote(self.game_dir.get())}\n'
            "wine Oblivion\\ Launcher.exe\n",
            encoding="utf-8",
        )
        launcher.chmod(0o755)
        self.log_queue.put(f"Created launcher: {launcher}")

    def launch_game(self) -> None:
        self._run_async("Launching Oblivion", self._launch_game_sync)

    def _launch_game_sync(self) -> None:
        env = dict(os.environ)
        env["WINEPREFIX"] = self.prefix_dir.get()

        game_path = Path(self.game_dir.get()) / "Oblivion Launcher.exe"
        if not game_path.exists():
            raise RuntimeError(f"Missing game launcher at: {game_path}")

        code = self._run_cmd(f"cd {shlex.quote(self.game_dir.get())} && wine 'Oblivion Launcher.exe'", env=env)
        if code != 0:
            raise RuntimeError("Game launch failed.")

    def full_setup(self) -> None:
        self._run_async("Running full setup", self._full_setup_sync)

    def _full_setup_sync(self) -> None:
        results: list[StepResult] = []

        for name, fn in [
            ("Install prerequisites", self._install_prereqs_sync),
            ("Download game", self._download_game_sync),
            ("Configure wine", self._configure_wine_sync),
        ]:
            try:
                fn()
                results.append(StepResult(name=name, ok=True))
            except Exception as exc:  # noqa: BLE001
                results.append(StepResult(name=name, ok=False))
                self.log_queue.put(f"{name} failed: {exc}")
                break

        ok_count = sum(1 for r in results if r.ok)
        self.log_queue.put(f"Finished full setup: {ok_count}/{len(results)} steps succeeded.")


def main() -> None:
    app = InstallerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
