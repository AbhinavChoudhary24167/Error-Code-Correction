$ErrorActionPreference = 'Stop'
$packageRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$buildDir = Join-Path $packageRoot 'build'
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
Push-Location $packageRoot
try {
    & 'D:\Compiler Cpp\ucrt64\bin\python3.exe' scripts\build_artifacts.py | Tee-Object -FilePath (Join-Path $buildDir 'artifact_generation.log')
    if ($LASTEXITCODE -ne 0) { throw "Artifact generation failed: $LASTEXITCODE" }
    & pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "-output-directory=$buildDir" DATE2027_MANUSCRIPT.tex
    if ($LASTEXITCODE -ne 0) { throw "First pdflatex pass failed: $LASTEXITCODE" }
    & bibtex (Join-Path $buildDir 'DATE2027_MANUSCRIPT')
    if ($LASTEXITCODE -ne 0) { throw "BibTeX failed: $LASTEXITCODE" }
    & pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "-output-directory=$buildDir" DATE2027_MANUSCRIPT.tex
    if ($LASTEXITCODE -ne 0) { throw "Second pdflatex pass failed: $LASTEXITCODE" }
    & pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "-output-directory=$buildDir" DATE2027_MANUSCRIPT.tex
    if ($LASTEXITCODE -ne 0) { throw "Final pdflatex pass failed: $LASTEXITCODE" }
    Copy-Item -LiteralPath (Join-Path $buildDir 'DATE2027_MANUSCRIPT.pdf') -Destination (Join-Path $packageRoot 'DATE2027_MANUSCRIPT_BLIND.pdf') -Force
}
finally {
    Pop-Location
}
