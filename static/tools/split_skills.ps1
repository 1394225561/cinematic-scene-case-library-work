$ErrorActionPreference = 'Stop'

$workspace = Split-Path -Parent $PSScriptRoot
$stagingRoot = Join-Path $workspace '.skill-staging'
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Write-Utf8File {
    param(
        [Parameter(Mandatory)] [string] $Path,
        [Parameter(Mandatory)] [string] $Content
    )

    $parent = Split-Path -Parent $Path
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    [System.IO.File]::WriteAllText($Path, $Content.TrimEnd() + "`n", $utf8NoBom)
}

function Get-SourceLines {
    param([Parameter(Mandatory)] [string] $Path)

    return [System.IO.File]::ReadAllLines($Path, $utf8NoBom)
}

function Get-LineRange {
    param(
        [Parameter(Mandatory)] [AllowEmptyString()] [string[]] $Lines,
        [Parameter(Mandatory)] [int] $Start,
        [Parameter(Mandatory)] [int] $End
    )

    if ($Start -lt 1 -or $End -gt $Lines.Count -or $Start -gt $End) {
        throw "Invalid source range ${Start}-${End} for a $($Lines.Count)-line file."
    }

    return ($Lines[($Start - 1)..($End - 1)] -join "`n")
}

function New-ReferenceContent {
    param(
        [Parameter(Mandatory)] [string] $Title,
        [Parameter(Mandatory)] [string] $Purpose,
        [Parameter(Mandatory)] [string[]] $Contents,
        [Parameter(Mandatory)] [string[]] $Chunks
    )

    $sourceLineCount = 0
    foreach ($chunk in $Chunks) {
        $sourceLineCount += ($chunk -split "`n").Count
    }

    $parts = [System.Collections.Generic.List[string]]::new()
    $parts.Add("# $Title")
    $parts.Add('')
    $parts.Add($Purpose)
    if ($sourceLineCount -gt 100) {
        $toc = $Contents | ForEach-Object { "- $_" }
        $parts.Add('')
        $parts.Add('## Contents')
        $parts.Add('')
        $parts.Add(($toc -join "`n"))
    }
    $parts.Add('')
    $parts.Add(($Chunks -join "`n`n---`n`n"))
    return $parts -join "`n"
}

function Assert-ExactCoverage {
    param(
        [Parameter(Mandatory)] [int] $SourceLineCount,
        [Parameter(Mandatory)] [object[]] $Ranges,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [int[]] $ExcludedLines,
        [Parameter(Mandatory)] [string] $Label
    )

    $counts = [int[]]::new($SourceLineCount + 1)
    foreach ($range in $Ranges) {
        for ($line = $range.Start; $line -le $range.End; $line++) {
            $counts[$line]++
        }
    }

    $excluded = [System.Collections.Generic.HashSet[int]]::new()
    foreach ($line in $ExcludedLines) {
        $excluded.Add($line) | Out-Null
    }

    $missing = [System.Collections.Generic.List[int]]::new()
    $duplicate = [System.Collections.Generic.List[int]]::new()
    for ($line = 1; $line -le $SourceLineCount; $line++) {
        if ($excluded.Contains($line)) {
            if ($counts[$line] -ne 0) {
                throw "$Label excluded line $line was unexpectedly assigned."
            }
            continue
        }
        if ($counts[$line] -eq 0) { $missing.Add($line) }
        if ($counts[$line] -gt 1) { $duplicate.Add($line) }
    }

    if ($missing.Count -gt 0 -or $duplicate.Count -gt 0) {
        throw "$Label coverage failed. Missing: $($missing -join ', '); duplicate: $($duplicate -join ', ')."
    }
}

