"""Dialogs for the Personal Journal app."""

import shutil
import tempfile
import zipfile
from datetime import date, datetime
from ftplib import FTP, FTP_TLS
from pathlib import Path
from typing import Optional

import wx
import wx.adv

import database
import i18n
import settings
import shortcuts as _sc
from i18n import format_date, t

try:
    import UniversalSpeech as _us
    def _speak(msg: str) -> None:
        try:
            _us.say(msg)
        except Exception:
            pass
except Exception:
    def _speak(msg: str) -> None:  # type: ignore[misc]
        pass


class PasswordSetupDialog(wx.Dialog):
    """Shown on first launch to create a master password."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=t("setup.title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP,
        )
        self._langs = i18n.get_available_languages()
        self._build_ui()
        self.Fit()
        self.SetMinSize((380, -1))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Language selector — shown before anything else so it takes effect first
        lang_row = wx.BoxSizer(wx.HORIZONTAL)
        self._lbl_lang = wx.StaticText(panel, label=t("menu.language").replace("&", ""))
        lang_names = [lang["name"] for lang in self._langs]
        self._lang_choice = wx.Choice(panel, choices=lang_names)
        current = i18n.current_code()
        for i, lang in enumerate(self._langs):
            if lang["code"] == current:
                self._lang_choice.SetSelection(i)
                break
        lang_row.Add(self._lbl_lang, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        lang_row.Add(self._lang_choice, 1, wx.EXPAND)
        sizer.Add(lang_row, 0, wx.EXPAND | wx.ALL, 10)

        self._intro = wx.StaticText(panel, label=t("setup.intro").replace("\\n", "\n"))
        self._intro.Wrap(340)
        sizer.Add(self._intro, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        grid = wx.FlexGridSizer(rows=2, cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)

        self._lbl_pw = wx.StaticText(panel, label=t("setup.label_password"))
        self._pw = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self._pw.SetName(t("setup.accessible_password"))
        self._pw.SetToolTip(t("setup.tooltip_password"))

        self._lbl_confirm = wx.StaticText(panel, label=t("setup.label_confirm"))
        self._confirm = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self._confirm.SetName(t("setup.accessible_confirm"))
        self._confirm.SetToolTip(t("setup.tooltip_confirm"))

        grid.Add(self._lbl_pw, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._pw, 1, wx.EXPAND)
        grid.Add(self._lbl_confirm, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._confirm, 1, wx.EXPAND)
        sizer.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_sizer = wx.StdDialogButtonSizer()
        self._ok_btn = wx.Button(panel, wx.ID_OK, label=t("setup.btn_create"))
        self._ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(self._ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(sizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._lang_choice.Bind(wx.EVT_CHOICE, self._on_lang_change)

    def _on_lang_change(self, event):
        idx = self._lang_choice.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        i18n.load(self._langs[idx]["code"])
        self._relabel()

    def _relabel(self):
        self.SetTitle(t("setup.title"))
        self._lbl_lang.SetLabel(t("menu.language").replace("&", ""))
        self._intro.SetLabel(t("setup.intro").replace("\\n", "\n"))
        self._intro.Wrap(340)
        self._lbl_pw.SetLabel(t("setup.label_password"))
        self._pw.SetName(t("setup.accessible_password"))
        self._pw.SetToolTip(t("setup.tooltip_password"))
        self._lbl_confirm.SetLabel(t("setup.label_confirm"))
        self._confirm.SetName(t("setup.accessible_confirm"))
        self._confirm.SetToolTip(t("setup.tooltip_confirm"))
        self._ok_btn.SetLabel(t("setup.btn_create"))
        self.Layout()
        self.Fit()

    def _on_ok(self, event):
        pw = self._pw.GetValue()
        confirm = self._confirm.GetValue()

        if len(pw) < 4:
            wx.MessageBox(
                t("setup.err_too_short"),
                t("setup.err_validation_title"),
                wx.OK | wx.ICON_ERROR,
                self,
            )
            self._pw.SetFocus()
            return

        if pw != confirm:
            wx.MessageBox(
                t("setup.err_no_match"),
                t("setup.err_validation_title"),
                wx.OK | wx.ICON_ERROR,
                self,
            )
            self._confirm.SetValue("")
            self._confirm.SetFocus()
            return

        self.EndModal(wx.ID_OK)

    def get_password(self) -> str:
        return self._pw.GetValue()


class BackupDialog(wx.Dialog):
    """Create a local or FTP backup of the journal database and settings."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=t("backup.title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._build_ui()
        self._load_saved_ftp()
        self.Fit()
        self.SetMinSize((440, -1))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)

        info = wx.StaticText(panel, label=t("backup.info"))
        info.Wrap(400)
        outer.Add(info, 0, wx.ALL, 10)

        # Mode selection
        mode_row = wx.BoxSizer(wx.HORIZONTAL)
        self._local_radio = wx.RadioButton(panel, label=t("backup.mode_local"), style=wx.RB_GROUP)
        self._ftp_radio   = wx.RadioButton(panel, label=t("backup.mode_ftp"))
        mode_row.Add(self._local_radio, 0, wx.RIGHT, 16)
        mode_row.Add(self._ftp_radio,   0)
        outer.Add(mode_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        outer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        # ── Local section ──────────────────────────────────────────────────
        self._local_panel = wx.Panel(panel)
        local_row = wx.BoxSizer(wx.HORIZONTAL)
        lbl_path = wx.StaticText(self._local_panel, label=t("backup.local_label"))
        self._local_path = wx.TextCtrl(self._local_panel, value=str(Path.home()))
        self._local_path.SetToolTip(t("backup.local_tip"))
        browse_btn = wx.Button(self._local_panel, label=t("backup.local_browse"), style=wx.BU_EXACTFIT)
        local_row.Add(lbl_path,         0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        local_row.Add(self._local_path, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        local_row.Add(browse_btn,       0, wx.ALIGN_CENTER_VERTICAL)
        self._local_panel.SetSizer(local_row)
        outer.Add(self._local_panel, 0, wx.EXPAND | wx.ALL, 10)

        # ── FTP section ────────────────────────────────────────────────────
        self._ftp_panel = wx.Panel(panel)
        ftp_outer = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(rows=5, cols=2, vgap=6, hgap=8)
        grid.AddGrowableCol(1, 1)

        def _fld(lbl_key, ctrl):
            lbl = wx.StaticText(self._ftp_panel, label=t(lbl_key))
            grid.Add(lbl,  0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(ctrl, 1, wx.EXPAND)

        self._ftp_host = wx.TextCtrl(self._ftp_panel)
        self._ftp_port = wx.TextCtrl(self._ftp_panel, value="21", size=(70, -1))
        self._ftp_user = wx.TextCtrl(self._ftp_panel)
        self._ftp_pass = wx.TextCtrl(self._ftp_panel, style=wx.TE_PASSWORD)
        self._ftp_path = wx.TextCtrl(self._ftp_panel, value="/")
        _fld("backup.ftp_host",     self._ftp_host)
        _fld("backup.ftp_port",     self._ftp_port)
        _fld("backup.ftp_user",     self._ftp_user)
        _fld("backup.ftp_password", self._ftp_pass)
        _fld("backup.ftp_path",     self._ftp_path)
        ftp_outer.Add(grid, 0, wx.EXPAND)

        self._ftp_tls      = wx.CheckBox(self._ftp_panel, label=t("backup.ftp_tls"))
        self._ftp_remember = wx.CheckBox(self._ftp_panel, label=t("backup.ftp_remember"))
        pass_note = wx.StaticText(self._ftp_panel, label=t("backup.ftp_pass_note"))
        pass_note.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        note_font = pass_note.GetFont()
        note_font.SetPointSize(note_font.GetPointSize() - 1)
        pass_note.SetFont(note_font)
        pass_note.Wrap(400)

        ftp_outer.Add(self._ftp_tls,      0, wx.TOP, 8)
        ftp_outer.Add(self._ftp_remember, 0, wx.TOP, 4)
        ftp_outer.Add(pass_note,          0, wx.TOP, 4)
        self._ftp_panel.SetSizer(ftp_outer)
        outer.Add(self._ftp_panel, 0, wx.EXPAND | wx.ALL, 10)
        self._ftp_panel.Hide()

        outer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        self._backup_btn = wx.Button(panel, wx.ID_OK, label=t("backup.btn_backup"))
        self._backup_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(self._backup_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        outer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(outer)

        self._local_radio.Bind(wx.EVT_RADIOBUTTON, self._on_mode)
        self._ftp_radio.Bind(wx.EVT_RADIOBUTTON, self._on_mode)
        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        self.Bind(wx.EVT_BUTTON, self._on_backup, id=wx.ID_OK)

    # ------------------------------------------------------------------

    def _on_mode(self, _event):
        ftp = self._ftp_radio.GetValue()
        self._local_panel.Show(not ftp)
        self._ftp_panel.Show(ftp)
        self.Layout()
        self.Fit()

    def _on_browse(self, _event):
        dlg = wx.DirDialog(
            self,
            t("backup.local_browse_title"),
            defaultPath=self._local_path.GetValue(),
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            self._local_path.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _load_saved_ftp(self):
        self._ftp_host.SetValue(settings.get("backup_ftp_host"))
        self._ftp_port.SetValue(settings.get("backup_ftp_port", "21"))
        self._ftp_user.SetValue(settings.get("backup_ftp_user"))
        self._ftp_pass.SetValue(settings.get("backup_ftp_password"))
        self._ftp_path.SetValue(settings.get("backup_ftp_path", "/"))
        self._ftp_tls.SetValue(settings.get("backup_ftp_tls", "0") == "1")
        self._ftp_remember.SetValue(settings.get("backup_ftp_remember", "0") == "1")

    # ------------------------------------------------------------------

    def _make_zip(self) -> "Optional[Path]":
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        tmp = Path(tempfile.gettempdir()) / f"PersonalJournal_backup_{ts}.zip"
        try:
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
                if database.DB_PATH.exists():
                    zf.write(database.DB_PATH, "journal.db")
                cfg = settings.get_path()
                if cfg.exists():
                    zf.write(cfg, "settings.ini")
        except Exception as exc:
            wx.MessageBox(
                t("backup.err_write", error=str(exc)),
                t("backup.err_title"),
                wx.OK | wx.ICON_ERROR,
                self,
            )
            return None
        return tmp

    def _on_backup(self, _event):
        if self._ftp_radio.GetValue():
            self._do_ftp()
        else:
            self._do_local()

    def _do_local(self):
        folder = self._local_path.GetValue().strip()
        if not folder:
            wx.MessageBox(t("backup.err_no_output"), t("backup.err_title"),
                          wx.OK | wx.ICON_ERROR, self)
            self._local_path.SetFocus()
            return

        tmp = self._make_zip()
        if tmp is None:
            return

        dest = Path(folder) / tmp.name
        try:
            shutil.move(str(tmp), str(dest))
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            wx.MessageBox(t("backup.err_write", error=str(exc)),
                          t("backup.err_title"), wx.OK | wx.ICON_ERROR, self)
            return

        wx.MessageBox(
            t("backup.success_local", path=str(dest)).replace("\\n", "\n"),
            t("backup.success_title"),
            wx.OK | wx.ICON_INFORMATION,
            self,
        )
        self.EndModal(wx.ID_OK)

    def _do_ftp(self):
        host    = self._ftp_host.GetValue().strip()
        user    = self._ftp_user.GetValue().strip()
        passwd  = self._ftp_pass.GetValue()
        rpath   = self._ftp_path.GetValue().strip() or "/"
        use_tls = self._ftp_tls.GetValue()

        try:
            port = int(self._ftp_port.GetValue().strip())
        except ValueError:
            port = 21

        if not host:
            wx.MessageBox(t("backup.err_no_host"), t("backup.err_title"),
                          wx.OK | wx.ICON_ERROR, self)
            self._ftp_host.SetFocus()
            return
        if not user:
            wx.MessageBox(t("backup.err_no_user"), t("backup.err_title"),
                          wx.OK | wx.ICON_ERROR, self)
            self._ftp_user.SetFocus()
            return

        if self._ftp_remember.GetValue():
            settings.set("backup_ftp_host",     host)
            settings.set("backup_ftp_port",     str(port))
            settings.set("backup_ftp_user",     user)
            settings.set("backup_ftp_password", passwd)
            settings.set("backup_ftp_path",     rpath)
            settings.set("backup_ftp_tls",      "1" if use_tls else "0")
            settings.set("backup_ftp_remember", "1")
        else:
            settings.set("backup_ftp_remember", "0")

        tmp = self._make_zip()
        if tmp is None:
            return

        upload_error: Optional[Exception] = None
        wx.BeginBusyCursor()
        try:
            cls = FTP_TLS if use_tls else FTP
            with cls() as ftp:
                ftp.connect(host, port, timeout=30)
                ftp.login(user, passwd)
                if use_tls:
                    ftp.prot_p()
                if rpath and rpath != "/":
                    ftp.cwd(rpath)
                with open(tmp, "rb") as fh:
                    ftp.storbinary(f"STOR {tmp.name}", fh)
        except Exception as exc:
            upload_error = exc
        finally:
            wx.EndBusyCursor()
            tmp.unlink(missing_ok=True)

        if upload_error:
            wx.MessageBox(t("backup.err_ftp", error=str(upload_error)),
                          t("backup.err_title"), wx.OK | wx.ICON_ERROR, self)
            return

        wx.MessageBox(
            t("backup.success_ftp", host=host, path=rpath),
            t("backup.success_title"),
            wx.OK | wx.ICON_INFORMATION,
            self,
        )
        self.EndModal(wx.ID_OK)


class PasswordDialog(wx.Dialog):
    """Shown on every launch after the first to unlock the journal."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=t("unlock.title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP,
        )
        self._build_ui()
        self.SetSize((340, 180))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(panel, label=t("unlock.prompt"))
        lbl.Wrap(300)
        sizer.Add(lbl, 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(rows=1, cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)

        lbl_pw = wx.StaticText(panel, label=t("unlock.label_password"))
        self._pw = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self._pw.SetName(t("unlock.accessible_password"))
        self._pw.SetToolTip(t("unlock.tooltip_password"))

        grid.Add(lbl_pw, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._pw, 1, wx.EXPAND)
        sizer.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label=t("unlock.btn_unlock"))
        ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, label=t("unlock.btn_exit"))
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(sizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._pw.Bind(wx.EVT_KEY_DOWN, self._on_key)

    def _on_key(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN:
            self._on_ok(None)
        else:
            event.Skip()

    def _on_ok(self, event):
        if not self._pw.GetValue():
            wx.MessageBox(
                t("unlock.err_enter_password"),
                t("unlock.err_required_title"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            self._pw.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def get_password(self) -> str:
        return self._pw.GetValue()


class NewNoteDialog(wx.Dialog):
    """Dialog to create a new journal note."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=t("note.title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._build_ui()
        self.SetSize((480, 380))
        self.SetMinSize((360, 300))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        today_str = format_date(datetime.today(), "%A, %B %d, %Y")
        date_lbl = wx.StaticText(panel, label=t("note.label_date", date=today_str))
        sizer.Add(date_lbl, 0, wx.ALL, 10)

        lbl_subject = wx.StaticText(panel, label=t("note.label_subject"))
        sizer.Add(lbl_subject, 0, wx.LEFT | wx.RIGHT, 10)
        self._subject = wx.TextCtrl(panel)
        self._subject.SetName(t("note.accessible_subject"))
        self._subject.SetToolTip(t("note.tooltip_subject"))
        sizer.Add(self._subject, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        lbl_content = wx.StaticText(panel, label=t("note.label_note"))
        sizer.Add(lbl_content, 0, wx.LEFT | wx.RIGHT, 10)
        self._content = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self._content.SetName(t("note.accessible_note"))
        self._content.SetToolTip(t("note.tooltip_note"))
        sizer.Add(self._content, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label=t("note.btn_save"))
        ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(sizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._subject.SetFocus()

    def _on_ok(self, event):
        if not self._subject.GetValue().strip():
            wx.MessageBox(
                t("note.err_enter_subject"),
                t("note.err_required_title"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            self._subject.SetFocus()
            return
        if not self._content.GetValue().strip():
            wx.MessageBox(
                t("note.err_enter_content"),
                t("note.err_required_title"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            self._content.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def get_subject(self) -> str:
        return self._subject.GetValue().strip()

    def get_content(self) -> str:
        return self._content.GetValue().strip()


class EditNoteDialog(wx.Dialog):
    """Pre-populated dialog for editing an existing journal note."""

    def __init__(self, parent, note: dict):
        super().__init__(
            parent,
            title=t("note.edit_title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._note = note
        self._build_ui()
        self.SetSize((480, 380))
        self.SetMinSize((360, 300))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        try:
            dt = datetime.strptime(self._note["note_date"], "%Y-%m-%d")
            date_str = format_date(dt, "%A, %B %d, %Y")
        except ValueError:
            date_str = self._note["note_date"]
        date_lbl = wx.StaticText(panel, label=t("note.label_date", date=date_str))
        sizer.Add(date_lbl, 0, wx.ALL, 10)

        lbl_subject = wx.StaticText(panel, label=t("note.label_subject"))
        sizer.Add(lbl_subject, 0, wx.LEFT | wx.RIGHT, 10)
        self._subject = wx.TextCtrl(panel, value=self._note["subject"])
        self._subject.SetName(t("note.accessible_subject"))
        self._subject.SetToolTip(t("note.tooltip_subject"))
        sizer.Add(self._subject, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        lbl_content = wx.StaticText(panel, label=t("note.label_note"))
        sizer.Add(lbl_content, 0, wx.LEFT | wx.RIGHT, 10)
        self._content = wx.TextCtrl(
            panel, value=self._note["content"], style=wx.TE_MULTILINE | wx.TE_RICH2
        )
        self._content.SetName(t("note.accessible_note"))
        self._content.SetToolTip(t("note.tooltip_note"))
        sizer.Add(self._content, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label=t("note.edit_btn_save"))
        ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(sizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._subject.SetFocus()
        self._subject.SelectAll()

    def _on_ok(self, event):
        if not self._subject.GetValue().strip():
            wx.MessageBox(
                t("note.err_enter_subject"),
                t("note.err_required_title"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            self._subject.SetFocus()
            return
        if not self._content.GetValue().strip():
            wx.MessageBox(
                t("note.err_enter_content"),
                t("note.err_required_title"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            self._content.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def get_subject(self) -> str:
        return self._subject.GetValue().strip()

    def get_content(self) -> str:
        return self._content.GetValue().strip()


# ---------------------------------------------------------------------------
# Alarm dialogs
# ---------------------------------------------------------------------------

def _wx_date_to_py(wx_dt: wx.DateTime) -> datetime:
    """Convert wx.DateTime to Python datetime (wx months are 0-based)."""
    return datetime(wx_dt.GetYear(), wx_dt.GetMonth() + 1, wx_dt.GetDay())


def _py_to_wx_date(py_dt: datetime) -> wx.DateTime:
    wx_dt = wx.DateTime()
    wx_dt.Set(py_dt.day, py_dt.month - 1, py_dt.year)
    return wx_dt


def _setup_cal_accessibility(cal: wx.adv.CalendarCtrl) -> None:
    """Attach screen-reader announcements and Tab navigation to a CalendarCtrl."""

    def _announce() -> None:
        py_dt = _wx_date_to_py(cal.GetDate())
        _speak(format_date(py_dt, "%A, %B %d, %Y"))

    def _on_key_down(event: wx.KeyEvent) -> None:
        key = event.GetKeyCode()
        if key == wx.WXK_TAB:
            # Navigate to next/previous control; CalendarCtrl swallows Tab itself.
            cal.Navigate(0 if event.ShiftDown() else wx.NavigationKeyEvent.IsForward)
            return  # consume — do not skip
        event.Skip()
        # Announce after the control has processed the navigation key.
        if key in (wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_UP, wx.WXK_DOWN,
                   wx.WXK_PAGEUP, wx.WXK_PAGEDOWN):
            wx.CallAfter(_announce)

    cal.Bind(wx.EVT_KEY_DOWN, _on_key_down)
    cal.Bind(wx.EVT_SET_FOCUS, lambda e: (e.Skip(), _announce()))
    cal.Bind(wx.adv.EVT_CALENDAR_SEL_CHANGED, lambda e: (e.Skip(), _announce()))


class NewAlarmDialog(wx.Dialog):
    """Dialog to create a new alarm."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=t("alarm.new_title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._build_ui()
        self.SetSize((440, 540))
        self.SetMinSize((360, 460))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl_subject = wx.StaticText(panel, label=t("alarm.label_subject"))
        sizer.Add(lbl_subject, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._subject = wx.TextCtrl(panel)
        self._subject.SetName(t("alarm.accessible_subject"))
        self._subject.SetToolTip(t("alarm.tooltip_subject"))
        sizer.Add(self._subject, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        lbl_note = wx.StaticText(panel, label=t("alarm.label_note"))
        sizer.Add(lbl_note, 0, wx.LEFT | wx.RIGHT, 10)
        self._note = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self._note.SetName(t("alarm.accessible_note"))
        self._note.SetToolTip(t("alarm.tooltip_note"))
        sizer.Add(self._note, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        lbl_dt = wx.StaticText(panel, label=t("alarm.label_datetime"))
        sizer.Add(lbl_dt, 0, wx.LEFT | wx.RIGHT, 10)

        now = datetime.now()
        self._cal = wx.adv.CalendarCtrl(
            panel,
            date=_py_to_wx_date(now),
            style=wx.adv.CAL_MONDAY_FIRST,
        )
        self._cal.SetName(t("alarm.accessible_date"))
        _setup_cal_accessibility(self._cal)
        sizer.Add(self._cal, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        time_row = wx.BoxSizer(wx.HORIZONTAL)
        hour_lbl = wx.StaticText(panel, label=t("alarm.accessible_hour"))
        hour_lbl.Show(False)
        self._hour_spin = wx.SpinCtrl(panel, min=0, max=23, initial=now.hour)
        self._hour_spin.SetName(t("alarm.accessible_hour"))
        colon_lbl = wx.StaticText(panel, label=":")
        minute_lbl = wx.StaticText(panel, label=t("alarm.accessible_minute"))
        minute_lbl.Show(False)
        self._minute_spin = wx.SpinCtrl(panel, min=0, max=59, initial=now.minute)
        self._minute_spin.SetName(t("alarm.accessible_minute"))
        time_row.Add(hour_lbl, 0)
        time_row.Add(self._hour_spin, 0, wx.RIGHT, 4)
        time_row.Add(colon_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        time_row.Add(minute_lbl, 0)
        time_row.Add(self._minute_spin, 0)
        sizer.Add(time_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label=t("alarm.btn_save"))
        ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(sizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._subject.SetFocus()

    def _parse_alarm_dt(self) -> datetime:
        d = _wx_date_to_py(self._cal.GetDate())
        return datetime(d.year, d.month, d.day, self._hour_spin.GetValue(), self._minute_spin.GetValue(), 0)

    def _on_ok(self, event):
        if not self._subject.GetValue().strip():
            wx.MessageBox(
                t("alarm.err_enter_subject"),
                t("alarm.err_required_title"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            self._subject.SetFocus()
            return
        if self._parse_alarm_dt() <= datetime.now():
            wx.MessageBox(
                t("alarm.err_past_datetime"),
                t("alarm.err_required_title"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            return
        self.EndModal(wx.ID_OK)

    def get_subject(self) -> str:
        return self._subject.GetValue().strip()

    def get_note(self) -> str:
        return self._note.GetValue().strip()

    def get_alarm_dt(self) -> str:
        return self._parse_alarm_dt().strftime("%Y-%m-%d %H:%M:%S")


class EditAlarmDialog(wx.Dialog):
    """Pre-populated dialog for editing an existing alarm."""

    def __init__(self, parent, alarm: dict):
        super().__init__(
            parent,
            title=t("alarm.edit_title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._alarm = alarm
        self._build_ui()
        self.SetSize((440, 540))
        self.SetMinSize((360, 460))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl_subject = wx.StaticText(panel, label=t("alarm.label_subject"))
        sizer.Add(lbl_subject, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._subject = wx.TextCtrl(panel, value=self._alarm["subject"])
        self._subject.SetName(t("alarm.accessible_subject"))
        self._subject.SetToolTip(t("alarm.tooltip_subject"))
        sizer.Add(self._subject, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        lbl_note = wx.StaticText(panel, label=t("alarm.label_note"))
        sizer.Add(lbl_note, 0, wx.LEFT | wx.RIGHT, 10)
        self._note = wx.TextCtrl(
            panel, value=self._alarm["note"], style=wx.TE_MULTILINE | wx.TE_RICH2
        )
        self._note.SetName(t("alarm.accessible_note"))
        self._note.SetToolTip(t("alarm.tooltip_note"))
        sizer.Add(self._note, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        lbl_dt = wx.StaticText(panel, label=t("alarm.label_datetime"))
        sizer.Add(lbl_dt, 0, wx.LEFT | wx.RIGHT, 10)

        try:
            py_dt = datetime.strptime(self._alarm["alarm_dt"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            py_dt = datetime.now()

        self._cal = wx.adv.CalendarCtrl(
            panel,
            date=_py_to_wx_date(py_dt),
            style=wx.adv.CAL_MONDAY_FIRST,
        )
        self._cal.SetName(t("alarm.accessible_date"))
        _setup_cal_accessibility(self._cal)
        sizer.Add(self._cal, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        time_row = wx.BoxSizer(wx.HORIZONTAL)
        hour_lbl = wx.StaticText(panel, label=t("alarm.accessible_hour"))
        hour_lbl.Show(False)
        self._hour_spin = wx.SpinCtrl(panel, min=0, max=23, initial=py_dt.hour)
        self._hour_spin.SetName(t("alarm.accessible_hour"))
        colon_lbl = wx.StaticText(panel, label=":")
        minute_lbl = wx.StaticText(panel, label=t("alarm.accessible_minute"))
        minute_lbl.Show(False)
        self._minute_spin = wx.SpinCtrl(panel, min=0, max=59, initial=py_dt.minute)
        self._minute_spin.SetName(t("alarm.accessible_minute"))
        time_row.Add(hour_lbl, 0)
        time_row.Add(self._hour_spin, 0, wx.RIGHT, 4)
        time_row.Add(colon_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        time_row.Add(minute_lbl, 0)
        time_row.Add(self._minute_spin, 0)
        sizer.Add(time_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label=t("alarm.edit_btn_save"))
        ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(sizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._subject.SetFocus()
        self._subject.SelectAll()

    def _parse_alarm_dt(self) -> datetime:
        d = _wx_date_to_py(self._cal.GetDate())
        return datetime(d.year, d.month, d.day, self._hour_spin.GetValue(), self._minute_spin.GetValue(), 0)

    def _on_ok(self, event):
        if not self._subject.GetValue().strip():
            wx.MessageBox(
                t("alarm.err_enter_subject"),
                t("alarm.err_required_title"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            self._subject.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def get_subject(self) -> str:
        return self._subject.GetValue().strip()

    def get_note(self) -> str:
        return self._note.GetValue().strip()

    def get_alarm_dt(self) -> str:
        return self._parse_alarm_dt().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Missed alarms notification
# ---------------------------------------------------------------------------

class MissedAlarmsDialog(wx.Dialog):
    """Shown at startup when alarms fired while the app was closed."""

    RESULT_DISMISS = "dismiss"
    RESULT_SNOOZE  = "snooze"

    def __init__(self, parent, alarms: list[dict]):
        super().__init__(
            parent,
            title=t("alarm.missed_title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP,
        )
        self._result = self.RESULT_DISMISS
        self._build_ui(alarms)
        self.SetSize((480, 320))
        self.SetMinSize((380, 240))
        self.Centre()

    def _build_ui(self, alarms: list[dict]):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        n = len(alarms)
        msg_lbl = wx.StaticText(panel, label=t("alarm.missed_msg", n=n))
        sizer.Add(msg_lbl, 0, wx.ALL, 10)

        list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN)
        list_ctrl.SetName(t("alarm.missed_list_name"))
        list_ctrl.InsertColumn(0, t("alarm.missed_col_time"),    width=160)
        list_ctrl.InsertColumn(1, t("alarm.missed_col_subject"), width=260)
        for a in alarms:
            try:
                dt = datetime.strptime(a["alarm_dt"], "%Y-%m-%d %H:%M:%S")
                time_str = format_date(dt, "%A, %B %d, %Y %H:%M")
            except ValueError:
                time_str = a["alarm_dt"][:16]
            idx = list_ctrl.InsertItem(list_ctrl.GetItemCount(), time_str)
            list_ctrl.SetItem(idx, 1, a["subject"])
        sizer.Add(list_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        snooze_btn  = wx.Button(panel, label=t("alarm.missed_snooze"))
        dismiss_btn = wx.Button(panel, label=t("alarm.missed_dismiss"))
        btn_row.Add(snooze_btn,  0, wx.RIGHT, 8)
        btn_row.Add(dismiss_btn, 0)
        sizer.Add(btn_row, 0, wx.ALIGN_CENTER | wx.BOTTOM, 12)

        panel.SetSizer(sizer)
        snooze_btn.Bind(wx.EVT_BUTTON,  lambda e: self._close(self.RESULT_SNOOZE))
        dismiss_btn.Bind(wx.EVT_BUTTON, lambda e: self._close(self.RESULT_DISMISS))
        self.Bind(wx.EVT_CHAR_HOOK, lambda e: self._close(self.RESULT_DISMISS)
                  if e.GetKeyCode() == wx.WXK_ESCAPE else e.Skip())
        dismiss_btn.SetDefault()
        dismiss_btn.SetFocus()

    def _close(self, result: str):
        self._result = result
        self.EndModal(wx.ID_OK)

    def get_result(self) -> str:
        return self._result


class AlarmFiredDialog(wx.Dialog):
    """Shown when an alarm time is reached. Offers Snooze or Stop."""

    RESULT_SNOOZE = "snooze"
    RESULT_STOP   = "stop"

    def __init__(self, parent, alarm: dict, locked: bool = False):
        super().__init__(
            parent,
            title=t("alarm.fired_title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP,
        )
        self._result = self.RESULT_STOP
        self._build_ui(alarm, locked)
        self.SetSize((420, 280))
        self.Centre()

    def _build_ui(self, alarm: dict, locked: bool):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        if locked:
            msg_lbl = wx.StaticText(panel, label=t("alarm.fired_locked_msg"))
            font = msg_lbl.GetFont()
            font.SetPointSize(font.GetPointSize() + 2)
            msg_lbl.SetFont(font)
            sizer.Add(msg_lbl, 1, wx.ALIGN_CENTER | wx.ALL, 16)
        else:
            subject_lbl = wx.StaticText(panel, label=alarm["subject"])
            font = subject_lbl.GetFont()
            font.SetPointSize(font.GetPointSize() + 3)
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            subject_lbl.SetFont(font)
            sizer.Add(subject_lbl, 0, wx.ALL, 12)

            if alarm["note"].strip():
                note_ctrl = wx.TextCtrl(
                    panel,
                    value=alarm["note"],
                    style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.BORDER_SUNKEN,
                )
                note_ctrl.SetName(t("alarm.accessible_note"))
                sizer.Add(note_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        snooze_btn = wx.Button(panel, label=t("alarm.btn_snooze"))
        snooze_btn.SetToolTip("Ctrl+Alt+F1")
        stop_btn = wx.Button(panel, label=t("alarm.btn_stop"))
        stop_btn.SetToolTip("Ctrl+Alt+F2")
        btn_row.Add(snooze_btn, 0, wx.RIGHT, 8)
        btn_row.Add(stop_btn, 0)
        sizer.Add(btn_row, 0, wx.ALIGN_CENTER | wx.BOTTOM, 14)

        panel.SetSizer(sizer)
        snooze_btn.Bind(wx.EVT_BUTTON, lambda e: self.do_snooze())
        stop_btn.Bind(wx.EVT_BUTTON, lambda e: self.do_stop())
        stop_btn.SetDefault()
        stop_btn.SetFocus()

    def do_snooze(self):
        self._result = self.RESULT_SNOOZE
        self.EndModal(wx.ID_OK)

    def do_stop(self):
        self._result = self.RESULT_STOP
        self.EndModal(wx.ID_OK)

    def get_result(self) -> str:
        return self._result


# ---------------------------------------------------------------------------
# Search dialog
# ---------------------------------------------------------------------------

class SearchDialog(wx.Dialog):
    """Combined search-input and results dialog."""

    RESULT_GOTO_DIARY = 9001  # custom EndModal code

    def __init__(self, parent, fernet):
        super().__init__(
            parent,
            title=t("search.title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._fernet = fernet
        self._results: list[dict] = []
        self._goto_diary_date: str | None = None
        self._goto_diary_id: Optional[int] = None
        self._search_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda e: self._run_search(), self._search_timer)
        self.SetEscapeId(wx.ID_CLOSE)
        self._build_ui()
        self.SetSize((740, 520))
        self.SetMinSize((500, 360))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # ── Query row ─────────────────────────────────────────────────
        query_row = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(panel, label=t("search.label_query"))
        self._query_ctrl = wx.TextCtrl(panel)
        self._query_ctrl.SetName(t("search.accessible_query"))
        self._query_ctrl.SetToolTip(t("search.tooltip_query"))
        query_row.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        query_row.Add(self._query_ctrl, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(query_row, 0, wx.EXPAND | wx.ALL, 10)

        # ── Status label ──────────────────────────────────────────────
        self._status_lbl = wx.StaticText(panel, label="")
        sizer.Add(self._status_lbl, 0, wx.LEFT | wx.BOTTOM, 10)

        # ── Results list ──────────────────────────────────────────────
        self._list = wx.ListCtrl(
            panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
        )
        self._list.SetName(t("search.accessible_results"))
        self._list.InsertColumn(0, t("search.col_type"),    width=80)
        self._list.InsertColumn(1, t("search.col_title"),   width=200)
        self._list.InsertColumn(2, t("search.col_preview"), width=280)
        self._list.InsertColumn(3, t("search.col_date"),    width=140)
        sizer.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # ── Close button ──────────────────────────────────────────────
        btn_sizer = wx.StdDialogButtonSizer()
        close_btn = wx.Button(panel, wx.ID_CLOSE)
        btn_sizer.AddButton(close_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(sizer)

        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE))
        self._query_ctrl.Bind(wx.EVT_TEXT, self._on_query_text)
        self._list.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_item_activated)
        self._query_ctrl.SetFocus()

    # ------------------------------------------------------------------
    # Search logic
    # ------------------------------------------------------------------

    def _on_query_text(self, event):
        self._search_timer.StartOnce(300)

    def _run_search(self):
        query = self._query_ctrl.GetValue().strip()
        self._list.DeleteAllItems()
        if not query:
            self._status_lbl.SetLabel("")
            self._results = []
            self.Layout()
            return
        self._results = database.search_all(query, self._fernet)
        for idx, r in enumerate(self._results):
            type_label = t(f"search.type_{r['type']}")
            if r["type"] == "note":
                title    = r["subject"]
                preview  = r["content"].replace("\n", " ")[:80]
                date_str = r["note_date"]
            elif r["type"] == "alarm":
                title    = r["subject"]
                preview  = r.get("note", "").replace("\n", " ")[:80]
                date_str = r["alarm_dt"][:16]   # "YYYY-MM-DD HH:MM"
            else:  # diary
                title    = r["entry_date"]
                preview  = r["content"].replace("\n", " ")[:80]
                date_str = r["entry_date"]
            self._list.InsertItem(idx, type_label)
            self._list.SetItem(idx, 1, title)
            self._list.SetItem(idx, 2, preview)
            self._list.SetItem(idx, 3, date_str)
        if self._results:
            self._status_lbl.SetLabel(
                t("search.results_count", n=len(self._results))
            )
        else:
            self._status_lbl.SetLabel(t("search.no_results", query=query))
        self.Layout()

    # ------------------------------------------------------------------
    # Context menu / keyboard / activation
    # ------------------------------------------------------------------

    def _on_context_menu(self, event):
        idx = self._list.GetFirstSelected()
        if idx < 0:
            return
        result = self._results[idx]
        pos = event.GetPosition()
        if pos == wx.DefaultPosition:
            rect = self._list.GetItemRect(idx)
            pos = self._list.ClientToScreen(
                wx.Point(rect.x + 4, rect.y + rect.height)
            )
        menu = wx.Menu()
        if result["type"] == "note":
            edit_item = menu.Append(wx.ID_ANY, t("note.ctx_edit") + "\tCtrl+E")
            del_item  = menu.Append(wx.ID_ANY, t("note.ctx_delete") + "\tDel")
            menu.Bind(wx.EVT_MENU, lambda e: self._edit_note(result),   edit_item)
            menu.Bind(wx.EVT_MENU, lambda e: self._delete_note(result), del_item)
        elif result["type"] == "alarm":
            edit_item = menu.Append(wx.ID_ANY, t("alarm.ctx_edit") + "\tCtrl+E")
            del_item  = menu.Append(wx.ID_ANY, t("alarm.ctx_delete") + "\tDel")
            menu.Bind(wx.EVT_MENU, lambda e: self._edit_alarm(result),   edit_item)
            menu.Bind(wx.EVT_MENU, lambda e: self._delete_alarm(result), del_item)
        else:  # diary
            goto_item = menu.Append(wx.ID_ANY, t("search.ctx_goto_diary"))
            menu.Bind(wx.EVT_MENU, lambda e: self._goto_diary(result), goto_item)
        self._list.PopupMenu(menu, self._list.ScreenToClient(pos))
        menu.Destroy()

    def _on_list_key(self, event):
        key = event.GetKeyCode()
        idx = self._list.GetFirstSelected()
        if idx < 0:
            event.Skip()
            return
        result = self._results[idx]
        if key == wx.WXK_DELETE:
            if result["type"] == "note":
                self._delete_note(result)
            elif result["type"] == "alarm":
                self._delete_alarm(result)
            else:
                event.Skip()
        elif key == ord("E") and event.ControlDown():
            if result["type"] == "note":
                self._edit_note(result)
            elif result["type"] == "alarm":
                self._edit_alarm(result)
            else:
                event.Skip()
        else:
            event.Skip()

    def _on_item_activated(self, event):
        idx = event.GetIndex()
        if idx < 0:
            return
        result = self._results[idx]
        if result["type"] == "note":
            self._edit_note(result)
        elif result["type"] == "alarm":
            self._edit_alarm(result)
        else:
            self._goto_diary(result)

    # ------------------------------------------------------------------
    # Per-type actions
    # ------------------------------------------------------------------

    def _edit_note(self, result: dict):
        dlg = EditNoteDialog(self, result)
        if dlg.ShowModal() == wx.ID_OK:
            database.update_note(
                result["id"], dlg.get_subject(), dlg.get_content(), self._fernet
            )
            self._run_search()
        dlg.Destroy()

    def _delete_note(self, result: dict):
        dlg = wx.MessageDialog(
            self,
            t("note.delete_confirm_msg", subject=result["subject"]),
            t("note.delete_confirm_title"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if dlg.ShowModal() == wx.ID_YES:
            database.delete_note(result["id"])
            self._run_search()
        dlg.Destroy()

    def _edit_alarm(self, result: dict):
        dlg = EditAlarmDialog(self, result)
        if dlg.ShowModal() == wx.ID_OK:
            database.update_alarm(
                result["id"],
                dlg.get_subject(), dlg.get_note(), dlg.get_alarm_dt(),
                self._fernet,
            )
            self._run_search()
        dlg.Destroy()

    def _delete_alarm(self, result: dict):
        dlg = wx.MessageDialog(
            self,
            t("alarm.delete_confirm_msg", subject=result["subject"]),
            t("alarm.delete_confirm_title"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if dlg.ShowModal() == wx.ID_YES:
            database.delete_alarm(result["id"])
            self._run_search()
        dlg.Destroy()

    def _goto_diary(self, result: dict):
        self._goto_diary_date = result["entry_date"]
        self._goto_diary_id = result.get("diary_id")
        self.EndModal(self.RESULT_GOTO_DIARY)

    def get_goto_diary_date(self) -> str | None:
        return self._goto_diary_date

    def get_goto_diary_id(self) -> Optional[int]:
        return self._goto_diary_id


# ---------------------------------------------------------------------------
# Diary go-to-date dialog
# ---------------------------------------------------------------------------

class DiaryGoToDateDialog(wx.Dialog):
    """Calendar picker to navigate to any past (or today's) diary date."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=t("diary.goto_title"),
            style=wx.DEFAULT_DIALOG_STYLE,
        )
        self._date: Optional[date] = None
        self._build_ui()
        self.SetSize((320, 340))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(panel, label=t("diary.goto_label"))
        sizer.Add(lbl, 0, wx.ALL, 10)

        today = datetime.today()
        self._cal = wx.adv.CalendarCtrl(
            panel,
            date=_py_to_wx_date(today),
            style=wx.adv.CAL_MONDAY_FIRST,
        )
        self._cal.SetName(t("diary.goto_accessible_cal"))
        _setup_cal_accessibility(self._cal)
        sizer.Add(self._cal, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label=t("diary.goto_btn_go"))
        ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(sizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._cal.SetFocus()

    def _on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN:
            self._on_ok(None)
        else:
            event.Skip()

    def _on_ok(self, event):
        selected = _wx_date_to_py(self._cal.GetDate()).date()
        if selected > date.today():
            wx.MessageBox(
                t("diary.goto_err_future"),
                t("diary.goto_err_title"),
                wx.OK | wx.ICON_WARNING, self,
            )
            return
        self._date = selected
        self.EndModal(wx.ID_OK)

    def get_date(self) -> Optional[date]:
        return self._date


# ---------------------------------------------------------------------------
# Diary management dialogs
# ---------------------------------------------------------------------------

class _DiaryNameDialog(wx.Dialog):
    """Small modal dialog to enter or edit a diary name."""

    def __init__(self, parent, title: str, label: str, initial: str = ""):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)
        self._name = ""
        self._label = label
        self._initial = initial
        self._build_ui()
        self.SetSize((340, 150))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(panel, label=self._label)
        sizer.Add(lbl, 0, wx.LEFT | wx.TOP | wx.RIGHT, 10)
        self._ctrl = wx.TextCtrl(panel, value=self._initial)
        self._ctrl.SetName(self._label)
        sizer.Add(self._ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(sizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._ctrl.SetFocus()
        self._ctrl.SelectAll()

    def _on_ok(self, event):
        val = self._ctrl.GetValue().strip()
        if not val:
            wx.MessageBox(
                t("diary.err_empty_name"),
                t("diary.err_name_title"),
                wx.OK | wx.ICON_WARNING, self,
            )
            self._ctrl.SetFocus()
            return
        self._name = val
        self.EndModal(wx.ID_OK)

    def get_name(self) -> str:
        return self._name


class ManageDiariesDialog(wx.Dialog):
    """Dialog to create, rename and delete named diaries."""

    def __init__(self, parent, fernet, diaries: list[dict]):
        super().__init__(
            parent,
            title=t("diary.manage_title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._fernet = fernet
        self._diaries = list(diaries)  # local mutable copy
        self._build_ui()
        self.SetSize((380, 320))
        self.SetMinSize((300, 260))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._listbox = wx.ListBox(panel, style=wx.LB_SINGLE)
        self._listbox.SetName(t("diary.manage_accessible_list"))
        self._populate_list()
        sizer.Add(self._listbox, 1, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_new    = wx.Button(panel, label=t("diary.btn_new_diary"))
        self._btn_rename = wx.Button(panel, label=t("diary.btn_rename_diary"))
        self._btn_delete = wx.Button(panel, label=t("diary.btn_delete_diary"))
        btn_row.Add(self._btn_new,    0, wx.RIGHT, 4)
        btn_row.Add(self._btn_rename, 0, wx.RIGHT, 4)
        btn_row.Add(self._btn_delete, 0)
        sizer.Add(btn_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        close_sizer = wx.StdDialogButtonSizer()
        close_btn = wx.Button(panel, wx.ID_CLOSE)
        close_sizer.AddButton(close_btn)
        close_sizer.Realize()
        sizer.Add(close_sizer, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CLOSE)

        self._btn_new.Bind(wx.EVT_BUTTON, self._on_new)
        self._btn_rename.Bind(wx.EVT_BUTTON, self._on_rename)
        self._btn_delete.Bind(wx.EVT_BUTTON, self._on_delete)
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE))
        self._listbox.Bind(wx.EVT_LISTBOX, self._on_selection_changed)
        self._update_buttons()

    def _populate_list(self, select_id: Optional[int] = None):
        self._listbox.Clear()
        for d in self._diaries:
            self._listbox.Append(d["name"])
        if select_id is not None:
            idx = next((i for i, d in enumerate(self._diaries) if d["id"] == select_id), 0)
        else:
            idx = 0
        if self._diaries:
            self._listbox.SetSelection(idx)

    def _on_selection_changed(self, event):
        self._update_buttons()

    def _update_buttons(self):
        has_sel = self._listbox.GetSelection() != wx.NOT_FOUND
        self._btn_rename.Enable(has_sel)
        self._btn_delete.Enable(has_sel and len(self._diaries) > 1)

    def _on_new(self, event):
        dlg = _DiaryNameDialog(
            self,
            title=t("diary.new_diary_title"),
            label=t("diary.new_diary_label"),
        )
        if dlg.ShowModal() == wx.ID_OK:
            new_id = database.add_diary(dlg.get_name(), self._fernet)
            self._diaries.append({"id": new_id, "name": dlg.get_name()})
            self._populate_list(select_id=new_id)
            self._update_buttons()
        dlg.Destroy()

    def _on_rename(self, event):
        idx = self._listbox.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        diary = self._diaries[idx]
        dlg = _DiaryNameDialog(
            self,
            title=t("diary.rename_diary_title"),
            label=t("diary.rename_diary_label"),
            initial=diary["name"],
        )
        if dlg.ShowModal() == wx.ID_OK:
            database.rename_diary(diary["id"], dlg.get_name(), self._fernet)
            self._diaries[idx]["name"] = dlg.get_name()
            self._populate_list(select_id=diary["id"])
        dlg.Destroy()

    def _on_delete(self, event):
        idx = self._listbox.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        if len(self._diaries) <= 1:
            wx.MessageBox(
                t("diary.delete_confirm_last"),
                t("diary.delete_confirm_title"),
                wx.OK | wx.ICON_WARNING, self,
            )
            return
        diary = self._diaries[idx]
        n = database.count_diary_entries(diary["id"])
        confirm = wx.MessageBox(
            t("diary.delete_confirm_msg", name=diary["name"], n=n),
            t("diary.delete_confirm_title"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, self,
        )
        if confirm == wx.YES:
            database.delete_diary(diary["id"])
            self._diaries.pop(idx)
            self._populate_list()
            self._update_buttons()


# ---------------------------------------------------------------------------
# Export dialog
# ---------------------------------------------------------------------------

class ExportDialog(wx.Dialog):
    """Dialog to export diary entries or notes in various Markdown formats."""

    def __init__(self, parent, fernet, diaries: list[dict] = ()):
        super().__init__(
            parent,
            title=t("export.title"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._fernet = fernet
        self._diaries = list(diaries)
        self._build_ui()
        self.SetSize((540, 560))
        self.SetMinSize((440, 480))
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)

        # ── Source ────────────────────────────────────────────────────
        src_box = wx.StaticBox(panel, label=t("export.source"))
        src_sizer = wx.StaticBoxSizer(src_box, wx.HORIZONTAL)
        self._rb_diary = wx.RadioButton(panel, label=t("export.source_diary"), style=wx.RB_GROUP)
        self._rb_notes = wx.RadioButton(panel, label=t("export.source_notes"))
        self._rb_diary.SetName(t("export.source_diary"))
        self._rb_notes.SetName(t("export.source_notes"))
        src_sizer.Add(self._rb_diary, 0, wx.ALL, 6)
        src_sizer.Add(self._rb_notes, 0, wx.ALL, 6)
        outer.Add(src_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ── Diary selector (shown only when Diary source is selected) ─
        self._diary_sel_panel = wx.Panel(panel)
        ds_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ds_lbl = wx.StaticText(self._diary_sel_panel, label=t("diary.label_selector"))
        diary_choices = [d["name"] for d in self._diaries]
        if len(self._diaries) > 1:
            diary_choices.append(t("export.all_diaries"))
        self._export_diary_choice = wx.Choice(self._diary_sel_panel, choices=diary_choices)
        self._export_diary_choice.SetName(t("diary.accessible_selector"))
        if self._diaries:
            self._export_diary_choice.SetSelection(0)
        ds_sizer.Add(ds_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        ds_sizer.Add(self._export_diary_choice, 1, wx.EXPAND)
        self._diary_sel_panel.SetSizer(ds_sizer)
        outer.Add(self._diary_sel_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # ── Format ────────────────────────────────────────────────────
        fmt_box = wx.StaticBox(panel, label=t("export.format"))
        fmt_sizer = wx.StaticBoxSizer(fmt_box, wx.VERTICAL)
        self._rb_per_entry = wx.RadioButton(panel, label=t("export.fmt_per_entry"), style=wx.RB_GROUP)
        self._rb_per_week  = wx.RadioButton(panel, label=t("export.fmt_per_week"))
        self._rb_per_month = wx.RadioButton(panel, label=t("export.fmt_per_month"))
        self._rb_single_md = wx.RadioButton(panel, label=t("export.fmt_single_md"))
        for rb in (self._rb_per_entry, self._rb_per_week, self._rb_per_month, self._rb_single_md):
            fmt_sizer.Add(rb, 0, wx.LEFT | wx.BOTTOM, 6)
        outer.Add(fmt_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # ── Pelican metadata (hidden when single-markdown is chosen) ──
        self._meta_panel = wx.Panel(panel)
        meta_box = wx.StaticBox(self._meta_panel, label=t("export.metadata"))
        meta_sizer = wx.StaticBoxSizer(meta_box, wx.VERTICAL)
        grid = wx.FlexGridSizer(rows=3, cols=2, vgap=6, hgap=8)
        grid.AddGrowableCol(1, 1)

        lbl_lang   = wx.StaticText(self._meta_panel, label=t("export.meta_lang"))
        self._lang_ctrl = wx.TextCtrl(self._meta_panel, value=i18n.current_code())
        self._lang_ctrl.SetName(t("export.meta_lang"))
        self._lang_ctrl.SetToolTip(t("export.meta_lang_tip"))

        lbl_tags   = wx.StaticText(self._meta_panel, label=t("export.meta_tags"))
        self._tags_ctrl = wx.TextCtrl(self._meta_panel)
        self._tags_ctrl.SetName(t("export.meta_tags"))
        self._tags_ctrl.SetToolTip(t("export.meta_tags_tip"))

        lbl_series = wx.StaticText(self._meta_panel, label=t("export.meta_series"))
        self._series_ctrl = wx.TextCtrl(self._meta_panel)
        self._series_ctrl.SetName(t("export.meta_series"))
        self._series_ctrl.SetToolTip(t("export.meta_series_tip"))

        grid.Add(lbl_lang,          0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._lang_ctrl,   1, wx.EXPAND)
        grid.Add(lbl_tags,          0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._tags_ctrl,   1, wx.EXPAND)
        grid.Add(lbl_series,        0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._series_ctrl, 1, wx.EXPAND)
        meta_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 6)

        meta_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        meta_panel_sizer.Add(meta_sizer, 0, wx.EXPAND)
        self._meta_panel.SetSizer(meta_panel_sizer)
        outer.Add(self._meta_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # ── Custom template ───────────────────────────────────────────
        self._tmpl_panel = wx.Panel(panel)
        tmpl_sizer = wx.BoxSizer(wx.VERTICAL)
        self._tmpl_chk = wx.CheckBox(self._tmpl_panel, label=t("export.template_chk"))
        tmpl_row = wx.BoxSizer(wx.HORIZONTAL)
        self._tmpl_ctrl = wx.TextCtrl(self._tmpl_panel)
        self._tmpl_ctrl.SetToolTip(t("export.template_tip"))
        self._tmpl_browse_btn = wx.Button(self._tmpl_panel, label=t("export.btn_browse"))
        self._tmpl_default_btn = wx.Button(self._tmpl_panel, label=t("export.template_default_btn"))
        tmpl_row.Add(self._tmpl_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        tmpl_row.Add(self._tmpl_browse_btn, 0, wx.RIGHT, 4)
        tmpl_row.Add(self._tmpl_default_btn, 0)
        tmpl_sizer.Add(self._tmpl_chk, 0, wx.BOTTOM, 4)
        tmpl_sizer.Add(tmpl_row, 0, wx.EXPAND)
        self._tmpl_panel.SetSizer(tmpl_sizer)
        outer.Add(self._tmpl_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # ── Output location ───────────────────────────────────────────
        out_row = wx.BoxSizer(wx.HORIZONTAL)
        out_lbl = wx.StaticText(panel, label=t("export.output_label"))
        self._out_ctrl = wx.TextCtrl(panel)
        self._out_ctrl.SetName(t("export.output_label"))
        self._out_ctrl.SetToolTip(t("export.output_tip"))
        self._browse_btn = wx.Button(panel, label=t("export.btn_browse"))
        out_row.Add(out_lbl,          0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        out_row.Add(self._out_ctrl,   1, wx.EXPAND | wx.RIGHT, 6)
        out_row.Add(self._browse_btn, 0)
        outer.Add(out_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # ── Buttons ───────────────────────────────────────────────────
        btn_sizer = wx.StdDialogButtonSizer()
        self._export_btn = wx.Button(panel, wx.ID_OK, label=t("export.btn_export"))
        self._export_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(self._export_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        outer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(outer)

        # Bindings
        self._browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        self._tmpl_browse_btn.Bind(wx.EVT_BUTTON, self._on_browse_template)
        self._tmpl_default_btn.Bind(wx.EVT_BUTTON, self._on_save_default_template)
        self._tmpl_chk.Bind(wx.EVT_CHECKBOX, self._on_template_chk)
        self.Bind(wx.EVT_BUTTON, self._on_export, id=wx.ID_OK)
        for rb in (self._rb_per_entry, self._rb_per_week, self._rb_per_month, self._rb_single_md):
            rb.Bind(wx.EVT_RADIOBUTTON, self._on_format_changed)
        self._rb_diary.Bind(wx.EVT_RADIOBUTTON, self._on_source_changed)
        self._rb_notes.Bind(wx.EVT_RADIOBUTTON, self._on_source_changed)

        self._rb_diary.SetValue(True)
        self._rb_per_entry.SetValue(True)
        self._update_meta_visibility()
        self._update_diary_sel_visibility()
        self._update_template_controls()
        self._rb_diary.SetFocus()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_folder_output(self) -> bool:
        return not self._rb_single_md.GetValue()

    def _on_format_changed(self, event):
        self._update_meta_visibility()
        # Clear output path when switching between folder/file mode.
        self._out_ctrl.SetValue("")

    def _on_source_changed(self, event):
        self._update_diary_sel_visibility()

    def _update_meta_visibility(self):
        show = not self._rb_single_md.GetValue()
        self._meta_panel.Show(show)
        self._tmpl_panel.Show(show)
        self.Layout()

    def _update_diary_sel_visibility(self):
        show = self._rb_diary.GetValue() and len(self._diaries) > 1
        self._diary_sel_panel.Show(show)
        self.Layout()

    def _update_template_controls(self):
        active = self._tmpl_chk.GetValue()
        self._tmpl_ctrl.Enable(active)
        self._tmpl_browse_btn.Enable(active)
        self._tmpl_default_btn.Enable(active)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_template_chk(self, event):
        self._update_template_controls()

    def _on_browse_template(self, event):
        dlg = wx.FileDialog(
            self, t("export.template_browse_title"),
            wildcard="Text files (*.txt;*.md)|*.txt;*.md|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            self._tmpl_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _on_save_default_template(self, event):
        import export as exp
        dlg = wx.FileDialog(
            self, t("export.template_save_title"),
            defaultFile="pelican_default.txt",
            wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if not path.lower().endswith(".txt"):
                path += ".txt"
            try:
                from pathlib import Path
                Path(path).write_text(exp.DEFAULT_TEMPLATE, encoding="utf-8")
                self._tmpl_ctrl.SetValue(path)
            except Exception as exc:
                wx.MessageBox(
                    t("export.err_template_read", error=str(exc)),
                    t("export.err_title"),
                    wx.OK | wx.ICON_ERROR, self,
                )
        dlg.Destroy()

    def _on_browse(self, event):
        if self._is_folder_output():
            dlg = wx.DirDialog(
                self, t("export.browse_folder"),
                style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON,
            )
            if dlg.ShowModal() == wx.ID_OK:
                self._out_ctrl.SetValue(dlg.GetPath())
            dlg.Destroy()
        else:
            dlg = wx.FileDialog(
                self, t("export.browse_file"),
                wildcard="Markdown files (*.md)|*.md|All files (*.*)|*.*",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            )
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                if not path.lower().endswith(".md"):
                    path += ".md"
                self._out_ctrl.SetValue(path)
            dlg.Destroy()

    def _on_export(self, event):
        from pathlib import Path
        import export as exp

        out_str = self._out_ctrl.GetValue().strip()
        if not out_str:
            wx.MessageBox(
                t("export.err_no_output"),
                t("export.err_title"),
                wx.OK | wx.ICON_WARNING, self,
            )
            self._out_ctrl.SetFocus()
            return

        out_path = Path(out_str)
        lang   = self._lang_ctrl.GetValue().strip() or "en"
        tags   = self._tags_ctrl.GetValue().strip()
        series = self._series_ctrl.GetValue().strip()

        # Load custom template if enabled
        template: str | None = None
        if self._tmpl_chk.GetValue() and self._tmpl_panel.IsShown():
            tmpl_path = self._tmpl_ctrl.GetValue().strip()
            if tmpl_path:
                try:
                    template = Path(tmpl_path).read_text(encoding="utf-8")
                except Exception as exc:
                    wx.MessageBox(
                        t("export.err_template_read", error=str(exc)),
                        t("export.err_title"),
                        wx.OK | wx.ICON_ERROR, self,
                    )
                    return

        # Determine which diary to export (None = all diaries)
        diary_idx = self._export_diary_choice.GetSelection()
        if self._diaries and diary_idx == len(self._diaries):
            diary_id = None  # "All diaries" option selected
        elif self._diaries and 0 <= diary_idx < len(self._diaries):
            diary_id = self._diaries[diary_idx]["id"]
        elif self._diaries:
            diary_id = self._diaries[0]["id"]
        else:
            diary_id = 1

        try:
            if self._rb_diary.GetValue():
                if self._rb_per_entry.GetValue():
                    count = exp.export_diary_per_entry(self._fernet, out_path, lang, tags, series, diary_id, template)
                elif self._rb_per_week.GetValue():
                    count = exp.export_diary_per_week(self._fernet, out_path, lang, tags, series, diary_id, template)
                elif self._rb_per_month.GetValue():
                    count = exp.export_diary_per_month(self._fernet, out_path, lang, tags, series, diary_id, template)
                else:
                    count = exp.export_diary_single_markdown(self._fernet, out_path, diary_id)
            else:
                if self._rb_per_entry.GetValue():
                    count = exp.export_notes_per_note(self._fernet, out_path, lang, tags, series, template)
                elif self._rb_per_week.GetValue():
                    count = exp.export_notes_per_week(self._fernet, out_path, lang, tags, series, template)
                elif self._rb_per_month.GetValue():
                    count = exp.export_notes_per_month(self._fernet, out_path, lang, tags, series, template)
                else:
                    count = exp.export_notes_single_markdown(self._fernet, out_path)
        except Exception as exc:
            wx.MessageBox(
                t("export.err_failed", error=str(exc)),
                t("export.err_title"),
                wx.OK | wx.ICON_ERROR, self,
            )
            return

        if self._rb_single_md.GetValue():
            msg = t("export.success_single", count=count)
        else:
            msg = t("export.success_files", count=count)
        wx.MessageBox(msg, t("export.success_title"), wx.OK | wx.ICON_INFORMATION, self)
        self.EndModal(wx.ID_OK)


# ---------------------------------------------------------------------------
# Shortcut capture dialog  (private helper)
# ---------------------------------------------------------------------------

class _KeyCaptureDialog(wx.Dialog):
    """Modal dialog that captures a single key combination from the user."""

    def __init__(self, parent, action_label: str):
        super().__init__(parent, title=t("shortcuts.capture_title"),
                         style=wx.DEFAULT_DIALOG_STYLE)
        self._combo: Optional[str] = None
        self._action_label = action_label
        self._build_ui()
        self.Layout()
        self.Fit()
        self.SetMinSize((340, -1))
        self.CentreOnParent()
        self._capture_ctrl.SetFocus()

    def _build_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        prompt = wx.StaticText(
            self,
            label=f"{t('shortcuts.capture_prompt')}\n{self._action_label}",
        )
        sizer.Add(prompt, 0, wx.ALL | wx.EXPAND, 12)

        self._capture_ctrl = wx.TextCtrl(
            self,
            value=t("shortcuts.capture_hint"),
            style=wx.TE_READONLY | wx.TE_CENTRE,
        )
        self._capture_ctrl.SetName(t("shortcuts.capture_prompt"))
        font = self._capture_ctrl.GetFont()
        font.SetPointSize(font.GetPointSize() + 2)
        self._capture_ctrl.SetFont(font)
        sizer.Add(self._capture_ctrl, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

        btn_sizer = wx.StdDialogButtonSizer()
        self._ok_btn = wx.Button(self, wx.ID_OK)
        self._ok_btn.Enable(False)
        btn_sizer.AddButton(self._ok_btn)
        self._cancel_btn = wx.Button(self, wx.ID_CANCEL)
        btn_sizer.AddButton(self._cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 8)

        self.SetSizer(sizer)
        self._capture_ctrl.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

    def _on_key_down(self, event):
        keycode = event.GetKeyCode()
        mods = 0
        if event.ControlDown(): mods |= wx.ACCEL_CTRL
        if event.AltDown():     mods |= wx.ACCEL_ALT
        if event.ShiftDown():   mods |= wx.ACCEL_SHIFT

        # Pass through Tab so focus can move to OK / Cancel
        if keycode == wx.WXK_TAB:
            event.Skip()
            return

        # Ignore bare modifier keys
        if keycode in (wx.WXK_CONTROL, wx.WXK_ALT, wx.WXK_SHIFT,
                       wx.WXK_RAW_CONTROL):
            return

        # Escape without modifier = cancel
        if keycode == wx.WXK_ESCAPE and mods == 0:
            self.EndModal(wx.ID_CANCEL)
            return

        # Enter without modifier = confirm if a combo was already captured
        if keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and mods == 0:
            if self._combo:
                self.EndModal(wx.ID_OK)
            return

        # Require at least one modifier for a valid shortcut
        if mods == 0:
            wx.Bell()
            return

        display = _sc.combo_to_display(mods, keycode)
        self._capture_ctrl.ChangeValue(display)
        self._combo = display
        self._ok_btn.Enable()
        self._ok_btn.SetDefault()
        _speak(display)

    def get_combo(self) -> Optional[str]:
        return self._combo


# ---------------------------------------------------------------------------
# Shortcuts customisation dialog
# ---------------------------------------------------------------------------

class ShortcutsDialog(wx.Dialog):
    """Dialog for viewing and reassigning keyboard shortcuts.

    shortcut_defs: list of (action_key, label_i18n_key, wx_id, default_display)
    """

    def __init__(self, parent, shortcut_defs: list):
        super().__init__(parent, title=t("shortcuts.title"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._defs = shortcut_defs
        self._build_ui()
        self._populate()
        self.Layout()
        self.SetSize((460, 380))
        self.SetMinSize((380, 300))
        self.CentreOnParent()

    def _build_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._list = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE,
        )
        self._list.SetName(t("shortcuts.accessible_list"))
        self._list.InsertColumn(0, t("shortcuts.col_action"),   width=230)
        self._list.InsertColumn(1, t("shortcuts.col_shortcut"), width=160)
        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._reassign_btn = wx.Button(self, label=t("shortcuts.btn_reassign"))
        self._reset_btn    = wx.Button(self, label=t("shortcuts.btn_reset"))
        self._reassign_btn.Enable(False)
        self._reset_btn.Enable(False)
        btn_row.Add(self._reassign_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._reset_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        close_btn = wx.Button(self, wx.ID_CLOSE)
        close_btn.SetDefault()
        btn_row.Add(close_btn, 0)
        sizer.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.SetSizer(sizer)

        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED,   self._on_select)
        self._list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_deselect)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED,  self._on_reassign)
        self._reassign_btn.Bind(wx.EVT_BUTTON, self._on_reassign)
        self._reset_btn.Bind(wx.EVT_BUTTON,    self._on_reset)
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE))
        self.Bind(wx.EVT_CLOSE, lambda e: self.EndModal(wx.ID_CLOSE))

    def _populate(self):
        self._list.DeleteAllItems()
        for i, (action_key, label_key, _wx_id, default_display) in enumerate(self._defs):
            label = t(label_key).split("\t")[0].replace("&", "").rstrip(".")
            current = _sc.load_shortcut(action_key, default_display)
            self._list.InsertItem(i, label)
            self._list.SetItem(i, 1, current)

    def _selected_index(self) -> int:
        return self._list.GetFirstSelected()

    def _on_select(self, _event):
        self._reassign_btn.Enable()
        self._reset_btn.Enable()

    def _on_deselect(self, _event):
        if self._selected_index() == -1:
            self._reassign_btn.Enable(False)
            self._reset_btn.Enable(False)

    def _on_reassign(self, _event):
        idx = self._selected_index()
        if idx < 0:
            return
        action_key, label_key, _wx_id, default_display = self._defs[idx]
        label = t(label_key).split("\t")[0].replace("&", "").rstrip(".")

        dlg = _KeyCaptureDialog(self, label)
        result = dlg.ShowModal()
        new_combo = dlg.get_combo()
        dlg.Destroy()

        if result != wx.ID_OK or not new_combo:
            return

        # Check for conflicts against the list's current state
        conflict_idx = self._find_conflict(new_combo, skip=idx)
        if conflict_idx is not None:
            conflict_label = (t(self._defs[conflict_idx][1])
                              .split("\t")[0].replace("&", "").rstrip("."))
            msg = t("shortcuts.conflict_msg").format(
                shortcut=new_combo, action=conflict_label
            )
            answer = wx.MessageBox(
                msg, t("shortcuts.conflict_title"),
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, self,
            )
            if answer != wx.YES:
                return

        _sc.save_shortcut(action_key, new_combo)
        self._list.SetItem(idx, 1, new_combo)
        _speak(new_combo)

    def _on_reset(self, _event):
        idx = self._selected_index()
        if idx < 0:
            return
        action_key, _label_key, _wx_id, default_display = self._defs[idx]
        _sc.reset_shortcut(action_key)
        self._list.SetItem(idx, 1, default_display)

    def _find_conflict(self, display: str, skip: int) -> Optional[int]:
        for i in range(self._list.GetItemCount()):
            if i == skip:
                continue
            if self._list.GetItemText(i, 1).lower() == display.lower():
                return i
        return None
