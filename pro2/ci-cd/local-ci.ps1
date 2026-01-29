#!/usr/bin/env powershell
#requires -Version 5.1

<#
.SYNOPSIS
    本地CI/CD流水线脚本

.DESCRIPTION
    在本地运行完整的CI/CD流程，包括：
    - 代码质量检查
    - 单元测试
    - 集成测试
    - 测试报告生成
    - 覆盖率报告
    - 构建打包

.EXAMPLE
    .\local-ci.ps1                    # 运行完整流程
    .\local-ci.ps1 -SkipTests         # 跳过测试
    .\local-ci.ps1 -Quick             # 快速模式（只运行单元测试）
    .\local-ci.ps1 -ReportOnly        # 只生成报告

.PARAMETER SkipTests
    跳过测试步骤

.PARAMETER Quick
    快速模式，只运行单元测试

.PARAMETER ReportOnly
    只生成测试报告，不运行测试

.PARAMETER Deploy
    测试通过后自动部署
#>

[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$Quick,
    [switch]$ReportOnly,
    [switch]$Deploy,
    [string]$Environment = "local"
)

# 设置错误处理
$ErrorActionPreference = "Stop"

# 颜色定义
$Colors = @{
    Success = "Green"
    Error = "Red"
    Warning = "Yellow"
    Info = "Cyan"
    Title = "Magenta"
}

# 日志函数
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "Info"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = $Colors[$Level]
    Write-Host "[$timestamp] $Message" -ForegroundColor $color
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
$LogDir = Join-Path $TestDir "logs"
$VenvDir = Join-Path $ProjectRoot ".venv"

# 确保目录存在
@($ReportDir, $LogDir) | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }
}

# 时间戳
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir "ci-cd-$Timestamp.log"

# 开始记录日志
Start-Transcript -Path $LogFile -Append

Write-Title "基金分析系统 - 本地CI/CD流水线"
Write-Log "项目路径: $ProjectRoot" -Level "Info"
Write-Log "日志文件: $LogFile" -Level "Info"
Write-Log "环境: $Environment" -Level "Info"

# 步骤计数器
$TotalSteps = 7
if ($Quick) { $TotalSteps = 4 }
if ($SkipTests) { $TotalSteps = 3 }
$CurrentStep = 0

function Show-Progress {
    param([string]$StepName)
    $CurrentStep++
    Write-Title "步骤 $CurrentStep/$TotalSteps : $StepName"
}

# ============================================
# 步骤 1: 环境检查
# ============================================
Show-Progress "环境检查"

try {
    # 检查Python
    $PythonVersion = python --version 2>&1
    Write-Log "Python版本: $PythonVersion" -Level "Success"
    
    # 检查虚拟环境
    if (Test-Path $VenvDir) {
        Write-Log "虚拟环境已存在: $VenvDir" -Level "Success"
        & "$VenvDir\Scripts\Activate.ps1"
    } else {
        Write-Log "创建虚拟环境..." -Level "Warning"
        python -m venv $VenvDir
        & "$VenvDir\Scripts\Activate.ps1"
    }
    
    # 检查pip
    pip --version | Out-Null
    Write-Log "pip可用" -Level "Success"
    
} catch {
    Write-Log "环境检查失败: $_" -Level "Error"
    exit 1
}

# ============================================
# 步骤 2: 依赖安装
# ============================================
Show-Progress "依赖安装"

try {
    Write-Log "升级pip..." -Level "Info"
    python -m pip install --upgrade pip -q
    
    Write-Log "安装项目依赖..." -Level "Info"
    $ReqFile = Join-Path $ProjectRoot "requirements.txt"
    if (Test-Path $ReqFile) {
        pip install -r $ReqFile -q
        Write-Log "项目依赖安装完成" -Level "Success"
    }
    
    Write-Log "安装测试依赖..." -Level "Info"
    pip install pytest pytest-cov pytest-html pytest-mock pytest-xdist -q
    Write-Log "测试依赖安装完成" -Level "Success"
    
} catch {
    Write-Log "依赖安装失败: $_" -Level "Error"
    exit 1
}

# ============================================
# 步骤 3: 代码质量检查 (可选)
# ============================================
if (-not $Quick -and -not $SkipTests) {
    Show-Progress "代码质量检查"
    
    try {
        # 安装代码检查工具
        pip install flake8 black isort pylint -q
        
        # 检查Python语法
        Write-Log "检查Python语法..." -Level "Info"
        $PyFiles = Get-ChildItem -Path (Join-Path $ProjectRoot "fund_search") -Filter "*.py" -Recurse | Select-Object -First 50
        $SyntaxErrors = 0
        foreach ($file in $PyFiles) {
            $result = python -m py_compile $file.FullName 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Log "语法错误: $($file.FullName)" -Level "Error"
                $SyntaxErrors++
            }
        }
        
        if ($SyntaxErrors -eq 0) {
            Write-Log "语法检查通过" -Level "Success"
        } else {
            Write-Log "发现 $SyntaxErrors 个语法错误" -Level "Error"
        }
        
    } catch {
        Write-Log "代码质量检查失败: $_" -Level "Warning"
        # 不中断流程，继续执行
    }
}

