; Inno Setup script – built by scripts\build.bat and the GitHub workflow.
; Both pass absolute paths, because ISCC resolves /D paths relative to this
; script's folder: ISCC "/DAppVersion=2.0.0" "/DSourceDir=%CD%\dist\Voicewright"
; "/DOutputDir=%CD%\release" voicewright.iss

#ifndef AppVersion
  #define AppVersion "2.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\dist\Voicewright"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\release"
#endif

[Setup]
AppId={{8B7C1E52-5D0A-4E0B-9C0F-6A3C7A1F2E11}
AppName=Voicewright
AppVersion={#AppVersion}
AppPublisher=Voicewright
DefaultDirName={localappdata}\Programs\Voicewright
DefaultGroupName=Voicewright
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename=Voicewright-{#AppVersion}-windows-x64-setup
SetupIconFile=..\..\src\voicewright\assets\icon.ico
UninstallDisplayIcon={app}\Voicewright.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Voicewright"; Filename: "{app}\Voicewright.exe"
Name: "{group}\{cm:UninstallProgram,Voicewright}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Voicewright"; Filename: "{app}\Voicewright.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Voicewright.exe"; Description: "{cm:LaunchProgram,Voicewright}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/IM Voicewright.exe /F"; Flags: runhidden; RunOnceId: "KillVoicewright"
