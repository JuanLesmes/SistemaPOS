; Instalador de SistemaPOS para Windows, con Inno Setup 6 (https://jrsoftware.org/isdl.php).
; Se genera con scripts\build_installer.ps1, que primero empaqueta el .exe con PyInstaller
; y luego pasa la versión con /DAppVersion=x.y.z.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "SistemaPOS"
#define AppPublisher "Inti Nova"
#define AppExeName "SistemaPOS.exe"

[Setup]
AppId={{7E1D3C2A-5B44-4C4E-9E0B-2F6D1A7C9B31}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
; La aplicación escribe .env, config.json, logs y copias junto al .exe, por eso no va en Archivos de programa.
DefaultDirName={sd}\{#AppName}
DisableDirPage=no
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=..\dist\installer
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#AppName}
; No se borran los datos del cliente al desinstalar: .env, config.json, logs y backups quedan.

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Dirs]
; Los cajeros no son administradores del equipo: la carpeta debe ser escribible para todos.
Name: "{app}"; Permissions: users-modify
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\backups"; Permissions: users-modify

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config.example.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName} ahora (aparece el asistente de configuración)"; Flags: nowait postinstall skipifsilent

[Messages]
BeveledLabel={#AppPublisher}