function Write-SplitReferences {
    param(
        [Parameter(Mandatory)] [AllowEmptyString()] [string[]] $SourceLines,
        [Parameter(Mandatory)] [string] $Destination,
        [Parameter(Mandatory)] [hashtable[]] $Modules
    )

    foreach ($module in $Modules) {
        $chunks = foreach ($range in $module.Ranges) {
            $chunk = Get-LineRange -Lines $SourceLines -Start $range.Start -End $range.End
            if ($range.Label) {
                "## Source context: $($range.Label)`n`n$chunk"
            }
            else {
                $chunk
            }
        }
        $content = New-ReferenceContent `
            -Title $module.Title `
            -Purpose $module.Purpose `
            -Contents $module.Contents `
            -Chunks $chunks
        Write-Utf8File -Path (Join-Path $Destination $module.File) -Content $content

        $written = [System.IO.File]::ReadAllText((Join-Path $Destination $module.File), $utf8NoBom)
        foreach ($range in $module.Ranges) {
            $sourceChunk = Get-LineRange -Lines $SourceLines -Start $range.Start -End $range.End
            $first = $written.IndexOf($sourceChunk, [System.StringComparison]::Ordinal)
            if ($first -lt 0) {
                throw "$($module.File) does not contain source range $($range.Start)-$($range.End) verbatim."
            }
            $second = $written.IndexOf($sourceChunk, $first + $sourceChunk.Length, [System.StringComparison]::Ordinal)
            if ($second -ge 0) {
                throw "$($module.File) contains source range $($range.Start)-$($range.End) more than once."
            }
        }
    }
}

function Assert-MarkdownLinks {
    param([Parameter(Mandatory)] [string] $SkillDirectory)

    $markdownFiles = Get-ChildItem -LiteralPath $SkillDirectory -Recurse -File -Filter '*.md'
    foreach ($file in $markdownFiles) {
        $content = [System.IO.File]::ReadAllText($file.FullName, $utf8NoBom)
        foreach ($match in [regex]::Matches($content, '\[[^\]]+\]\(([^)]+\.md)\)')) {
            $target = Join-Path $file.DirectoryName $match.Groups[1].Value
            if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
                throw "Broken Markdown link in $($file.FullName): $($match.Groups[1].Value)"
            }
        }
    }
}

$cinedanceSource = Join-Path $workspace 'my_skills\CINEDANCE HIGGSFIELD SKILL.md'
$liraSource = Join-Path $workspace 'my_skills\LIRA SKILL.md'
$cinedanceLines = Get-SourceLines $cinedanceSource
$liraLines = Get-SourceLines $liraSource

$cinedanceModules = @(
    @{
        File = 'core-workflow.md'
        Title = 'CINEDANCE Core Workflow'
        Purpose = 'Read this reference for every CINEDANCE request. It owns the director method, prompt architecture, context isolation, density and style rules, safe language, final QA, and output contract.'
        Contents = @('Director role and core objective', 'Internal 4-D method and prompt architecture', 'Scene context and output settings', 'Single-take versus multi-shot decision', 'Context isolation', 'Density, style, constraints, language, quality, QA, and output')
        Ranges = @(@{Start=1;End=240}, @{Start=457;End=506}, @{Start=1045;End=1066}, @{Start=1112;End=1330})
    },
    @{
        File = 'spatial-and-references.md'
        Title = 'CINEDANCE Spatial and Reference Control'
        Purpose = 'Read this reference whenever a request creates, changes, or audits subjects, reference tags, location geography, first-frame occupancy, blocking, gaze, orientation, or landmark proximity.'
        Contents = @('Active references and character descriptions', 'Location mapping', 'First-frame and spatial locks', 'Gaze, orientation, and landmark locks', 'Reference hierarchy')
        Ranges = @(@{Start=241;End=456}, @{Start=1067;End=1111})
    },
    @{
        File = 'multi-shot-continuity.md'
        Title = 'CINEDANCE Multi-Shot Continuity'
        Purpose = 'Read this reference only for multi-shot sequences, internal cuts, montage, reverse coverage, insert shots, or continuity repair across cuts.'
        Contents = @('Multi-shot continuity locks', 'Allowed and forbidden cut types')
        Ranges = @(@{Start=507;End=562})
    },
    @{
        File = 'camera-and-optics.md'
        Title = 'CINEDANCE Camera and Optics'
        Purpose = 'Read this reference whenever a request creates, changes, or audits framing, field of view, lens character, camera distance, focus, camera movement, composition, or handheld behavior.'
        Contents = @('Optics control and decision tree', 'Field-of-view language bank', 'Wide and telephoto outcome stacks', 'Lens continuity and anti-drift locks', 'Camera, composition, and handheld behavior')
        Ranges = @(@{Start=563;End=849})
    },
    @{
        File = 'motion-physics-lighting.md'
        Title = 'CINEDANCE Motion, Physics, and Lighting'
        Purpose = 'Read this reference whenever a request creates, changes, or audits physical action, material behavior, movement timing, exposure, light direction, or lighting preservation.'
        Contents = @('Physics and material behavior', 'Lighting priority and direction', 'Action timing')
        Ranges = @(@{Start=850;End=1001})
    },
    @{
        File = 'dialogue-and-audio.md'
        Title = 'CINEDANCE Dialogue and Audio'
        Purpose = 'Read this reference only when the shot contains speech, narration, offscreen sound, prior-line context, lip-sync requirements, silence, or audio-mix constraints.'
        Contents = @('Dialogue constraints', 'Clean dialogue and silence timing', 'Prior audio context')
        Ranges = @(@{Start=1002;End=1044})
    }
)

