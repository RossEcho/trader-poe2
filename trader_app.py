import json
import sys
import tkinter as tk
from pathlib import Path
from queue import Empty, Queue
from tkinter import ttk

import pyautogui

from trader_logic import DEFAULT_TRADER_SETTINGS, TraderAutomation


SETTINGS_FILENAME = "trader_settings.json"


class TraderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PoE 2 Trader")
        self.geometry("620x720")
        self.minsize(560, 640)
        self.configure(bg="#101820")

        self.log_queue = Queue()
        self.settings_path = self.get_settings_path()
        self.trader_settings = dict(DEFAULT_TRADER_SETTINGS)
        self.trader_settings.update(self.load_settings())
        self.trader = TraderAutomation(self.trader_settings, self.update_log)
        self.capture_target = None

        self.create_styles()
        self.create_widgets()
        self.after(80, self.flush_log_queue)
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.update_log("Ready. Start in dry run until calibration is confirmed.")

    def get_settings_path(self):
        app_path = Path(sys.executable if getattr(sys, "frozen", False) else __file__)
        return app_path.resolve().parent / SETTINGS_FILENAME

    def load_settings(self):
        if not self.settings_path.exists():
            return {}

        try:
            settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            self.update_log(f"Could not load saved settings: {error}")
            return {}

        if not isinstance(settings, dict):
            return {}
        return self.clean_settings(settings)

    def clean_settings(self, settings):
        cleaned = {}
        for key in ("clear_search_pos", "add_stat_filter_pos", "value_input_pos", "search_button_pos"):
            cleaned[key] = self.clean_point(settings.get(key))

        for key in ("hotkey", "abort_hotkey"):
            if settings.get(key):
                cleaned[key] = str(settings.get(key))

        for key in ("dry_run", "deduplicate", "find_match"):
            cleaned[key] = bool(settings.get(key, DEFAULT_TRADER_SETTINGS[key]))

        for key in (
            "trade_open_delay",
            "after_clear_delay",
            "after_add_click_delay",
            "after_search_delay",
            "dropdown_delay",
            "between_mod_delay",
            "clipboard_delay",
        ):
            try:
                cleaned[key] = max(0.0, float(settings.get(key, DEFAULT_TRADER_SETTINGS[key])))
            except (TypeError, ValueError):
                cleaned[key] = DEFAULT_TRADER_SETTINGS[key]

        try:
            cleaned["add_stat_row_offset_y"] = int(settings.get("add_stat_row_offset_y", DEFAULT_TRADER_SETTINGS["add_stat_row_offset_y"]))
        except (TypeError, ValueError):
            cleaned["add_stat_row_offset_y"] = DEFAULT_TRADER_SETTINGS["add_stat_row_offset_y"]

        return cleaned

    def clean_point(self, point):
        if not isinstance(point, list) or len(point) != 2:
            return None
        try:
            return [int(point[0]), int(point[1])]
        except (TypeError, ValueError):
            return None

    def save_settings(self):
        try:
            self.settings_path.write_text(json.dumps(self.trader_settings, indent=2), encoding="utf-8")
        except OSError as error:
            self.update_log(f"Could not save settings: {error}")

    def create_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#101820")
        self.style.configure("TLabel", background="#101820", foreground="#dce6ee", font=("Segoe UI", 10))
        self.style.configure("Panel.TLabel", background="#18242e", foreground="#dce6ee", font=("Segoe UI", 10))
        self.style.configure("Muted.TLabel", background="#18242e", foreground="#94a3af", font=("Segoe UI", 9))
        self.style.configure("Title.TLabel", background="#101820", foreground="#f6f8fb", font=("Segoe UI", 18, "bold"))
        self.style.configure("Status.TLabel", background="#101820", foreground="#8fbf7f", font=("Segoe UI", 10, "bold"))
        self.style.configure("TLabelframe", background="#18242e", foreground="#f6f8fb", bordercolor="#2e3c48")
        self.style.configure("TLabelframe.Label", background="#18242e", foreground="#f6f8fb", font=("Segoe UI", 11, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=(10, 7), background="#233241", foreground="#f6f8fb")
        self.style.map("TButton", background=[("active", "#2d4254")], foreground=[("disabled", "#7b8790")])
        self.style.configure("Accent.TButton", background="#2d6cdf", foreground="#ffffff")
        self.style.map("Accent.TButton", background=[("active", "#3b7ff0")])
        self.style.configure("Danger.TButton", background="#8f3f4a", foreground="#ffffff")
        self.style.map("Danger.TButton", background=[("active", "#a64a56")])
        self.style.configure("TEntry", fieldbackground="#0f171f", foreground="#f6f8fb", insertcolor="#f6f8fb")
        self.style.configure("TCheckbutton", background="#18242e", foreground="#dce6ee", font=("Segoe UI", 10))

    def create_widgets(self):
        shell = ttk.Frame(self, padding=18)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(4, weight=1)

        header = ttk.Frame(shell)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="PoE 2 Trader", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.status_var = tk.StringVar(value="Hotkeys inactive")
        ttk.Label(header, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=1, sticky="e")

        setup = ttk.LabelFrame(shell, text="Calibration", padding=12)
        setup.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        setup.columnconfigure(1, weight=1)
        ttk.Label(
            setup,
            text="Click Set, hover the requested PoE trade UI element, then press F4.",
            style="Panel.TLabel",
            wraplength=520,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        self.point_vars = {}
        point_rows = [
            ("clear_search_pos", "Clear Search"),
            ("add_stat_filter_pos", "Add Stat Filter"),
            ("value_input_pos", "Value Input"),
            ("search_button_pos", "Search Button"),
        ]
        for row_index, (key, label) in enumerate(point_rows, start=1):
            self.point_vars[key] = tk.StringVar(value=self.format_point(key))
            ttk.Label(setup, text=label, style="Panel.TLabel").grid(row=row_index, column=0, sticky="w", pady=(10, 0))
            ttk.Label(setup, textvariable=self.point_vars[key], style="Muted.TLabel").grid(row=row_index, column=1, sticky="w", padx=12, pady=(10, 0))
            ttk.Button(setup, text="Set", command=lambda field=key: self.start_capture(field)).grid(row=row_index, column=2, sticky="e", pady=(10, 0))

        runtime = ttk.LabelFrame(shell, text="Runtime", padding=12)
        runtime.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        runtime.columnconfigure(1, weight=1)

        self.dry_run_var = tk.BooleanVar(value=self.trader_settings["dry_run"])
        self.dedupe_var = tk.BooleanVar(value=self.trader_settings["deduplicate"])
        self.find_match_var = tk.BooleanVar(value=self.trader_settings["find_match"])
        ttk.Checkbutton(runtime, text="Dry run only", variable=self.dry_run_var, command=self.update_options).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(runtime, text="Deduplicate exact stat strings", variable=self.dedupe_var, command=self.update_options).grid(row=0, column=1, sticky="w")
        ttk.Checkbutton(runtime, text="Find match", variable=self.find_match_var, command=self.update_options).grid(row=1, column=0, sticky="w", pady=(10, 0))

        self.hotkey_entry = self.create_entry(runtime, 2, "Run hotkey", "hotkey")
        self.abort_entry = self.create_entry(runtime, 3, "Abort hotkey", "abort_hotkey")

        delays = ttk.LabelFrame(shell, text="Timing", padding=12)
        delays.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        for index in range(4):
            delays.columnconfigure(index, weight=1)

        self.delay_entries = {}
        delay_fields = [
            ("trade_open_delay", "Trade open"),
            ("after_clear_delay", "After clear"),
            ("after_add_click_delay", "After click"),
            ("after_search_delay", "After search"),
            ("dropdown_delay", "Dropdown"),
            ("between_mod_delay", "Between rows"),
            ("clipboard_delay", "Clipboard"),
        ]
        for index, (key, label) in enumerate(delay_fields):
            row = index // 2
            col = (index % 2) * 2
            ttk.Label(delays, text=label, style="Panel.TLabel").grid(row=row, column=col, sticky="w", pady=(0, 8))
            entry = ttk.Entry(delays, width=8)
            entry.insert(0, str(self.trader_settings[key]))
            entry.grid(row=row, column=col + 1, sticky="w", padx=(8, 18), pady=(0, 8))
            entry.bind("<FocusOut>", lambda event, field=key: self.update_delay(field))
            entry.bind("<Return>", lambda event, field=key: self.update_delay(field))
            self.delay_entries[key] = entry

        ttk.Label(delays, text="Row step Y", style="Panel.TLabel").grid(row=3, column=2, sticky="w", pady=(0, 8))
        self.row_offset_entry = ttk.Entry(delays, width=8)
        self.row_offset_entry.insert(0, str(self.trader_settings["add_stat_row_offset_y"]))
        self.row_offset_entry.grid(row=3, column=3, sticky="w", padx=(8, 18), pady=(0, 8))
        self.row_offset_entry.bind("<FocusOut>", lambda event: self.update_row_offset())
        self.row_offset_entry.bind("<Return>", lambda event: self.update_row_offset())

        log_frame = ttk.LabelFrame(shell, text="Log", padding=12)
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 12))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(
            log_frame,
            height=10,
            state="disabled",
            wrap="word",
            relief="flat",
            bd=0,
            bg="#0b1117",
            fg="#dce6ee",
            insertbackground="#dce6ee",
            selectbackground="#2d6cdf",
            font=("Consolas", 9),
            padx=10,
            pady=10,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        controls = ttk.Frame(shell)
        controls.grid(row=5, column=0, sticky="ew")
        controls.columnconfigure(0, weight=1)
        self.hotkey_button = ttk.Button(controls, text="Enable Hotkeys", style="Accent.TButton", command=self.toggle_hotkeys)
        self.hotkey_button.grid(row=0, column=0, sticky="ew")
        ttk.Button(controls, text="Run Once", command=self.trader.start_async).grid(row=0, column=1, padx=(12, 0))
        ttk.Button(controls, text="Abort", style="Danger.TButton", command=self.trader.abort).grid(row=0, column=2, padx=(12, 0))
        ttk.Button(controls, text="Reset", command=self.reset_settings).grid(row=0, column=3, padx=(12, 0))

    def create_entry(self, parent, row, label, key):
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=(10, 0))
        entry = ttk.Entry(parent, width=16)
        entry.insert(0, self.trader_settings[key])
        entry.grid(row=row, column=1, sticky="w", pady=(10, 0))
        entry.bind("<FocusOut>", lambda event: self.update_hotkeys_from_entries())
        entry.bind("<Return>", lambda event: self.update_hotkeys_from_entries())
        return entry

    def start_capture(self, target):
        self.capture_target = target
        self.status_var.set("Move mouse over target, then press F4")
        self.bind_all("<F4>", self.finish_capture)
        self.update_log("Calibration armed: press F4 over the target.")

    def finish_capture(self, event=None):
        if not self.capture_target:
            return
        x, y = pyautogui.position()
        self.trader_settings[self.capture_target] = [int(x), int(y)]
        self.trader.update_settings(self.trader_settings)
        self.save_settings()
        self.point_vars[self.capture_target].set(self.format_point(self.capture_target))
        self.capture_target = None
        self.unbind_all("<F4>")
        self.status_var.set("Coordinate saved")
        self.update_log(f"Coordinate saved at {x}, {y}.")

    def format_point(self, key):
        point = self.trader_settings.get(key)
        if not point:
            return "Not set"
        return f"{point[0]}, {point[1]}"

    def update_options(self):
        self.trader_settings["dry_run"] = self.dry_run_var.get()
        self.trader_settings["deduplicate"] = self.dedupe_var.get()
        self.trader_settings["find_match"] = self.find_match_var.get()
        self.trader.update_settings(self.trader_settings)
        self.save_settings()

    def update_hotkeys_from_entries(self):
        self.trader_settings["hotkey"] = self.hotkey_entry.get().strip() or DEFAULT_TRADER_SETTINGS["hotkey"]
        self.trader_settings["abort_hotkey"] = self.abort_entry.get().strip() or DEFAULT_TRADER_SETTINGS["abort_hotkey"]
        self.trader.update_settings(self.trader_settings)
        self.save_settings()

    def update_delay(self, key):
        entry = self.delay_entries[key]
        try:
            value = max(0.0, float(entry.get()))
        except ValueError:
            value = DEFAULT_TRADER_SETTINGS[key]
        self.trader_settings[key] = value
        entry.delete(0, tk.END)
        entry.insert(0, str(value))
        self.trader.update_settings(self.trader_settings)
        self.save_settings()

    def update_row_offset(self):
        try:
            value = int(self.row_offset_entry.get())
        except ValueError:
            value = DEFAULT_TRADER_SETTINGS["add_stat_row_offset_y"]
        self.trader_settings["add_stat_row_offset_y"] = value
        self.row_offset_entry.delete(0, tk.END)
        self.row_offset_entry.insert(0, str(value))
        self.trader.update_settings(self.trader_settings)
        self.save_settings()

    def reset_settings(self):
        saved_points = {key: self.trader_settings.get(key) for key in ("clear_search_pos", "add_stat_filter_pos", "value_input_pos", "search_button_pos")}
        self.trader_settings = dict(DEFAULT_TRADER_SETTINGS)
        self.trader_settings.update(saved_points)
        self.trader.update_settings(self.trader_settings)

        for key, variable in self.point_vars.items():
            variable.set(self.format_point(key))
        self.dry_run_var.set(self.trader_settings["dry_run"])
        self.dedupe_var.set(self.trader_settings["deduplicate"])
        self.find_match_var.set(self.trader_settings["find_match"])
        self.hotkey_entry.delete(0, tk.END)
        self.hotkey_entry.insert(0, self.trader_settings["hotkey"])
        self.abort_entry.delete(0, tk.END)
        self.abort_entry.insert(0, self.trader_settings["abort_hotkey"])
        for key, entry in self.delay_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, str(self.trader_settings[key]))
        self.row_offset_entry.delete(0, tk.END)
        self.row_offset_entry.insert(0, str(self.trader_settings["add_stat_row_offset_y"]))
        self.save_settings()
        self.update_log("Settings reset; calibration points were kept.")

    def toggle_hotkeys(self):
        self.update_hotkeys_from_entries()
        if self.trader.hotkey_handles:
            self.trader.unregister_hotkeys()
            self.hotkey_button.config(text="Enable Hotkeys", style="Accent.TButton")
            self.status_var.set("Hotkeys inactive")
            return
        if self.trader.register_hotkeys():
            self.hotkey_button.config(text="Disable Hotkeys", style="Danger.TButton")
            self.status_var.set("Hotkeys active")

    def update_log(self, message):
        self.log_queue.put(message)

    def flush_log_queue(self):
        try:
            while True:
                self.write_log(self.log_queue.get_nowait())
        except Empty:
            pass
        self.after(80, self.flush_log_queue)

    def write_log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def close_app(self):
        self.trader.unregister_hotkeys()
        self.destroy()


if __name__ == "__main__":
    app = TraderApp()
    app.mainloop()
