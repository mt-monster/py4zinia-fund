"""
Strategy Report Parser

This module provides functionality to parse the strategy comparison report
markdown file and extract structured strategy metadata.
"""

import re
from typing import List, Dict, Optional
from pathlib import Path


class StrategyReportParser:
    """Parser for strategy comparison report markdown files."""
    
    def __init__(self, report_path: str):
        """
        Initialize the parser with a report file path.
        
        Args:
            report_path: Path to the strategy comparison report markdown file
        """
        self.report_path = report_path
        self._strategies = None
    
    def parse(self) -> List[Dict]:
        """
        Parse the strategy report and extract all strategy metadata.
        
        Returns:
            List of dictionaries containing strategy metadata with keys:
            - strategy_id: Internal identifier (e.g., 'dual_ma')
            - name: Display name (e.g., '双均线策略')
            - description: Strategy description
            - total_return: Total return percentage
            - annualized_return: Annualized return percentage
            - max_drawdown: Maximum drawdown percentage
            - sharpe_ratio: Sharpe ratio
            - win_rate: Win rate percentage
            - profit_loss_ratio: Profit/loss ratio
            
        Raises:
            FileNotFoundError: If report file doesn't exist
            ValueError: If report format is invalid or cannot be parsed
        """
        if self._strategies is not None:
            return self._strategies
        
        try:
            # Read the report file
            report_path = Path(self.report_path)
            if not report_path.exists():
                raise FileNotFoundError(f"Report file not found: {self.report_path}")
            
            content = report_path.read_text(encoding='utf-8')
            
            # Extract the table section
            strategies = self._parse_table(content)
            
            if not strategies:
                raise ValueError("No strategies found in report")
            
            self._strategies = strategies
            return strategies
            
        except FileNotFoundError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse strategy report: {str(e)}")
    
    def _parse_table(self, content: str) -> List[Dict]:
        """
        Parse the markdown table from the report content.
        
        Args:
            content: Full markdown content
            
        Returns:
            List of strategy dictionaries
        """
        strategies = []
        
        # Find the table section (starts after "### 绩效指标对比")
        table_pattern = r'\|\s*策略名称.*?\n\|:.*?\n((?:\|.*?\n)+)'
        match = re.search(table_pattern, content)
        
        if not match:
            raise ValueError("Could not find strategy table in report")
        
        # Extract table rows
        table_rows = match.group(1).strip().split('\n')
        
        for row in table_rows:
            if not row.strip() or not row.startswith('|'):
                continue
            
            # Split by pipe and clean up
            cells = [cell.strip() for cell in row.split('|')[1:-1]]
            
            if len(cells) < 11:
                continue
            
            try:
                # 表格格式: | strategy_id | 中文名称 | 总收益率 | ...
                # cells[0] = strategy_id (如 'enhanced_rule_based')
                # cells[1] = 中文显示名称 (如 '增强型规则策略')
                strategy = {
                    'strategy_id': cells[0].strip(),
                    'name': cells[1].strip(),  # FIXED: 使用中文名称而非strategy_id
                    'description': cells[1].strip(),  # 描述使用中文名称
                    'total_return': self._parse_percentage(cells[2]),
                    'annualized_return': self._parse_percentage(cells[3]),
                    'annualized_volatility': self._parse_percentage(cells[4]),
                    'max_drawdown': self._parse_percentage(cells[5]),
                    'sharpe_ratio': self._parse_float(cells[6]),
                    'win_rate': self._parse_percentage(cells[7]),
                    'profit_loss_ratio': self._parse_float(cells[8]),
                    'trades_count': self._parse_int(cells[9]),
                    'final_value': self._parse_float(cells[10])
                }
                strategies.append(strategy)
            except (ValueError, IndexError) as e:
                # Skip malformed rows but continue parsing
                continue
        
        return strategies
    
    def _parse_percentage(self, value: str) -> float:
        """
        Parse percentage string to float.
        
        Args:
            value: String like "51.20%" or "-15.74%"
            
        Returns:
            Float value (e.g., 51.20 or -15.74)
        """
        try:
            # Remove % sign and convert to float
            cleaned = value.strip().replace('%', '')
            return float(cleaned)
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid percentage value: {value}")
    
    def _parse_float(self, value: str) -> float:
        """
        Parse float string to float.
        
        Args:
            value: String like "1.35" or "0.65"
            
        Returns:
            Float value
        """
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid float value: {value}")
    
    def _parse_int(self, value: str) -> int:
        """
        Parse integer string to int.
        
        Args:
            value: String like "689"
            
        Returns:
            Integer value
        """
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid integer value: {value}")
    
    def get_strategy_by_id(self, strategy_id: str) -> Optional[Dict]:
        """
        Get specific strategy metadata by ID.
        
        Args:
            strategy_id: Strategy identifier (e.g., 'dual_ma')
            
        Returns:
            Strategy dictionary or None if not found
        """
        if self._strategies is None:
            self.parse()
        
        for strategy in self._strategies:
            if strategy['strategy_id'] == strategy_id:
                return strategy
        
        return None
    
    def get_all_strategy_ids(self) -> List[str]:
        """
        Get list of all strategy IDs in the report.
        
        Returns:
            List of strategy ID strings
        """
        if self._strategies is None:
            self.parse()
        
        return [s['strategy_id'] for s in self._strategies]
