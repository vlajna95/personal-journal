; ================================================================
; DP PersonalJournal – NSIS Installer
; Unicode True required for Danijela Popović, Română, etc.
; ================================================================
Unicode True

!define APPNAME      "DP PersonalJournal"
!define APPNAME_SAFE "PersonalJournal"
!define VERSION      "1.0.2026.613"
!define PUBLISHER    "Danijela Popović"
!define REGKEY       "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME_SAFE}"
!define DIST         "dist\PersonalJournal"

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"
!include "WinMessages.nsh"
!include "FileFunc.nsh"

; ----------------------------------------------------------------
; General
; ----------------------------------------------------------------
Name    "${APPNAME}"
OutFile "PersonalJournal-${VERSION}-setup.exe"
InstallDir "$LOCALAPPDATA\${APPNAME_SAFE}"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails   show
ShowUninstDetails show

; ----------------------------------------------------------------
; Variables
; ----------------------------------------------------------------
Var InstallType   ; 0 = Standard  1 = Portable
Var AppLangCode   ; "en", "sr", …
Var AppLangIndex  ; index inside the list-box (0-based)

; nsDialogs handles – Install Type page
Var hRadioStd
Var hRadioPort

; nsDialogs handles – Options page
Var hCheckDesk
Var hCheckStart

; nsDialogs handle – Language page
Var hLangList

; ----------------------------------------------------------------
; MUI settings
; ----------------------------------------------------------------
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE       "${APPNAME}"

; ----------------------------------------------------------------
; Pages
; ----------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
Page custom   pg_InstType       pg_InstType_Leave
!insertmacro MUI_PAGE_DIRECTORY
Page custom   pg_Options        pg_Options_Leave
Page custom   pg_Lang           pg_Lang_Leave
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_RUN          "$INSTDIR\${APPNAME_SAFE}.exe"
!define MUI_FINISHPAGE_RUN_TEXT     "$(FinishRun)"
!define MUI_FINISHPAGE_NOREBOOTSUPPORT
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ----------------------------------------------------------------
; Installer UI languages
; ----------------------------------------------------------------
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "Catalan"
!insertmacro MUI_LANGUAGE "Romanian"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "Italian"
!insertmacro MUI_LANGUAGE "PortugueseBR"
!insertmacro MUI_LANGUAGE "Swedish"
!insertmacro MUI_LANGUAGE "Norwegian"
!insertmacro MUI_LANGUAGE "SerbianLatin"

; ----------------------------------------------------------------
; Custom LangStrings  (must be defined for every installed language)
; ----------------------------------------------------------------

; ── Finish page ──────────────────────────────────────────────────
LangString FinishRun ${LANG_ENGLISH}      "Launch ${APPNAME}"
LangString FinishRun ${LANG_SPANISH}      "Iniciar ${APPNAME}"
LangString FinishRun ${LANG_CATALAN}      "Inicia ${APPNAME}"
LangString FinishRun ${LANG_ROMANIAN}     "Lansați ${APPNAME}"
LangString FinishRun ${LANG_FRENCH}       "Lancer ${APPNAME}"
LangString FinishRun ${LANG_ITALIAN}      "Avvia ${APPNAME}"
LangString FinishRun ${LANG_PORTUGUESEBR} "Iniciar ${APPNAME}"
LangString FinishRun ${LANG_SWEDISH}      "Starta ${APPNAME}"
LangString FinishRun ${LANG_NORWEGIAN}    "Start ${APPNAME}"
LangString FinishRun ${LANG_SERBIANLATIN} "Pokreni ${APPNAME}"

