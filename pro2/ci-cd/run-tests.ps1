#!/usr/bin/env powershell
#requires -Version 5.1

<#
.SYNOPSIS
    测试运行脚本

.DESCRIPTION
    运行项目的各种测试并生成报告

.PARAMETER Type
    测试类型 (all, unit, integration, api, db)

.PARAMETER Coverage
    是否生成覆盖率报告

.PARAMETER Parallel
    是否并行运行测试

.PARAMETER Markers
    指定pytest标记

.EXAMPLE
    .\run-tests.ps1                    # 运行所有测试
    .\run-tests.ps1 -Type unit         # 只运行单元测试
    .\run-tests.ps1 -Coverage          # 带覆盖率报告
    .\run-tests.ps1 -Markers "api"     # 只运行API测试
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("all", "unit", "integration", "api", "db")]
    [string]$Type = "all",
    
    [switch]$Coverage,
    [switch]$Parallel,
    [string]$Markers = "",
    [switch]$Verbose,
    [switch]$FailFast
)

# 颜色定义
$Colors = @{
    Success = "Green"
    Error = "Red"
    Warning = "Yellow"
    Info = "Cyan"
    Title = "Magenta"
}

function Write-Log {
    param([string]$Message, [string]$Level = "Info")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor $Colors[$Level]
}

function Write-Title {
    param([string]$Title)
    Write-Host "`n========================================" -ForegroundColor $Colors.Title
    Write-Host "  $Title" -ForegroundColor $Colors.Title
    Write-Host "========================================`n" -ForegroundColor $Colors.Title
}

# 项目路径
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$TestDir = Join-Path $ProjectRoot "tests"
$ReportDir = Join-Path $TestDir "reports"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# 确保目录存在
if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
}

# 激活虚拟环境
$VenvDir = Join-Path $ProjectRoot ".venv"
if (Test-Path $VenvDir) {
    & "$VenvDir\Scripts\Activate.ps1"
    Write-Log "已激活虚拟环境" -Level "Info"
}

# 构建pytest参数
$PytestArgs = @()

# 测试目录
switch ($Type) {
    "unit" { $PytestArgs += (Join-Path $TestDir "unit") }
    "integration" { $PytestArgs += (Join-Path $TestDir "integration") }
    "api" { $PytestArgs += (Join-Path $TestDir "integration\test_api.py") }
    "db" { $PytestArgs += (Join-Path $TestDir "integration\test_database.py") }
    default { $PytestArgs += $TestDir }
}

# 详细输出
if ($Verbose) {
    $PytestArgs += "-v"
} else {
    $PytestArgs += "-v"
}

# 标记
if ($Markers) {
    $PytestArgs += "-m"
    $PytestArgs += $Markers
}

# 覆盖率
if ($Coverage) {
    $PytestArgs += "--cov=fund_search"
    $PytestArgs += "--cov-report=html:$(Join-Path $ReportDir "coverage_$Timestamp")"
    $PytestArgs += "--cov-report=xml:$(Join-Path $ReportDir "coverage.xml")"
    $PytestArgs += "--cov-report=term-missing"
}

# HTML报告
$HtmlReport = Join-Path $ReportDir "test_report_$Timestamp.html"
$PytestArgs += "--html=$HtmlReport"
$PytestArgs += "--self-contained-html"

# 并行执行
if ($Parallel) {
    $PytestArgs += "-n"
    $PytestArgs += "auto"
}

# 快速失败
if ($FailFast) {
    $PytestArgs += "-x"
}

# 显示信息
Write-Title "运行测试 - $Type"
Write-Log "测试目录: $($PytestArgs[0])" -Level "Info"
Write-Log "报告文件: $HtmlReport" -Level "Info"
if ($Coverage) {
    Write-Log "覆盖率报告: $(Join-Path $ReportDir "coverage_$Timestamp")" -Level "Info"
}

# 运行测试
Write-Log "执行命令: pytest $($PytestArgs -join ' ')" -Level "Info"

try {
    pytest @PytestArgs
    $ExitCode = $LASTEXITCODE
    
    if ($ExitCode -eq 0) {
        Write-Log "所有测试通过!" -Level "Success"
    } else {
        Write-Log "测试失败 (退出码: $ExitCode)" -Level "Error"
    }
    
    # 显示报告位置
    Write-Host "`n测试报告:" -ForegroundColor $Colors.Title
    Write-Host "  HTML报告: $HtmlReport" -ForegroundColor $Colors.Info
    if ($Coverage) {
        Write-Host "  覆盖率报告: $(Join-Path $ReportDir "coverage_$Timestamp\index.html")" -ForegroundColor $Colors.Info
    }
    
    exit $ExitCode
    
} catch {
    Write-Log "测试执行失败: $_" -Level "Error"
    exit 1
}
