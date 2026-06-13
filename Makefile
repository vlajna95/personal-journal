SHELL      := powershell.exe
.SHELLFLAGS := -NoProfile -NonInteractive -Command
.DEFAULT_GOAL := help

# Commit message for push / release targets
MSG ?=

.PHONY: build installer installer-only push release help

build:            ## Compile Python sources with PyInstaller
	.\build.ps1

installer:        ## PyInstaller + NSIS setup package
	.\build.ps1 -Installer

installer-only:   ## NSIS setup package only (skip PyInstaller)
	.\build.ps1 -InstallerOnly

push:             ## Stage all changes, commit and push  (MSG="your message")
	@if ([string]::IsNullOrWhiteSpace("$(MSG)")) { Write-Error "Provide a commit message:  make push MSG=`"your message`""; exit 1 }
	git add -A
	git commit -m "$(MSG)"
	git push

release: installer push  ## Build installer then push  (MSG="your message")

help:             ## Show this help
	@Write-Host ""
	@Write-Host "Usage:  make <target> [MSG=`"commit message`"]" -ForegroundColor Cyan
	@Write-Host ""
	@Write-Host "  build            Compile Python sources with PyInstaller"
	@Write-Host "  installer        PyInstaller + NSIS setup package"
	@Write-Host "  installer-only   NSIS setup package only (skip PyInstaller)"
	@Write-Host "  push             Stage all, commit and push to GitHub"
	@Write-Host "  release          installer + push  (MSG required)"
	@Write-Host "  help             Show this help"
	@Write-Host ""
	@Write-Host "Examples:" -ForegroundColor Yellow
	@Write-Host "  make build"
	@Write-Host "  make installer"
	@Write-Host '  make push MSG="Fix alarm crash on empty title"'
	@Write-Host '  make release MSG="v2.0 - multiple diaries"'
	@Write-Host ""
