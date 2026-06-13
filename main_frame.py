"""Main application window for Personal Journal."""

from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

import wx
import wx.adv
from cryptography.fernet import Fernet

import database
import i18n
import settings
import shortcuts
from dialogs import (
    AlarmFiredDialog,
    BackupDialog,
    DiaryGoToDateDialog,
    EditAlarmDialog,
    EditNoteDialog,
    ExportDialog,
    ManageDiariesDialog,
    MissedAlarmsDialog,
    NewAlarmDialog,
    NewNoteDialog,
    PasswordDialog,
    SearchDialog,
    ShortcutsDialog,
)
from i18n import format_date, t

# ---------------------------------------------------------------------------
# Audio (optional — graceful no-op if pygame is absent or alarm.ogg missing)
# ---------------------------------------------------------------------------

_SOUND_PATH = Path(__file__).parent / "sounds" / "alarm.ogg"

try:
    import pygame as _pygame
    _AUDIO_OK = True
except ImportError:
    _AUDIO_OK = False


def _start_alarm_sound() -> None:
    if not _AUDIO_OK or not _SOUND_PATH.exists():
        return
    try:
        _pygame.mixer.init()
        _pygame.mixer.music.load(str(_SOUND_PATH))
        _pygame.mixer.music.play(-1)   # loop indefinitely
    except Exception:
        pass


def _stop_alarm_sound() -> None:
    if not _AUDIO_OK:
        return
    try:
        _pygame.mixer.music.stop()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Menu / hotkey IDs
# ---------------------------------------------------------------------------

ID_NEW_NOTE       = wx.NewIdRef()
ID_LOCK           = wx.NewIdRef()
ID_TRAY           = wx.NewIdRef()
ID_NEW_ALARM      = wx.NewIdRef()
ID_SEARCH         = wx.NewIdRef()
ID_EXPORT         = wx.NewIdRef()
ID_BACKUP         = wx.NewIdRef()
ID_SHORTCUTS      = wx.NewIdRef()
ID_NEW_DIARY      = wx.NewIdRef()
ID_GOTO_DATE      = wx.NewIdRef()
ID_MANAGE_DIARIES = wx.NewIdRef()
ID_TAB_NOTES      = wx.NewIdRef()
ID_TAB_ALARMS     = wx.NewIdRef()
ID_TAB_DIARY      = wx.NewIdRef()
HOTKEY_SNOOZE = wx.NewIdRef()
HOTKEY_STOP   = wx.NewIdRef()

# (settings_key, label_i18n_key, wx_id, default_display)
SHORTCUT_DEFS = [
    ("lock",           "menu.lock",           ID_LOCK,           "Ctrl+Alt+L"),
    ("search",         "menu.search",         ID_SEARCH,         "Ctrl+F"),
    ("new_note",       "menu.new_note",       ID_NEW_NOTE,       "Ctrl+N"),
    ("new_alarm",      "menu.new_alarm",      ID_NEW_ALARM,      "Ctrl+Shift+N"),
    ("new_diary",      "menu.new_diary",      ID_NEW_DIARY,      "Ctrl+D"),
    ("goto_date",      "menu.goto_date",      ID_GOTO_DATE,      "Ctrl+G"),
    ("manage_diaries", "menu.manage_diaries", ID_MANAGE_DIARIES, "Ctrl+Shift+D"),
    ("export",         "menu.export",         ID_EXPORT,         "Ctrl+E"),
    ("backup",         "menu.backup",         ID_BACKUP,         "Ctrl+Shift+B"),
    ("tray",           "menu.tray",           ID_TRAY,           "Alt+Shift+F4"),
]

SNOOZE_MINUTES = 5


# ---------------------------------------------------------------------------
# System-tray icon
# ---------------------------------------------------------------------------

