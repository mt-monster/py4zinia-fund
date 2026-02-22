import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_imports():
    """Test that main modules can be imported."""
    try:
        import data_retrieval
        assert data_retrieval is not None
    except ImportError as e:
        pytest.fail(f"Failed to import data_retrieval: {e}")

    try:
        import services
        assert services is not None
    except ImportError as e:
        pytest.fail(f"Failed to import services: {e}")
        
    try:
        import data_access
        assert data_access is not None
    except ImportError as e:
        pytest.fail(f"Failed to import data_access: {e}")

    # backtesting requires external dependencies like plotly, so we wrap it
    try:
        import backtesting
        assert backtesting is not None
    except ImportError as e:
        if "plotly" in str(e) or "cvxpy" in str(e) or "akshare" in str(e):
            pytest.skip(f"Skipping backtesting import due to missing dependency: {e}")
        else:
            pytest.fail(f"Failed to import backtesting: {e}")

    # enhanced_main also depends on backtesting
    try:
        import enhanced_main
        assert enhanced_main is not None
    except ImportError as e:
        if "plotly" in str(e) or "cvxpy" in str(e) or "akshare" in str(e):
            pytest.skip(f"Skipping enhanced_main import due to missing dependency: {e}")
        else:
            pytest.fail(f"Failed to import enhanced_main: {e}")
