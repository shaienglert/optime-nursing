$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host 'Syncing repository...'
git pull --ff-only origin main

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js is required.' }

if (-not (Test-Path 'node_modules/playwright')) {
  Write-Host 'Installing Playwright locally...'
  npm install --no-save playwright
}

Write-Host 'Installing Chromium browser runtime if needed...'
npx playwright install chromium

Write-Host 'Starting browser-mediated AHCA extraction...'
node scripts/ahca_browser_extractor.mjs

Write-Host 'Extraction finished. Manifest:'
Get-Content database/ahca_browser_extract/manifest.json
