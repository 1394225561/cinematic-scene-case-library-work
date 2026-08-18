$ErrorActionPreference = 'Stop'

$workRoot = 'D:\1_AIGC\SeeDance\cinematic-scene-case-library-work'
$installRoot = 'C:\Users\Admin\.agents\skills'
$caseSource = Join-Path $workRoot 'skill\cinematic-scene-case-library'
$caseTarget = Join-Path $installRoot 'cinematic-scene-case-library'
$seedanceTarget = Join-Path $installRoot 'cinema-studio-production\SKILL.md'
$h3Target = Join-Path $installRoot 'minimax-h3-director\SKILL.md'
$seedancePatch = Join-Path $workRoot 'integration\cinema-studio-production.patch.md'
$h3Patch = Join-Path $workRoot 'integration\minimax-h3-director.patch.md'
$runDir = Join-Path $workRoot 'data\runs\stage-8-install'
$backupDir = Join-Path $runDir 'backup'
$manifestPath = Join-Path $runDir 'installation-manifest.json'

$expectedSeedanceHash = '891ddce7d62004900e6e67f5581d6dccfc9713dcc493ae2fc37ec92c26211034'
$expectedH3Hash = '98296eaab78dc44444ad5f6196e266fb96e62be26dc9dc96280320e2b80b291c'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$createdCaseTarget = $false

function Get-LowerHash([string] $Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Extract-InsertSection([string] $PatchPath) {
    $patchText = [IO.File]::ReadAllText($PatchPath)
    $fence = [char]96
    $pattern = '## Insert this section\s+' + $fence + $fence + $fence + 'markdown\s*(.*?)\s*' + $fence + $fence + $fence
    $match = [regex]::Match($patchText, $pattern, [Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $match.Success) {
        throw "Could not extract insertion section from $PatchPath"
    }
    return $match.Groups[1].Value.Trim()
}

try {
    if (-not (Test-Path -LiteralPath $caseSource -PathType Container)) {
        throw "Candidate Skill source is missing: $caseSource"
    }
    if (Test-Path -LiteralPath $caseTarget) {
        throw "Install target already exists; refusing to overwrite: $caseTarget"
    }
    if ((Get-LowerHash $seedanceTarget) -ne $expectedSeedanceHash) {
        throw 'Seedance target hash drifted before install.'
    }
    if ((Get-LowerHash $h3Target) -ne $expectedH3Hash) {
        throw 'H3 target hash drifted before install.'
    }
    if ((Select-String -LiteralPath $seedanceTarget -Pattern '^## Compose mixed requests$').Count -ne 1) {
        throw 'Seedance patch anchor is not unique.'
    }
    if ((Select-String -LiteralPath $h3Target -Pattern '^## Select the H3 mode$').Count -ne 1) {
        throw 'H3 patch anchor is not unique.'
    }
    if (Test-Path -LiteralPath $runDir) {
        throw "Stage 8 run directory already exists; refusing to overwrite: $runDir"
    }

    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    $seedanceBackup = Join-Path $backupDir 'cinema-studio-production.SKILL.md.before'
    $h3Backup = Join-Path $backupDir 'minimax-h3-director.SKILL.md.before'
    Copy-Item -LiteralPath $seedanceTarget -Destination $seedanceBackup
    Copy-Item -LiteralPath $h3Target -Destination $h3Backup

    $targets = @(
        [ordered]@{
            Name = 'seedance'
            Target = $seedanceTarget
            Patch = $seedancePatch
            Anchor = '## Compose mixed requests'
        },
        [ordered]@{
            Name = 'h3'
            Target = $h3Target
            Patch = $h3Patch
            Anchor = '## Select the H3 mode'
        }
    )

    foreach ($item in $targets) {
        $section = Extract-InsertSection $item.Patch
        $currentText = [IO.File]::ReadAllText($item.Target)
        if (($currentText.Split($item.Anchor).Count - 1) -ne 1) {
            throw "Anchor occurrence changed during install: $($item.Target)"
        }
        $newText = $currentText.Replace(
            $item.Anchor,
            $section + [Environment]::NewLine + [Environment]::NewLine + $item.Anchor
        )
        $tempPath = Join-Path (
            Split-Path -Parent $item.Target
        ) ('.stage8-' + $item.Name + '-' + [guid]::NewGuid().ToString('N') + '.tmp')
        [IO.File]::WriteAllText($tempPath, $newText, $utf8NoBom)
        Move-Item -LiteralPath $tempPath -Destination $item.Target -Force
    }

    $seedanceBody = [IO.File]::ReadAllText($seedanceTarget)
    $h3Body = [IO.File]::ReadAllText($h3Target)
    if (($seedanceBody.Split('## Retrieve an optional scene case').Count - 1) -ne 1) {
        throw 'Seedance patch verification failed.'
    }
    if (($h3Body.Split('## Retrieve an optional scene case').Count - 1) -ne 1) {
        throw 'H3 patch verification failed.'
    }
    if ((Get-LowerHash $seedanceTarget) -eq $expectedSeedanceHash) {
        throw 'Seedance target did not change after patch.'
    }
    if ((Get-LowerHash $h3Target) -eq $expectedH3Hash) {
        throw 'H3 target did not change after patch.'
    }

    Copy-Item -LiteralPath $caseSource -Destination $caseTarget -Recurse
    $createdCaseTarget = $true
    $installedFiles = @(Get-ChildItem -LiteralPath $caseTarget -Recurse -File)
    $manifest = [ordered]@{
        stage = '8'
        status = 'installed'
        installed_at_utc = [DateTime]::UtcNow.ToString('o')
        source_skill = $caseSource
        installed_skill = $caseTarget
        installed_file_count = $installedFiles.Count
        installed_skill_manifest_sha256 = (Get-LowerHash (Join-Path $caseTarget 'references\build-manifest.json'))
        target_before_sha256 = [ordered]@{
            seedance = $expectedSeedanceHash
            h3 = $expectedH3Hash
        }
        target_after_sha256 = [ordered]@{
            seedance = (Get-LowerHash $seedanceTarget)
            h3 = (Get-LowerHash $h3Target)
        }
        backups = @($seedanceBackup, $h3Backup)
    }
    $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding utf8
    $manifest | ConvertTo-Json -Depth 6
}
catch {
    if ($createdCaseTarget -and (Test-Path -LiteralPath $caseTarget)) {
        Remove-Item -LiteralPath $caseTarget -Recurse -Force
    }
    $seedanceBackup = Join-Path $backupDir 'cinema-studio-production.SKILL.md.before'
    $h3Backup = Join-Path $backupDir 'minimax-h3-director.SKILL.md.before'
    if (Test-Path -LiteralPath $seedanceBackup) {
        Copy-Item -LiteralPath $seedanceBackup -Destination $seedanceTarget -Force
    }
    if (Test-Path -LiteralPath $h3Backup) {
        Copy-Item -LiteralPath $h3Backup -Destination $h3Target -Force
    }
    throw
}