$liraModules = @(
    @{
        File = 'core-workflow.md'
        Title = 'Lira Core Workflow'
        Purpose = 'Read this reference for every Lira request. It owns the optimization method, task routing, universal anti-fail rules, response format, fixed routing summary, universal checklist, and video handoff note.'
        Contents = @('4-D methodology, modes, and response format', 'Task and model routing', 'Universal anti-fail rules', 'Fixed routing and pre-send checklist', 'Video handoff note')
        Ranges = @(@{Start=19;End=227}, @{Start=248;End=258}, @{Start=352;End=370}, @{Start=614;End=619})
    },
    @{
        File = 'character-generation.md'
        Title = 'Lira Character Generation'
        Purpose = 'Read this reference for character sheets, casting portraits, character portraits, Soul ID character work, Soul 2.0, or Cinema Studio AI Cast.'
        Contents = @('Soul 2.0 character rules', 'Cinema Studio AI Cast rules', 'Photoreal three-panel character-sheet template')
        Ranges = @(@{Start=259;End=275}, @{Start=294;End=302}, @{Start=499;End=540})
    },
    @{
        File = 'scene-location-generation.md'
        Title = 'Lira Scene and Location Generation'
        Purpose = 'Read this reference for locations, environments, cinematic stills, establishing frames, Soul Cinema, reverse angles, or another camera position in the same location.'
        Contents = @('Soul Cinema rules', 'GPT Image 2 location-view role', 'Location and environment template', 'Reverse-angle geometry workflow')
        Ranges = @(@{Start=276;End=293}, @{Start=344;End=345;Label='GPT Image 2 location-view role'}, @{Start=541;End=568}, @{Start=605;End=612;Label='Location view-change workflow'})
    },
    @{
        File = 'prop-generation.md'
        Title = 'Lira Prop Generation'
        Purpose = 'Read this reference for prop sheets, product-style objects, exact in-frame text on objects, or realistic NBP/GPT Image 2 object generation.'
        Contents = @('NBP prop capabilities and parameters', 'GPT Image 2 prop role', 'Prop-sheet template and safeguards')
        Ranges = @(@{Start=309;End=317;Label='Nano Banana Pro prop capabilities'}, @{Start=342;End=343;Label='GPT Image 2 prop capabilities'}, @{Start=569;End=590})
    },
    @{
        File = 'image-editing.md'
        Title = 'Lira Image Editing'
        Purpose = 'Read this reference for every edit of an existing frame, including NBP edits, Seedream texture repair, GPT Image 2 local surgery, and edit-lane QA. For location view changes, also read scene-location-generation.md.'
        Contents = @('NBP edit and location-change rules', 'Seedream texture-only role', 'GPT Image 2 local-edit rules', 'Surgical edit template', 'Image-edit workflow')
        Ranges = @(@{Start=303;End=308}, @{Start=318;End=341;Label='Nano Banana Pro edit continuation'}, @{Start=346;End=351;Label='GPT Image 2 edit continuation'}, @{Start=457;End=482}, @{Start=591;End=604})
    },
    @{
        File = 'generation-style.md'
        Title = 'Lira Generation Style and Building Blocks'
        Purpose = 'Read this reference for new character, scene, location, or prop generation. It owns platform parameters, technical camera and film blocks, palette construction, mood references, positive constraint patterns, and standing generation rules.'
        Contents = @('Platform parameters', 'Technical capture blocks', 'Palette and cinematographer references', 'Positive constraint patterns', 'Standing rules and prompt-type introduction')
        Ranges = @(@{Start=371;End=456}, @{Start=483;End=498})
    }
)

