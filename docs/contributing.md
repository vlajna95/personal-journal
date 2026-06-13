---
title: Contributing
nav_order: 5
---

# Contributing
{: .no_toc }

<details open markdown="block">
  <summary>Contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

## Ways to contribute

- **Translate the app** into a new language, or improve an existing translation.
- **Report a bug** by opening an [issue on GitHub](https://github.com/vlajna95/personal-journal/issues).
- **Suggest a feature** by opening an issue and describing the use case.

This guide focuses on translation. No programming knowledge is required.

## Translation overview

All user-visible text lives in locale files inside the `locales/` directory. Each file is named after its [IETF language tag](https://en.wikipedia.org/wiki/IETF_language_tag) with a `.lng` extension – for example `en.lng` for English, `pt_BR.lng` for Brazilian Portuguese.

The app loads `en.lng` first as a fallback, then overlays the active language on top. This means any key you do not translate will silently fall back to English – useful when a translation is incomplete.

## Locale file format

Each file is a plain UTF-8 text file. Every non-blank, non-comment line is a key–value pair:

```
key.name = Translated text
```

Rules:

- **Encoding** – UTF-8, no BOM.
- **Line endings** – LF or CRLF are both accepted.
- **Comments** – lines starting with `#` are ignored.
- **Blank lines** – ignored; use them freely to organise sections.
- **Whitespace around `=`** – stripped from both the key and the value. `key = value` and `key=value` are equivalent.
- **The value is everything after the first `=`** – do not quote it.

### Special syntax in values

| Syntax | Meaning | Example |
|---|---|---|
| `{name}` | Placeholder replaced at runtime | `Hello, {name}!` |
| `\t` (literal tab character) | Separator between a menu label and its shortcut hint | `&Lock journal\tCtrl+Alt+L` |
| `&` before a letter | Keyboard mnemonic for the menu item | `&New Note` |

{: .warning }
Never change a `{placeholder}` name. The code inserts values by name; renaming a placeholder will break the substitution and may crash the app.

## The two required keys

Every locale file must define these two keys at the top:

```
lang.code = en
lang.name = English
```

- `lang.code` must be the exact code used in the filename (e.g. `pt_BR` for `pt_BR.lng`).
- `lang.name` is the language's **own-language name** shown in the Language menu – write it in the target language, not in English (e.g. `Français`, not `French`).

## Creating a new translation

### 1. Fork and clone the repository

```
git clone https://github.com/vlajna95/personal-journal.git
cd personal-journal
```

### 2. Copy the English locale as a starting point

```
cp locales/en.lng locales/xx.lng
```

Replace `xx` with your language code (use `xx_YY` for regional variants, e.g. `pt_BR`).

### 3. Edit the new file

Open `locales/xx.lng` in any plain-text editor that saves UTF-8 (Notepad on Windows works; Notepad++ is more comfortable). Translate each value. Leave keys you are unsure about unchanged – they will fall back to English.

Start with the most visible keys:

```
lang.code
lang.name
tab.notes
tab.diary
tab.alarms
menu.*
btn.*
lbl.*
msg.*
```

### 4. Test your translation

If you have Python installed:

```
pip install -r requirements.txt
python main.py
```

Open the Language menu – your new language should appear. Select it, restart if prompted, and check the interface.

If you do not have Python, ask the maintainer to build a test version for you by opening an issue.

### 5. Submit a pull request

Commit your file and open a pull request against the `main` branch. Title it `Add XX translation` (replacing XX with your language name in English).

## Improving an existing translation

The process is the same: fork, edit the relevant `.lng` file, and submit a pull request.

If you only have a small correction, you can also edit the file directly on GitHub using the pencil icon and submit a pull request from there without cloning.

## Key reference

Below is the complete list of keys from `en.lng`, grouped by section. The English value is shown so you know what each key refers to.

### Language identity

| Key | English value |
|---|---|
| `lang.code` | `en` |
| `lang.name` | `English` |

### Tabs

| Key | English value |
|---|---|
| `tab.notes` | `Notes` |
| `tab.diary` | `Diary` |
| `tab.alarms` | `Alarms` |

### Menu – File

| Key | English value |
|---|---|
| `menu.file` | `&File` |
| `menu.lock` | `&Lock journal\tCtrl+Alt+L` |
| `menu.tray` | `Minimise to &Tray\tAlt+Shift+F4` |
| `menu.search` | `&Search...\tCtrl+F` |
| `menu.export` | `&Export...\tCtrl+E` |
| `menu.backup` | `&Backup...\tCtrl+Shift+B` |
| `menu.shortcuts` | `Customize &Shortcuts...` |
| `menu.exit` | `E&xit` |

### Menu – Notes

| Key | English value |
|---|---|
| `menu.notes` | `&Notes` |
| `menu.new_note` | `&New Note\tCtrl+N` |

### Menu – Alarms

| Key | English value |
|---|---|
| `menu.alarms` | `&Alarms` |
| `menu.new_alarm` | `&New Alarm\tCtrl+Shift+N` |

### Menu – Diaries

| Key | English value |
|---|---|
| `menu.diaries` | `&Diaries` |
| `menu.new_diary` | `&New Diary\tCtrl+D` |
| `menu.goto_date` | `&Go to Date...\tCtrl+G` |
| `menu.manage_diaries` | `&Manage Diaries...\tCtrl+Shift+D` |

### Menu – Language

| Key | English value |
|---|---|
| `menu.language` | `&Language` |
| `lang.changed_title` | `Language Changed` |
| `lang.changed_msg` | `The language has been changed. Reloading the window.` |

### Notes tab

| Key | English value |
|---|---|
| `notes.lbl_list` | `Notes:` |
| `notes.lbl_editor` | `Note:` |
| `notes.new_title` | `New Note` |
| `notes.new_label` | `Note title:` |
| `notes.delete_confirm_title` | `Delete Note` |
| `notes.delete_confirm_msg` | `Delete "{title}"? This cannot be undone.` |
| `notes.err_empty_title` | `Please enter a title for the note.` |
| `notes.err_title` | `Title Required` |

### Diary tab

| Key | English value |
|---|---|
| `diary.lbl_entries` | `Entries:` |
| `diary.lbl_editor` | `Entry:` |
| `diary.btn_goto` | `Go to date` |
| `diary.label_selector` | `Diary:` |
| `diary.accessible_selector` | `Active diary` |
| `diary.btn_manage` | `Manage...` |
| `diary.btn_manage_tip` | `Create, rename or delete diaries` |
| `diary.default_name` | `Diary` |
| `diary.manage_title` | `Manage Diaries` |
| `diary.manage_accessible_list` | `Diaries` |
| `diary.btn_new_diary` | `New Diary` |
| `diary.btn_rename_diary` | `Rename` |
| `diary.btn_delete_diary` | `Delete` |
| `diary.new_diary_title` | `New Diary` |
| `diary.new_diary_label` | `Diary name:` |
| `diary.rename_diary_title` | `Rename Diary` |
| `diary.rename_diary_label` | `New name:` |
| `diary.delete_confirm_title` | `Delete Diary` |
| `diary.delete_confirm_msg` | `Delete "{name}" and all its {n} entries? This cannot be undone.` |
| `diary.delete_confirm_last` | `Cannot delete the only diary.` |
| `diary.err_empty_name` | `Please enter a name for the diary.` |
| `diary.err_name_title` | `Name Required` |

### Alarms tab

| Key | English value |
|---|---|
| `alarms.lbl_list` | `Alarms:` |
| `alarms.new_title` | `New Alarm` |
| `alarms.edit_title` | `Edit Alarm` |
| `alarms.lbl_title` | `Title:` |
| `alarms.lbl_date` | `Date:` |
| `alarms.lbl_time` | `Time:` |
| `alarms.delete_confirm_title` | `Delete Alarm` |
| `alarms.delete_confirm_msg` | `Delete "{title}"? This cannot be undone.` |
| `alarms.fired_title` | `Alarm` |
| `alarms.fired_msg` | `{title}` |

### Search dialog

| Key | English value |
|---|---|
| `search.title` | `Search` |
| `search.lbl_query` | `Search for:` |
| `search.btn_search` | `Search` |
| `search.lbl_results` | `Results:` |
| `search.col_type` | `Type` |
| `search.col_date` | `Date` |
| `search.col_excerpt` | `Excerpt` |
| `search.type_note` | `Note` |
| `search.type_diary` | `Diary` |
| `search.no_results` | `No results found.` |

### Export dialog

| Key | English value |
|---|---|
| `export.title` | `Export` |
| `export.lbl_source` | `Export:` |
| `export.source_notes` | `Notes` |
| `export.source_diary` | `Diary` |
| `export.lbl_diary` | `Diary:` |
| `export.lbl_format` | `Format:` |
| `export.btn_export` | `Export` |
| `export.success_title` | `Export Complete` |
| `export.success_msg` | `Exported to {path}` |

### Password / lock

| Key | English value |
|---|---|
| `password.title` | `Unlock Journal` |
| `password.lbl` | `Password:` |
| `password.btn_unlock` | `Unlock` |
| `password.set_title` | `Set Password` |
| `password.set_lbl` | `Choose a password:` |
| `password.confirm_lbl` | `Confirm password:` |
| `password.btn_set` | `Set Password` |
| `password.err_mismatch` | `Passwords do not match.` |
| `password.err_empty` | `Please enter a password.` |
| `password.err_wrong` | `Incorrect password.` |
| `password.err_title` | `Error` |

### Shortcuts dialog

| Key | English value |
|---|---|
| `shortcuts.title` | `Customize Shortcuts` |
| `shortcuts.col_action` | `Action` |
| `shortcuts.col_shortcut` | `Shortcut` |
| `shortcuts.accessible_list` | `Keyboard shortcuts` |
| `shortcuts.btn_reassign` | `&Reassign...` |
| `shortcuts.btn_reset` | `Reset to &Default` |
| `shortcuts.conflict_title` | `Shortcut Conflict` |
| `shortcuts.conflict_msg` | `{shortcut} is already assigned to "{action}". Use it anyway?` |
| `shortcuts.capture_title` | `New Shortcut` |
| `shortcuts.capture_prompt` | `Press the new key combination for:` |
| `shortcuts.capture_hint` | `Press a key combination (Ctrl, Alt or Shift + key). Enter to confirm. Esc to cancel.` |

### Backup

| Key | English value |
|---|---|
| `backup.title` | `Backup` |
| `backup.success_title` | `Backup Complete` |
| `backup.success_msg` | `Backup saved to {path}` |
| `backup.err_title` | `Backup Failed` |

### Date formatting

| Key | English value |
|---|---|
| `date.format` | `%B %d, %Y` |
| `date.format_short` | `%Y-%m-%d` |

## Translation tips

- **Keep menu mnemonics** – the `&` marks the letter a user can press to activate the menu item with the keyboard. Place it on a letter that is not already used by another item in the same menu. If your translation makes this impossible, it is fine to omit it.
- **Keep shortcut hints** – in menu labels the part after `\t` (e.g. `\tCtrl+Alt+L`) must stay exactly as-is; it is a display hint and does not affect the actual shortcut.
- **Preserve placeholders** – `{name}`, `{title}`, `{n}`, `{path}`, `{shortcut}`, `{action}` must remain unchanged.
- **Date formats** – `date.format` and `date.format_short` use [Python strftime codes](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes). Adjust for your locale's conventions.
- **Test with a screen reader** – if possible, verify that announced text sounds natural in your language.

## Building from source

### Prerequisites

- Python 3.11 or newer
- [PyInstaller](https://pyinstaller.org/) (`pip install pyinstaller`)
- [UPX](https://github.com/upx/upx/releases) – download and extract to `tools\upx\upx-5.2.0-win64\`

### Install dependencies

```
pip install -r requirements.txt
```

### Run without building

```
python main.py
```

### Build the executable

```
make build          # PyInstaller only
make installer      # PyInstaller + NSIS setup package
make installer-only # NSIS package only (repackage existing build)
```

See [build.ps1](https://github.com/vlajna95/personal-journal/blob/main/build.ps1) for the full build parameters.
