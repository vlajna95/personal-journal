---
title: User guide
nav_order: 3
---

# User guide
{: .no_toc }

<details open markdown="block">
  <summary>Contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

## Overview

After unlocking, the main window opens with three tabs:

| Tab | Shortcut | Purpose |
|---|---|---|
| **Notes** | Ctrl+1 | Free-form notes with a title |
| **Alarms** | Ctrl+2 | Date and time reminders |
| **Diaries** | Ctrl+3 | Date-stamped diary entries, organised by diary |

The menu bar gives access to all features. Most actions also have a keyboard shortcut.

## Notes

### Creating a note

Press **Ctrl+N** (or *Notes → New note*). A dialog asks for a title; type one and press **Enter**. The new note opens in the editor on the right.

### Editing a note

Select the note in the list on the left and type in the editor on the right. Changes are saved automatically as you type – there is no Save button.

### Deleting a note

Select the note in the list, then press **Delete** or use the right-click context menu and choose *Delete*. A confirmation dialog appears before the note is removed.

### Navigating between notes

Use the **Up** and **Down** arrow keys in the note list, or click a note to select it. The editor updates immediately.

## Alarms

### Setting an alarm

Press **Ctrl+Shift+N** (or *Alarms → New alarm*). The alarm dialog lets you set:

- **Title** – a short description of the reminder.
- **Date and time** – when the alarm should fire. Use the calendar control to pick a date and the time fields for the hour and minute.

Press OK to save the alarm. It appears in the list on the Alarms tab.

### When an alarm fires

When the set date and time is reached, a notification window appears and, if a sound file is present in the `sounds` folder, the sound plays.

From the notification you can:

- Press **Enter** or click *OK* to dismiss it.
- Press **Ctrl+Alt+F1** to snooze (global shortcut, works even when the app is minimised).
- Press **Ctrl+Alt+F2** to stop the alarm sound without dismissing (global shortcut).

### Editing or deleting an alarm

Select the alarm in the list and press **Enter** (or double-click) to open it for editing. Press **Delete** to remove it.

## Diary

### How the diary is organised

The diary tab shows a tree of years and months on the left. Expand a year to see months, expand a month to see individual entries. Select an entry to read or edit it in the editor on the right.

Each entry belongs to a specific **diary** (e.g. *Personal*, *Travel*, *Medical*). The active diary is shown in the selector below the diary entry editor.

### Switching between diaries

Click the diary selector below the diary entry editor and choose a diary. The tree updates to show only entries that belong to that diary.

### Writing an entry

Navigate to the date you want to write about:

- **Go to today** – press **Ctrl+G** (or *Diaries → Go to date*) and leave today's date selected, then press OK.
- **Go to a specific date** – press **Ctrl+G**, type or pick the date, press OK.
- **Click a date in the tree** – expand the year and month, then click the date.

If no entry exists for the selected date it is created automatically when you start typing. Changes are saved automatically.

### Managing diaries

Press **Ctrl+Shift+D** (or *Diaries → Manage diaries*) to open the diary manager. From there you can:

- **New diary** – create a named diary.
- **Rename** – rename the selected diary.
- **Delete** – permanently delete a diary and all its entries. The number of entries is shown in the confirmation dialog. You cannot delete the last remaining diary.

### Creating a new diary quickly

Press **Ctrl+D** (or *Diaries → New diary*) to create a new diary without opening the manager.

## Search

Press **Ctrl+F** or **F3** (or *File → Search*) to open the search dialog. Type any word or phrase and press **Enter**. Results from both notes and diary entries are shown together.

Each result shows the **type** (Note or Diary), the **date**, and a short excerpt. Double-click a result (or press **Enter**) to jump directly to it in the main window. The search dialog closes automatically.

## Export

Press **Ctrl+E** (or *File → Export*) to open the export dialog.

1. **Source** – choose whether to export *Notes* or a *Diary*.
2. **Diary** (diary export only) – choose which diary to export from the drop-down.
3. **Format** – choose the output format (plain text, etc.).
4. Click *Export* and choose where to save the file.

## Backup

Press **Ctrl+Shift+B** (or *File → Backup*) to create a backup copy of your journal database. Choose a destination folder and a backup file is saved there.

{: .tip }
Back up regularly. The backup file is encrypted with the same password as your journal.

## Locking and unlocking

Press **Ctrl+Alt+L** (or *File → Lock journal*) to lock the journal at any time. The editor and all content are hidden and the unlock screen is shown. This is useful when you need to step away from your computer.

To unlock, type your password and press **Enter**.

## Minimising to the system tray

Press **Alt+Shift+F4** (or *File → Minimise to tray*) to hide the window and keep the app running in the system tray. Click the tray icon to restore the window. Right-clicking the tray icon shows options to restore or exit.

## Customising keyboard shortcuts

Press *File → Customize shortcuts* to open the shortcuts editor.

The list shows every assignable action and its current shortcut. To change a shortcut:

1. Select the action in the list.
2. Click **Reassign…**
3. In the dialog that opens, press the key combination you want. The combination is shown immediately. Press **Enter** to confirm or **Escape** to cancel.
4. If the combination is already used by another action, you are asked whether to reassign it anyway.

To restore an action to its factory default, select it and click **Reset to default**.

Your shortcuts are saved immediately and take effect without restarting the app.
