#!/usr/bin/env python3
"""One-click Oblivion GOTY installer/launcher for macOS."""

from __future__ import annotations

import os
import platform
import queue
import shlex
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

APP_TITLE = "Oblivion GOTY One-Click (macOS)"
APP_ID = "22330"
DEFAULT_GAME_DIR = Path.home() / "Games" / "OblivionGOTY"
DEFAULT_PREFIX = Path.home() / ".oblivion-wineprefix"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x640")

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.steam_user = tk.StringVar()
        self.steam_pass = tk.StringVar()
        self.steam_guard = tk.StringVar()
        self.game_dir = tk.StringVar(value=str(DEFAULT_GAME_DIR))
        self.prefix_dir = tk.StringVar(value=str(DEFAULT_PREFIX))
        self.status = tk.StringVar(value="Ready")

        self._build()
        self.after(100, self._drain_logs)

    def _build(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, text=APP_TITLE, font=("SF Pro", 18, "bold")).pack(anchor="w")
        ttk.Label(
            root,
            text="Fill Steam login once, click Install + Play, and wait for completion.",
        ).pack(anchor="w", pady=(0, 10))

        form = ttk.LabelFrame(root, text="Required", padding=10)
        form.pack(fill=tk.X)

        self._field(form, 0, "Steam username", ttk.Entry(form, textvariable=self.steam_user, width=36))
        self._field(form, 1, "Steam password", ttk.Entry(form, textvariable=self.steam_pass, show="*", width=36))
        self._field(form, 2, "Steam Guard code (optional)", ttk.Entry(form, textvariable=self.steam_guard, width=18))

        adv = ttk.LabelFrame(root, text="Advanced (optional)", padding=10)
        adv.pack(fill=tk.X, pady=(10, 0))
        self._field(adv, 0, "Install directory", ttk.Entry(adv, textvariable=self.game_dir, width=62))
        self._field(adv, 1, "Wine prefix", ttk.Entry(adv, textvariable=self.prefix_dir, width=62))

        bar = ttk.Frame(root)
        bar.pack(fill=tk.X, pady=12)
        ttk.Button(bar, text="Install + Play", command=self.install_and_play).pack(side=tk.LEFT)
        ttk.Button(bar, text="Launch only", command=self.launch_only).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(bar, textvariable=self.status).pack(side=tk.RIGHT)

        out = ttk.LabelFrame(root, text="Live Log", padding=8)
        out.pack(fill=tk.BOTH, expand=True)
        self.log = tk.Text(out, wrap=tk.WORD, height=24)
        self.log.pack(fill=tk.BOTH, expand=True)

    def _field(self, parent: ttk.Frame, row: int, label: str, widget: ttk.Widget) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        widget.grid(row=row, column=1, sticky="ew", pady=4)
        parent.columnconfigure(1, weight=1)

    def _drain_logs(self) -> None:
        while not self.log_queue.empty():
            line = self.log_queue.get_nowait()
            self.log.insert(tk.END, line + "\n")
            self.log.see(tk.END)
        self.after(100, self._drain_logs)

    def _run_bg(self, name: str, fn) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo(APP_TITLE, "A task is already running.")
            return

        def task() -> None:
            self.status.set(name)
            try:
                fn()
                self.status.set("Done")
            except Exception as exc:  # noqa: BLE001
                self.log_queue.put(f"ERROR: {exc}")
                self.status.set("Failed")

        self.worker = threading.Thread(target=task, daemon=True)
        self.worker.start()

    def _run(self, cmd: str, env: dict[str, str] | None = None) -> None:
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
        code = proc.wait()
        if code != 0:
            raise RuntimeError(f"Command failed ({code}): {cmd}")

    def _preflight(self) -> tuple[str, str, str]:
        user = self.steam_user.get().strip()
        passwd = self.steam_pass.get().strip()
        guard = self.steam_guard.get().strip()
        if not user or not passwd:
            raise RuntimeError("Steam username and password are required.")
        Path(self.game_dir.get()).mkdir(parents=True, exist_ok=True)
        Path(self.prefix_dir.get()).mkdir(parents=True, exist_ok=True)
        return user, passwd, guard

    def _install_prereqs(self) -> None:
        if platform.machine() == "arm64":
            self._run("/usr/sbin/softwareupdate --install-rosetta --agree-to-license || true")
        self._run("command -v brew >/dev/null || /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        self._run("brew update")
        self._run("brew install --cask --no-quarantine wine-stable")
        self._run("brew install winetricks steamcmd")

    def _download_oblivion(self, user: str, passwd: str, guard: str) -> None:
        install_dir = shlex.quote(self.game_dir.get())
        login = f"+login {shlex.quote(user)} {shlex.quote(passwd)}"
        if guard:
            login = f"+set_steam_guard_code {shlex.quote(guard)} {login}"
        self._run(
            "steamcmd "
            "+@sSteamCmdForcePlatformType windows "
            f"+force_install_dir {install_dir} "
            f"{login} "
            f"+app_update {APP_ID} validate +quit"
        )

    def _configure_wine(self) -> None:
        env = dict(os.environ)
        env["WINEPREFIX"] = self.prefix_dir.get()
        self._run("WINEARCH=win64 wineboot -u", env=env)
        self._run("winetricks -q vcrun2008 d3dx9 xact corefonts", env=env)

    def _launch(self) -> None:
        env = dict(os.environ)
        env["WINEPREFIX"] = self.prefix_dir.get()
        exe = Path(self.game_dir.get()) / "Oblivion Launcher.exe"
        if not exe.exists():
            raise RuntimeError(f"Game not found: {exe}")
        self._run(f"cd {shlex.quote(self.game_dir.get())} && wine 'Oblivion Launcher.exe'", env=env)

    def install_and_play(self) -> None:
        self._run_bg("Installing + Playing", self._install_and_play_sync)

    def _install_and_play_sync(self) -> None:
        user, passwd, guard = self._preflight()
        self.log_queue.put("Starting one-click setup...")
        self._install_prereqs()
        self._download_oblivion(user, passwd, guard)
        self._configure_wine()
        launcher = Path(self.game_dir.get()) / "Play-Oblivion.command"
        launcher.write_text(
            "#!/bin/bash\n"
            f"export WINEPREFIX={shlex.quote(self.prefix_dir.get())}\n"
            f"cd {shlex.quote(self.game_dir.get())}\n"
            "wine 'Oblivion Launcher.exe'\n",
            encoding="utf-8",
        )
        launcher.chmod(0o755)
        self.log_queue.put(f"Created clickable launcher: {launcher}")
        self._launch()

    def launch_only(self) -> None:
        self._run_bg("Launching", self._launch)


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
