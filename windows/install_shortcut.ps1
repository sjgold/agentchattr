param([string]$Destination = [Environment]::GetFolderPath('Desktop'))
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$path = Join-Path $Destination 'Agentchattr.lnk'
$shell = New-Object -ComObject WScript.Shell
if (Test-Path -LiteralPath $path) {
    throw "Shortcut already exists: $path. Move it before installing this checkout's shortcut."
}
$shortcut = $shell.CreateShortcut($path)
$shortcut.TargetPath = $env:ComSpec
$shortcut.Arguments = '/d /c ""' + (Join-Path $root 'windows\start.bat') + '""'
$shortcut.WorkingDirectory = $root
$shortcut.Description = 'Open agentchattr pre-flight'
$shortcut.Save()
Write-Output "Created $path"