; ── Install Type page ─────────────────────────────────────────────
LangString InstTypeTitle    ${LANG_ENGLISH}      "Installation Type"
LangString InstTypeTitle    ${LANG_SPANISH}      "Tipo de instalación"
LangString InstTypeTitle    ${LANG_CATALAN}      "Tipus d'instal·lació"
LangString InstTypeTitle    ${LANG_ROMANIAN}     "Tip de instalare"
LangString InstTypeTitle    ${LANG_FRENCH}       "Type d'installation"
LangString InstTypeTitle    ${LANG_ITALIAN}      "Tipo di installazione"
LangString InstTypeTitle    ${LANG_PORTUGUESEBR} "Tipo de instalação"
LangString InstTypeTitle    ${LANG_SWEDISH}      "Installationstyp"
LangString InstTypeTitle    ${LANG_NORWEGIAN}    "Installasjonstype"
LangString InstTypeTitle    ${LANG_SERBIANLATIN} "Vrsta instalacije"

LangString InstTypeSubtitle ${LANG_ENGLISH}      "Choose how to install ${APPNAME}."
LangString InstTypeSubtitle ${LANG_SPANISH}      "Elija cómo instalar ${APPNAME}."
LangString InstTypeSubtitle ${LANG_CATALAN}      "Trieu com instal·lar ${APPNAME}."
LangString InstTypeSubtitle ${LANG_ROMANIAN}     "Alegeți cum să instalați ${APPNAME}."
LangString InstTypeSubtitle ${LANG_FRENCH}       "Choisissez comment installer ${APPNAME}."
LangString InstTypeSubtitle ${LANG_ITALIAN}      "Scegli come installare ${APPNAME}."
LangString InstTypeSubtitle ${LANG_PORTUGUESEBR} "Escolha como instalar o ${APPNAME}."
LangString InstTypeSubtitle ${LANG_SWEDISH}      "Välj hur ${APPNAME} ska installeras."
LangString InstTypeSubtitle ${LANG_NORWEGIAN}    "Velg hvordan ${APPNAME} skal installeres."
LangString InstTypeSubtitle ${LANG_SERBIANLATIN} "Izaberite način instalacije programa ${APPNAME}."

LangString InstTypeStdLabel ${LANG_ENGLISH}      "Standard install (recommended)"
LangString InstTypeStdLabel ${LANG_SPANISH}      "Instalación estándar (recomendada)"
LangString InstTypeStdLabel ${LANG_CATALAN}      "Instal·lació estàndard (recomanada)"
LangString InstTypeStdLabel ${LANG_ROMANIAN}     "Instalare standard (recomandat)"
LangString InstTypeStdLabel ${LANG_FRENCH}       "Installation standard (recommandée)"
LangString InstTypeStdLabel ${LANG_ITALIAN}      "Installazione standard (consigliata)"
LangString InstTypeStdLabel ${LANG_PORTUGUESEBR} "Instalação padrão (recomendada)"
LangString InstTypeStdLabel ${LANG_SWEDISH}      "Standardinstallation (rekommenderas)"
LangString InstTypeStdLabel ${LANG_NORWEGIAN}    "Standardinstallasjon (anbefalt)"
LangString InstTypeStdLabel ${LANG_SERBIANLATIN} "Standardna instalacija (preporučeno)"

LangString InstTypeStdDesc  ${LANG_ENGLISH}      "Installs to your user profile. Creates an uninstaller and optional Start Menu entry."
LangString InstTypeStdDesc  ${LANG_SPANISH}      "Instala en su perfil de usuario. Crea un desinstalador y una entrada opcional en el menú Inicio."
LangString InstTypeStdDesc  ${LANG_CATALAN}      "S'instal·la al vostre perfil d'usuari. Crea un desinstal·lador i una entrada opcional al menú Inici."
LangString InstTypeStdDesc  ${LANG_ROMANIAN}     "Se instalează în profilul dvs. de utilizator. Creează un dezinstalator și o intrare opțională în meniul Start."
LangString InstTypeStdDesc  ${LANG_FRENCH}       "Installe dans votre profil utilisateur. Crée un désinstalleur et une entrée optionnelle dans le menu Démarrer."
LangString InstTypeStdDesc  ${LANG_ITALIAN}      "Installa nel profilo utente. Crea un programma di disinstallazione e una voce opzionale nel menu Start."
LangString InstTypeStdDesc  ${LANG_PORTUGUESEBR} "Instala no perfil do usuário. Cria um desinstalador e uma entrada opcional no menu Iniciar."
LangString InstTypeStdDesc  ${LANG_SWEDISH}      "Installerar i din användarprofil. Skapar ett avinstallationsprogram och en valfri Start-menypost."
LangString InstTypeStdDesc  ${LANG_NORWEGIAN}    "Installerer i din brukerprofil. Oppretter en avinstaller og en valgfri Start-menyoppføring."
LangString InstTypeStdDesc  ${LANG_SERBIANLATIN} "Instalira se u vaš korisnički profil. Kreira deinstalater i opcioni unos u Start meni."

