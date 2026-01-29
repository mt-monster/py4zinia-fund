#!/usr/bin/env powershell
#requires -Version 5.1

<#
.SYNOPSIS
    部署脚本

.DESCRIPTION
    自动化部署基金分析系统到指定环境

.PARAMETER Environment
    部署环境 (local, staging, production)

.PARAMETER Backup
    部署前是否备份

.PARAMETER DryRun
    试运行模式，不实际执行部署
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("local", "staging", "production")]
    [string]$Environment = "local",
    
    [switch]$Backup,
    [switch]$DryRun
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

# 项目路径
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ConfigFile = Join-Path $PSScriptRoot "deploy-config.ps1"

# 加载配置文件
if (Test-Path $ConfigFile) {
    . $ConfigFile
    Write-Log "加载配置文件: $ConfigFile" -Level "Info"
} else {
    Write-Log "使用默认配置" -Level "Warning"
}

# 部署配置
$DeployConfig = @{
    local = @{
        TargetDir = Join-Path $ProjectRoot "deploy\local"
        AppPort = 5000
        DbName = "fund_local"
        BackupDir = Join-Path $ProjectRoot "backups\local"
    }
    staging = @{
        TargetDir = "\\staging-server\fund-analysis"
        AppPort = 5000
        DbName = "fund_staging"
        BackupDir = "\\staging-server\backups"
    }
    production = @{
        TargetDir = "\\prod-server\fund-analysis"
        AppPort = 80
        DbName = "fund_production"
        BackupDir = "\\prod-server\backups"
    }
}

$config = $DeployConfig[$Environment]

Write-Log "========================================" -Level "Title"
Write-Log "部署到 $Environment 环境" -Level "Title"
Write-Log "========================================" -Level "Title"

if ($DryRun) {
    Write-Log "【试运行模式】不会实际执行部署" -Level "Warning"
}

# 步骤 1: 预部署检查
Write-Log "执行预部署检查..." -Level "Info"

# 检查必要文件
$RequiredFiles = @(
    (Join-Path $ProjectRoot "fund_search\web\app.py"),
    (Join-Path $ProjectRoot "requirements.txt")
)

foreach ($file in $RequiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Log "缺少必要文件: $file" -Level "Error"
        exit 1
    }
}
Write-Log "文件检查通过" -Level "Success"

# 步骤 2: 备份 (如果启用)
if ($Backup) {
    Write-Log "创建备份..." -Level "Info"
    
    if (-not (Test-Path $config.BackupDir)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $config.BackupDir -Force | Out-Null
        }
    }
    
    $BackupName = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"
    $BackupPath = Join-Path $config.BackupDir $BackupName
    
    if (Test-Path $config.TargetDir) {
        if (-not $DryRun) {
            Compress-Archive -Path $config.TargetDir -DestinationPath $BackupPath -Force
        }
        Write-Log "备份创建: $BackupPath" -Level "Success"
    } else {
        Write-Log "目标目录不存在，跳过备份" -Level "Warning"
    }
}

# 步骤 3: 创建目标目录
if (-not (Test-Path $config.TargetDir)) {
    Write-Log "创建目标目录: $($config.TargetDir)" -Level "Info"
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $config.TargetDir -Force | Out-Null
    }
}

# 步骤 4: 复制文件
Write-Log "复制应用程序文件..." -Level "Info"

$SourceItems = @(
    "fund_search",
    "requirements.txt",
    "README.md"
)

foreach ($item in $SourceItems) {
    $source = Join-Path $ProjectRoot $item
    $dest = Join-Path $config.TargetDir $item
    
    if (Test-Path $source) {
        Write-Log "复制: $item" -Level "Info"
        if (-not $DryRun) {
            if (Test-Path $source -PathType Container) {
                if (Test-Path $dest) {
                    Remove-Item -Path $dest -Recurse -Force
                }
                Copy-Item -Path $source -Destination $dest -Recurse -Force
            } else {
                Copy-Item -Path $source -Destination $dest -Force
            }
        }
    }
}

Write-Log "文件复制完成" -Level "Success"

# 步骤 5: 安装依赖
Write-Log "安装Python依赖..." -Level "Info"

if (-not $DryRun) {
    $VenvDir = Join-Path $config.TargetDir ".venv"
    
    # 创建虚拟环境
    if (-not (Test-Path $VenvDir)) {
        python -m venv $VenvDir
    }
    
    # 激活并安装依赖
    & "$VenvDir\Scripts\Activate.ps1"
    pip install -r (Join-Path $config.TargetDir "requirements.txt") -q
}

