import pandas as pd
import pytest


@pytest.fixture
def mock_csv(tmp_path):
    """Mock dataset with hand-checkable statistics."""
    path = tmp_path / "metrics.csv"
    pd.DataFrame({
        "company": ["A", "B", "C", "D"],
        "revenue": [100, 200, 300, 400],
        "profit": [10, 20, 30, 40],
    }).to_csv(path, index=False)
    return path