LangString InstTypePortLabel ${LANG_ENGLISH}      "Portable (no registry, no uninstaller)"
LangString InstTypePortLabel ${LANG_SPANISH}      "Portátil (sin registro, sin desinstalador)"
LangString InstTypePortLabel ${LANG_CATALAN}      "Portàtil (sense registre, sense desinstal·lador)"
LangString InstTypePortLabel ${LANG_ROMANIAN}     "Portabil (fără registru, fără dezinstalator)"
LangString InstTypePortLabel ${LANG_FRENCH}       "Portable (sans registre ni désinstalleur)"
LangString InstTypePortLabel ${LANG_ITALIAN}      "Portabile (nessun registro, nessun disinstallatore)"
LangString InstTypePortLabel ${LANG_PORTUGUESEBR} "Portátil (sem registro, sem desinstalador)"
LangString InstTypePortLabel ${LANG_SWEDISH}      "Portabel (inget register, ingen avinstallation)"
LangString InstTypePortLabel ${LANG_NORWEGIAN}    "Portabel (ikke register, ingen avinstaller)"
LangString InstTypePortLabel ${LANG_SERBIANLATIN} "Prenosivi (bez registra, bez deinstalatera)"

LangString InstTypePortDesc  ${LANG_ENGLISH}      "Extracts all files to a folder of your choice. No changes to the system registry."
LangString InstTypePortDesc  ${LANG_SPANISH}      "Extrae todos los archivos en una carpeta de su elección. Sin cambios en el registro del sistema."
LangString InstTypePortDesc  ${LANG_CATALAN}      "Extreu tots els fitxers a una carpeta de la vostra elecció. Sense canvis al registre del sistema."
LangString InstTypePortDesc  ${LANG_ROMANIAN}     "Extrage toate fișierele într-un dosar la alegerea dvs. Fără modificări în registrul sistemului."
LangString InstTypePortDesc  ${LANG_FRENCH}       "Extrait tous les fichiers dans un dossier de votre choix. Aucune modification du registre système."
LangString InstTypePortDesc  ${LANG_ITALIAN}      "Estrae tutti i file in una cartella a tua scelta. Nessuna modifica al registro di sistema."
LangString InstTypePortDesc  ${LANG_PORTUGUESEBR} "Extrai todos os arquivos para uma pasta de sua escolha. Nenhuma alteração no registro do sistema."
LangString InstTypePortDesc  ${LANG_SWEDISH}      "Extraherar alla filer till en valfri mapp. Inga ändringar i systemregistret."
LangString InstTypePortDesc  ${LANG_NORWEGIAN}    "Pakker ut alle filer til en valgfri mappe. Ingen endringer i systemregisteret."
LangString InstTypePortDesc  ${LANG_SERBIANLATIN} "Raspakuje sve datoteke u izabranu fasciklu. Bez promena u sistemskom registru."

; ── Options page ─────────────────────────────────────────────────
LangString OptTitle    ${LANG_ENGLISH}      "Install Options"
LangString OptTitle    ${LANG_SPANISH}      "Opciones de instalación"
LangString OptTitle    ${LANG_CATALAN}      "Opcions d'instal·lació"
LangString OptTitle    ${LANG_ROMANIAN}     "Opțiuni de instalare"
LangString OptTitle    ${LANG_FRENCH}       "Options d'installation"
LangString OptTitle    ${LANG_ITALIAN}      "Opzioni di installazione"
LangString OptTitle    ${LANG_PORTUGUESEBR} "Opções de instalação"
LangString OptTitle    ${LANG_SWEDISH}      "Installationsalternativ"
LangString OptTitle    ${LANG_NORWEGIAN}    "Installasjonsalternativer"
LangString OptTitle    ${LANG_SERBIANLATIN} "Opcije instalacije"

