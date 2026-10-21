; Inno Setup script — per-user install, no admin rights needed.
#define AppVersion GetEnv("SF_VERSION")
#if AppVersion == ""
  #define AppVersion "1.0.0"
#endif
#define AppCompression GetEnv("SF_COMPRESSION")
#if AppCompression == ""
  #define AppCompression "lzma2/ultra64"
#endif

[Setup]
AppId={{5A883197-48BE-4CF2-8F36-6435E870B71C}
AppName=ShiftForge
AppVersion={#AppVersion}
AppPublisher=ShiftForge
DefaultDirName={localappdata}\Programs\ShiftForge
DefaultGroupName=ShiftForge
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=ShiftForge-Setup
SetupIconFile=..\dragshift\assets\dragshift.ico
UninstallDisplayIcon={app}\ShiftForge.exe
Compression={#AppCompression}
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "autostart"; Description: "Запускать ShiftForge вместе с Windows"; Flags: checkedonce
Name: "contextmenu"; Description: "Добавить ShiftForge в контекстное меню файлов"; Flags: checkedonce
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; Flags: unchecked

[Files]
Source: "..\dist\ShiftForge\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\ShiftForge"; Filename: "{app}\ShiftForge.exe"
Name: "{autodesktop}\ShiftForge"; Filename: "{app}\ShiftForge.exe"; Tasks: desktopicon
Name: "{usersendto}\ShiftForge"; Filename: "{app}\ShiftForge.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ShiftForge"; ValueData: """{app}\ShiftForge.exe"" --quiet"; Tasks: autostart; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\*\shell\ShiftForge"; ValueType: string; ValueName: "MUIVerb"; ValueData: "ShiftForge…"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\ShiftForge"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\ShiftForge.exe"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\ShiftForge"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\ShiftForge\command"; ValueType: string; ValueName: ""; ValueData: """{app}\ShiftForge.exe"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\ShiftForge"; Flags: uninsdeletekey

[Run]
Filename: "{app}\ShiftForge.exe"; Description: "Запустить ShiftForge"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM ShiftForge.exe"; Flags: runhidden; RunOnceId: "KillShiftForge"