$cinedanceRanges = @($cinedanceModules | ForEach-Object { $_.Ranges } | ForEach-Object { $_ })
Assert-ExactCoverage -SourceLineCount $cinedanceLines.Count -Ranges $cinedanceRanges -ExcludedLines @() -Label 'CINEDANCE'

# The original YAML metadata moves into SKILL.md. Lines 18 and 613 are blank.
# Lines 228-247 are obsolete navigation claiming the modules are merged into one file;
# the new SKILL.md routing table replaces that navigation without dropping domain rules.
$liraExcluded = @(1..18) + @(228..247) + @(613)
$liraRanges = @($liraModules | ForEach-Object { $_.Ranges } | ForEach-Object { $_ })
Assert-ExactCoverage -SourceLineCount $liraLines.Count -Ranges $liraRanges -ExcludedLines $liraExcluded -Label 'LIRA'

$cinedanceDestination = Join-Path $stagingRoot 'cinedance-seedance-director'
$liraDestination = Join-Path $stagingRoot 'lira-image-prompts'
[System.IO.Directory]::CreateDirectory((Join-Path $cinedanceDestination 'references')) | Out-Null
[System.IO.Directory]::CreateDirectory((Join-Path $liraDestination 'references')) | Out-Null
[System.IO.Directory]::CreateDirectory((Join-Path $cinedanceDestination 'agents')) | Out-Null
[System.IO.Directory]::CreateDirectory((Join-Path $liraDestination 'agents')) | Out-Null

$cinedanceSkill = @'
---
name: cinedance-seedance-director
description: Convert a scene, shot brief, storyboard beat, reference set, or existing prompt into a production-ready cinematic Seedance 2.0 or Higgsfield Seedance video prompt. Use when directing or fixing first-frame occupancy, reference tags, spatial blocking, gaze, body orientation, landmark proximity, single-take or multi-shot structure, optics, camera movement, physical motion, lighting, timing, dialogue, audio, continuity, or context leakage.
---

# Cinedance Seedance Director

Always read [references/core-workflow.md](references/core-workflow.md). Classify the task, then completely read the union of applicable references:

- **Complete shot/rewrite:** [spatial-and-references.md](references/spatial-and-references.md), [camera-and-optics.md](references/camera-and-optics.md), and [motion-physics-lighting.md](references/motion-physics-lighting.md).
- **Subjects, tags, geography, first frame, blocking, gaze, orientation, landmarks:** [spatial-and-references.md](references/spatial-and-references.md).
- **Lens, FOV, focus, framing, camera, composition, handheld:** [camera-and-optics.md](references/camera-and-optics.md); also load spatial rules when framing affects placement, direction, gaze, or landmarks.
- **Action, timing, contact, materials, physics, light, exposure:** [motion-physics-lighting.md](references/motion-physics-lighting.md).
- **Speech, narration, offscreen/prior audio, lip-sync, deliberate silence/mix:** [dialogue-and-audio.md](references/dialogue-and-audio.md).
- **Multiple shots, cuts, montage, or cross-cut continuity:** [multi-shot-continuity.md](references/multi-shot-continuity.md) plus camera-and-optics.
- **Comprehensive audit:** all references.