class _TrayIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame: "MainFrame"):
        super().__init__()
        self._frame = frame
        bmp = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16))
        icon = wx.Icon()
        icon.CopyFromBitmap(bmp)
        self.SetIcon(icon, t("tray.tooltip"))
        self.Bind(
            wx.adv.EVT_TASKBAR_LEFT_DCLICK,
            lambda e: self._frame._restore_from_tray(),
        )

    def CreatePopupMenu(self) -> wx.Menu:
        menu = wx.Menu()
        restore_item = menu.Append(wx.ID_ANY, t("tray.restore"))
        quit_item    = menu.Append(wx.ID_ANY, t("tray.quit"))
        self.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(self._frame._restore_from_tray), restore_item)
        self.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(self._frame._quit_app),           quit_item)
        return menu


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainFrame(wx.Frame):
    """Primary window containing the Notes and Alarms tabs."""

    def __init__(self, fernet: Fernet, on_language_change: Callable[[str], None]):
        super().__init__(
            parent=None,
            title=t("app.title"),
            size=(900, 600),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self._fernet: Optional[Fernet] = fernet
        self._on_language_change = on_language_change
        self._dates:  list[str]  = []
        self._notes:  list[dict] = []
        self._alarms: list[dict] = []
        self._lang_menu_ids: dict[str, int] = {}
        self._tray_icon: Optional[_TrayIcon] = None
        # Alarm firing state
        self._active_alarm: Optional[dict]       = None
        self._alarm_dlg:    Optional[AlarmFiredDialog] = None
        # Diary state
        self._diary_date: Optional[str] = None
        self._diary_tree_items: dict[str, "wx.TreeItemId"] = {}
        self._current_diary_id: int = 1
        self._diaries: list[dict] = []

        self._build_menu()
        self._build_ui()
        self._build_status_bar()

        # Timers must be created before any refresh that might call Stop() on them.
        self._alarm_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_alarm_timer, self._alarm_timer)
        self._alarm_timer.Start(1_000)

        self._diary_autosave_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_diary_autosave, self._diary_autosave_timer)

        self.SetMinSize((600, 400))
        self.Centre()
        database.ensure_default_diary(t("diary.default_name"), self._fernet)
        self._diaries = database.get_diaries(self._fernet)
        if self._diaries:
            self._current_diary_id = self._diaries[0]["id"]
        self._refresh_dates()
        self._refresh_alarms()
        self._refresh_diary_selector()
        self._refresh_diary()

        # Global hotkeys (system-wide, work even when window is not focused)
        self.RegisterHotKey(HOTKEY_SNOOZE, wx.MOD_CONTROL | wx.MOD_ALT, wx.WXK_F1)
        self.RegisterHotKey(HOTKEY_STOP,   wx.MOD_CONTROL | wx.MOD_ALT, wx.WXK_F2)
        self.Bind(wx.EVT_HOTKEY, self._on_hotkey_snooze, id=HOTKEY_SNOOZE)
        self.Bind(wx.EVT_HOTKEY, self._on_hotkey_stop,   id=HOTKEY_STOP)

        # Fix: make notebook tab bar reachable by forward Tab
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Bind(wx.EVT_CLOSE, self._on_close)

        wx.CallAfter(self._check_missed_alarms)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_menu(self):
        """First-time menu setup: create menubar, bind all events, set accelerators."""
        self.SetMenuBar(self._create_menubar())
        self._bind_menu_events()
        self._update_accelerator_table()

    def _refresh_menu_shortcuts(self):
        """Rebuild menu labels and accelerators after shortcut changes (no rebinding)."""
        self.SetMenuBar(self._create_menubar())
        self._update_accelerator_table()

    def _menu_label(self, i18n_key: str, action_key: str, default: str) -> str:
        """Return menu item label with the current (possibly custom) shortcut hint."""
        base = t(i18n_key).split("\t")[0]
        hint = shortcuts.load_shortcut(action_key, default)
        return f"{base}\t{hint}"

    def _create_menubar(self) -> wx.MenuBar:
        menubar = wx.MenuBar()

        # File ──────────────────────────────────────────────────────────
        file_menu = wx.Menu()
        file_menu.Append(ID_LOCK,    self._menu_label("menu.lock",   "lock",   "Ctrl+Alt+L"),    t("menu.lock_help"))
        file_menu.Append(ID_SEARCH,  self._menu_label("menu.search", "search", "Ctrl+F"),        t("menu.search_help"))
        file_menu.Append(ID_EXPORT,  self._menu_label("menu.export", "export", "Ctrl+E"),        t("menu.export_help"))
        file_menu.Append(ID_BACKUP,  self._menu_label("menu.backup", "backup", "Ctrl+Shift+B"),  t("menu.backup_help"))
        file_menu.Append(ID_SHORTCUTS, t("menu.shortcuts"), t("menu.shortcuts_help"))
        file_menu.Append(ID_TRAY,    self._menu_label("menu.tray",   "tray",   "Alt+Shift+F4"),  t("menu.tray_help"))
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, t("menu.exit"), t("menu.exit_help"))
        menubar.Append(file_menu, t("menu.file"))

        # Notes ─────────────────────────────────────────────────────────
        notes_menu = wx.Menu()
        notes_menu.Append(ID_NEW_NOTE, self._menu_label("menu.new_note", "new_note", "Ctrl+N"), t("menu.new_note_help"))
        menubar.Append(notes_menu, t("menu.notes"))

        # Alarms ────────────────────────────────────────────────────────
        alarms_menu = wx.Menu()
        alarms_menu.Append(ID_NEW_ALARM, self._menu_label("menu.new_alarm", "new_alarm", "Ctrl+Shift+N"), t("menu.new_alarm_help"))
        menubar.Append(alarms_menu, t("menu.alarms"))

        # Diaries ───────────────────────────────────────────────────────
        diaries_menu = wx.Menu()
        diaries_menu.Append(ID_NEW_DIARY,      self._menu_label("menu.new_diary",      "new_diary",      "Ctrl+D"),        t("menu.new_diary_help"))
        diaries_menu.Append(ID_MANAGE_DIARIES, self._menu_label("menu.manage_diaries", "manage_diaries", "Ctrl+Shift+D"), t("menu.manage_diaries_help"))
        diaries_menu.Append(ID_GOTO_DATE,      self._menu_label("menu.goto_date",      "goto_date",      "Ctrl+G"),        t("menu.goto_date_help"))
        menubar.Append(diaries_menu, t("menu.diaries"))

        # Language ──────────────────────────────────────────────────────
        menubar.Append(self._create_language_menu(), t("menu.language"))

        return menubar

    def _bind_menu_events(self):
        """Bind all menu event handlers. Called exactly once at startup."""
        self.Bind(wx.EVT_MENU, self._on_new_note,              id=ID_NEW_NOTE)
        self.Bind(wx.EVT_MENU, self._on_search,                id=ID_SEARCH)
        self.Bind(wx.EVT_MENU, self._on_export,                id=ID_EXPORT)
        self.Bind(wx.EVT_MENU, self._on_backup,                id=ID_BACKUP)
        self.Bind(wx.EVT_MENU, self._on_shortcuts,             id=ID_SHORTCUTS)
        self.Bind(wx.EVT_MENU, lambda e: self._lock(),         id=ID_LOCK)
        self.Bind(wx.EVT_MENU, lambda e: self._send_to_tray(), id=ID_TRAY)
        self.Bind(wx.EVT_MENU, lambda e: self.Close(),         id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self._on_new_alarm,             id=ID_NEW_ALARM)
        self.Bind(wx.EVT_MENU, self._on_new_diary_menu,        id=ID_NEW_DIARY)
        self.Bind(wx.EVT_MENU, self._on_goto_date_menu,        id=ID_GOTO_DATE)
        self.Bind(wx.EVT_MENU, self._on_manage_diaries_menu,   id=ID_MANAGE_DIARIES)
        self.Bind(wx.EVT_MENU, lambda e: self._notebook.SetSelection(0), id=ID_TAB_NOTES)
        self.Bind(wx.EVT_MENU, lambda e: self._notebook.SetSelection(1), id=ID_TAB_ALARMS)
        self.Bind(wx.EVT_MENU, lambda e: self._notebook.SetSelection(2), id=ID_TAB_DIARY)
        self._bind_language_menu_events()

    def _create_language_menu(self) -> wx.Menu:
        menu = wx.Menu()
        current = i18n.current_code()
        for lang in i18n.get_available_languages():
            item_id = self._lang_menu_ids.get(lang["code"]) or wx.NewIdRef()
            self._lang_menu_ids[lang["code"]] = item_id
            item = menu.AppendRadioItem(item_id, lang["name"])
            if lang["code"] == current:
                item.Check(True)
        return menu

    def _bind_language_menu_events(self):
        for lang in i18n.get_available_languages():
            item_id = self._lang_menu_ids.get(lang["code"])
            if item_id:
                self.Bind(wx.EVT_MENU, self._make_lang_handler(lang["code"]), id=item_id)

    def _update_accelerator_table(self):
        entries = [
            (wx.ACCEL_CTRL,   ord("1"),    ID_TAB_NOTES),
            (wx.ACCEL_CTRL,   ord("2"),    ID_TAB_ALARMS),
            (wx.ACCEL_CTRL,   ord("3"),    ID_TAB_DIARY),
            (wx.ACCEL_NORMAL, wx.WXK_F3,  ID_SEARCH),   # F3 always triggers search
        ]
        for action_key, _label_key, wx_id, default_display in SHORTCUT_DEFS:
            parsed = shortcuts.parse_display(shortcuts.load_shortcut(action_key, default_display))
            if parsed:
                entries.append((parsed[0], parsed[1], wx_id))
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))

    def _make_lang_handler(self, code: str) -> Callable:
        def handler(event):
            if code == i18n.current_code():
                return
            wx.MessageBox(
                t("lang.changed_msg"),
                t("lang.changed_title"),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            self._on_language_change(code)
        return handler

    def _build_ui(self):
        self._outer_panel = wx.Panel(self)
        outer_sizer = wx.BoxSizer(wx.VERTICAL)

        # Journal panel — normal unlocked view (notebook with tabs)
        self._journal_panel = wx.Panel(self._outer_panel)
        self._build_journal_contents(self._journal_panel)
        outer_sizer.Add(self._journal_panel, 1, wx.EXPAND)

        # Lock panel — shown when locked
        self._lock_panel = wx.Panel(self._outer_panel)
        self._build_lock_contents(self._lock_panel)
        outer_sizer.Add(self._lock_panel, 1, wx.EXPAND)
        self._lock_panel.Hide()

        self._outer_panel.SetSizer(outer_sizer)

    def _build_journal_contents(self, parent: wx.Panel):
        self._notebook = wx.Notebook(parent)
        self._notebook.SetName(t("app.title"))

        # ── Tab 1: Notes ──────────────────────────────────────────────
        notes_page = wx.Panel(self._notebook)
        self._build_notes_tab(notes_page)
        self._notebook.AddPage(notes_page, t("tab.notes"))

        # ── Tab 2: Alarms ─────────────────────────────────────────────
        alarms_page = wx.Panel(self._notebook)
        self._build_alarms_tab(alarms_page)
        self._notebook.AddPage(alarms_page, t("tab.alarms"))

        # ── Tab 3: Diary ──────────────────────────────────────────────
        diary_page = wx.Panel(self._notebook)
        self._build_diary_tab(diary_page)
        self._notebook.AddPage(diary_page, t("tab.diary"))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._notebook, 1, wx.EXPAND)
        parent.SetSizer(sizer)

    def _build_notes_tab(self, parent: wx.Panel):
        splitter = wx.SplitterWindow(
            parent, style=wx.SP_LIVE_UPDATE | wx.SP_3DSASH
        )
        splitter.SetName(t("frame.accessible_splitter"))
        splitter.SetMinimumPaneSize(160)

        # Left pane: dates
        left_panel = wx.Panel(splitter)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        dates_lbl = wx.StaticText(left_panel, label=t("frame.label_dates"))
        left_sizer.Add(dates_lbl, 0, wx.LEFT | wx.TOP | wx.RIGHT, 6)
        self._dates_list = wx.ListCtrl(
            left_panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
        )
        self._dates_list.SetName(t("frame.accessible_dates"))
        self._dates_list.InsertColumn(0, t("frame.col_date"), width=180)
        self._dates_list.InsertColumn(1, t("frame.col_notes_count"), width=60)
        left_sizer.Add(self._dates_list, 1, wx.EXPAND | wx.ALL, 6)
        left_panel.SetSizer(left_sizer)

        # Right pane: notes + preview
        right_panel = wx.Panel(splitter)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        notes_lbl = wx.StaticText(right_panel, label=t("frame.label_notes"))
        right_sizer.Add(notes_lbl, 0, wx.LEFT | wx.TOP | wx.RIGHT, 6)
        self._notes_list = wx.ListCtrl(
            right_panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
        )
        self._notes_list.SetName(t("frame.accessible_notes"))
        self._notes_list.InsertColumn(0, t("frame.col_subject"), width=260)
        self._notes_list.InsertColumn(1, t("frame.col_time"), width=120)
        right_sizer.Add(self._notes_list, 1, wx.EXPAND | wx.ALL, 6)
        preview_lbl = wx.StaticText(right_panel, label=t("frame.label_content"))
        right_sizer.Add(preview_lbl, 0, wx.LEFT | wx.RIGHT, 6)
        self._preview = wx.TextCtrl(
            right_panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.BORDER_SUNKEN,
        )
        self._preview.SetName(t("frame.accessible_preview"))
        self._preview.SetToolTip(t("frame.tooltip_preview"))
        right_sizer.Add(self._preview, 1, wx.EXPAND | wx.ALL, 6)
        right_panel.SetSizer(right_sizer)

        splitter.SplitVertically(left_panel, right_panel, 260)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 1, wx.EXPAND)
        parent.SetSizer(sizer)

        self._dates_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_date_selected)
        self._notes_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_note_selected)
        self._notes_list.Bind(wx.EVT_CONTEXT_MENU, self._on_notes_context_menu)
        self._notes_list.Bind(wx.EVT_KEY_DOWN, self._on_notes_key_down)

    def _build_alarms_tab(self, parent: wx.Panel):
        sizer = wx.BoxSizer(wx.VERTICAL)
        lbl = wx.StaticText(parent, label=t("frame.label_alarms"))
        sizer.Add(lbl, 0, wx.LEFT | wx.TOP | wx.RIGHT, 6)

        self._alarms_list = wx.ListCtrl(
            parent,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
        )
        self._alarms_list.SetName(t("frame.accessible_alarms"))
        self._alarms_list.InsertColumn(0, t("frame.col_alarm_subject"), width=180)
        self._alarms_list.InsertColumn(1, t("frame.col_alarm_note"),    width=220)
        self._alarms_list.InsertColumn(2, t("frame.col_alarm_date"),    width=160)
        self._alarms_list.InsertColumn(3, t("frame.col_alarm_time"),    width=80)
        sizer.Add(self._alarms_list, 1, wx.EXPAND | wx.ALL, 6)
        parent.SetSizer(sizer)

        self._alarms_list.Bind(wx.EVT_CONTEXT_MENU, self._on_alarms_context_menu)
        self._alarms_list.Bind(wx.EVT_KEY_DOWN, self._on_alarms_key_down)

    def _build_diary_tab(self, parent: wx.Panel):
        tree_lbl  = wx.StaticText(parent, label=t("diary.label_tree"))
        self._diary_tree = wx.TreeCtrl(parent, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
        self._diary_tree.SetName(t("diary.accessible_tree"))

        entry_lbl = wx.StaticText(parent, label=t("diary.label_entry"))
        self._diary_text = wx.TextCtrl(parent, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.BORDER_SUNKEN)
        self._diary_text.SetName(t("diary.accessible_entry"))
        self._diary_text.SetToolTip(t("diary.tooltip_entry"))
        self._diary_text.Disable()

        self._diary_goto_btn = wx.Button(parent, label=t("diary.btn_goto_date"),
                                         style=wx.BU_EXACTFIT)
        self._diary_goto_btn.SetName(t("diary.btn_goto_date"))
        self._diary_goto_btn.SetToolTip(t("diary.btn_goto_date_tip"))

        selector_lbl = wx.StaticText(parent, label=t("diary.label_selector"))
        self._diary_choice = wx.Choice(parent, choices=[])
        self._diary_choice.SetName(t("diary.accessible_selector"))

        self._manage_diaries_btn = wx.Button(parent, label=t("diary.btn_manage"),
                                             style=wx.BU_EXACTFIT)
        self._manage_diaries_btn.SetToolTip(t("diary.btn_manage_tip"))

        # Bottom-right cell: selector label + choice + manage button
        bottom_right = wx.BoxSizer(wx.HORIZONTAL)
        bottom_right.Add(selector_lbl,             0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        bottom_right.Add(self._diary_choice,       1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        bottom_right.Add(self._manage_diaries_btn, 0, wx.ALIGN_CENTER_VERTICAL)

        # GridBagSizer: 3 rows × 2 columns
        #   row 0: labels (fixed height)
        #   row 1: tree | diary text (growable — takes the bulk of the height)
        #   row 2: goto btn | selector + choice + manage (fixed height)
        #   col 0 : 1/3 width   col 1 : 2/3 width
        gbs = wx.GridBagSizer(vgap=0, hgap=0)
        gbs.Add(tree_lbl,              (0, 0), flag=wx.LEFT | wx.TOP,                   border=6)
        gbs.Add(entry_lbl,             (0, 1), flag=wx.LEFT | wx.TOP,                   border=6)
        gbs.Add(self._diary_tree,      (1, 0), flag=wx.EXPAND | wx.ALL,                 border=6)
        gbs.Add(self._diary_text,      (1, 1), flag=wx.EXPAND | wx.ALL,                 border=6)
        gbs.Add(self._diary_goto_btn,  (2, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL,  border=6)
        gbs.Add(bottom_right,          (2, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=6)

        gbs.AddGrowableRow(1)          # row 1 expands vertically
        gbs.AddGrowableCol(0, 1)       # col 0 gets 1 share
        gbs.AddGrowableCol(1, 2)       # col 1 gets 2 shares
        parent.SetSizer(gbs)

        self._diary_tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_diary_tree_selected)
        self._diary_text.Bind(wx.EVT_TEXT, self._on_diary_text_changed)
        self._diary_goto_btn.Bind(wx.EVT_BUTTON, self._on_diary_goto_date)
        self._diary_choice.Bind(wx.EVT_CHOICE, self._on_diary_choice_changed)
        self._manage_diaries_btn.Bind(wx.EVT_BUTTON, self._on_manage_diaries)

    def _build_lock_contents(self, parent: wx.Panel):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer()

        msg = wx.StaticText(parent, label=t("lock.message"))
        msg.SetName(t("lock.message"))
        sizer.Add(msg, 0, wx.ALIGN_CENTER | wx.BOTTOM, 16)

        self._unlock_btn = wx.Button(parent, label=t("lock.btn_unlock"))
        self._unlock_btn.SetName(t("lock.btn_unlock"))
        self._unlock_btn.Bind(wx.EVT_BUTTON, lambda e: self._prompt_unlock())
        sizer.Add(self._unlock_btn, 0, wx.ALIGN_CENTER)

        sizer.AddStretchSpacer()
        parent.SetSizer(sizer)

    def _build_status_bar(self):
        self.CreateStatusBar(2)
        self.SetStatusWidths([-1, 160])
        self._update_status_date()

    # ------------------------------------------------------------------
    # Lock / unlock
    # ------------------------------------------------------------------

    def _lock(self):
        """Wipe the fernet key and all sensitive data; show the lock screen."""
        self._flush_diary_autosave()  # must be before clearing _fernet
        self._fernet = None
        self._dates = []
        self._notes = []
        self._alarms = []
        self._dates_list.DeleteAllItems()
        self._notes_list.DeleteAllItems()
        self._preview.SetValue("")
        self._alarms_list.DeleteAllItems()
        self._diary_tree.DeleteAllItems()
        self._diary_text.ChangeValue("")
        self._diary_text.Disable()
        self._diary_date = None
        self._diaries = []
        self._current_diary_id = 1
        self._diary_choice.Clear()
        self._diary_choice.Disable()
        self._journal_panel.Hide()
        self._lock_panel.Show()
        self._outer_panel.Layout()
        self.SetTitle(t("app.title") + " \u2014 " + t("lock.status"))
        self.SetStatusText(t("lock.status"), 0)
        self._unlock_btn.SetFocus()

    def _unlock_journal(self, fernet: Fernet):
        """Restore journal access after successful authentication."""
        self._fernet = fernet
        database.ensure_default_diary(t("diary.default_name"), fernet)
        self._diaries = database.get_diaries(fernet)
        if self._diaries:
            self._current_diary_id = self._diaries[0]["id"]
        self._lock_panel.Hide()
        self._journal_panel.Show()
        self._outer_panel.Layout()
        self.SetTitle(t("app.title"))
        self._refresh_dates()
        self._refresh_alarms()
        self._refresh_diary_selector()
        self._refresh_diary()
        self._notebook.SetFocus()

    def _prompt_unlock(self):
        """Show the password dialog; unlock on success, stay locked on cancel."""
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            dlg = PasswordDialog(self)
            result = dlg.ShowModal()
            password = dlg.get_password() if result == wx.ID_OK else None
            dlg.Destroy()

            if result != wx.ID_OK:
                return

            fernet = database.authenticate(password)
            if fernet is not None:
                self._unlock_journal(fernet)
                return

            remaining = max_attempts - attempt
            if remaining > 0:
                wx.MessageBox(
                    t("app.err_auth_failed", remaining=remaining),
                    t("app.err_auth_failed_title"),
                    wx.OK | wx.ICON_WARNING,
                    self,
                )
            else:
                wx.MessageBox(
                    t("app.err_locked_out"),
                    t("app.err_locked_out_title"),
                    wx.OK | wx.ICON_ERROR,
                    self,
                )
                self.Close()

    # ------------------------------------------------------------------
    # System tray
    # ------------------------------------------------------------------

    def _send_to_tray(self):
        self._lock()
        self._tray_icon = _TrayIcon(self)
        self.Hide()

    def _restore_from_tray(self):
        if self._tray_icon:
            self._tray_icon.RemoveIcon()
            self._tray_icon.Destroy()
            self._tray_icon = None
        self.Show()
        self.Raise()
        self._prompt_unlock()

    def _quit_app(self):
        if self._tray_icon:
            self._tray_icon.RemoveIcon()
            self._tray_icon.Destroy()
            self._tray_icon = None
        self.Destroy()

    # ------------------------------------------------------------------
    # Alarm timer and hotkeys
    # ------------------------------------------------------------------

    def _on_char_hook(self, event):
        """Make the notebook tab bar reachable via forward Tab.

        EVT_NAVIGATION_KEY on a page panel fires for every Tab press within the page
        (not just when escaping), so we use a targeted frame-level char hook instead:
        - Tab from the last focusable control in the current page → focus the notebook.
        - Tab from the notebook itself → focus the first control of the current page.
        All other Tab/Shift+Tab presses are left to the default wxPython handler.
        """
        if event.GetKeyCode() == wx.WXK_TAB and not event.ControlDown():
            focused = wx.Window.FindFocus()
            if focused is self._notebook:
                idx = self._notebook.GetSelection()
                if event.ShiftDown():
                    # Shift+Tab from notebook: go to last control of current page.
                    if idx == 0:
                        self._preview.SetFocus()
                    elif idx == 1:
                        self._alarms_list.SetFocus()
                    else:
                        self._manage_diaries_btn.SetFocus()
                else:
                    # Tab from notebook: go to first control of current page.
                    if idx == 0:
                        self._dates_list.SetFocus()
                    elif idx == 1:
                        self._alarms_list.SetFocus()
                    else:
                        self._diary_tree.SetFocus()
                return  # consume
            elif not event.ShiftDown():
                # Forward Tab from last control in a page → notebook tab bar.
                if focused in (self._preview, self._alarms_list, self._manage_diaries_btn):
                    self._notebook.SetFocus()
                    return  # consume
        event.Skip()

    def _check_missed_alarms(self):
        """Show a summary of alarms that fired while the app was closed."""
        if self._active_alarm is not None:
            return
        due = database.get_due_alarms()
        if not due:
            return
        self._active_alarm = due[0]  # block the timer while dialog is open
        try:
            dlg = MissedAlarmsDialog(self, due)
            dlg.ShowModal()
            result = dlg.get_result()
            dlg.Destroy()
            if result == MissedAlarmsDialog.RESULT_SNOOZE:
                for a in due:
                    database.snooze_alarm(a["id"], SNOOZE_MINUTES)
            else:
                for a in due:
                    database.delete_alarm(a["id"])
            self._refresh_alarms()
        finally:
            self._active_alarm = None

    def _on_alarm_timer(self, event):
        """Check for due alarms every 30 s. Fire at most one at a time."""
        if self._active_alarm is not None:
            return

        due = database.get_due_alarms()
        if not due:
            return

        locked = self._fernet is None
        try:
            alarm = database.get_alarm_by_id(due[0]["id"], self._fernet)
        except Exception:
            return

        self._active_alarm = alarm
        _start_alarm_sound()

        self.Raise()
        self._alarm_dlg = AlarmFiredDialog(self, alarm, locked=locked)
        self._alarm_dlg.ShowModal()
        result = self._alarm_dlg.get_result()
        self._alarm_dlg.Destroy()
        self._alarm_dlg = None

        _stop_alarm_sound()
        self._active_alarm = None

        if result == AlarmFiredDialog.RESULT_SNOOZE:
            database.snooze_alarm(alarm["id"], SNOOZE_MINUTES)
        else:
            database.delete_alarm(alarm["id"])

        self._refresh_alarms()

    def _on_hotkey_snooze(self, event):
        if self._alarm_dlg is not None:
            self._alarm_dlg.do_snooze()

    def _on_hotkey_stop(self, event):
        if self._alarm_dlg is not None:
            self._alarm_dlg.do_stop()

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _refresh_dates(self):
        self._dates_list.DeleteAllItems()
        self._notes_list.DeleteAllItems()
        self._preview.SetValue("")
        self._dates = database.get_dates_with_notes()

        for idx, d in enumerate(self._dates):
            try:
                dt = datetime.strptime(d, "%Y-%m-%d")
                display = format_date(dt, "%A, %B %d, %Y")
            except ValueError:
                display = d
            self._dates_list.InsertItem(idx, display)
            notes = database.get_notes_for_date(d, self._fernet)
            self._dates_list.SetItem(idx, 1, str(len(notes)))

        self._update_statusbar_count()

    def _refresh_alarms(self):
        self._alarms_list.DeleteAllItems()
        self._alarms = []
        if self._fernet is None:
            return
        self._alarms = database.get_all_alarms(self._fernet)
        for idx, alarm in enumerate(self._alarms):
            self._alarms_list.InsertItem(idx, alarm["subject"])
            note_preview = alarm["note"].replace("\n", " ")[:60]
            if len(alarm["note"]) > 60:
                note_preview += "…"
            self._alarms_list.SetItem(idx, 1, note_preview)
            try:
                dt = datetime.strptime(alarm["alarm_dt"], "%Y-%m-%d %H:%M:%S")
                self._alarms_list.SetItem(idx, 2, format_date(dt, "%A, %B %d, %Y"))
                self._alarms_list.SetItem(idx, 3, dt.strftime("%H:%M"))
            except ValueError:
                self._alarms_list.SetItem(idx, 2, alarm["alarm_dt"])

    def _refresh_diary(self, goto_date: Optional[str] = None):
        """Rebuild the diary tree from DB and navigate to *goto_date* (or today)."""
        self._diary_autosave_timer.Stop()
        self._diary_tree.DeleteAllItems()
        self._diary_date = None
        self._diary_text.ChangeValue("")
        self._diary_text.Disable()

        if self._fernet is None:
            return

        from collections import defaultdict
        self._diary_tree_items = {}
        diary_dates = set(database.get_diary_dates(self._current_diary_id))
        today = date.today()
        today_iso = today.isoformat()
        diary_dates.add(today_iso)  # always show today
        if goto_date:
            diary_dates.add(goto_date)  # ensure requested date appears in tree

        target_iso = goto_date or today_iso
        try:
            target_dt = datetime.strptime(target_iso, "%Y-%m-%d")
        except ValueError:
            target_dt = datetime.combine(today, datetime.min.time())

        by_year: dict = defaultdict(lambda: defaultdict(set))
        for d_str in diary_dates:
            try:
                dt = datetime.strptime(d_str, "%Y-%m-%d")
                by_year[dt.year][dt.month].add(dt.day)
            except ValueError:
                continue

        root = self._diary_tree.AddRoot("")
        today_item = None
        target_item = None

        for year in sorted(by_year.keys()):
            year_item = self._diary_tree.AppendItem(root, str(year))
            self._diary_tree.SetItemData(year_item, None)

            today_month_item = None
            target_month_item = None
            for month in sorted(by_year[year].keys()):
                month_name = format_date(datetime(year, month, 1), "%B")
                month_item = self._diary_tree.AppendItem(year_item, month_name)
                self._diary_tree.SetItemData(month_item, None)
                if year == today.year and month == today.month:
                    today_month_item = month_item
                if year == target_dt.year and month == target_dt.month:
                    target_month_item = month_item

                for day in sorted(by_year[year][month]):
                    day_dt = datetime(year, month, day)
                    day_iso = day_dt.date().isoformat()
                    day_label = f"{day:02d} \u2013 {format_date(day_dt, '%A')}"
                    day_item = self._diary_tree.AppendItem(month_item, day_label)
                    self._diary_tree.SetItemData(day_item, day_iso)
                    self._diary_tree_items[day_iso] = day_item
                    if day_iso == today_iso:
                        today_item = day_item
                    if day_iso == target_iso:
                        target_item = day_item

            if year == today.year:
                self._diary_tree.Expand(year_item)
                if today_month_item:
                    self._diary_tree.Expand(today_month_item)
            if goto_date and year == target_dt.year and year != today.year:
                self._diary_tree.Expand(year_item)
                if target_month_item:
                    self._diary_tree.Expand(target_month_item)

        select_item = target_item or today_item
        select_iso  = target_iso if target_item else today_iso
        if select_item:
            self._diary_tree.SelectItem(select_item)
            self._diary_tree.EnsureVisible(select_item)
            self._load_diary_entry(select_iso)

    def _load_diary_entry(self, iso_date: str):
        """Load the diary entry for *iso_date* into the text control."""
        self._flush_diary_autosave()
        self._diary_date = iso_date
        content = database.get_diary_entry(iso_date, self._current_diary_id, self._fernet)
        self._diary_text.ChangeValue(content)  # ChangeValue does not fire EVT_TEXT
        self._diary_text.Enable()
        self._diary_text.SetInsertionPointEnd()

    def _flush_diary_autosave(self):
        """Immediately write any pending diary change to the database."""
        self._diary_autosave_timer.Stop()
        if self._diary_date and self._fernet:
            database.save_diary_entry(
                self._diary_date, self._diary_text.GetValue(),
                self._current_diary_id, self._fernet
            )

    # ------------------------------------------------------------------
    # Event handlers — diary
    # ------------------------------------------------------------------

    def _on_diary_tree_selected(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        iso_date = self._diary_tree.GetItemData(item)
        if iso_date is None:
            # Year or month node — save pending work and disable the text box.
            self._flush_diary_autosave()
            self._diary_date = None
            self._diary_text.ChangeValue("")
            self._diary_text.Disable()
        else:
            self._load_diary_entry(iso_date)

    def _on_diary_text_changed(self, event):
        """Restart the auto-save countdown on every keystroke."""
        if self._diary_date is None:
            return
        self._diary_autosave_timer.Stop()
        self._diary_autosave_timer.Start(1_000, wx.TIMER_ONE_SHOT)

    def _on_diary_autosave(self, event):
        if self._diary_date and self._fernet:
            database.save_diary_entry(
                self._diary_date, self._diary_text.GetValue(),
                self._current_diary_id, self._fernet
            )

    def _on_diary_goto_date(self, event):
        dlg = DiaryGoToDateDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            selected = dlg.get_date()
            if selected:
                self._refresh_diary(goto_date=selected.isoformat())
                self._diary_text.SetFocus()
        dlg.Destroy()

    def _refresh_diary_selector(self):
        """Repopulate the diary choice widget from self._diaries."""
        self._diary_choice.Clear()
        if not self._diaries:
            self._diary_choice.Disable()
            return
        self._diary_choice.Enable()
        for d in self._diaries:
            self._diary_choice.Append(d["name"])
        idx = next(
            (i for i, d in enumerate(self._diaries) if d["id"] == self._current_diary_id),
            0,
        )
        self._diary_choice.SetSelection(idx)
        if self._diaries:
            self._current_diary_id = self._diaries[idx]["id"]

    def _on_diary_choice_changed(self, event):
        self._flush_diary_autosave()
        idx = self._diary_choice.GetSelection()
        if 0 <= idx < len(self._diaries):
            self._current_diary_id = self._diaries[idx]["id"]
        self._refresh_diary()

    def _on_manage_diaries(self, event):
        dlg = ManageDiariesDialog(self, self._fernet, self._diaries)
        dlg.ShowModal()
        dlg.Destroy()
        self._diaries = database.get_diaries(self._fernet)
        if not any(d["id"] == self._current_diary_id for d in self._diaries):
            self._current_diary_id = self._diaries[0]["id"] if self._diaries else 1
        self._refresh_diary_selector()
        self._refresh_diary()

    def _on_new_diary_menu(self, _event):
        if not self._fernet:
            return
        dlg = wx.TextEntryDialog(self, t("diary.new_diary_label"), t("diary.new_diary_title"))
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue().strip()
            if name:
                new_id = database.add_diary(name, self._fernet)
                self._diaries = database.get_diaries(self._fernet)
                self._current_diary_id = new_id
                self._refresh_diary_selector()
                self._refresh_diary()
        dlg.Destroy()

    def _on_goto_date_menu(self, _event):
        self._on_diary_goto_date(None)

    def _on_manage_diaries_menu(self, _event):
        self._on_manage_diaries(None)

    def _load_notes_for_date(self, iso_date: str):
        self._notes_list.DeleteAllItems()
        self._preview.SetValue("")
        self._notes = database.get_notes_for_date(iso_date, self._fernet)
        for idx, note in enumerate(self._notes):
            self._notes_list.InsertItem(idx, note["subject"])
            try:
                dt = datetime.fromisoformat(note["created_at"])
                time_str = dt.strftime("%H:%M:%S")
            except ValueError:
                time_str = note["created_at"]
            self._notes_list.SetItem(idx, 1, time_str)

    def _update_statusbar_count(self):
        self.SetStatusText(t("frame.status_count", n=len(self._dates)), 0)

    def _update_status_date(self):
        self.SetStatusText(date.today().strftime("%Y-%m-%d"), 1)

    def _select_date(self, iso_date: str):
        if iso_date not in self._dates:
            return
        idx = self._dates.index(iso_date)
        self._dates_list.Select(idx)
        self._dates_list.EnsureVisible(idx)
        self._load_notes_for_date(iso_date)

    # ------------------------------------------------------------------
    # Event handlers — frame
    # ------------------------------------------------------------------

    def _on_close(self, event):
        self._alarm_timer.Stop()
        self._flush_diary_autosave()
        self._diary_autosave_timer.Stop()
        self.UnregisterHotKey(HOTKEY_SNOOZE)
        self.UnregisterHotKey(HOTKEY_STOP)
        if self._tray_icon:
            self._tray_icon.RemoveIcon()
            self._tray_icon.Destroy()
            self._tray_icon = None
        event.Skip()

    # ------------------------------------------------------------------
    # Event handlers — notes list
    # ------------------------------------------------------------------

    def _on_date_selected(self, event):
        idx = event.GetIndex()
        if 0 <= idx < len(self._dates):
            self._load_notes_for_date(self._dates[idx])

    def _on_note_selected(self, event):
        idx = event.GetIndex()
        if 0 <= idx < len(self._notes):
            self._preview.SetValue(self._notes[idx]["content"])

    def _on_notes_context_menu(self, event):
        if self._notes_list.GetFirstSelected() < 0:
            return
        pos = event.GetPosition()
        if pos == wx.DefaultPosition:
            idx = self._notes_list.GetFirstSelected()
            rect = self._notes_list.GetItemRect(idx)
            pos = self._notes_list.ClientToScreen(
                wx.Point(rect.x + 4, rect.y + rect.height)
            )
        menu = wx.Menu()
        edit_item   = menu.Append(wx.ID_ANY, t("note.ctx_edit")   + "\tCtrl+E")
        delete_item = menu.Append(wx.ID_ANY, t("note.ctx_delete") + "\tDel")
        menu.Bind(wx.EVT_MENU, lambda e: self._edit_selected_note(),   edit_item)
        menu.Bind(wx.EVT_MENU, lambda e: self._delete_selected_note(), delete_item)
        self._notes_list.PopupMenu(menu, self._notes_list.ScreenToClient(pos))
        menu.Destroy()

    def _on_notes_key_down(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_DELETE:
            self._delete_selected_note()
        elif key == ord("E") and event.ControlDown():
            self._edit_selected_note()
        else:
            event.Skip()

    def _on_search(self, event):
        if self._fernet is None:
            return
        dlg = SearchDialog(self, self._fernet)
        result = dlg.ShowModal()
        goto_date = dlg.get_goto_diary_date()
        goto_diary_id = dlg.get_goto_diary_id()
        dlg.Destroy()
        # Refresh lists in case the user edited or deleted items during search.
        self._refresh_dates()
        self._refresh_alarms()
        if result == SearchDialog.RESULT_GOTO_DIARY and goto_date:
            self._goto_diary_entry(goto_date, diary_id=goto_diary_id)

    def _on_export(self, event):
        if self._fernet is None:
            return
        dlg = ExportDialog(self, self._fernet, self._diaries)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_backup(self, _event):
        dlg = BackupDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_shortcuts(self, _event):
        dlg = ShortcutsDialog(self, SHORTCUT_DEFS)
        dlg.ShowModal()
        dlg.Destroy()
        self._refresh_menu_shortcuts()

    def _goto_diary_entry(self, entry_date: str, diary_id: Optional[int] = None):
        """Switch to the Diary tab and select the given date in the tree."""
        diary_changed = diary_id is not None and diary_id != self._current_diary_id
        if diary_changed:
            self._flush_diary_autosave()
            self._current_diary_id = diary_id
            self._refresh_diary_selector()
            self._notebook.SetSelection(2)
            self._refresh_diary(goto_date=entry_date)
            return
        self._notebook.SetSelection(2)
        item = self._diary_tree_items.get(entry_date)
        if item is not None and item.IsOk():
            self._diary_tree.EnsureVisible(item)
            self._diary_tree.SelectItem(item)
            self._diary_text.SetFocus()
        else:
            # Entry might have been added since last refresh; rebuild tree.
            self._refresh_diary()

    def _on_new_note(self, event):
        if self._fernet is None:
            return
        dlg = NewNoteDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            database.add_note(dlg.get_subject(), dlg.get_content(), self._fernet)
            self._refresh_dates()
            today = date.today().isoformat()
            if today in self._dates:
                idx = self._dates.index(today)
                self._dates_list.Select(idx)
                self._dates_list.EnsureVisible(idx)
                self._dates_list.SetFocus()
        dlg.Destroy()

    def _edit_selected_note(self):
        if self._fernet is None:
            return
        idx = self._notes_list.GetFirstSelected()
        if idx < 0:
            return
        note = self._notes[idx]
        dlg = EditNoteDialog(self, note)
        if dlg.ShowModal() == wx.ID_OK:
            database.update_note(
                note["id"], dlg.get_subject(), dlg.get_content(), self._fernet
            )
            self._refresh_dates()
            self._select_date(note["note_date"])
            if idx < self._notes_list.GetItemCount():
                self._notes_list.Select(idx)
                self._notes_list.Focus(idx)
                self._notes_list.SetFocus()
        dlg.Destroy()

    def _delete_selected_note(self):
        if self._fernet is None:
            return
        idx = self._notes_list.GetFirstSelected()
        if idx < 0:
            return
        note = self._notes[idx]
        dlg = wx.MessageDialog(
            self,
            t("note.delete_confirm_msg", subject=note["subject"]),
            t("note.delete_confirm_title"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if dlg.ShowModal() == wx.ID_YES:
            iso_date = note["note_date"]
            database.delete_note(note["id"])
            self._refresh_dates()
            if iso_date in self._dates:
                self._select_date(iso_date)
        dlg.Destroy()

    # ------------------------------------------------------------------
    # Event handlers — alarms list
    # ------------------------------------------------------------------

    def _on_alarms_context_menu(self, event):
        if self._alarms_list.GetFirstSelected() < 0:
            return
        pos = event.GetPosition()
        if pos == wx.DefaultPosition:
            idx = self._alarms_list.GetFirstSelected()
            rect = self._alarms_list.GetItemRect(idx)
            pos = self._alarms_list.ClientToScreen(
                wx.Point(rect.x + 4, rect.y + rect.height)
            )
        menu = wx.Menu()
        edit_item   = menu.Append(wx.ID_ANY, t("alarm.ctx_edit")   + "\tCtrl+E")
        delete_item = menu.Append(wx.ID_ANY, t("alarm.ctx_delete") + "\tDel")
        menu.Bind(wx.EVT_MENU, lambda e: self._edit_selected_alarm(),   edit_item)
        menu.Bind(wx.EVT_MENU, lambda e: self._delete_selected_alarm(), delete_item)
        self._alarms_list.PopupMenu(menu, self._alarms_list.ScreenToClient(pos))
        menu.Destroy()

    def _on_alarms_key_down(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_DELETE:
            self._delete_selected_alarm()
        elif key == ord("E") and event.ControlDown():
            self._edit_selected_alarm()
        else:
            event.Skip()

    def _on_new_alarm(self, event):
        if self._fernet is None:
            return
        dlg = NewAlarmDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            database.add_alarm(
                dlg.get_subject(), dlg.get_note(), dlg.get_alarm_dt(), self._fernet
            )
            self._refresh_alarms()
        dlg.Destroy()

    def _edit_selected_alarm(self):
        if self._fernet is None:
            return
        idx = self._alarms_list.GetFirstSelected()
        if idx < 0:
            return
        alarm = self._alarms[idx]
        dlg = EditAlarmDialog(self, alarm)
        if dlg.ShowModal() == wx.ID_OK:
            database.update_alarm(
                alarm["id"],
                dlg.get_subject(),
                dlg.get_note(),
                dlg.get_alarm_dt(),
                self._fernet,
            )
            self._refresh_alarms()
            if idx < self._alarms_list.GetItemCount():
                self._alarms_list.Select(idx)
                self._alarms_list.Focus(idx)
                self._alarms_list.SetFocus()
        dlg.Destroy()

    def _delete_selected_alarm(self):
        if self._fernet is None:
            return
        idx = self._alarms_list.GetFirstSelected()
        if idx < 0:
            return
        alarm = self._alarms[idx]
        dlg = wx.MessageDialog(
            self,
            t("alarm.delete_confirm_msg", subject=alarm["subject"]),
            t("alarm.delete_confirm_title"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if dlg.ShowModal() == wx.ID_YES:
            database.delete_alarm(alarm["id"])
            self._refresh_alarms()
        dlg.Destroy()