LangString OptSubtitle ${LANG_ENGLISH}      "Choose additional options."
LangString OptSubtitle ${LANG_SPANISH}      "Elija opciones adicionales."
LangString OptSubtitle ${LANG_CATALAN}      "Trieu opcions addicionals."
LangString OptSubtitle ${LANG_ROMANIAN}     "Alegeți opțiuni suplimentare."
LangString OptSubtitle ${LANG_FRENCH}       "Choisissez des options supplémentaires."
LangString OptSubtitle ${LANG_ITALIAN}      "Scegli opzioni aggiuntive."
LangString OptSubtitle ${LANG_PORTUGUESEBR} "Escolha opções adicionais."
LangString OptSubtitle ${LANG_SWEDISH}      "Välj ytterligare alternativ."
LangString OptSubtitle ${LANG_NORWEGIAN}    "Velg tilleggsalternativer."
LangString OptSubtitle ${LANG_SERBIANLATIN} "Izaberite dodatne opcije."

LangString OptDesk     ${LANG_ENGLISH}      "Create a desktop shortcut"
LangString OptDesk     ${LANG_SPANISH}      "Crear acceso directo en el escritorio"
LangString OptDesk     ${LANG_CATALAN}      "Crea una drecera a l'escriptori"
LangString OptDesk     ${LANG_ROMANIAN}     "Creați o scurtătură pe desktop"
LangString OptDesk     ${LANG_FRENCH}       "Créer un raccourci sur le bureau"
LangString OptDesk     ${LANG_ITALIAN}      "Crea collegamento sul desktop"
LangString OptDesk     ${LANG_PORTUGUESEBR} "Criar atalho na área de trabalho"
LangString OptDesk     ${LANG_SWEDISH}      "Skapa genväg på skrivbordet"
LangString OptDesk     ${LANG_NORWEGIAN}    "Lag snarvei på skrivebordet"
LangString OptDesk     ${LANG_SERBIANLATIN} "Napravi prečicu na radnoj površini"

LangString OptStart    ${LANG_ENGLISH}      "Create a Start Menu folder"
LangString OptStart    ${LANG_SPANISH}      "Crear una carpeta en el menú Inicio"
LangString OptStart    ${LANG_CATALAN}      "Crea una carpeta al menú Inici"
LangString OptStart    ${LANG_ROMANIAN}     "Creați un dosar în meniul Start"
LangString OptStart    ${LANG_FRENCH}       "Créer un dossier dans le menu Démarrer"
LangString OptStart    ${LANG_ITALIAN}      "Crea cartella nel menu Start"
LangString OptStart    ${LANG_PORTUGUESEBR} "Criar pasta no menu Iniciar"
LangString OptStart    ${LANG_SWEDISH}      "Skapa en mapp i Start-menyn"
LangString OptStart    ${LANG_NORWEGIAN}    "Lag en mappe i Start-menyen"
LangString OptStart    ${LANG_SERBIANLATIN} "Napravi fasciklu u Start meniju"

; ── Language selection page ───────────────────────────────────────
LangString LangPgTitle    ${LANG_ENGLISH}      "Application Language"
LangString LangPgTitle    ${LANG_SPANISH}      "Idioma de la aplicación"
LangString LangPgTitle    ${LANG_CATALAN}      "Idioma de l'aplicació"
LangString LangPgTitle    ${LANG_ROMANIAN}     "Limba aplicației"
LangString LangPgTitle    ${LANG_FRENCH}       "Langue de l'application"
LangString LangPgTitle    ${LANG_ITALIAN}      "Lingua dell'applicazione"
LangString LangPgTitle    ${LANG_PORTUGUESEBR} "Idioma do aplicativo"
LangString LangPgTitle    ${LANG_SWEDISH}      "Programspråk"
LangString LangPgTitle    ${LANG_NORWEGIAN}    "Programspråk"
LangString LangPgTitle    ${LANG_SERBIANLATIN} "Jezik programa"