# ============================================
# 步骤 4: 单元测试
# ============================================
if (-not $SkipTests) {
    Show-Progress "单元测试"
    
    try {
        $UnitTestDir = Join-Path $TestDir "unit"
        $UnitReport = Join-Path $ReportDir "unit_test_report_$Timestamp.html"
        $CoverageDir = Join-Path $ReportDir "coverage_$Timestamp"
        
        if (Test-Path $UnitTestDir) {
            Write-Log "运行单元测试..." -Level "Info"
            
            $TestArgs = @(
                $UnitTestDir,
                "-v",
                "--cov=fund_search",
                "--cov-report=html:$CoverageDir",
                "--cov-report=xml:$(Join-Path $ReportDir 'coverage.xml')",
                "--html=$UnitReport",
                "--self-contained-html",
                "--tb=short"
            )
            
            if (-not $Quick) {
                $TestArgs += "--cov-fail-under=60"
            }
            
            pytest @TestArgs 2>&1 | Tee-Object -FilePath (Join-Path $LogDir "unit_test_$Timestamp.log")
            
            if ($LASTEXITCODE -eq 0) {
                Write-Log "单元测试通过" -Level "Success"
                Write-Log "测试报告: $UnitReport" -Level "Info"
                Write-Log "覆盖率报告: $CoverageDir" -Level "Info"
            } else {
                Write-Log "单元测试失败" -Level "Error"
                if (-not $Quick) {
                    exit 1
                }
            }
        } else {
            Write-Log "单元测试目录不存在: $UnitTestDir" -Level "Warning"
        }
        
    } catch {
        Write-Log "单元测试执行失败: $_" -Level "Error"
        if (-not $Quick) {
            exit 1
        }
    }
}

# ============================================
# 步骤 5: 集成测试
# ============================================
if (-not $Quick -and -not $SkipTests) {
    Show-Progress "集成测试"
    
    try {
        $IntegrationTestDir = Join-Path $TestDir "integration"
        $IntegrationReport = Join-Path $ReportDir "integration_test_report_$Timestamp.html"
        
        if (Test-Path $IntegrationTestDir) {
            Write-Log "运行集成测试..." -Level "Info"
            
            pytest $IntegrationTestDir -v `
                --html=$IntegrationReport `
                --self-contained-html `
                --tb=short 2>&1 | Tee-Object -FilePath (Join-Path $LogDir "integration_test_$Timestamp.log")
            
            if ($LASTEXITCODE -eq 0) {
                Write-Log "集成测试通过" -Level "Success"
                Write-Log "测试报告: $IntegrationReport" -Level "Info"
            } else {
                Write-Log "集成测试失败" -Level "Warning"
                # 集成测试失败不中断流程
            }
        } else {
            Write-Log "集成测试目录不存在: $IntegrationTestDir" -Level "Warning"
        }
        
    } catch {
        Write-Log "集成测试执行失败: $_" -Level "Warning"
    }
}

# ============================================
# 步骤 6: 构建打包
# ============================================
Show-Progress "构建打包"

try {
    $BuildDir = Join-Path $ProjectRoot "dist"
    
    # 清理旧构建
    if (Test-Path $BuildDir) {
        Remove-Item -Path $BuildDir -Recurse -Force
    }
    
    # 安装构建工具
    pip install build wheel -q
    
    # 执行构建
    Write-Log "构建Python包..." -Level "Info"
    python -m build $ProjectRoot 2>&1 | Tee-Object -FilePath (Join-Path $LogDir "build_$Timestamp.log")
    
    if (Test-Path $BuildDir) {
        $BuildArtifacts = Get-ChildItem -Path $BuildDir
        Write-Log "构建完成，生成以下文件:" -Level "Success"
        $BuildArtifacts | ForEach-Object {
            Write-Log "  - $($_.Name) ($([math]::Round($_.Length/1KB, 2)) KB)" -Level "Info"
        }
    } else {
        Write-Log "构建目录未生成" -Level "Warning"
    }
    
} catch {
    Write-Log "构建失败: $_" -Level "Error"
    exit 1
}

# ============================================
# 步骤 7: 部署 (可选)
# ============================================
if ($Deploy) {
    Show-Progress "部署"
    
    try {
        Write-Log "开始部署到 $Environment 环境..." -Level "Info"
        
        # 这里添加实际的部署逻辑
        # 例如：
        # - 复制文件到部署目录
        # - 重启服务
        # - 执行数据库迁移
        
        $DeployScript = Join-Path $PSScriptRoot "deploy.ps1"
        if (Test-Path $DeployScript) {
            & $DeployScript -Environment $Environment
        } else {
            Write-Log "部署脚本不存在: $DeployScript" -Level "Warning"
            Write-Log "跳过部署步骤" -Level "Warning"
        }
        
    } catch {
        Write-Log "部署失败: $_" -Level "Error"
        exit 1
    }
}

# ============================================
# 完成
# ============================================
Write-Title "CI/CD流水线执行完成"

Write-Log "所有步骤执行完毕" -Level "Success"
Write-Log "测试报告目录: $ReportDir" -Level "Info"
Write-Log "日志文件: $LogFile" -Level "Info"

# 生成摘要
Write-Host "`n========================================" -ForegroundColor $Colors.Title
Write-Host "执行摘要" -ForegroundColor $Colors.Title
Write-Host "========================================" -ForegroundColor $Colors.Title
Write-Host "项目: 基金分析系统" -ForegroundColor $Colors.Info
Write-Host "环境: $Environment" -ForegroundColor $Colors.Info
Write-Host "时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor $Colors.Info
Write-Host "日志: $LogFile" -ForegroundColor $Colors.Info
Write-Host "========================================" -ForegroundColor $Colors.Title

Stop-Transcript

exit 0
