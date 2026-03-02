$json = @{
    name = "test_strategy"
    description = "test"
    config = @{
        strategy_type = "momentum"
        name = "test_strategy"
        description = "test"
    }
} | ConvertTo-Json

# 先创建策略
$createResult = Invoke-WebRequest -Uri "http://localhost:5001/api/user-strategies" -Method POST -ContentType "application/json" -Body $json -UseBasicParsing | Select-Object -ExpandProperty Content
Write-Host "Create result: $createResult"

# 解析返回的 ID
$createResult | ConvertFrom-Json | ForEach-Object { 
    if ($_.success -and $_.data.id) {
        $strategyId = $_.data.id
        Write-Host "Created strategy ID: $strategyId"
        
        # 删除策略
        $deleteResult = Invoke-WebRequest -Uri "http://localhost:5001/api/user-strategies/$strategyId" -Method DELETE -UseBasicParsing | Select-Object -ExpandProperty Content
        Write-Host "Delete result: $deleteResult"
    }
}
