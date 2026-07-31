[CmdletBinding()]
param(
    [string]$Treeish = "HEAD",
    [switch]$Worktree,
    [switch]$UseWorktreeAttributes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$workRoot = Join-Path $repositoryRoot ("build/source-archive-check-" + [guid]::NewGuid().ToString("N"))
$archivePath = Join-Path $workRoot "source.zip"
$extractRoot = Join-Path $workRoot "extracted"

$forbiddenFileNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
@(
    ".gitattributes",
    ".gitignore"
) | ForEach-Object { [void]$forbiddenFileNames.Add($_) }

$forbiddenPrefixes = @(
    ".codex",
    ".pio",
    ".tools",
    "build",
    "build_win",
    "local_folder",
    "release-artifacts"
)

try {
    [void](New-Item -ItemType Directory -Path $workRoot -Force)

    & git -C $repositoryRoot rev-parse --verify "$Treeish`^{tree}" *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot resolve treeish '$Treeish'."
    }

    $useWorktreeSnapshot = $Worktree -or $UseWorktreeAttributes
    $archiveTreeish = $Treeish
    if ($useWorktreeSnapshot) {
        $temporaryIndex = Join-Path $workRoot "worktree.index"
        $previousIndex = $env:GIT_INDEX_FILE
        try {
            $env:GIT_INDEX_FILE = $temporaryIndex
            & git -C $repositoryRoot read-tree $Treeish
            if ($LASTEXITCODE -ne 0) { throw "Cannot initialize the temporary worktree index." }
            & git -C $repositoryRoot add -A -- .
            if ($LASTEXITCODE -ne 0) { throw "Cannot stage the complete worktree in the temporary index." }
            $archiveTreeish = (& git -C $repositoryRoot write-tree).Trim()
            if ($LASTEXITCODE -ne 0 -or -not $archiveTreeish) {
                throw "Cannot create the synthetic worktree tree."
            }
        }
        finally {
            $env:GIT_INDEX_FILE = $previousIndex
        }
    }

    $archiveArguments = @("archive", "--format=zip", "--output=$archivePath")
    if ($useWorktreeSnapshot) { $archiveArguments += "--worktree-attributes" }
    $archiveArguments += $archiveTreeish
    & git -C $repositoryRoot @archiveArguments
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $archivePath)) {
        throw "git archive failed for '$archiveTreeish'."
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
    try {
        $archiveFiles = @(
            $archive.Entries |
                ForEach-Object { $_.FullName.Replace("\", "/") } |
                Where-Object { -not $_.EndsWith("/") } |
                Sort-Object -Unique
        )
    }
    finally {
        $archive.Dispose()
    }
    $trackedFiles = @(& git -C $repositoryRoot ls-tree -r --name-only $archiveTreeish |
        ForEach-Object { $_.Replace("\", "/") } |
        Sort-Object -Unique)
    if ($LASTEXITCODE -ne 0) { throw "Cannot enumerate files for '$archiveTreeish'." }

    $requiredTracked = @($trackedFiles | Where-Object {
        $_ -match '^(test|tests|\.github|docsrc/maintainer|internal_docs|scripts|tools)/' -or
        $_ -in @("AGENTS.md", "TODO.md", "release_check.bat", "run_ci.bat")
    })
    $missingTracked = @($requiredTracked | Where-Object { $_ -notin $archiveFiles })
    if ($missingTracked.Count -ne 0) {
        throw "Source archive omits tracked validation or maintainer material: $($missingTracked -join ', ')"
    }

    foreach ($guide in @("GETTING_STARTED.md", "USAGE_GUIDE.md", "PROFILES.md", "GOTCHAS.md", "API_REFERENCE.md")) {
        $guideCandidates = @("docsrc/user/$guide", "docs/$guide")
        if (@($guideCandidates | Where-Object { $_ -in $archiveFiles }).Count -eq 0) {
            throw "Source archive is missing standard user guide '$guide'."
        }
    }


    $forbidden = @(
        foreach ($path in $archiveFiles) {
            $fileName = [System.IO.Path]::GetFileName($path)
            $lowerPath = $path.ToLowerInvariant()
            $hasForbiddenPrefix = $false
            foreach ($prefix in $forbiddenPrefixes) {
                $lowerPrefix = $prefix.ToLowerInvariant()
                if ($lowerPath -eq $lowerPrefix -or $lowerPath.StartsWith("$lowerPrefix/")) {
                    $hasForbiddenPrefix = $true
                    break
                }
            }
            if ($forbiddenFileNames.Contains($fileName) -or $hasForbiddenPrefix) {
                $path
            }
        }
    )
    if ($forbidden.Count -ne 0) {
        throw "Source archive contains forbidden generated or release-output files: $($forbidden -join ', ')"
    }

    $requiredRootFiles = @("CHANGELOG.md", "LICENSE", "README.md")
    $missingRootFiles = @($requiredRootFiles | Where-Object { $_ -notin $archiveFiles })
    if ($missingRootFiles.Count -ne 0) {
        throw "Source archive is missing required root files: $($missingRootFiles -join ', ')"
    }

    $expectedSamples = @(
        & git -C $repositoryRoot ls-tree -r --name-only $archiveTreeish -- examples samples |
            ForEach-Object { $_.Replace("\", "/") } |
            Sort-Object -Unique
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot enumerate samples for '$archiveTreeish'."
    }
    if ($expectedSamples.Count -eq 0) {
        throw "No tracked files were found under examples/ or samples/."
    }

    $actualSamples = @(
        $archiveFiles |
            Where-Object { $_.StartsWith("examples/") -or $_.StartsWith("samples/") } |
            Sort-Object -Unique
    )
    $sampleDifference = @(Compare-Object -ReferenceObject $expectedSamples -DifferenceObject $actualSamples -CaseSensitive)
    if ($sampleDifference.Count -ne 0) {
        $differenceText = ($sampleDifference | ForEach-Object { "$($_.SideIndicator) $($_.InputObject)" }) -join "; "
        throw "Source archive sample set differs from the tracked sample set: $differenceText"
    }

    $expectedTests = @(
        & git -C $repositoryRoot ls-tree -r --name-only $archiveTreeish -- tests |
            ForEach-Object { $_.Replace("\", "/") } |
            Sort-Object -Unique
    )
    if ($LASTEXITCODE -ne 0 -or $expectedTests.Count -eq 0) {
        throw "Cannot enumerate tests for '$archiveTreeish'."
    }
    $actualTests = @($archiveFiles | Where-Object { $_.StartsWith("tests/") } | Sort-Object -Unique)
    $testDifference = @(Compare-Object -ReferenceObject $expectedTests -DifferenceObject $actualTests -CaseSensitive)
    if ($testDifference.Count -ne 0) {
        $differenceText = ($testDifference | ForEach-Object { "$($_.SideIndicator) $($_.InputObject)" }) -join "; "
        throw "Source archive test set differs from the tracked test set: $differenceText"
    }

    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractRoot
    Push-Location $extractRoot
    $previousArchivePythonPath = $env:PYTHONPATH
    try {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
        if ($env:OS -eq "Windows_NT") {
            & cmd.exe /d /c run_ci.bat
            if ($LASTEXITCODE -ne 0) { throw "Full non-hardware gate failed in the extracted source archive." }
        }
        else {
            & python -m ruff check toyopuc tests scripts samples
            if ($LASTEXITCODE -ne 0) { throw "Ruff lint failed in the extracted source archive." }
            & python -m ruff format --check toyopuc tests scripts samples
            if ($LASTEXITCODE -ne 0) { throw "Ruff format failed in the extracted source archive." }
            & python -m mypy toyopuc
            if ($LASTEXITCODE -ne 0) { throw "Mypy failed in the extracted source archive." }
            foreach ($path in @(Get-ChildItem scripts, samples -Filter "*.py" -File)) {
                & python -m py_compile $path.FullName
                if ($LASTEXITCODE -ne 0) { throw "Python compilation failed for '$($path.FullName)'." }
            }
            & python scripts/check_public_api_docs.py
            if ($LASTEXITCODE -ne 0) { throw "Public API documentation check failed in the extracted source archive." }
            & python -m pytest tests
            if ($LASTEXITCODE -ne 0) { throw "Tests failed in the extracted source archive." }
            & python -m PyInstaller --onefile --noconfirm --specpath build --distpath publish --name toyopuc scripts/interactive_cli.py
            if ($LASTEXITCODE -ne 0) { throw "CLI consumer build failed in the extracted source archive." }
        }
        & (Join-Path $extractRoot "scripts/check_package_contents.ps1")
        if ($LASTEXITCODE -ne 0) { throw "Package and isolated-consumer gate failed in the extracted source archive." }
    }
    finally {
        $env:PYTHONPATH = $previousArchivePythonPath
        Pop-Location
    }

    $sourceLabel = if ($useWorktreeSnapshot) { "worktree" } else { $Treeish }
    Write-Host "[OK] Source archive contract passed: source=$sourceLabel files=$($archiveFiles.Count) samples=$($actualSamples.Count) tests=$($actualTests.Count) full-gate=true package-consumer=true"
}
finally {
    Remove-Item -LiteralPath $workRoot -Recurse -Force -ErrorAction SilentlyContinue
}
