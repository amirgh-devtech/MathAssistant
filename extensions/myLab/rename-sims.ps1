# rename-sims.ps1 (Adapted for Iranian Educational Curriculum)
$buildDir = "D:\AMIR-Projects\KhrProject\Main\Forks\Main\MathAssistant\extensions\myLab\LABs"

$simMap = @{
    # ===== (Math) =====
    "area-builder"                            = @{ grade = "GEN"; subject = "MATH" }
    "area-model-algebra"                      = @{ grade = "G9"; subject = "MATH" }
    "area-model-decimals"                     = @{ grade = "GEN"; subject = "MATH" }
    "area-model-introduction"                 = @{ grade = "GEN"; subject = "MATH" }
    "area-model-multiplication"               = @{ grade = "GEN"; subject = "MATH" }
    "balancing-act"                           = @{ grade = "GEN"; subject = "MATH" }
    "build-a-fraction"                        = @{ grade = "GEN"; subject = "MATH" }
    "calculus-grapher"                        = @{ grade = "G12"; subject = "MATH" }
    "center-and-variability"                  = @{ grade = "G11"; subject = "MATH" }
    "curve-fitting"                           = @{ grade = "GEN"; subject = "MATH" }
    "equality-explorer"                       = @{ grade = "G8"; subject = "MATH" }
    "equality-explorer-basics"                = @{ grade = "G8"; subject = "MATH" }
    "equality-explorer-two-variables"         = @{ grade = "G9"; subject = "MATH" }
    "expression-exchange"                     = @{ grade = "G7"; subject = "MATH" }
    "fourier-making-waves"                    = @{ grade = "GEN"; subject = "MATH" }
    "fraction-matcher"                        = @{ grade = "GEN"; subject = "MATH" }
    "fractions-equality"                      = @{ grade = "GEN"; subject = "MATH" }
    "fractions-intro"                         = @{ grade = "GEN"; subject = "MATH" }
    "fractions-mixed-numbers"                 = @{ grade = "GEN"; subject = "MATH" }
    "function-builder"                        = @{ grade = "G10"; subject = "MATH" }
    "function-builder-basics"                 = @{ grade = "G10"; subject = "MATH" }
    "graphing-lines"                          = @{ grade = "G9"; subject = "MATH" }
    "graphing-quadratics"                     = @{ grade = "G10"; subject = "MATH" }
    "graphing-slope-intercept"                = @{ grade = "G9"; subject = "MATH" }
    "least-squares-regression"                = @{ grade = "GEN"; subject = "MATH" }
    "make-a-ten"                              = @{ grade = "GEN"; subject = "MATH" }
    "mean-share-and-balance"                  = @{ grade = "G8"; subject = "MATH" }
    "number-compare"                          = @{ grade = "GEN"; subject = "MATH" }
    "number-line-distance"                    = @{ grade = "G7"; subject = "MATH" }
    "number-line-integers"                    = @{ grade = "G7"; subject = "MATH" }
    "number-line-operations"                  = @{ grade = "G7"; subject = "MATH" }
    "number-play"                             = @{ grade = "GEN"; subject = "MATH" }
    "plinko-probability"                      = @{ grade = "G9"; subject = "MATH" }
    "proportion-playground"                   = @{ grade = "G7"; subject = "MATH" }
    "quadrilateral"                           = @{ grade = "G8"; subject = "MATH" }
    "trig-tour"                               = @{ grade = "G10"; subject = "MATH" }
    "unit-rates"                              = @{ grade = "G7"; subject = "MATH" }
    "vector-addition"                         = @{ grade = "G11"; subject = "MATH" }
    "vector-addition-equations"               = @{ grade = "G11"; subject = "MATH" }

    # ===== (Physics) =====
    "atomic-interactions"                     = @{ grade = "G12"; subject = "PHYS" }
    "balloons-and-static-electricity"         = @{ grade = "G11"; subject = "PHYS" }
    "bending-light"                           = @{ grade = "G12"; subject = "PHYS" }
    "blackbody-spectrum"                      = @{ grade = "GEN"; subject = "PHYS" }
    "buoyancy"                                = @{ grade = "G9"; subject = "PHYS" }
    "capacitor-lab-basics"                    = @{ grade = "G11"; subject = "PHYS" }
    "charges-and-fields"                      = @{ grade = "G11"; subject = "PHYS" }
    "circuit-construction-kit-ac-virtual-lab" = @{ grade = "G11"; subject = "PHYS" }
    "circuit-construction-kit-dc"             = @{ grade = "G11"; subject = "PHYS" }
    "circuit-construction-kit-dc-virtual-lab" = @{ grade = "G11"; subject = "PHYS" }
    "collision-lab"                           = @{ grade = "G12"; subject = "PHYS" }
    "color-vision"                            = @{ grade = "G8"; subject = "PHYS" }
    "coulombs-law"                            = @{ grade = "G11"; subject = "PHYS" }
    "density"                                 = @{ grade = "G10"; subject = "PHYS" }
    "energy-forms-and-changes"                = @{ grade = "G10"; subject = "PHYS" }
    "energy-skate-park"                       = @{ grade = "G10"; subject = "PHYS" }
    "energy-skate-park-basics"                = @{ grade = "G10"; subject = "PHYS" }
    "faradays-law"                            = @{ grade = "G11"; subject = "PHYS" }
    "forces-and-motion-basics"                = @{ grade = "G12"; subject = "PHYS" }
    "friction"                                = @{ grade = "G12"; subject = "PHYS" }
    "gas-properties"                          = @{ grade = "G10"; subject = "PHYS" }
    "geometric-optics"                        = @{ grade = "G8"; subject = "PHYS" }
    "geometric-optics-basics"                 = @{ grade = "G8"; subject = "PHYS" }
    "gravity-and-orbits"                      = @{ grade = "G12"; subject = "PHYS" }
    "gravity-force-lab"                       = @{ grade = "G12"; subject = "PHYS" }
    "gravity-force-lab-basics"                = @{ grade = "G12"; subject = "PHYS" }
    "hookes-law"                              = @{ grade = "G12"; subject = "PHYS" }
    "john-travoltage"                         = @{ grade = "G11"; subject = "PHYS" }
    "keplers-laws"                            = @{ grade = "GEN"; subject = "PHYS" }
    "masses-and-springs"                      = @{ grade = "G12"; subject = "PHYS" }
    "masses-and-springs-basics"               = @{ grade = "G12"; subject = "PHYS" }
    "my-solar-system"                         = @{ grade = "G9"; subject = "PHYS" }
    "ohms-law"                                = @{ grade = "G11"; subject = "PHYS" }
    "pendulum-lab"                            = @{ grade = "G12"; subject = "PHYS" }
    "photoelectric-effect"                    = @{ grade = "G12"; subject = "PHYS" }
    "projectile-motion"                       = @{ grade = "GEN"; subject = "PHYS" }
    "resistance-in-a-wire"                    = @{ grade = "G11"; subject = "PHYS" }
    "rutherford-scattering"                   = @{ grade = "G12"; subject = "PHYS" }
    "under-pressure"                          = @{ grade = "G10"; subject = "PHYS" }
    "wave-interference"                       = @{ grade = "G12"; subject = "PHYS" }
    "wave-on-a-string"                        = @{ grade = "G12"; subject = "PHYS" }
    "waves-intro"                             = @{ grade = "G12"; subject = "PHYS" }

    # ===== (Chemistry) =====
    "acid-base-solutions"                     = @{ grade = "G12"; subject = "CHEM" }
    "balancing-chemical-equations"            = @{ grade = "G10"; subject = "CHEM" }
    "beers-law-lab"                           = @{ grade = "GEN"; subject = "CHEM" }
    "build-a-nucleus"                         = @{ grade = "GEN"; subject = "CHEM" }
    "build-an-atom"                           = @{ grade = "G10"; subject = "CHEM" }
    "concentration"                           = @{ grade = "G10"; subject = "CHEM" }
    "diffusion"                               = @{ grade = "GEN"; subject = "CHEM" }
    "isotopes-and-atomic-mass"                = @{ grade = "G10"; subject = "CHEM" }
    "molarity"                                = @{ grade = "G10"; subject = "CHEM" }
    "molecule-polarity"                       = @{ grade = "G12"; subject = "CHEM" }
    "molecule-shapes"                         = @{ grade = "G12"; subject = "CHEM" }
    "molecule-shapes-basics"                  = @{ grade = "G12"; subject = "CHEM" }
    "ph-scale"                                = @{ grade = "G12"; subject = "CHEM" }
    "ph-scale-basics"                         = @{ grade = "G12"; subject = "CHEM" }
    "reactants-products-and-leftovers"        = @{ grade = "G11"; subject = "CHEM" }
    "states-of-matter"                        = @{ grade = "G10"; subject = "CHEM" }
    "states-of-matter-basics"                 = @{ grade = "G10"; subject = "CHEM" }

    # ===== (Biology) =====
    "gene-expression-essentials"              = @{ grade = "G12"; subject = "BIO" }
    "membrane-transport"                      = @{ grade = "G10"; subject = "BIO" }
    "natural-selection"                       = @{ grade = "G12"; subject = "BIO" }
    "neuron"                                  = @{ grade = "G11"; subject = "BIO" }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PhET Simulation Renamer (Iran Curriculum)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$renamed = 0
$skipped = 0
$notFound = @()

Get-ChildItem -Path $buildDir -Filter "*_all_adapted-from-phet.html" | ForEach-Object {
    $oldName = $_.Name
    $simName = $oldName -replace "_all_adapted-from-phet\.html$", ""

    if ($simMap.ContainsKey($simName)) {
        $info = $simMap[$simName]
        $newName = "${simName}_$($info.grade)-$($info.subject).html"
        $newPath = Join-Path $buildDir $newName

        if (-not (Test-Path $newPath)) {
            Rename-Item -Path $_.FullName -NewName $newName
            Write-Host "  $simName -> $newName" -ForegroundColor Green
            $renamed++
        }
        else {
            Write-Host "  SKIP: $newName already exists" -ForegroundColor Yellow
            $skipped++
        }
    }
    else {
        Write-Host "  NOT IN MAP: $simName" -ForegroundColor Red
        $notFound += $simName
    }
}

Write-Host "`nRenamed: $renamed | Skipped: $skipped" -ForegroundColor Green
if ($notFound.Count -gt 0) {
    Write-Host "Not found ($($notFound.Count)):" -ForegroundColor Red
    $notFound | ForEach-Object { Write-Host "  $_" }
}
Write-Host "Done!" -ForegroundColor Green
