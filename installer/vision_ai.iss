; Inno Setup 6 script. Build with:  ISCC /DAppVersion=0.2.0 installer\vision_ai.iss
; (scripts\build.ps1 does this). NOT TESTED YET.
#ifndef AppVersion
  #define AppVersion "0.2.0"
#endif

[Setup]
AppId={{B6E4D9F2-6B4A-4F0E-9C57-5C2A7D1F3A10}
AppName=Vision AI
AppVersion={#AppVersion}
AppPublisher=Agniv Sarkar
AppCopyright=Copyright (c) 2026 Agniv Sarkar
DefaultDirName={autopf}\Vision AI
DefaultGroupName=Vision AI
OutputDir=..\dist
OutputBaseFilename=VisionAI-Setup-{#AppVersion}
SetupIconFile=..\assets\icons\app.ico
UninstallDisplayIcon={app}\Vision AI.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\build\launcher.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Vision AI"; Filename: "{app}\Vision AI.exe"
Name: "{group}\Uninstall Vision AI"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Vision AI"; Filename: "{app}\Vision AI.exe"; Tasks: desktopicon

[Registry]
; remove "start with Windows" when the app is uninstalled
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "VisionAI"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Vision AI.exe"; Description: "Start Vision AI now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM ""Vision AI.exe"" /F"; Flags: runhidden; RunOnceId: "KillVisionAI"
