# PoE 2 Trader

PoE 2 Trader is a small Windows desktop utility for Path of Exile 2's in-game trade window.

It copies the item you are hovering, reads its explicit modifiers, converts those modifiers into PoE trade stat filters, fills in the rolled values, and can optionally lower those values one by one while searching for matches.

This is not a trade API tool, price checker, website scraper, OCR tool, or browser automation tool. It only automates keyboard and mouse actions in the game's own trade UI.

## What It Does

When you press the run hotkey:

1. Sends `Ctrl+C` to copy the hovered PoE 2 item.
2. Reads the item text from the clipboard.
3. Finds explicit item modifiers only.
4. Normalizes each modifier for PoE trade search.
5. Opens the in-game trade window with `/`.
6. Clicks `Clear Search`.
7. Clicks `Item Category`.
8. Pastes the copied item's `Item Class`.
9. Selects the first category dropdown result with `Down Arrow` then `Enter`.
10. Adds each stat through `Add Stat Filter`.
11. Selects the first stat dropdown result with `Down Arrow` then `Enter`.
12. Clicks the value field for that row.
13. Pastes the item's actual rolled value.

Example:

```text
+114(105-124) to maximum Mana
```

Becomes:

```text
+# to maximum Mana
```

And Trader enters:

```text
114
```

in that stat row's value field.

## Modifier Parsing

Trader includes these explicit modifier blocks:

- `Prefix Modifier`
- `Suffix Modifier`
- `Desecrated Prefix Modifier`
- `Desecrated Suffix Modifier`
- `Crafted Prefix Modifier`
- `Crafted Suffix Modifier`

Trader ignores:

- item name
- base item
- requirements
- item level
- implicit modifiers
- separator lines
- metadata that is not an explicit modifier block

## Normalization Examples

```text
+114(105-124) to maximum Mana
-> +# to maximum Mana

+145(120-149) to maximum Life
-> +# to maximum Life

+34(31-35)% to Fire Resistance
-> +#% to Fire Resistance

19(19-21)% increased Cast Speed
-> #% increased Cast Speed
```

The full wording is preserved. Only numeric roll values are replaced with `#`, and parenthesized roll ranges are removed.

## First Run

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the app:

```powershell
python trader_app.py
```

Or run the packaged executable if you built or downloaded one:

```powershell
trader-poe2.exe
```

## Calibration

Open PoE 2's trade window before calibrating.

For each calibration point:

1. Click `Set` in Trader.
2. Move your mouse over the matching UI element in PoE 2.
3. Press `F4`.

Set these points:

- `Clear Search`: the in-game Clear Search button.
- `Item Category`: the in-game Item Category filter field.
- `Add Stat Filter`: the first Add Stat Filter row where the next stat should be added.
- `Value Input`: the first row's numeric value input field.
- `Search Button`: the in-game Search button. This is only required for Find Match.

Calibration is saved to `trader_settings.json` next to the app or exe.

## Runtime Controls

- `Dry run only`: copies and parses the item, then logs what would be entered without clicking the game.
- `Deduplicate exact stat strings`: skips repeated normalized stat strings.
- `Find match`: enables the value-lowering search loop after all stat filters are entered.
- `Run hotkey`: default is `num 1`, but you can change it.
- `Abort hotkey`: default is `f12`.
- `Run Once`: runs immediately from the app window.
- `Abort`: requests a stop.
- `Reset`: restores timing/hotkey/default values while keeping calibration points.

Use dry run first. Turn it off only after the parser output looks correct and all calibration points are set.

## Timing Settings

The timing fields exist because PoE's UI timing can vary by PC, resolution, latency, and game state.

- `Trade open`: wait after pressing `/`.
- `After clear`: wait after clicking Clear Search.
- `After click`: wait after clicking Add Stat Filter or Value Input.
- `After search`: wait after clicking Search during Find Match.
- `Dropdown`: wait after typing the stat before pressing `Down Arrow`.
- `Between rows`: wait before moving to the next stat.
- `Clipboard`: wait after `Ctrl+C` before reading the clipboard.
- `Row step Y`: vertical distance between stat rows. The default is `31` pixels for the tested 1920x1080 setup.

If later rows are off by one line, adjust `Row step Y`.

## Find Match

Find Match is optional.

After Trader finishes adding all stat filters and values:

1. It clicks Search once.
2. It goes to the first value row.
3. It double-clicks the value field.
4. It lowers that row's tracked value by `1`.
5. It pastes the new value.
6. It clicks Search again.
7. It moves to the next row and repeats.

The loop stops when:

- you press the abort hotkey, usually `F12`
- you click `Abort`
- all tracked values reach `0`

Example starting values:

```text
114, 145, 77, 34, 19, 17
```

Find Match searches the full values first, then tries:

```text
113, 145, 77, 34, 19, 17
113, 144, 77, 34, 19, 17
113, 144, 76, 34, 19, 17
...
```

It currently edits the first numeric value for each modifier. Multi-value modifiers are parsed, but only the first value is automated.

## Build An Exe With No Command Window

Install PyInstaller:

```powershell
python -m pip install pyinstaller
```

Build:

```powershell
python -m PyInstaller --clean --noconsole --onefile --name trader-poe2 trader_app.py
```

The exe will be created at:

```text
dist/trader-poe2.exe
```

`--noconsole` is what prevents a command prompt window from opening.

## Tests

Run parser and value tests:

```powershell
python -m pytest tests -q
```

## Notes

This tool assumes the first dropdown result is the correct stat after typing the full normalized stat string.

No OCR, image recognition, trade API, or browser automation is used.

Use at your own risk and make sure your use complies with the game's rules and terms.
