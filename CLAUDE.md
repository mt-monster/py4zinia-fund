# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

py4zinia is a comprehensive Chinese fund investment analysis platform built with Flask. It provides fund search, position management, investment strategy backtesting, and real-time analysis with web visualization.

## Common Commands

### Running the Application

```bash
# Start Flask web application (access at http://localhost:5000)
cd pro2/fund_search
python enhanced_main.py

# Or directly run app.py
cd pro2/fund_search/web
python app.py

# Run main analysis program
python pro2/fund_search/enhanced_main.py --analyze

# Run strategy comparison analysis
python pro2/fund_search/enhanced_main.py --strategy-analysis
```

### Testing

```bash
cd pro2

# Run all tests via Makefile
make test

# Run specific test types
make test-unit         # Unit tests
make test-integration  # Integration tests
make coverage          # Generate coverage report

# Run pytest directly
pytest tests/ -v
pytest tests/unit -v
pytest tests/integration -v
```

### CI/CD

```bash
cd pro2
make ci              # Full CI pipeline
make ci-quick        # Quick mode (unit tests only)
make ci-deploy       # CI with deployment
make deploy-local    # Local deployment
```

### Code Quality

```bash
cd pro2
make lint           # Code checking (flake8 + pylint)
make format         # Code formatting (black + isort)
make clean          # Clean temporary files
```

### Dependency Installation

```bash
pip install -r requirements.txt          # Root dependencies
pip install -r pro2/requirements.txt     # pro2 module dependencies
```

## Architecture

### Directory Structure

```
py4zinia/
├── pro2/                          # Main project code
│   ├── fund_search/               # Core business module
│   │   ├── web/                   # Flask web layer
│   │   │   ├── routes/           # API routes (funds, holdings, analysis, backtest, etc.)
│   │   │   ├── templates/         # Jinja2 HTML templates
│   │   │   ├── static/           # CSS/JS assets
│   │   │   └── app.py            # Flask app entry
│   │   ├── services/             # Business services (cache, analysis, etc.)
│   │   ├── data_retrieval/       # Data fetchers (AkShare, Sina finance)
│   │   ├── backtesting/          # Backtesting engine with strategies
│   │   ├── celery_tasks/         # Async tasks
│   │   ├── graphql_api/          # GraphQL interface
│   │   ├── shared/               # Shared utilities
│   │   ├── strategies/           # Trading strategies
│   │   └── enhanced_main.py     # Main entry point
│   └── services/
│       └── backtest_service/     # Backtest microservice
├── Makefile                       # Build commands (in pro2/)
├── Dockerfile
└── docker-compose.yml
```

### Technology Stack

- **Web Framework**: Flask 3.0
- **Frontend**: Bootstrap 5 + Chart.js
- **Data Sources**: AkShare, Sina Finance
- **Caching**: Memory Cache, Redis-compatible
- **Async Tasks**: Celery
- **Testing**: pytest, pytest-cov
- **Data Analysis**: NumPy, Pandas, Scikit-learn, CVXPy

### Key Backtesting Strategies

1. **Dual MA (Dual Moving Average)** - Trend following for markets with clear trends
2. **Mean Reversion** - Buy low/sell high for oscillating markets
3. **Target Value** - Cost averaging for long-term SIP investment
4. **Grid Trading** - Position building in waves to reduce average cost

### API Routes

| Route | Description |
|-------|-------------|
| `/` | Dashboard - holdings overview, profit trends |
| `/funds` | Fund search and analysis |
| `/holdings` | Position management |
| `/etf` | ETF analysis |
| `/backtest` | Strategy backtesting |
| `/strategies` | Strategy management |
| `/investment-advice` | Investment recommendations |

## Important Notes

- The main entry point is `pro2/fund_search/enhanced_main.py`
- Database: SQLite (`fund_analysis.db`) or MySQL (configurable)
- Project uses Chinese language for documentation and UI
- Active development planning in `.trae/documents/`