Apply the selected rules as one director system and run the core silent QA. Unless the user explicitly asks for analysis, variants, critique, or explanation, return only the final cinematic English Seedance prompt in the prescribed structure.
'@

$liraSkill = @'
---
name: lira-image-prompts
description: Route, write, repair, and optimize production-ready AI image prompts for cinematic preproduction assets and image edits. Use for character sheets, casting portraits, locations, environments, film stills, props, reference frames, surgical image edits, texture cleanup, or prompts targeting Higgsfield Soul 2.0, Soul Cinema, Cinema Studio AI Cast, Nano Banana Pro, Seedream 4.5, GPT Image 2, or another image model. Do not use as the primary director for a complete Seedance video prompt.
---

# Lira Image Prompts

Always read [references/core-workflow.md](references/core-workflow.md). Classify the task, then completely read the union of applicable references:

- **Character/sheet/portrait, Soul ID, Soul 2.0, AI Cast:** [character-generation.md](references/character-generation.md) plus [generation-style.md](references/generation-style.md).
- **Location/environment/still/establishing frame, Soul Cinema:** [scene-location-generation.md](references/scene-location-generation.md) plus generation-style.
- **Prop/product object/exact object text:** [prop-generation.md](references/prop-generation.md) plus generation-style.
- **Existing-frame edit, NBP, Seedream texture repair, GPT Image 2 surgery:** [image-editing.md](references/image-editing.md).
- **Existing-location reverse angle/new camera position:** scene-location-generation plus image-editing.
- **Comprehensive or mixed review:** all applicable references; load all only for a true full-system task.

Do not load unrelated task references. Keep project building blocks consistent and preserve core routing, edit order, anti-fail rules, response format, and user-language behavior. Hand complete Seedance video-prompt assembly to a dedicated video-director skill when available.
'@

$cinedanceOpenAi = @'
interface:
  display_name: "Cinedance Seedance Director"
  short_description: "Direct production-ready cinematic Seedance prompts"
  default_prompt: "Use $cinedance-seedance-director to turn this scene into a production-ready Seedance prompt."
'@

$liraOpenAi = @'
interface:
  display_name: "Lira Image Prompts"
  short_description: "Route and optimize cinematic AI image prompts"
  default_prompt: "Use $lira-image-prompts to create or refine a production-ready AI image prompt."
'@

Write-Utf8File -Path (Join-Path $cinedanceDestination 'SKILL.md') -Content $cinedanceSkill
Write-Utf8File -Path (Join-Path $liraDestination 'SKILL.md') -Content $liraSkill
Write-Utf8File -Path (Join-Path $cinedanceDestination 'agents\openai.yaml') -Content $cinedanceOpenAi
Write-Utf8File -Path (Join-Path $liraDestination 'agents\openai.yaml') -Content $liraOpenAi
Write-SplitReferences -SourceLines $cinedanceLines -Destination (Join-Path $cinedanceDestination 'references') -Modules $cinedanceModules
Write-SplitReferences -SourceLines $liraLines -Destination (Join-Path $liraDestination 'references') -Modules $liraModules
Assert-MarkdownLinks -SkillDirectory $cinedanceDestination
Assert-MarkdownLinks -SkillDirectory $liraDestination

Write-Output "Generated staged skills under $stagingRoot"
Write-Output "CINEDANCE: $($cinedanceLines.Count) source lines covered exactly once."
Write-Output "LIRA: all substantive source lines covered exactly once; obsolete merged-file navigation replaced."
