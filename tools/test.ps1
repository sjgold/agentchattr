param([string]$Pattern = 'test_*.py')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$previous = $env:PYTHONPATH
try {
    $env:PYTHONPATH = (Join-Path $root 'src') + [IO.Path]::PathSeparator + $root
    Push-Location $root
    try { & "$root\.venv-windows\Scripts\python.exe" -B -m unittest discover -s tests -p $Pattern; $result = $LASTEXITCODE }
    finally { Pop-Location }
} finally { $env:PYTHONPATH = $previous }
exit $result