Write-Log "依赖安装完成" -Level "Success"

# 步骤 6: 数据库迁移
Write-Log "执行数据库迁移..." -Level "Info"

if (-not $DryRun) {
    # 这里可以添加数据库迁移脚本
    # 例如：alembic upgrade head
    # 或者执行SQL脚本
    
    $MigrationScript = Join-Path $PSScriptRoot "migrate-db.ps1"
    if (Test-Path $MigrationScript) {
        & $MigrationScript -Environment $Environment
    } else {
        Write-Log "数据库迁移脚本不存在，跳过" -Level "Warning"
    }
}

# 步骤 7: 配置应用程序
Write-Log "配置应用程序..." -Level "Info"

$ConfigTemplate = @"
# 自动生成的配置文件
# 环境: $Environment
# 生成时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

[app]
port = $($config.AppPort)
debug = $(if ($Environment -eq 'production') { 'false' } else { 'true' })

[database]
host = localhost
port = 3306
database = $($config.DbName)

[logging]
level = $(if ($Environment -eq 'production') { 'INFO' } else { 'DEBUG' })
file = logs/app.log
"@

if (-not $DryRun) {
    $ConfigPath = Join-Path $config.TargetDir "config.ini"
    $ConfigTemplate | Out-File -FilePath $ConfigPath -Encoding UTF8
}

Write-Log "配置完成" -Level "Success"

# 步骤 8: 创建服务 (Windows) 或Systemd服务 (Linux)
if ($Environment -ne "local") {
    Write-Log "配置系统服务..." -Level "Info"
    
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        # Windows服务配置
        $ServiceName = "FundAnalysis_$Environment"
        # 使用nssm或sc创建服务
        Write-Log "Windows服务: $ServiceName" -Level "Info"
    } else {
        # Linux Systemd服务
        $ServiceFile = "/etc/systemd/system/fund-analysis-$Environment.service"
        Write-Log "Systemd服务: $ServiceFile" -Level "Info"
    }
}

# 步骤 9: 启动应用程序
Write-Log "启动应用程序..." -Level "Info"

if (-not $DryRun) {
    $AppScript = Join-Path $PSScriptRoot "start-app.ps1"
    if (Test-Path $AppScript) {
        & $AppScript -Environment $Environment -Port $config.AppPort
    } else {
        # 直接启动
        $AppPath = Join-Path $config.TargetDir "fund_search\web\app.py"
        if (Test-Path $AppPath) {
            Write-Log "应用程序路径: $AppPath" -Level "Info"
            # 在后台启动
            Start-Process -FilePath "python" -ArgumentList $AppPath -WorkingDirectory $config.TargetDir
        }
    }
}

# 步骤 10: 健康检查
Write-Log "执行健康检查..." -Level "Info"

$MaxRetries = 30
$RetryInterval = 2
$HealthUrl = "http://localhost:$($config.AppPort)/"

for ($i = 1; $i -le $MaxRetries; $i++) {
    Start-Sleep -Seconds $RetryInterval
    
    try {
        $response = Invoke-WebRequest -Uri $HealthUrl -Method GET -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Log "健康检查通过! 应用程序运行正常" -Level "Success"
            break
        }
    } catch {
        Write-Log "健康检查尝试 $i/$MaxRetries..." -Level "Warning"
    }
    
    if ($i -eq $MaxRetries) {
        Write-Log "健康检查失败，应用程序可能未正常启动" -Level "Error"
    }
}

# 部署完成
Write-Log "========================================" -Level "Title"
Write-Log "部署完成!" -Level "Success"
Write-Log "环境: $Environment" -Level "Info"
Write-Log "访问地址: http://localhost:$($config.AppPort)" -Level "Info"
Write-Log "========================================" -Level "Title"

# 发送通知 (可选)
$WebhookUrl = $env:DEPLOY_WEBHOOK_URL
if ($WebhookUrl) {
    $Notification = @{
        text = "基金分析系统部署完成`n环境: $Environment`n时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    } | ConvertTo-Json
    
    try {
        Invoke-RestMethod -Uri $WebhookUrl -Method POST -Body $Notification -ContentType "application/json"
    } catch {
        Write-Log "通知发送失败: $_" -Level "Warning"
    }
}

exit 0
