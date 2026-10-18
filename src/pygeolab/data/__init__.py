"""Data management, statistical models, and tabular imports/exports."""

from pygeolab.data.bivariate import (
    LinearRegressionResult,
    covariance,
    linear_regression,
    pearson_correlation,
)
from pygeolab.data.csv_io import read_csv, write_csv
from pygeolab.data.dataset import DatasetObject
from pygeolab.data.statistics import (
    DescriptiveStats,
    compute_descriptive_stats,
    detect_outliers,
    percentile,
    quartiles,
)

__all__ = [
    "DatasetObject",
    "DescriptiveStats",
    "LinearRegressionResult",
    "compute_descriptive_stats",
    "covariance",
    "detect_outliers",
    "linear_regression",
    "pearson_correlation",
    "percentile",
    "quartiles",
    "read_csv",
    "write_csv",
]
