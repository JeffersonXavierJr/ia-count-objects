; Instalador do Contador de Componentes (Inno Setup 6) — Sprint 11, tarefa 11.1.3.
;
; Compilado pelo instalador\build.ps1 depois que dist\ContadorComponentes\ existe:
;   ISCC.exe /DSourceDir=<repo>\dist\ContadorComponentes /DOutputDir=<repo>\dist /DMyAppVersion=AAAA.MM.DD instalador\instalador.iss
;
; Instalacao POR USUARIO (sem administrador): vai para
; %LOCALAPPDATA%\Programs\ContadorComponentes, pasta gravavel — necessario
; porque o config_local.json (ROI/camera) e o log ficam ao lado do .exe.

#ifndef SourceDir
  #define SourceDir "..\dist\ContadorComponentes"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#define MyAppName "Contador de Componentes"
#define MyAppExe "ContadorComponentes.exe"

[Setup]
AppId={{6B1F4C2E-8E7A-4C51-9D2B-3A0F5E7C9B14}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\ContadorComponentes
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=Instalar_ContadorComponentes
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppExe}
WizardStyle=modern

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; config_local.json NAO e distribuido: uma reinstalacao preserva a ROI/camera ja calibradas.
; models\ E sobrescrito: reinstalar com um pacote novo instala o modelo desse pacote.
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{group}\Calibrar ROI da camera"; Filename: "{app}\{#MyAppExe}"; Parameters: "--calibrar-roi"; WorkingDir: "{app}"
Name: "{group}\Pasta do programa (modelo e configuracao)"; Filename: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\ContadorComponentes.log"
Type: files; Name: "{app}\config_local.tmp"