LangString LangPgSubtitle ${LANG_ENGLISH}      "Select the language for ${APPNAME}."
LangString LangPgSubtitle ${LANG_SPANISH}      "Seleccione el idioma para ${APPNAME}."
LangString LangPgSubtitle ${LANG_CATALAN}      "Seleccioneu l'idioma per a ${APPNAME}."
LangString LangPgSubtitle ${LANG_ROMANIAN}     "Selectați limba pentru ${APPNAME}."
LangString LangPgSubtitle ${LANG_FRENCH}       "Sélectionnez la langue pour ${APPNAME}."
LangString LangPgSubtitle ${LANG_ITALIAN}      "Seleziona la lingua per ${APPNAME}."
LangString LangPgSubtitle ${LANG_PORTUGUESEBR} "Selecione o idioma para ${APPNAME}."
LangString LangPgSubtitle ${LANG_SWEDISH}      "Välj språk för ${APPNAME}."
LangString LangPgSubtitle ${LANG_NORWEGIAN}    "Velg språk for ${APPNAME}."
LangString LangPgSubtitle ${LANG_SERBIANLATIN} "Izaberite jezik za ${APPNAME}."

LangString LangPgLabel    ${LANG_ENGLISH}      "Language:"
LangString LangPgLabel    ${LANG_SPANISH}      "Idioma:"
LangString LangPgLabel    ${LANG_CATALAN}      "Idioma:"
LangString LangPgLabel    ${LANG_ROMANIAN}     "Limbă:"
LangString LangPgLabel    ${LANG_FRENCH}       "Langue :"
LangString LangPgLabel    ${LANG_ITALIAN}      "Lingua:"
LangString LangPgLabel    ${LANG_PORTUGUESEBR} "Idioma:"
LangString LangPgLabel    ${LANG_SWEDISH}      "Språk:"
LangString LangPgLabel    ${LANG_NORWEGIAN}    "Språk:"
LangString LangPgLabel    ${LANG_SERBIANLATIN} "Jezik:"

; ================================================================
; Helper macro – set header/subheader text on custom pages
; ================================================================
!macro SetPageHeader Title Subtitle
    !insertmacro MUI_HEADER_TEXT "${Title}" "${Subtitle}"
!macroend

; ================================================================
; Install Type page
; ================================================================
Function pg_InstType
    nsDialogs::Create 1018
    Pop $0
    ${If} $0 == error
        Abort
    ${EndIf}

    !insertmacro MUI_HEADER_TEXT "$(InstTypeTitle)" "$(InstTypeSubtitle)"

    ; Standard radio + description
    ${NSD_CreateRadioButton} 0 10u 100% 12u "$(InstTypeStdLabel)"
    Pop $hRadioStd
    ${NSD_CreateLabel} 12u 24u 100% 18u "$(InstTypeStdDesc)"
    Pop $0

    ; Portable radio + description
    ${NSD_CreateRadioButton} 0 50u 100% 12u "$(InstTypePortLabel)"
    Pop $hRadioPort
    ${NSD_CreateLabel} 12u 64u 100% 18u "$(InstTypePortDesc)"
    Pop $0

    ; Default selection
    ${If} $InstallType == "1"
        ${NSD_SetState} $hRadioPort ${BST_CHECKED}
    ${Else}
        ${NSD_SetState} $hRadioStd  ${BST_CHECKED}
    ${EndIf}

    nsDialogs::Show
FunctionEnd

