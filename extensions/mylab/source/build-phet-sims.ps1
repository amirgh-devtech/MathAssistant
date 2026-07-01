# build-phet-sims.ps1
# PhET Simulation Build Script v1.3.0
# Builds PhET simulations and embeds custom fonts via base64
# Usage: .\build-phet-sims.ps1 [-CleanBuild] [-OnlySims "sim1","sim2"] [-SkipFontInjection]

param(
    [string]$ConfigFile = "build-list.json",
    [string]$SourceDir = $PSScriptRoot,
    [switch]$CleanBuild = $false,
    [string[]]$OnlySims = @(),
    [switch]$SkipFontInjection = $false
)

$ErrorActionPreference = "Continue"

# Ensure UTF-8 encoding
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

# Load fnm if Node not found
try {
    $null = node --version 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Node not in path" }
} catch {
    Write-Host "Loading fnm..." -ForegroundColor Cyan
    fnm env --use-on-cd --shell powershell | Out-String | Invoke-Expression
}

# Load configuration
$configPath = Join-Path $SourceDir $ConfigFile
if (-not (Test-Path $configPath)) {
    Write-Host "ERROR: Configuration file not found: $configPath" -ForegroundColor Red
    exit 1
}

try {
    $config = Get-Content $configPath -Raw | ConvertFrom-Json
} catch {
    Write-Host "ERROR: Invalid JSON in $configPath : $_" -ForegroundColor Red
    exit 1
}

# Setup logging
$logDir = Join-Path $SourceDir "build-logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$logFile = Join-Path $logDir "build-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"

    switch ($Level) {
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "ERROR"   { Write-Host $logMessage -ForegroundColor Red }
        "WARN"    { Write-Host $logMessage -ForegroundColor Yellow }
        default   { Write-Host $logMessage -ForegroundColor White }
    }

    $logMessage | Out-File -FilePath $logFile -Append -Encoding utf8
}

# Verify Node.js version
function Test-NodeVersion {
    try {
        $nodeVersion = (node --version 2>&1).Trim()
        $expected = $config.node_version

        if ($nodeVersion -ne "v$expected") {
            Write-Log "Node version mismatch! Expected: v$expected, Found: $nodeVersion" "WARN"
            Write-Log "Switching via fnm..." "INFO"
            fnm use $expected 2>&1 | Out-Null
            $nodeVersion = (node --version 2>&1).Trim()
            if ($nodeVersion -ne "v$expected") {
                Write-Log "Failed to switch Node version" "ERROR"
                return $false
            }
        }
        Write-Log "Node version OK: $nodeVersion" "SUCCESS"
        return $true
    } catch {
        Write-Log "Node.js error: $_" "ERROR"
        return $false
    }
}

# Check simulation directory exists
function Test-Simulation {
    param([string]$SimName)
    return (Test-Path (Join-Path $SourceDir "$SimName\package.json"))
}

# Install npm dependencies
function Install-SimDependencies {
    param([string]$SimName)

    $simPath = Join-Path $SourceDir $SimName
    Set-Location $simPath

    if ($CleanBuild) {
        Write-Log "Cleaning node_modules for $SimName..." "INFO"
        if (Test-Path "node_modules") {
            Remove-Item -Recurse -Force "node_modules" -ErrorAction SilentlyContinue
        }
    }

    if (-not $CleanBuild -and (Test-Path "node_modules")) {
        Write-Log "Skipping npm install (node_modules exists)" "INFO"
        return
    }

    Write-Log "Running npm install for $SimName..." "INFO"
    $output = npm install --no-audit --no-fund 2>&1
    if ($output) {
        $output | ForEach-Object { Write-Log "  [npm] $_" "INFO" }
    }

    if ($LASTEXITCODE -ne 0) {
        throw "npm install failed (exit code: $LASTEXITCODE)"
    }
    Write-Log "npm install done" "SUCCESS"
}

# Build simulation with grunt
function Build-Simulation {
    param([string]$SimName)

    $simPath = Join-Path $SourceDir $SimName
    Set-Location $simPath

    $buildCmd = $config.build_command
    Write-Log "Building: $buildCmd" "INFO"

    $output = Invoke-Expression $buildCmd 2>&1
    if ($output) {
        $output | ForEach-Object { Write-Log "  [build] $_" "INFO" }
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Build failed (exit code: $LASTEXITCODE)"
    }
    Write-Log "Build completed" "SUCCESS"
}

# Check if output HTML exists
function Test-BuildOutput {
    param([string]$SimName, [string]$OutputFile)

    $outputPath = Join-Path $SourceDir "$SimName\$($config.output_dir)\$OutputFile"

    if (Test-Path $outputPath) {
        $sizeKB = [math]::Round((Get-Item $outputPath).Length / 1KB, 2)
        Write-Log "Output: $OutputFile ($sizeKB KB)" "SUCCESS"
        return $true
    }
    Write-Log "Output NOT found: $outputPath" "ERROR"
    return $false
}

