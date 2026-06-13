---
title: Getting started
nav_order: 2
---

# Getting Started
{: .no_toc }

<details open markdown="block">
  <summary>Contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>


## System requirements 

- Windows 10 or Windows 11, 64-bit 
- Approximately 80 MB of disk space 
- No Python or any other runtime installation required 


## Installation 

### Standard install (recommended) 

1. Download `PersonalJournal-*-setup.exe` from the [releases page](https://github.com/vlajna95/personal-journal/releases/latest). 
2. Run the installer. Because it installs to your user profile, **no administrator password is required**. 
3. Work through the installer pages: 
	- **Installation type** – choose *standard install* to install normally, or *portable* to extract to a folder of your choice. 
	- **Destination folder** – standard defaults to `%LOCALAPPDATA%\PersonalJournal`; portable defaults to `Documents\PersonalJournal`. 
	- **Options** – optionally create a desktop shortcut and a Start Menu folder (Start Menu is not available in portable mode). 
	- **Application language** – choose the language the app will start in. You can change it later from the Language menu. 
4. Click *Install*, then optionally tick *Launch DP PersonalJournal* on the Finish page. 

### Portable mode 

Portable mode extracts all files to the folder you choose. No registry entries are written and there is no uninstaller. To remove the app, simply delete the folder. 


## Setting your password 

The very first time the app launches you will be prompted to create a password. 

- Choose a strong password – it is the only key to your data. 
- There is **no password recovery**. If you forget it, your data cannot be retrieved. 
- The password is never stored anywhere; it is used only to derive the encryption key when the app is running. 

After entering your password twice, the app opens and your (empty) journal is ready to use. 


## Unlocking on subsequent launches 

On every subsequent launch, the app shows the unlock screen. Type your password and press **Enter** (or click *Unlock*) to open the journal. 


## Changing the application language 

Open the **Language** menu and click the language you want. The interface reloads immediately. Your choice is saved and used on the next launch. 


## Uninstalling 

### Standard install 

Open *Settings → Apps* (or *Control Panel → Programs and Features*), find **DP PersonalJournal**, and click *Uninstall*. 

Alternatively, run `Uninstall.exe` from the installation folder (`%LOCALAPPDATA%\PersonalJournal` by default). 

{: .warning }
Uninstalling removes the application files but **does not delete your journal database**. The file `_internal\journal.db` remains in the installation folder. Delete it manually if you want to remove your data. 

### Portable mode 

Delete the folder you extracted the app to. No other files exist outside that folder. 
