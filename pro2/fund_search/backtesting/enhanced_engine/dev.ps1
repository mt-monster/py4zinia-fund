# PowerShell development script for Enhanced Backtesting Engine

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Enhanced Backtesting Engine - Development Commands" -ForegroundColor Green
    Write-Host ""
    Write-Host "Setup:" -ForegroundColor Yellow
    Write-Host "  install      Install production dependencies"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  demo         Run basic engine demonstration"
    Write-Host "  visual       Generate visualization charts"
    Write-Host ""
    Write-Host "Code Quality:" -ForegroundColor Yellow
    Write-Host "  format       Format code with black"
    Write-Host ""
    Write-Host "Utilities:" -ForegroundColor Yellow
    Write-Host "  clean        Clean build artifacts and cache"
}

function Install-Dependencies {
    Write-Host "Installing production dependencies..." -ForegroundColor Green
    pip install numpy pandas matplotlib seaborn
}

function Run-Demo {
    Write-Host "Running basic engine demonstration..." -ForegroundColor Green
    python simple_example.py
}

function Run-Visual {
    Write-Host "Generating visualization charts..." -ForegroundColor Green
    python visual_example.py
}

function Format-Code {
    Write-Host "Formatting code with black..." -ForegroundColor Green
    if (Get-Command black -ErrorAction SilentlyContinue) {
        black .
    } else {
        Write-Host "Black not installed. Installing..." -ForegroundColor Yellow
        pip install black
        black .
    }
}

function Clean-Artifacts {
    Write-Host "Cleaning build artifacts and cache..." -ForegroundColor Green
    Get-ChildItem -Path . -Recurse -Name "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Recurse -Name "__pycache__" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path "*.png") { Remove-Item -Force "*.png" -ErrorAction SilentlyContinue }
    Write-Host "Cleanup completed!" -ForegroundColor Green
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Dependencies }
    "demo" { Run-Demo }
    "visual" { Run-Visual }
    "format" { Format-Code }
    "clean" { Clean-Artifacts }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Use 'dev.ps1 help' to see available commands." -ForegroundColor Yellow
    }
}