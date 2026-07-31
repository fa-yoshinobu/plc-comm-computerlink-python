[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$outputDirectory = Join-Path $repositoryRoot ("build/package-contract-" + [guid]::NewGuid().ToString("N"))

try {
    [void](New-Item -ItemType Directory -Path $outputDirectory -Force)
    Push-Location $repositoryRoot
    try {
        & python -m build --outdir $outputDirectory
        if ($LASTEXITCODE -ne 0) { throw "python -m build failed." }
    }
    finally {
        Pop-Location
    }

    $wheel = @(Get-ChildItem -LiteralPath $outputDirectory -Filter "*.whl")
    $sdist = @(Get-ChildItem -LiteralPath $outputDirectory -Filter "*.tar.gz")
    if ($wheel.Count -ne 1 -or $sdist.Count -ne 1) {
        throw "Expected one wheel and one sdist; found wheel=$($wheel.Count) sdist=$($sdist.Count)."
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($wheel[0].FullName)
    try {
        $wheelFiles = @($archive.Entries |
            Where-Object { -not $_.FullName.EndsWith("/") } |
            ForEach-Object { $_.FullName.Replace("\", "/") } |
            Sort-Object -Unique)
    }
    finally {
        $archive.Dispose()
    }

    $tarExecutable = if ($env:OS -eq "Windows_NT") { "tar.exe" } else { "tar" }
    $sdistFiles = @(& $tarExecutable -tf $sdist[0].FullName |
        ForEach-Object {
            $path = $_.Replace("\", "/")
            if ($path.Contains("/")) { $path.Substring($path.IndexOf("/") + 1) }
        } |
        Where-Object { $_ -and -not $_.EndsWith("/") } |
        Sort-Object -Unique)
    if ($LASTEXITCODE -ne 0) { throw "Cannot inspect sdist." }

    foreach ($artifact in @(@{ Name = "wheel"; Files = $wheelFiles }, @{ Name = "sdist"; Files = $sdistFiles })) {
        $forbidden = @($artifact.Files | Where-Object {
            $_ -match '^(tests?|samples?|examples?|docsrc|docs|internal_docs|scripts|tools)/' -or
            $_ -match '(^|/)(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache)(/|$)'
        })
        if ($forbidden.Count -ne 0) {
            throw "$($artifact.Name) contains repository-only files: $($forbidden -join ', ')"
        }
    }

    if (@($wheelFiles | Where-Object { $_ -match '\.dist-info/METADATA$' }).Count -ne 1 -or
        @($wheelFiles | Where-Object { $_ -match '\.dist-info/(licenses/)?LICENSE$' }).Count -ne 1 -or
        "toyopuc/py.typed" -notin $wheelFiles) {
        throw "Wheel is missing metadata, license, or py.typed."
    }
    $missingSdist = @(@("LICENSE", "README.md", "pyproject.toml", "toyopuc/py.typed") |
        Where-Object { $_ -notin $sdistFiles -and $_ -ne "toyopuc/py.typed" }
    )
    if (@($sdistFiles | Where-Object { $_ -eq "toyopuc/py.typed" -or $_ -eq "src/toyopuc/py.typed" }).Count -ne 1) {
        $missingSdist += "toyopuc/py.typed"
    }
    if ($missingSdist.Count -ne 0) {
        throw "sdist is missing required consumer files: $($missingSdist -join ', ')"
    }

    $consumerDirectory = Join-Path $outputDirectory "isolated-consumer"
    $venvDirectory = Join-Path $consumerDirectory ".venv"
    [void](New-Item -ItemType Directory -Path $consumerDirectory -Force)
    & python -m venv $venvDirectory
    if ($LASTEXITCODE -ne 0) { throw "Cannot create isolated wheel-consumer virtual environment." }

    $venvPython = if ($env:OS -eq "Windows_NT") {
        Join-Path $venvDirectory "Scripts/python.exe"
    }
    else {
        Join-Path $venvDirectory "bin/python"
    }
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        throw "Isolated virtual-environment Python was not created: $venvPython"
    }

    $previousPythonPath = $env:PYTHONPATH
    try {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
        & $venvPython -I -m pip install --no-index --no-deps $wheel[0].FullName
        if ($LASTEXITCODE -ne 0) { throw "Cannot install the wheel into the isolated consumer environment." }

        $consumerSmoke = @'
import inspect
import sys
from importlib.metadata import version
from pathlib import Path

import toyopuc

expected = (
    "ToyopucClient",
    "ToyopucDeviceClient",
    "open_and_connect",
    "read_typed",
    "write_typed",
    "read_named",
    "poll",
    "write_bit_in_word",
)
if not inspect.getdoc(toyopuc):
    raise SystemExit("toyopuc package docstring is missing")
if not isinstance(toyopuc.__all__, list):
    raise SystemExit("toyopuc.__all__ is not a list")
for name in expected:
    if name not in toyopuc.__all__:
        raise SystemExit(f"public symbol is missing from toyopuc.__all__: {name}")
    value = getattr(toyopuc, name)
    if not inspect.getdoc(value):
        raise SystemExit(f"public symbol docstring is missing: {name}")
    inspect.signature(value)
module_path = Path(toyopuc.__file__).resolve()
environment_root = Path(sys.prefix).resolve()
if not module_path.is_relative_to(environment_root):
    raise SystemExit(f"toyopuc was not imported from the isolated environment: {module_path}")
if version("plc-comm-toyopuc") != toyopuc.__version__:
    raise SystemExit("installed distribution and runtime versions differ")
print(f"[OK] isolated wheel consumer imported {module_path} and checked {len(expected)} public symbols")
'@
        $consumerSmokePath = Join-Path $consumerDirectory "wheel_consumer_smoke.py"
        [System.IO.File]::WriteAllText(
            $consumerSmokePath,
            $consumerSmoke,
            [System.Text.UTF8Encoding]::new($false)
        )
        Push-Location $consumerDirectory
        try {
            & $venvPython -I $consumerSmokePath
            if ($LASTEXITCODE -ne 0) { throw "Isolated wheel-consumer API smoke failed." }
        }
        finally {
            Pop-Location
        }
    }
    finally {
        $env:PYTHONPATH = $previousPythonPath
    }

    Write-Host "[OK] Python package content and isolated consumer passed: wheel=$($wheelFiles.Count) sdist=$($sdistFiles.Count)"
}
finally {
    if (Test-Path -LiteralPath $outputDirectory) {
        Remove-Item -LiteralPath $outputDirectory -Recurse -Force
    }
}