Function pg_InstType_Leave
    ${NSD_GetState} $hRadioPort $0
    ${If} $0 == ${BST_CHECKED}
        StrCpy $InstallType "1"
        StrCpy $INSTDIR "$DOCUMENTS\${APPNAME_SAFE}"
    ${Else}
        StrCpy $InstallType "0"
        StrCpy $INSTDIR "$LOCALAPPDATA\${APPNAME_SAFE}"
    ${EndIf}
FunctionEnd

; ================================================================
; Options page  (desktop shortcut + start menu)
; ================================================================
Function pg_Options
    nsDialogs::Create 1018
    Pop $0
    ${If} $0 == error
        Abort
    ${EndIf}

    !insertmacro MUI_HEADER_TEXT "$(OptTitle)" "$(OptSubtitle)"

    ${NSD_CreateCheckBox} 0 10u 100% 12u "$(OptDesk)"
    Pop $hCheckDesk
    ${NSD_SetState} $hCheckDesk ${BST_CHECKED}

    ${NSD_CreateCheckBox} 0 28u 100% 12u "$(OptStart)"
    Pop $hCheckStart
    ; For portable installs, disable the Start Menu option
    ${If} $InstallType == "1"
        EnableWindow $hCheckStart 0
        ${NSD_SetState} $hCheckStart ${BST_UNCHECKED}
    ${Else}
        ${NSD_SetState} $hCheckStart ${BST_CHECKED}
    ${EndIf}

    nsDialogs::Show
FunctionEnd

Function pg_Options_Leave
    ${NSD_GetState} $hCheckDesk $0
    ${If} $0 == ${BST_CHECKED}
        StrCpy $R0 "1"
    ${Else}
        StrCpy $R0 "0"
    ${EndIf}

    ${NSD_GetState} $hCheckStart $0
    ${If} $0 == ${BST_CHECKED}
        StrCpy $R1 "1"
    ${Else}
        StrCpy $R1 "0"
    ${EndIf}
FunctionEnd

; ================================================================
; Language selection page
; ================================================================
; App language list – order must match AppLangCodes below
; (12 entries: index 0..11)
; ================================================================
Function pg_Lang
    nsDialogs::Create 1018
    Pop $0
    ${If} $0 == error
        Abort
    ${EndIf}

    !insertmacro MUI_HEADER_TEXT "$(LangPgTitle)" "$(LangPgSubtitle)"

    ${NSD_CreateLabel} 0 0 100% 12u "$(LangPgLabel)"
    Pop $0

    ${NSD_CreateListBox} 0 14u 200u 80u ""
    Pop $hLangList

    ; Add languages in a fixed order
    ${NSD_LB_AddString} $hLangList "Català"
    ${NSD_LB_AddString} $hLangList "English"
    ${NSD_LB_AddString} $hLangList "Esperanto"
    ${NSD_LB_AddString} $hLangList "Español"
    ${NSD_LB_AddString} $hLangList "Euskera"
    ${NSD_LB_AddString} $hLangList "Français"
    ${NSD_LB_AddString} $hLangList "Italiano"
    ${NSD_LB_AddString} $hLangList "Norsk (Bokmål)"
    ${NSD_LB_AddString} $hLangList "Português (Brasil)"
    ${NSD_LB_AddString} $hLangList "Română"
    ${NSD_LB_AddString} $hLangList "Srpski"
    ${NSD_LB_AddString} $hLangList "Svenska"

    ; Default selection (English = index 1); restored on Back navigation
    ${If} $AppLangIndex == ""
        StrCpy $AppLangIndex "1"
    ${EndIf}
    SendMessage $hLangList ${LB_SETCURSEL} $AppLangIndex 0

    nsDialogs::Show
FunctionEnd

