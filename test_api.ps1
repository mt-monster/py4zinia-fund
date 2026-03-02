$json = @{
    fund_code = "010052"
    strategy_id = "default"
    period = "daily"
    start_date = "2024-01-01"
    end_date = "2024-12-31"
    initial_amount = 100000
    monthly_invest = 1000
    base_invest = 1000
    days = 365
    benchmark = "000300"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5001/api/strategy/backtest" -Method POST -ContentType "application/json" -Body $json -UseBasicParsing | Select-Object -ExpandProperty Content
