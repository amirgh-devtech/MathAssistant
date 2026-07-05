# rename-sims.ps1 (fixed)
$buildDir = "C:\Users\amirgh\Desktop\MathAssistant\extensions\myLab\build"

$simMap = @{
    # ===== ریاضی =====
    "area-builder"                            = @{ grade = "G7"; subject = "MATH" }
    "area-model-algebra"                      = @{ grade = "G8"; subject = "MATH" }
    "area-model-decimals"                     = @{ grade = "G7"; subject = "MATH" }
    "area-model-introduction"                 = @{ grade = "G7"; subject = "MATH" }
    "area-model-multiplication"               = @{ grade = "G7"; subject = "MATH" }
    "balancing-act"                           = @{ grade = "G7"; subject = "MATH" }
    "build-a-fraction"                        = @{ grade = "G7"; subject = "MATH" }
    "calculus-grapher"                        = @{ grade = "G12"; subject = "MATH" }
    "center-and-variability"                  = @{ grade = "G10"; subject = "MATH" }
    "curve-fitting"                           = @{ grade = "G11"; subject = "MATH" }
    "equality-explorer"                       = @{ grade = "G7"; subject = "MATH" }
    "equality-explorer-basics"                = @{ grade = "G7"; subject = "MATH" }
    "equality-explorer-two-variables"         = @{ grade = "G8"; subject = "MATH" }
    "expression-exchange"                     = @{ grade = "G8"; subject = "MATH" }
    "fourier-making-waves"                    = @{ grade = "ACA"; subject = "MATH" }
    "fraction-matcher"                        = @{ grade = "G7"; subject = "MATH" }
    "fractions-equality"                      = @{ grade = "G7"; subject = "MATH" }
    "fractions-intro"                         = @{ grade = "G7"; subject = "MATH" }
    "fractions-mixed-numbers"                 = @{ grade = "G7"; subject = "MATH" }
    "function-builder"                        = @{ grade = "G10"; subject = "MATH" }
    "function-builder-basics"                 = @{ grade = "G9"; subject = "MATH" }
    "graphing-lines"                          = @{ grade = "G8"; subject = "MATH" }
    "graphing-quadratics"                     = @{ grade = "G10"; subject = "MATH" }
    "graphing-slope-intercept"                = @{ grade = "G9"; subject = "MATH" }
    "least-squares-regression"                = @{ grade = "G11"; subject = "MATH" }
    "make-a-ten"                              = @{ grade = "G7"; subject = "MATH" }
    "mean-share-and-balance"                  = @{ grade = "G7"; subject = "MATH" }
    "number-compare"                          = @{ grade = "G7"; subject = "MATH" }
    "number-line-distance"                    = @{ grade = "G7"; subject = "MATH" }
    "number-line-integers"                    = @{ grade = "G7"; subject = "MATH" }
    "number-line-operations"                  = @{ grade = "G7"; subject = "MATH" }
    "number-play"                             = @{ grade = "G7"; subject = "MATH" }
    "plinko-probability"                      = @{ grade = "G9"; subject = "MATH" }
    "proportion-playground"                   = @{ grade = "G8"; subject = "MATH" }
    "quadrilateral"                           = @{ grade = "G8"; subject = "MATH" }
    "trig-tour"                               = @{ grade = "G11"; subject = "MATH" }
    "unit-rates"                              = @{ grade = "G8"; subject = "MATH" }
    "vector-addition"                         = @{ grade = "G10"; subject = "MATH" }
    "vector-addition-equations"               = @{ grade = "G10"; subject = "MATH" }

    # ===== فیزیک =====
    "atomic-interactions"                     = @{ grade = "G12"; subject = "PHYS" }
    "balloons-and-static-electricity"         = @{ grade = "G8"; subject = "PHYS" }
    "bending-light"                           = @{ grade = "G10"; subject = "PHYS" }
    "blackbody-spectrum"                      = @{ grade = "G11"; subject = "PHYS" }
    "buoyancy"                                = @{ grade = "G7"; subject = "PHYS" }
    "capacitor-lab-basics"                    = @{ grade = "G11"; subject = "PHYS" }
    "charges-and-fields"                      = @{ grade = "G11"; subject = "PHYS" }
    "circuit-construction-kit-ac-virtual-lab" = @{ grade = "ACA"; subject = "PHYS" }
    "circuit-construction-kit-dc"             = @{ grade = "G11"; subject = "PHYS" }
    "circuit-construction-kit-dc-virtual-lab" = @{ grade = "G11"; subject = "PHYS" }
    "collision-lab"                           = @{ grade = "G10"; subject = "PHYS" }
    "color-vision"                            = @{ grade = "G8"; subject = "PHYS" }
    "coulombs-law"                            = @{ grade = "G11"; subject = "PHYS" }
    "density"                                 = @{ grade = "G7"; subject = "PHYS" }
    "energy-forms-and-changes"                = @{ grade = "G7"; subject = "PHYS" }
    "energy-skate-park"                       = @{ grade = "G8"; subject = "PHYS" }
    "energy-skate-park-basics"                = @{ grade = "G7"; subject = "PHYS" }
    "faradays-law"                            = @{ grade = "G11"; subject = "PHYS" }
    "forces-and-motion-basics"                = @{ grade = "G9"; subject = "PHYS" }
    "friction"                                = @{ grade = "G9"; subject = "PHYS" }
    "gas-properties"                          = @{ grade = "G9"; subject = "PHYS" }
    "geometric-optics"                        = @{ grade = "G10"; subject = "PHYS" }
    "geometric-optics-basics"                 = @{ grade = "G10"; subject = "PHYS" }
    "gravity-and-orbits"                      = @{ grade = "G9"; subject = "PHYS" }
    "gravity-force-lab"                       = @{ grade = "G9"; subject = "PHYS" }
    "gravity-force-lab-basics"                = @{ grade = "G9"; subject = "PHYS" }
    "hookes-law"                              = @{ grade = "G10"; subject = "PHYS" }
    "john-travoltage"                         = @{ grade = "G8"; subject = "PHYS" }
    "keplers-laws"                            = @{ grade = "ACA"; subject = "PHYS" }
    "masses-and-springs"                      = @{ grade = "G10"; subject = "PHYS" }
    "masses-and-springs-basics"               = @{ grade = "G9"; subject = "PHYS" }
    "my-solar-system"                         = @{ grade = "G9"; subject = "PHYS" }
    "ohms-law"                                = @{ grade = "G8"; subject = "PHYS" }
    "pendulum-lab"                            = @{ grade = "G10"; subject = "PHYS" }
    "photoelectric-effect"                    = @{ grade = "G12"; subject = "PHYS" }
    "projectile-motion"                       = @{ grade = "G9"; subject = "PHYS" }
    "resistance-in-a-wire"                    = @{ grade = "G8"; subject = "PHYS" }
    "rutherford-scattering"                   = @{ grade = "G11"; subject = "PHYS" }
    "under-pressure"                          = @{ grade = "G9"; subject = "PHYS" }
    "wave-interference"                       = @{ grade = "G12"; subject = "PHYS" }
    "wave-on-a-string"                        = @{ grade = "G8"; subject = "PHYS" }
    "waves-intro"                             = @{ grade = "G8"; subject = "PHYS" }

    # ===== شیمی =====
    "acid-base-solutions"                     = @{ grade = "G10"; subject = "CHEM" }
    "balancing-chemical-equations"            = @{ grade = "G9"; subject = "CHEM" }
    "beers-law-lab"                           = @{ grade = "G11"; subject = "CHEM" }
    "build-a-nucleus"                         = @{ grade = "ACA"; subject = "CHEM" }
    "build-an-atom"                           = @{ grade = "G7"; subject = "CHEM" }
    "concentration"                           = @{ grade = "G10"; subject = "CHEM" }
    "diffusion"                               = @{ grade = "G9"; subject = "CHEM" }
    "isotopes-and-atomic-mass"                = @{ grade = "G10"; subject = "CHEM" }
    "molarity"                                = @{ grade = "G10"; subject = "CHEM" }
    "molecule-polarity"                       = @{ grade = "G10"; subject = "CHEM" }
    "molecule-shapes"                         = @{ grade = "G9"; subject = "CHEM" }
    "molecule-shapes-basics"                  = @{ grade = "G9"; subject = "CHEM" }
    "ph-scale"                                = @{ grade = "G9"; subject = "CHEM" }
    "ph-scale-basics"                         = @{ grade = "G8"; subject = "CHEM" }
    "reactants-products-and-leftovers"        = @{ grade = "G9"; subject = "CHEM" }
    "states-of-matter"                        = @{ grade = "G7"; subject = "CHEM" }
    "states-of-matter-basics"                 = @{ grade = "G7"; subject = "CHEM" }

    # ===== زیست =====
    "gene-expression-essentials"              = @{ grade = "G11"; subject = "BIO" }
    "membrane-transport"                      = @{ grade = "G10"; subject = "BIO" }
    "natural-selection"                       = @{ grade = "G11"; subject = "BIO" }
    "neuron"                                  = @{ grade = "G11"; subject = "BIO" }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PhET Simulation Renamer" -ForegroundColor Cyan
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
