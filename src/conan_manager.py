import tkinter as tk
from tkinter import messagebox
import os
import sys
import shutil
import subprocess
import threading
from datetime import datetime

# ── PATHS (relative to wherever this exe/script lives) ───────────────────────
# Place ConanSaveManager.exe in the same folder as DedicatedServerLauncher/
# Expected layout:
#   <your folder>/
#     ConanSaveManager.exe          ← this app
#     DedicatedServerLauncher/
#       ConanExilesDedicatedServer/
#         ConanSandbox/
#           Saved/
#     Worlds/                       ← created automatically
#     Backups/                      ← created automatically
BASE_DIR    = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
SAVED_DIR   = os.path.join(BASE_DIR, "DedicatedServerLauncher", "ConanExilesDedicatedServer", "ConanSandbox", "Saved")
WORLDS_DIR  = os.path.join(BASE_DIR, "Worlds")
BACKUP_DIR  = os.path.join(BASE_DIR, "Backups")
SERVER_EXE  = os.path.join(BASE_DIR, "DedicatedServerLauncher", "ConanExilesDedicatedServer", "ConanSandboxServer.exe")
# ─────────────────────────────────────────────────────────────────────────────

BG       = "#1a1a1a"
SURFACE  = "#242424"
BORDER   = "#333333"
ACCENT   = "#c8a96e"   # conan gold
TEXT     = "#e8e0d0"
MUTED    = "#7a7060"
DANGER   = "#a04040"
SUCCESS  = "#4a8c5c"
FONT     = ("Segoe UI", 10)
FONT_SM  = ("Segoe UI", 9)
FONT_LG  = ("Segoe UI", 13, "bold")


class ConanManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Conan Exiles — Save Manager")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.geometry("420x520")

        self.active_world = tk.StringVar(value="—")
        self.selected_world = tk.StringVar(value="")
        self._build_ui()
        self._refresh_worlds()
        self._detect_active()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG, pady=14)
        hdr.pack(fill="x", padx=20)
        tk.Label(hdr, text="CONAN EXILES", font=("Segoe UI", 9), fg=ACCENT,
                 bg=BG, letter_spacing=2).pack(anchor="w")
        tk.Label(hdr, text="Save Manager", font=("Segoe UI", 18, "bold"),
                 fg=TEXT, bg=BG).pack(anchor="w")

        # Active world strip
        strip = tk.Frame(self, bg=SURFACE, pady=10, padx=16,
                         highlightbackground=BORDER, highlightthickness=1)
        strip.pack(fill="x", padx=20, pady=(0, 14))
        tk.Label(strip, text="ACTIVE WORLD", font=("Segoe UI", 8),
                 fg=MUTED, bg=SURFACE).pack(anchor="w")
        tk.Label(strip, textvariable=self.active_world, font=("Segoe UI", 12, "bold"),
                 fg=ACCENT, bg=SURFACE).pack(anchor="w")

        # World list
        tk.Label(self, text="YOUR WORLDS", font=("Segoe UI", 8),
                 fg=MUTED, bg=BG).pack(anchor="w", padx=20)

        list_frame = tk.Frame(self, bg=SURFACE,
                              highlightbackground=BORDER, highlightthickness=1)
        list_frame.pack(fill="x", padx=20, pady=(4, 0))

        self.listbox = tk.Listbox(
            list_frame,
            bg=SURFACE, fg=TEXT, selectbackground=ACCENT,
            selectforeground="#1a1a1a", font=FONT,
            bd=0, highlightthickness=0,
            relief="flat", height=7,
            activestyle="none",
        )
        self.listbox.pack(fill="x", padx=2, pady=2)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Buttons row
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=10)

        self._btn(btn_row, "⟳  Refresh", self._refresh_worlds, MUTED).pack(side="left")
        self._btn(btn_row, "+  New world", self._new_world_dialog, MUTED).pack(side="left", padx=8)
        self._btn(btn_row, "⬛  Backup now", self._backup, MUTED).pack(side="right")

        # Divider
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=20, pady=8)

        # Main action
        self.load_btn = tk.Button(
            self, text="Load selected world & launch server",
            font=("Segoe UI", 10, "bold"), fg="#1a1a1a", bg=ACCENT,
            activebackground="#e0c080", activeforeground="#1a1a1a",
            bd=0, padx=0, pady=10, cursor="hand2",
            command=self._load_and_launch, state="disabled",
            relief="flat",
        )
        self.load_btn.pack(fill="x", padx=20)

        # Status bar
        self.status_var = tk.StringVar(value="Select a world to begin.")
        self.status = tk.Label(self, textvariable=self.status_var,
                               font=FONT_SM, fg=MUTED, bg=BG, wraplength=380,
                               justify="left")
        self.status.pack(anchor="w", padx=20, pady=(10, 4))

        # Backups link
        tk.Label(self, text="Open Backups folder",
                 font=("Segoe UI", 9, "underline"), fg=MUTED, bg=BG,
                 cursor="hand2").pack(anchor="w", padx=20)
        self.children[list(self.children)[-1]].bind(
            "<Button-1>", lambda e: os.startfile(BACKUP_DIR) if os.path.exists(BACKUP_DIR) else None)

    def _btn(self, parent, label, cmd, color):
        return tk.Button(parent, text=label, font=FONT_SM, fg=color,
                         bg=BG, activebackground=SURFACE, activeforeground=TEXT,
                         bd=0, relief="flat", cursor="hand2", command=cmd,
                         highlightthickness=1, highlightbackground=BORDER, padx=8, pady=4)

    # ── LOGIC ───────────────────────────────────────────────────────────────

    def _refresh_worlds(self):
        self.listbox.delete(0, "end")
        if not os.path.isdir(WORLDS_DIR):
            os.makedirs(WORLDS_DIR, exist_ok=True)
        worlds = sorted(d for d in os.listdir(WORLDS_DIR)
                        if os.path.isdir(os.path.join(WORLDS_DIR, d)))
        for w in worlds:
            self.listbox.insert("end", f"  {w}")
        self.load_btn.config(state="disabled")
        self.selected_world.set("")
        self._set_status("Select a world to begin.")

    def _detect_active(self):
        marker = os.path.join(SAVED_DIR, ".active_world")
        if os.path.exists(marker):
            with open(marker) as f:
                self.active_world.set(f.read().strip())

    def _on_select(self, _event):
        sel = self.listbox.curselection()
        if not sel:
            return
        world = self.listbox.get(sel[0]).strip()
        self.selected_world.set(world)
        if world == self.active_world.get():
            self._set_status(f'"{world}" is already loaded. Launch server directly.')
            self.load_btn.config(state="disabled")
        else:
            self._set_status(f'Ready to swap to "{world}".')
            self.load_btn.config(state="normal")

    def _set_status(self, msg, color=None):
        self.status_var.set(msg)
        self.status.config(fg=color or MUTED)

    def _load_and_launch(self):
        target = self.selected_world.get()
        current = self.active_world.get()
        if not target:
            return

        confirm = messagebox.askyesno(
            "Swap worlds",
            f'Save "{current}" and load "{target}"?\n\nThe server will be stopped if running.',
            icon="question"
        )
        if not confirm:
            return

        self.load_btn.config(state="disabled")
        self._set_status("Working…", ACCENT)
        threading.Thread(target=self._do_swap, args=(current, target), daemon=True).start()

    def _do_swap(self, current, target):
        try:
            # Stop server
            self._set_status("Stopping server…", ACCENT)
            subprocess.call(
                ["taskkill", "/IM", "ConanSandboxServer.exe", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            import time; time.sleep(2)

            # Save current world back
            if current and current != "—" and os.path.isdir(SAVED_DIR):
                dest = os.path.join(WORLDS_DIR, current)
                self._set_status(f'Saving "{current}"…', ACCENT)
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(SAVED_DIR, dest)

            # Load target world
            self._set_status(f'Loading "{target}"…', ACCENT)
            if os.path.exists(SAVED_DIR):
                shutil.rmtree(SAVED_DIR)
            src = os.path.join(WORLDS_DIR, target)
            if os.listdir(src):  # non-empty = existing world
                shutil.copytree(src, SAVED_DIR)
            else:                # empty folder = fresh world
                os.makedirs(SAVED_DIR, exist_ok=True)

            # Write active marker
            with open(os.path.join(SAVED_DIR, ".active_world"), "w") as f:
                f.write(target)

            self.active_world.set(target)
            self._set_status(f'"{target}" loaded. Launching server…', SUCCESS)

            # Launch server
            if os.path.exists(SERVER_EXE):
                subprocess.Popen([SERVER_EXE, "-log"],
                                 cwd=os.path.dirname(SERVER_EXE))
                self.after(2000, lambda: self._set_status(
                    f'Server launched with "{target}".', SUCCESS))
            else:
                self.after(0, lambda: self._set_status(
                    f'"{target}" loaded. Server exe not found — launch manually.', MUTED))

        except Exception as e:
            self.after(0, lambda: self._set_status(f"Error: {e}", DANGER))

        self.after(0, lambda: self._refresh_worlds())
        self.after(0, lambda: self._detect_active())

    def _backup(self):
        if not os.path.isdir(SAVED_DIR):
            messagebox.showerror("Error", "Saved\\ folder not found.")
            return
        current = self.active_world.get() or "world"
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        dest = os.path.join(BACKUP_DIR, f"{current}_{stamp}")
        os.makedirs(BACKUP_DIR, exist_ok=True)
        self._set_status("Backing up…", ACCENT)
        threading.Thread(target=self._do_backup, args=(dest,), daemon=True).start()

    def _do_backup(self, dest):
        try:
            shutil.copytree(SAVED_DIR, dest)
            self.after(0, lambda: self._set_status(
                f"Backup saved: {os.path.basename(dest)}", SUCCESS))
        except Exception as e:
            self.after(0, lambda: self._set_status(f"Backup error: {e}", DANGER))

    def _new_world_dialog(self):
        win = tk.Toplevel(self)
        win.title("New world")
        win.geometry("300x130")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="World name:", font=FONT, fg=TEXT, bg=BG).pack(
            anchor="w", padx=16, pady=(16, 4))
        entry = tk.Entry(win, font=FONT, bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                         bd=0, highlightthickness=1, highlightbackground=BORDER)
        entry.pack(fill="x", padx=16, ipady=5)
        entry.focus()

        def create():
            name = entry.get().strip()
            if not name:
                return
            path = os.path.join(WORLDS_DIR, name)
            if os.path.exists(path):
                messagebox.showerror("Exists", f'"{name}" already exists.', parent=win)
                return
            os.makedirs(path)
            win.destroy()
            self._refresh_worlds()
            self._set_status(f'"{name}" created. Select it and load to start fresh.', SUCCESS)

        tk.Button(win, text="Create", font=FONT, fg="#1a1a1a", bg=ACCENT,
                  bd=0, relief="flat", padx=12, pady=6, cursor="hand2",
                  command=create).pack(pady=12)
        win.bind("<Return>", lambda e: create())


if __name__ == "__main__":
    app = ConanManager()
    app.mainloop()
