# Builds "Vision AI.exe" (Nuitka) and, if Inno Setup is installed, the installer.
# Run from the project folder in PowerShell:   .\scripts\build.ps1
# NOT TESTED YET: the first build will probably need a fix or two. Send me the red text.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path .venv\Scripts\python.exe)) { throw "Run setup.bat first." }
.\.venv\Scripts\Activate.ps1

$version = (python -c "import vision_ai; print(vision_ai.__version__)")
Write-Host "Building Vision AI $version"

pip install --quiet nuitka ordered-set zstandard
python scripts\download_model.py

python -m nuitka `
  --standalone `
  --assume-yes-for-downloads `
  --enable-plugin=pyside6 `
  --windows-console-mode=disable `
  --windows-icon-from-ico=assets\icons\app.ico `
  --output-dir=build `
  --output-filename="Vision AI.exe" `
  --include-package=vision_ai `
  --include-package=mediapipe `
  --include-package-data=mediapipe `
  --include-data-dir=assets=assets `
  --company-name="Agniv Sarkar" `
  --product-name="Vision AI" `
  --file-description="Vision AI hand gesture control" `
  --file-version="$version.0" `
  --product-version="$version.0" `
  --copyright="(c) 2026 Agniv Sarkar" `
  scripts\launcher.py

if ($LASTEXITCODE -ne 0) { throw "Nuitka failed" }
Write-Host "Built: build\launcher.dist\Vision AI.exe"

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (Test-Path $iscc) {
  & $iscc "/DAppVersion=$version" installer\vision_ai.iss
  Write-Host "Installer: dist\VisionAI-Setup-$version.exe"
} else {
  Write-Host "Inno Setup 6 not found: install it from jrsoftware.org to make the installer."
}
Write-Host "Before you sell it: sign the .exe files. See docs\RELEASE.md."
