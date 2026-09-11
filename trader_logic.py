import threading
import time
from decimal import Decimal, InvalidOperation

import pyautogui
import pyperclip

from modifier_normalizer import extract_modifier_values, normalize_modifier
from poe_item_parser import looks_like_poe_item, parse_explicit_modifiers


DEFAULT_TRADER_SETTINGS = {
    "clear_search_pos": None,
    "add_stat_filter_pos": None,
    "value_input_pos": None,
    "search_button_pos": None,
    "hotkey": "num 1",
    "abort_hotkey": "f12",
    "dry_run": True,
    "deduplicate": True,
    "find_match": False,
    "trade_open_delay": 0.7,
    "after_clear_delay": 0.2,
    "after_add_click_delay": 0.12,
    "after_search_delay": 1.0,
    "dropdown_delay": 0.35,
    "between_mod_delay": 0.15,
    "clipboard_delay": 0.18,
    "add_stat_row_offset_y": 31,
}


class TraderAutomation:
    def __init__(self, settings, log_callback=None):
        self.settings = {**DEFAULT_TRADER_SETTINGS, **(settings or {})}
        self.log_callback = log_callback
        self.running = False
        self.abort_event = threading.Event()
        self.lock = threading.Lock()
        self.hotkey_handles = []

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        print(message)

    def update_settings(self, settings):
        self.settings = {**DEFAULT_TRADER_SETTINGS, **(settings or {})}

    def register_hotkeys(self):
        try:
            import keyboard
        except ImportError:
            self.log("Install the keyboard package to use global Trader hotkeys.")
            return False

        self.unregister_hotkeys()
        try:
            self.hotkey_handles.append(keyboard.add_hotkey(self.settings["hotkey"], self.start_async))
            self.hotkey_handles.append(keyboard.add_hotkey(self.settings["abort_hotkey"], self.abort))
        except Exception as error:
            self.log(f"Could not register Trader hotkeys: {error}")
            return False

        self.log(f"Trader hotkeys active: {self.settings['hotkey']} runs, {self.settings['abort_hotkey']} aborts.")
        return True

    def unregister_hotkeys(self):
        if not self.hotkey_handles:
            return

        try:
            import keyboard

            for handle in self.hotkey_handles:
                keyboard.remove_hotkey(handle)
        except Exception as error:
            self.log(f"Could not unregister Trader hotkeys cleanly: {error}")
        finally:
            self.hotkey_handles = []

    def start_async(self):
        with self.lock:
            if self.running:
                self.log("Trader is already running; ignored overlapping hotkey press.")
                return
            self.running = True
            self.abort_event.clear()

        thread = threading.Thread(target=self._run_guarded, daemon=True)
        thread.start()

    def _run_guarded(self):
        try:
            self.run_once()
        except Exception as error:
            self.log(f"Trader error: {error}")
        finally:
            with self.lock:
                self.running = False
            self.abort_event.clear()
            self.log("Trader ready.")

    def abort(self):
        self.abort_event.set()
        self.log("Trader abort requested.")

    def run_once(self):
        self.log("Copying hovered item with Ctrl+C.")
        pyautogui.hotkey("ctrl", "c")
        time.sleep(float(self.settings["clipboard_delay"]))

        item_text = pyperclip.paste()
        if not looks_like_poe_item(item_text):
            self.log("Clipboard does not look like a Path of Exile item; aborted.")
            return

        raw_modifiers = parse_explicit_modifiers(item_text)
        stat_rows = [
            {
                "raw": modifier,
                "normalized": normalize_modifier(modifier),
                "values": extract_modifier_values(modifier),
            }
            for modifier in raw_modifiers
        ]
        if self.settings.get("deduplicate", True):
            deduped_rows = []
            seen_stats = set()
            for row in stat_rows:
                if row["normalized"] in seen_stats:
                    continue
                seen_stats.add(row["normalized"])
                deduped_rows.append(row)
            stat_rows = deduped_rows

        if not stat_rows:
            self.log("No explicit modifiers found on copied item.")
            return

        for row in stat_rows:
            values = ", ".join(row["values"]) if row["values"] else "none"
            self.log(f"Raw: {row['raw']}")
            self.log(f"Normalized: {row['normalized']}")
            self.log(f"Value: {values}")

        if self.settings.get("dry_run", True):
            self.log("Dry run enabled; no trade UI clicks were sent.")
            return

        self._validate_positions()
        self._check_abort()

        self.log("Opening in-game trade search.")
        pyautogui.press("/")
        self._sleep("trade_open_delay")
        self._check_abort()

        clear_pos = tuple(self.settings["clear_search_pos"])
        self.log(f"Clicking Clear Search at {clear_pos[0]}, {clear_pos[1]}.")
        self._click(*clear_pos)
        self._sleep("after_clear_delay")

        add_pos = tuple(self.settings["add_stat_filter_pos"])
        value_pos = tuple(self.settings["value_input_pos"])
        row_offset_y = int(self.settings.get("add_stat_row_offset_y", DEFAULT_TRADER_SETTINGS["add_stat_row_offset_y"]))
        first_row = stat_rows[0]
        self._add_stat_filter(add_pos[0], add_pos[1], value_pos[0], value_pos[1], first_row, "first")

        for index, row in enumerate(stat_rows[1:], start=1):
            self._add_stat_filter(
                add_pos[0],
                add_pos[1] + (index * row_offset_y),
                value_pos[0],
                value_pos[1] + (index * row_offset_y),
                row,
                str(index + 1),
            )

        if self.settings.get("find_match", False):
            self._run_find_match(value_pos, row_offset_y, stat_rows)

        self.log("Trader finished adding stat filters.")

    def _add_stat_filter(self, click_x, click_y, value_x, value_y, row, label):
        self._check_abort()
        self.log(f"Clicking Add Stat Filter row {label} at {click_x}, {click_y}.")
        self._click(click_x, click_y)
        self._sleep("after_add_click_delay")
        self._check_abort()
        self.log(f"Typing stat filter row {label}: {row['normalized']}")
        pyperclip.copy(row["normalized"])
        pyautogui.hotkey("ctrl", "v")
        self._sleep("dropdown_delay")
        pyautogui.press("down")
        pyautogui.press("enter")
        if row["values"]:
            self._sleep("after_add_click_delay")
            value = row["values"][0]
            self.log(f"Typing value row {label} at {value_x}, {value_y}: {value}")
            self._click(value_x, value_y)
            self._sleep("after_add_click_delay")
            pyperclip.copy(value)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.hotkey("ctrl", "v")
        self._sleep("between_mod_delay")

    def _run_find_match(self, value_pos, row_offset_y, stat_rows):
        search_pos = tuple(self.settings["search_button_pos"])
        current_values = [parse_decrement_value(row["values"][0] if row["values"] else None) for row in stat_rows]

        self.log(f"Find Match: clicking Search at {search_pos[0]}, {search_pos[1]}.")
        self._click(*search_pos)
        self._sleep("after_search_delay")

        while any(value is not None and value > 0 for value in current_values):
            for index, value in enumerate(current_values):
                self._check_abort()
                if value is None or value <= 0:
                    continue

                new_value = max(Decimal("0"), value - Decimal("1"))
                current_values[index] = new_value
                row_number = index + 1
                click_x = value_pos[0]
                click_y = value_pos[1] + (index * row_offset_y)
                value_text = format_decrement_value(new_value)

                self.log(f"Find Match: row {row_number} value -> {value_text}.")
                self._double_click(click_x, click_y)
                pyperclip.copy(value_text)
                pyautogui.hotkey("ctrl", "v")
                self._sleep("after_add_click_delay")
                self.log(f"Find Match: searching after row {row_number}.")
                self._click(*search_pos)
                self._sleep("after_search_delay")

        self.log("Find Match finished: all tracked values reached 0.")

    def _click(self, x, y):
        pyautogui.moveTo(int(x), int(y), duration=0.05)
        time.sleep(0.04)
        pyautogui.mouseDown(button="left")
        time.sleep(0.06)
        pyautogui.mouseUp(button="left")

    def _double_click(self, x, y):
        self._click(x, y)
        time.sleep(0.08)
        self._click(x, y)

    def _validate_positions(self):
        for key, label in (
            ("clear_search_pos", "Clear Search"),
            ("add_stat_filter_pos", "Add Stat Filter"),
            ("value_input_pos", "Value Input"),
        ):
            pos = self.settings.get(key)
            if not isinstance(pos, list) or len(pos) != 2:
                raise ValueError(f"Set the {label} coordinate before running Trader.")

        if self.settings.get("find_match", False):
            pos = self.settings.get("search_button_pos")
            if not isinstance(pos, list) or len(pos) != 2:
                raise ValueError("Set the Search Button coordinate before using Find Match.")

    def _check_abort(self):
        if self.abort_event.is_set():
            raise RuntimeError("Trader run aborted.")

    def _sleep(self, key):
        end_time = time.time() + float(self.settings[key])
        while time.time() < end_time:
            self._check_abort()
            time.sleep(0.03)


def parse_decrement_value(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def format_decrement_value(value):
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")
