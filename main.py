"""Entry point for Personal Journal."""

import wx

import database
import i18n
import settings
from dialogs import PasswordDialog, PasswordSetupDialog
from i18n import t
from main_frame import MainFrame


class PersonalJournalApp(wx.App):
    def __init__(self, *args, **kwargs):
        self._fernet = None
        self._frame: MainFrame | None = None
        super().__init__(*args, **kwargs)

    def OnInit(self):
        if not self._authenticate():
            return False
        return True

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _authenticate(self) -> bool:
        if database.is_first_launch():
            return self._first_launch_setup()
        return self._unlock()

    def _first_launch_setup(self) -> bool:
        dlg = PasswordSetupDialog(None)
        result = dlg.ShowModal()
        password = dlg.get_password() if result == wx.ID_OK else None
        dlg.Destroy()

        if result != wx.ID_OK or not password:
            return False

        # Persist whichever language was active when the user clicked Create
        settings.set("language", i18n.current_code())

        database.setup_password(password)
        fernet = database.authenticate(password)
        if fernet is None:
            wx.MessageBox(
                t("app.err_db_init_failed"),
                t("app.err_title"),
                wx.OK | wx.ICON_ERROR,
            )
            return False

        self._fernet = fernet
        self._launch_main()
        return True

    def _unlock(self) -> bool:
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            dlg = PasswordDialog(None)
            result = dlg.ShowModal()
            password = dlg.get_password() if result == wx.ID_OK else None
            dlg.Destroy()

            if result != wx.ID_OK:
                return False

            fernet = database.authenticate(password)
            if fernet is not None:
                self._fernet = fernet
                self._launch_main()
                return True

            remaining = max_attempts - attempt
            if remaining > 0:
                wx.MessageBox(
                    t("app.err_auth_failed", remaining=remaining),
                    t("app.err_auth_failed_title"),
                    wx.OK | wx.ICON_WARNING,
                )
            else:
                wx.MessageBox(
                    t("app.err_locked_out"),
                    t("app.err_locked_out_title"),
                    wx.OK | wx.ICON_ERROR,
                )

        return False

    # ------------------------------------------------------------------
    # Frame lifecycle
    # ------------------------------------------------------------------

    def _launch_main(self):
        self._frame = MainFrame(
            fernet=self._fernet,
            on_language_change=self._on_language_change,
        )
        self.SetTopWindow(self._frame)
        self._frame.Show()

    def _on_language_change(self, code: str):
        """Save the new language, reload translations, and rebuild the frame."""
        settings.set("language", code)
        i18n.load(code)

        old_frame = self._frame
        self._launch_main()
        # Destroy the old frame after the new one is visible
        if old_frame:
            old_frame.Destroy()


def main():
    # Initialise translations before creating the wx.App so that even
    # the auth dialogs are displayed in the correct language.
    saved_lang = settings.get("language")
    if saved_lang:
        lang_code = i18n.best_available_language(saved_lang)
    else:
        detected = i18n.detect_system_language()
        lang_code = i18n.best_available_language(detected)

    i18n.load(lang_code)

    app = PersonalJournalApp(redirect=False)
    app.MainLoop()


if __name__ == "__main__":
    main()