Function pg_Lang_Leave
    SendMessage $hLangList ${LB_GETCURSEL} 0 0 $0
    StrCpy $AppLangIndex $0

    ; Map index → lang code  (must match list order above)
    ${Switch} $0
        ${Case} 0
            StrCpy $AppLangCode "ca"
            ${Break}
        ${Case} 1
            StrCpy $AppLangCode "en"
            ${Break}
        ${Case} 2
            StrCpy $AppLangCode "eo"
            ${Break}
        ${Case} 3
            StrCpy $AppLangCode "es"
            ${Break}
        ${Case} 4
            StrCpy $AppLangCode "eu"
            ${Break}
        ${Case} 5
            StrCpy $AppLangCode "fr"
            ${Break}
        ${Case} 6
            StrCpy $AppLangCode "it"
            ${Break}
        ${Case} 7
            StrCpy $AppLangCode "nb"
            ${Break}
        ${Case} 8
            StrCpy $AppLangCode "pt_BR"
            ${Break}
        ${Case} 9
            StrCpy $AppLangCode "ro"
            ${Break}
        ${Case} 10
            StrCpy $AppLangCode "sr"
            ${Break}
        ${Case} 11
            StrCpy $AppLangCode "sv"
            ${Break}
        ${Default}
            StrCpy $AppLangCode "en"
            ${Break}
    ${EndSwitch}
FunctionEnd

; ================================================================
; Init  – set default variable values
; ================================================================
Function .onInit
    StrCpy $InstallType  "0"
    StrCpy $AppLangCode  "en"
    StrCpy $AppLangIndex "1"
    StrCpy $R0 "1"   ; desktop shortcut default = yes
    StrCpy $R1 "1"   ; start menu default = yes
FunctionEnd

; ================================================================
; Main Install Section
; ================================================================
Section "Install" SecInstall
    SetOutPath "$INSTDIR"
    File /r "${DIST}\"

    ; ── Write app language to settings.ini (only if file absent) ──
    IfFileExists "$INSTDIR\_internal\settings.ini" settings_exists settings_missing
    settings_missing:
        WriteINIStr "$INSTDIR\_internal\settings.ini" "General" "language" "$AppLangCode"
    settings_exists:

    ; ── Desktop shortcut ──────────────────────────────────────────
    ${If} $R0 == "1"
        CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${APPNAME_SAFE}.exe"
    ${EndIf}

    ; ── Start Menu (standard install only) ────────────────────────
    ${If} $InstallType == "0"
    ${AndIf} $R1 == "1"
        CreateDirectory "$SMPROGRAMS\${APPNAME}"
        CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\${APPNAME_SAFE}.exe"
        CreateShortCut "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk" "$INSTDIR\Uninstall.exe"
    ${EndIf}

    ; ── Uninstaller + registry (standard install only) ────────────
    ${If} $InstallType == "0"
        WriteUninstaller "$INSTDIR\Uninstall.exe"
        WriteRegStr   HKCU "${REGKEY}" "DisplayName"          "${APPNAME}"
        WriteRegStr   HKCU "${REGKEY}" "DisplayVersion"       "${VERSION}"
        WriteRegStr   HKCU "${REGKEY}" "Publisher"            "${PUBLISHER}"
        WriteRegStr   HKCU "${REGKEY}" "InstallLocation"      "$INSTDIR"
        WriteRegStr   HKCU "${REGKEY}" "UninstallString"      "$INSTDIR\Uninstall.exe"
        WriteRegStr   HKCU "${REGKEY}" "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
        WriteRegDWORD HKCU "${REGKEY}" "NoModify"             1
        WriteRegDWORD HKCU "${REGKEY}" "NoRepair"             1

        ; Estimate installed size in KB
        ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
        WriteRegDWORD HKCU "${REGKEY}" "EstimatedSize" $0
    ${EndIf}
SectionEnd

; ================================================================
; Uninstall Section
; ================================================================
Section "Uninstall"
    ; Remove files
    RMDir /r "$INSTDIR\_internal"
    Delete "$INSTDIR\${APPNAME_SAFE}.exe"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir  "$INSTDIR"

    ; Remove Start Menu entries
    RMDir /r "$SMPROGRAMS\${APPNAME}"

    ; Remove desktop shortcut
    Delete "$DESKTOP\${APPNAME}.lnk"

    ; Remove registry key
    DeleteRegKey HKCU "${REGKEY}"
SectionEnd
