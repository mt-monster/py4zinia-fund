# Windows 定时任务配置脚本
# 创建每日自动同步基金净值数据的任务

# 需要以管理员身份运行 PowerShell

$TaskName = "FundNavDataSync"
$TaskDescription = "每日同步基金历史净值数据到数据库"
$ScriptPath = "$PSScriptRoot\sync_fund_nav_data.py"
$PythonPath = "$PSScriptRoot\..\..\.venv\Scripts\python.exe"

# 检查文件是否存在
if (-not (Test-Path $ScriptPath)) {
    Write-Error "脚本文件不存在: $ScriptPath"
    exit 1
}

# 创建任务动作
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "sync_fund_nav_data.py --sync-holdings" -WorkingDirectory $PSScriptRoot

# 创建任务触发器（每日16:30）
$Trigger = New-ScheduledTaskTrigger -Daily -At "16:30"

# 创建任务设置
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 注册任务
try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description $TaskDescription -Force
    Write-Host "定时任务创建成功！" -ForegroundColor Green
    Write-Host "任务名称: $TaskName"
    Write-Host "执行时间: 每日 16:30"
    Write-Host "执行命令: $PythonPath $ScriptPath --sync-holdings"
    Write-Host ""
    Write-Host "查看任务: 打开任务计划程序 -> 任务计划程序库 -> $TaskName"
} catch {
    Write-Error "创建定时任务失败: $_"
    exit 1
}
