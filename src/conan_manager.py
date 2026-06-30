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
#     ConanSaveManager.exe
#     DedicatedServerLauncher/
#       ConanExilesDedicatedServer/
#         ConanSandbox/
#           Saved/
#     Worlds/      ← created automatically
#     Backups/     ← created automatically, one subfolder per world
BASE_DIR   = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
SAVED_DIR  = os.path.join(BASE_DIR, "DedicatedServerLauncher", "ConanExilesDedicatedServer", "ConanSandbox", "Saved")
WORLDS_DIR = os.path.join(BASE_DIR, "Worlds")
BACKUP_DIR = os.path.join(BASE_DIR, "Backups")
SERVER_EXE = os.path.join(BASE_DIR, "DedicatedServerLauncher", "ConanExilesDedicatedServer", "ConanSandboxServer.exe")
# ─────────────────────────────────────────────────────────────────────────────

BG      = "#1e1e1e"
SURFACE = "#2a2a2a"
BORDER  = "#3a3a3a"
ACCENT  = "#c8a96e"
TEXT    = "#ddd8cc"
MUTED   = "#6e6860"
DANGER  = "#a04040"
SUCCESS = "#4a8c5c"
FONT    = ("Segoe UI", 10)
FONT_SM = ("Segoe UI", 9)


class ConanManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Conan Exiles — Save Manager")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.geometry("400x420")

        self.active_world = tk.StringVar(value="")
        self.selected_world = tk.StringVar(value="")
        self._build_ui()
        self._refresh_worlds()
        self._detect_active()
        self.after(100, self._check_untracked_save)

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 16, "pady": 0}

        # Active world bar
        bar = tk.Frame(self, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        bar.pack(fill="x", padx=12, pady=(12, 8))
        inner = tk.Frame(bar, bg=SURFACE)
        inner.pack(fill="x", padx=10, pady=8)
        tk.Label(inner, text="Active world", font=("Segoe UI", 8), fg=MUTED, bg=SURFACE).pack(anchor="w")
        self.active_lbl = tk.Label(inner, textvariable=self.active_world,
                                   font=("Segoe UI", 10, "bold"), fg=ACCENT, bg=SURFACE)
        self.active_lbl.pack(anchor="w")

        # World list
        list_frame = tk.Frame(self, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        self.listbox = tk.Listbox(
            list_frame,
            bg=SURFACE, fg=TEXT,
            selectbackground="#3a3020", selectforeground=ACCENT,
            font=FONT, bd=0, highlightthickness=0,
            relief="flat", height=8, activestyle="none",
        )
        self.listbox.pack(fill="both", expand=True, padx=1, pady=1)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self.listbox.bind("<Double-Button-1>", lambda e: self._load_and_launch())

        # Button row
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=12, pady=(0, 6))

        self._btn(btn_row, "New",    self._new_world_dialog).pack(side="left")
        self._btn(btn_row, "Rename", self._rename_dialog).pack(side="left", padx=4)
        self._btn(btn_row, "Backup", self._backup).pack(side="left")
        self._btn(btn_row, "Refresh", self._refresh_worlds).pack(side="right")

        # Load button
        self.load_btn = tk.Button(
            self, text="Load & Launch",
            font=("Segoe UI", 10, "bold"), fg="#111", bg=ACCENT,
            activebackground="#dbb97e", activeforeground="#111",
            bd=0, pady=8, cursor="hand2",
            command=self._load_and_launch, state="disabled", relief="flat",
        )
        self.load_btn.pack(fill="x", padx=12, pady=(0, 6))

        # Status
        self.status_var = tk.StringVar(value="No world selected.")
        self.status_lbl = tk.Label(self, textvariable=self.status_var,
                                   font=FONT_SM, fg=MUTED, bg=BG,
                                   wraplength=376, justify="left", anchor="w")
        self.status_lbl.pack(fill="x", padx=12, pady=(0, 10))

    def _btn(self, parent, label, cmd):
        return tk.Button(
            parent, text=label, font=FONT_SM, fg=TEXT,
            bg=SURFACE, activebackground=BORDER, activeforeground=TEXT,
            bd=0, relief="flat", cursor="hand2", command=cmd,
            highlightthickness=1, highlightbackground=BORDER,
            padx=10, pady=4,
        )

    # ── STATE ───────────────────────────────────────────────────────────────

    def _refresh_worlds(self):
        self.listbox.delete(0, "end")
        os.makedirs(WORLDS_DIR, exist_ok=True)
        worlds = sorted(d for d in os.listdir(WORLDS_DIR)
                        if os.path.isdir(os.path.join(WORLDS_DIR, d)))
        for w in worlds:
            self.listbox.insert("end", f"  {w}")
        self.load_btn.config(state="disabled")
        self.selected_world.set("")

    def _detect_active(self):
        marker = os.path.join(SAVED_DIR, ".active_world")
        if not os.path.exists(marker):
            self.active_world.set("None")
            return
        with open(marker) as f:
            name = f.read().strip()
        self.active_world.set(name)
        # Sync Saved/ back into Worlds/<name> on startup — the server may have
        # run and written new data after the manager was last closed.
        world_path = os.path.join(WORLDS_DIR, name)
        if os.path.isdir(SAVED_DIR):
            if os.path.exists(world_path):
                shutil.rmtree(world_path)
            shutil.copytree(SAVED_DIR, world_path,
                            ignore=shutil.ignore_patterns(".active_world"))

    def _check_untracked_save(self):
        """If Saved/ exists but has no .active_world marker, the user has an
        existing world the manager doesn't know about. Prompt them to name it
        and register it before they can do anything else."""
        marker = os.path.join(SAVED_DIR, ".active_world")
        saved_has_data = (
            os.path.isdir(SAVED_DIR)
            and any(f for f in os.listdir(SAVED_DIR) if not f.startswith("."))
        )
        if saved_has_data and not os.path.exists(marker):
            self._import_existing_save_dialog()

    def _import_existing_save_dialog(self):
        win = tk.Toplevel(self)
        win.title("Existing save detected")
        win.geometry("320x170")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: None)  # block closing

        tk.Label(win, text="Existing save data found",
                 font=("Segoe UI", 10, "bold"), fg=TEXT, bg=BG).pack(
                     anchor="w", padx=16, pady=(16, 4))
        tk.Label(win,
                 text="The Saved\\ folder already has data not tracked by this manager.\n"
                      "Give it a name to add it to your worlds list.",
                 font=("Segoe UI", 9), fg=MUTED, bg=BG, justify="left", wraplength=288).pack(
                     anchor="w", padx=16)

        entry = tk.Entry(win, font=("Segoe UI", 10), bg=SURFACE, fg=TEXT,
                         insertbackground=TEXT, bd=0,
                         highlightthickness=1, highlightbackground=BORDER)
        entry.pack(fill="x", padx=16, pady=(10, 0), ipady=5)
        entry.insert(0, "World 1")
        entry.select_range(0, "end")
        entry.focus()

        def confirm():
            name = entry.get().strip()
            if not name:
                return
            world_path = os.path.join(WORLDS_DIR, name)
            if os.path.exists(world_path):
                # Name taken — just write the marker and link to existing folder
                pass
            else:
                # Copy Saved/ into Worlds/<name> as the canonical copy
                os.makedirs(WORLDS_DIR, exist_ok=True)
                shutil.copytree(SAVED_DIR, world_path,
                                ignore=shutil.ignore_patterns(".active_world"))
            # Write marker so we track it from now on
            with open(os.path.join(SAVED_DIR, ".active_world"), "w") as f:
                f.write(name)
            self.active_world.set(name)
            win.destroy()
            self._refresh_worlds()
            self._set_status(f'Imported existing save as "{name}".', SUCCESS)

        tk.Button(win, text="Save & Continue", font=("Segoe UI", 9),
                  fg="#111", bg=ACCENT, activebackground="#dbb97e",
                  bd=0, relief="flat", padx=14, pady=5, cursor="hand2",
                  command=confirm).pack(pady=12)
        win.bind("<Return>", lambda e: confirm())

    def _on_select(self, _event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        world = self.listbox.get(sel[0]).strip()
        self.selected_world.set(world)
        if world == self.active_world.get():
            self._set_status(f'"{world}" is already loaded.')
            self.load_btn.config(state="disabled")
        else:
            self._set_status(f'Ready to load "{world}". Double-click or press Load & Launch.')
            self.load_btn.config(state="normal")

    def _set_status(self, msg, color=None):
        self.status_var.set(msg)
        self.status_lbl.config(fg=color or MUTED)

    def _get_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return None
        return self.listbox.get(sel[0]).strip()

    # ── ACTIONS ─────────────────────────────────────────────────────────────

    def _load_and_launch(self):
        target = self.selected_world.get()
        current = self.active_world.get()
        if not target or target == current:
            return
        if not messagebox.askyesno(
            "Load world",
            f'Save "{current}" and load "{target}"?\n\nThe server will be stopped if running.'
        ):
            return
        self.load_btn.config(state="disabled")
        self._set_status("Working…", ACCENT)
        threading.Thread(target=self._do_swap, args=(current, target), daemon=True).start()

    def _do_swap(self, current, target):
        import time
        try:
            self._set_status("Stopping server…", ACCENT)
            subprocess.call(["taskkill", "/IM", "ConanSandboxServer.exe", "/F"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)

            self._set_status(f'Loading "{target}"…', ACCENT)
            if os.path.exists(SAVED_DIR):
                shutil.rmtree(SAVED_DIR)
            src = os.path.join(WORLDS_DIR, target)
            if any(f for f in os.listdir(src) if not f.startswith(".")):
                shutil.copytree(src, SAVED_DIR)
            else:
                os.makedirs(SAVED_DIR, exist_ok=True)

            with open(os.path.join(SAVED_DIR, ".active_world"), "w") as f:
                f.write(target)

            self.after(0, lambda: self.active_world.set(target))

            if os.path.exists(SERVER_EXE):
                subprocess.Popen([SERVER_EXE, "-log"], cwd=os.path.dirname(SERVER_EXE))
                self.after(0, lambda: self._set_status(f'"{target}" loaded. Server launching…', SUCCESS))
            else:
                self.after(0, lambda: self._set_status(
                    f'"{target}" loaded. Server exe not found — launch manually.', MUTED))

        except Exception as e:
            self.after(0, lambda: self._set_status(f"Error: {e}", DANGER))

        self.after(0, self._refresh_worlds)
        self.after(0, self._detect_active)

    def _backup(self):
        world = self._get_selected() or self.active_world.get()
        if not world or world == "None":
            messagebox.showinfo("Backup", "Select a world to back up.")
            return
        if not os.path.isdir(SAVED_DIR):
            messagebox.showerror("Error", "Saved\\ folder not found.")
            return
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        world_backup_dir = os.path.join(BACKUP_DIR, world)
        dest = os.path.join(world_backup_dir, stamp)
        os.makedirs(world_backup_dir, exist_ok=True)
        self._set_status(f'Backing up "{world}"…', ACCENT)
        threading.Thread(target=self._do_backup, args=(dest, world), daemon=True).start()

    def _do_backup(self, dest, world):
        try:
            shutil.copytree(SAVED_DIR, dest)
            self.after(0, lambda: self._set_status(
                f'Backup saved to Backups\\{world}\\{os.path.basename(dest)}', SUCCESS))
        except Exception as e:
            self.after(0, lambda: self._set_status(f"Backup error: {e}", DANGER))

    def _new_world_dialog(self):
        self._name_dialog("New world", "", self._create_world)

    def _rename_dialog(self):
        world = self._get_selected()
        if not world:
            self._set_status("Select a world to rename.")
            return
        self._name_dialog("Rename world", world, lambda new: self._do_rename(world, new))

    def _name_dialog(self, title, prefill, on_confirm):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("280x110")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Name:", font=FONT_SM, fg=MUTED, bg=BG).pack(
            anchor="w", padx=14, pady=(14, 2))
        entry = tk.Entry(win, font=FONT, bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                         bd=0, highlightthickness=1, highlightbackground=BORDER)
        entry.pack(fill="x", padx=14, ipady=5)
        entry.insert(0, prefill)
        entry.select_range(0, "end")
        entry.focus()

        def confirm():
            name = entry.get().strip()
            if not name:
                return
            win.destroy()
            on_confirm(name)

        tk.Button(win, text="OK", font=FONT_SM, fg="#111", bg=ACCENT,
                  bd=0, relief="flat", padx=14, pady=5, cursor="hand2",
                  command=confirm).pack(pady=10)
        win.bind("<Return>", lambda e: confirm())
        win.bind("<Escape>", lambda e: win.destroy())

    def _create_world(self, name):
        path = os.path.join(WORLDS_DIR, name)
        if os.path.exists(path):
            messagebox.showerror("Exists", f'"{name}" already exists.')
            return
        os.makedirs(path)
        self._refresh_worlds()
        self._set_status(f'"{name}" created. Select it and click Load & Launch to start fresh.', SUCCESS)

    def _do_rename(self, old, new):
        if old == new:
            return
        old_path = os.path.join(WORLDS_DIR, old)
        new_path = os.path.join(WORLDS_DIR, new)
        if os.path.exists(new_path):
            messagebox.showerror("Exists", f'"{new}" already exists.')
            return
        try:
            os.rename(old_path, new_path)

            # Rename backup folder if it exists
            old_backup = os.path.join(BACKUP_DIR, old)
            new_backup = os.path.join(BACKUP_DIR, new)
            if os.path.exists(old_backup):
                os.rename(old_backup, new_backup)

            # Update active marker if this was the active world
            if self.active_world.get() == old:
                marker = os.path.join(SAVED_DIR, ".active_world")
                with open(marker, "w") as f:
                    f.write(new)
                self.active_world.set(new)

            self._refresh_worlds()
            self._set_status(f'Renamed "{old}" to "{new}".', SUCCESS)
        except Exception as e:
            self._set_status(f"Rename error: {e}", DANGER)


if __name__ == "__main__":
    app = ConanManager()
    app.mainloop()