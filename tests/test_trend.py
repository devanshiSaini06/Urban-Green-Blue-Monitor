"""
Unit tests for trend analysis (Mann-Kendall, Sen's slope, Linear Regression).
Tests against known examples from literature.
"""
import pytest
import numpy as np
from trend_analysis import (
    mann_kendall_test,
    sen_slope,
    linear_regression,
    run_trend_analysis,
    _normal_cdf,
    _normal_ppf
)


class TestMannKendall:
    """Test Mann-Kendall trend test."""

    def test_increasing_trend(self):
        """Perfect increasing trend should give tau=1, p<0.05."""
        values = [1, 2, 3, 4, 5, 6, 7, 8]
        years = list(range(8))
        result = mann_kendall_test(values)
        assert result.tau == 1.0
        assert result.p_value < 0.05
        assert result.trend == "increasing"
        assert result.significant is True
        assert result.s == 28  # n*(n-1)/2 = 8*7/2 = 28

    def test_decreasing_trend(self):
        """Perfect decreasing trend should give tau=-1, p<0.05."""
        values = [8, 7, 6, 5, 4, 3, 2, 1]
        result = mann_kendall_test(values)
        assert result.tau == -1.0
        assert result.p_value < 0.05
        assert result.trend == "decreasing"
        assert result.significant is True
        assert result.s == -28

    def test_no_trend(self):
        """Constant values should give tau=0, p=1."""
        values = [5, 5, 5, 5, 5, 5, 5, 5]
        result = mann_kendall_test(values)
        assert result.tau == 0.0
        assert result.p_value == 1.0
        assert result.trend == "no trend"
        assert result.significant is False

    def test_insufficient_data(self):
        """Less than 3 points should return insufficient_data."""
        values = [1, 2]
        result = mann_kendall_test(values)
        assert result.trend == "insufficient_data"
        assert result.tau == 0.0
        assert result.p_value == 1.0

    def test_random_no_trend(self):
        """Random data should typically not be significant."""
        np.random.seed(42)
        values = np.random.randn(20).tolist()
        result = mann_kendall_test(values)
        # With random data, p should usually be > 0.05
        # (but not guaranteed, so we don't assert significance)

    def test_tie_handling(self):
        """Test with tied values."""
        values = [1, 2, 2, 3, 3, 3, 4, 4, 5]  # Multiple ties
        result = mann_kendall_test(values)
        assert result.tau > 0  # Still increasing trend
        assert result.p_value < 0.05
        assert result.var_s > 0  # Variance should account for ties


class TestSenSlope:
    """Test Sen's slope estimator."""

    def test_perfect_increasing(self):
        """Perfect linear increase: slope should equal step size."""
        values = [1, 2, 3, 4, 5, 6, 7, 8]
        years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
        result = sen_slope(values, years)
        assert abs(result.slope - 1.0) < 0.001
        assert result.ci_lower <= result.slope <= result.ci_upper

    def test_perfect_decreasing(self):
        """Perfect linear decrease."""
        values = [8, 7, 6, 5, 4, 3, 2, 1]
        years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
        result = sen_slope(values, years)
        assert abs(result.slope - (-1.0)) < 0.001

    def test_no_trend_flat(self):
        """Flat line should have slope 0."""
        values = [5, 5, 5, 5, 5, 5, 5, 5]
        years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
        result = sen_slope(values, years)
        assert result.slope == 0.0

    def test_known_example(self):
        """Test against known example from Sen (1968)."""
        # Example: y = 2x + 1 with some noise
        years = [1, 2, 3, 4, 5]
        values = [3.1, 5.0, 6.9, 9.2, 10.8]  # Approx y = 2x + 1
        result = sen_slope(values, years)
        # Should be close to 2
        assert 1.5 < result.slope < 2.5


class TestLinearRegression:
    """Test linear regression."""

    def test_perfect_line(self):
        """Perfect linear relationship: y = 2x + 1."""
        x = [1, 2, 3, 4, 5]
        y = [3, 5, 7, 9, 11]  # y = 2x + 1
        result = linear_regression(y, x)
        assert abs(result.slope - 2.0) < 0.001
        assert abs(result.intercept - 1.0) < 0.001
        assert abs(result.r_squared - 1.0) < 0.001
        assert result.p_value < 0.001
        assert result.significant is True

    def test_flat_line(self):
        """No relationship: y = constant."""
        x = [1, 2, 3, 4, 5]
        y = [5, 5, 5, 5, 5]
        result = linear_regression(y, x)
        assert result.slope == 0.0
        assert result.r_squared == 0.0
        assert result.p_value == 1.0
        assert result.significant is False

    def test_noisy_trend(self):
        """Noisy but significant trend."""
        np.random.seed(123)
        x = np.arange(10).astype(float)
        y = 0.5 * x + 2 + np.random.randn(10) * 0.5
        result = linear_regression(y.tolist(), x.tolist())
        assert result.slope > 0
        # With this noise level, should be significant
        assert result.r_squared > 0.5


class TestRunTrendAnalysis:
    """Test the integrated trend analysis function."""

    def test_increasing_trend_output(self):
        """Test full output for increasing trend."""
        values = [1, 2, 3, 4, 5, 6, 7, 8]
        years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
        result = run_trend_analysis(values, years, "test_var")

        assert result["mann_kendall"]["tau"] == 1.0
        assert result["mann_kendall"]["significant"] is True
        assert result["sen_slope"]["slope"] == 1.0
        assert result["linear_regression"]["slope"] == 1.0
        assert "increasing" in result["interpretation"]
        assert len(result["warnings"]) > 0  # n=8 warning

    def test_no_trend_output(self):
        """Test output for no trend."""
        values = [5, 5, 5, 5, 5, 5, 5, 5]
        years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
        result = run_trend_analysis(values, years, "test_var")

        assert result["mann_kendall"]["tau"] == 0.0
        assert result["mann_kendall"]["significant"] is False
        assert result["interpretation"] == "test_var shows a no trend (p=1.0000, τ=0.000). Sen's slope: 0.0000/yr (95% CI: 0.0000 to 0.0000). Linear regression: slope=0.0000/yr (not significant, p=1.0000, R²=0.000). WARNING: Only 8 data points (n=8). Statistical power is very low. Results should be interpreted with extreme caution."


class TestNormalDistribution:
    """Test normal distribution approximations."""

    def test_cdf_ppf_inverse(self):
        """CDF and PPF should be inverses."""
        for p in [0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 0.999]:
            z = _normal_ppf(p)
            p_recovered = _normal_cdf(z)
            assert abs(p - p_recovered) < 0.01, f"Failed for p={p}"

    def test_cdf_symmetry(self):
        """CDF should be symmetric: CDF(-z) = 1 - CDF(z)."""
        for z in [0.5, 1.0, 1.5, 2.0, 2.5]:
            assert abs(_normal_cdf(-z) - (1 - _normal_cdf(z))) < 0.001

    def test_cdf_bounds(self):
        """CDF should approach 0 and 1 at extremes."""
        assert _normal_cdf(-10) < 1e-10
        assert _normal_cdf(10) > 1 - 1e-10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])