# Embed font as base64 into HTML
function Inject-Font {
    param([string]$SimName, [string]$HtmlFile)

    $fontCfg = $config.font_injection
    if (-not $fontCfg -or -not $fontCfg.enabled) {
        Write-Log "Font injection disabled" "INFO"
        return
    }

    # Build HTML path
    $htmlPath = "$SourceDir\$SimName\$($config.output_dir)\$HtmlFile"
    if (-not (Test-Path $htmlPath)) {
        Write-Log "HTML not found: $htmlPath" "WARN"
        return
    }

    # Build font path
    $fontFileName = $fontCfg.font_file
    if ($fontFileName -match '[/\\]') {
        $fontFileName = Split-Path $fontFileName -Leaf
    }
    $fontPath = "$SourceDir\assets\fonts\$fontFileName"

    if (-not (Test-Path $fontPath)) {
        Write-Log "Font file not found: $fontPath" "ERROR"
        return
    }

    try {
        # Read font as base64
        $fontBytes = [System.IO.File]::ReadAllBytes($fontPath)
        $fontB64 = [System.Convert]::ToBase64String($fontBytes)

        # Detect font format
        $ext = [System.IO.Path]::GetExtension($fontPath).TrimStart('.').ToLower()
        if ($ext -eq 'ttf') { $format = 'truetype' }
        elseif ($ext -eq 'otf') { $format = 'opentype' }
        elseif ($ext -eq 'woff') { $format = 'woff' }
        elseif ($ext -eq 'woff2') { $format = 'woff2' }
        else { $format = 'truetype' }

        # Build CSS string
        $family = $fontCfg.font_family
        $css = "@font-face{font-family:'$family';src:url(data:font/$format;base64,$fontB64) format('$format');font-weight:normal;font-style:normal;}html,body,div,p,span,button,input,select,textarea,h1,h2,h3,h4,h5,h6,a,li,td,th,label{font-family:'$family',Tahoma,Arial,sans-serif !important;}"

        # Read HTML file
        $html = [System.IO.File]::ReadAllText($htmlPath, [System.Text.Encoding]::UTF8)

        # Check for </head> tag
        if ($html -notmatch '</head>') {
            Write-Log "No </head> tag found in HTML" "ERROR"
            return
        }

        # Inject CSS before </head>
        $html = $html -replace '</head>', "<style>$css</style></head>"

        # Write modified HTML back
        [System.IO.File]::WriteAllText($htmlPath, $html, [System.Text.Encoding]::UTF8)

        # Report new size
        $newSize = [math]::Round((Get-Item $htmlPath).Length / 1KB, 2)
        Write-Log "Font embedded successfully! New size: $newSize KB" "SUCCESS"

    } catch {
        Write-Log "Font injection failed: $_" "ERROR"
    }
}

# === MAIN BUILD FUNCTION ===

function Start-Build {
    Write-Log "========================================" "INFO"
    Write-Log "  PhET Build Script v1.3.0" "INFO"
    Write-Log "========================================" "INFO"
    Write-Log "Source: $SourceDir" "INFO"
    Write-Log "Config: $ConfigFile" "INFO"
    Write-Log "Log: $logFile" "INFO"

    if (-not (Test-NodeVersion)) {
        Write-Log "Aborting - Node version check failed" "ERROR"
        Set-Location $SourceDir
        return
    }

    # Determine which sims to build
    $allSims = $config.simulations.PSObject.Properties.Name
    $simsToBuild = if ($OnlySims.Count -gt 0) {
        $OnlySims | Where-Object { $_ -in $allSims }
    } else {
        $allSims
    }

    if ($simsToBuild.Count -eq 0) {
        Write-Log "No simulations to build!" "ERROR"
        Set-Location $SourceDir
        return
    }

    Write-Log "`nSimulations to build: $($simsToBuild.Count)" "INFO"
    foreach ($s in $simsToBuild) {
        $info = $config.simulations.$s
        Write-Log "  - $s | $($info.name_fa) | Grade $($info.grade) $($info.subject)" "INFO"
    }

    # Build loop
    $ok = 0
    $fail = 0
    $failed = @()
    $startTime = Get-Date

    foreach ($sim in $simsToBuild) {
        $t1 = Get-Date
        Write-Log "`n--- $sim ---" "INFO"
        try {
            if (-not (Test-Simulation $sim)) {
                throw "Simulation not found"
            }

            Install-SimDependencies $sim
            Build-Simulation $sim

            $outFile = $config.simulations.$sim.output_file
            if (-not (Test-BuildOutput $sim $outFile)) {
                throw "Output check failed"
            }

            if (-not $SkipFontInjection) {
                Inject-Font $sim $outFile
            } else {
                Write-Log "Font injection skipped (--SkipFontInjection)" "INFO"
            }

            $dur = [math]::Round(((Get-Date) - $t1).TotalSeconds, 1)
            Write-Log "Done in ${dur}s" "SUCCESS"
            $ok++

        } catch {
            Write-Log "FAILED: $_" "ERROR"
            $fail++
            $failed += $sim
        }
    }

    # Summary
    $totalMin = [math]::Round(((Get-Date) - $startTime).TotalMinutes, 1)

    Write-Log "`n========================================" "INFO"
    Write-Log "  BUILD SUMMARY" "INFO"
    Write-Log "========================================" "INFO"
    Write-Log "Success: $ok / $($simsToBuild.Count)" "SUCCESS"
    Write-Log "Failed:  $fail" "ERROR"
    Write-Log "Duration: $totalMin min" "INFO"
    Write-Log "Log: $logFile" "INFO"

    if ($failed.Count -gt 0) {
        Write-Log "Failed sims: $($failed -join ', ')" "ERROR"
    }

    Set-Location $SourceDir
}

# Run
Start-Build
