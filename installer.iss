[Setup]
; Informações do aplicativo
AppName=Label Quality Manager
AppVersion=1.0
; Instala o programa em uma pasta onde o usuário pode gravar (por exemplo, AppData local)
DefaultDirName={localappdata}\Label Quality Manager
DefaultGroupName=Label Quality Manager
OutputBaseFilename=LabelQualityInstaller
Compression=lzma
SolidCompression=yes

[Files]
; Copia o executável e arquivos gerados pelo PyInstaller
Source: "dist\gui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Copia os arquivos de dados para dentro da pasta _internal, onde o PyInstaller os procura
Source: "config.json"; DestDir: "{app}\_internal"; Flags: ignoreversion
Source: "azure.tcl"; DestDir: "{app}\_internal"; Flags: ignoreversion
Source: "workorder_cache.json"; DestDir: "{app}\_internal"; Flags: ignoreversion
Source: "printed_serials.json"; DestDir: "{app}\_internal"; Flags: ignoreversion
Source: "impressoes.csv"; DestDir: "{app}\_internal"; Flags: ignoreversion
Source: "api1_cache.json"; DestDir: "{app}\_internal"; Flags: ignoreversion
Source: "theme\*"; DestDir: "{app}\_internal\theme"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "app.log"; DestDir: "{app}\_internal"; Flags: ignoreversion

[Icons]
; Cria o atalho no menu Iniciar utilizando o ícone do gui.exe
Name: "{group}\Label Quality Manager"; Filename: "{app}\gui.exe"; IconFilename: "{app}\gui.exe"; IconIndex: 0
; Cria o atalho na área de trabalho utilizando o ícone do gui.exe
Name: "{commondesktop}\Label Quality Manager"; Filename: "{app}\gui.exe"; IconFilename: "{app}\gui.exe"; IconIndex: 0
