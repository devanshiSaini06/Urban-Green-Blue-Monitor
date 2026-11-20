"""
Trend analysis module: Mann-Kendall test, Sen's slope, linear regression.
All implementations are pure Python with no external statistical dependencies.
"""
import math
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from config import TREND_ALPHA, TREND_WARNING_N


@dataclass
class MannKendallResult:
    tau: float
    p_value: float
    s: int
    var_s: float
    z: float
    significant: bool
    trend: str  # "increasing", "decreasing", "no trend"


@dataclass
class SenSlopeResult:
    slope: float
    intercept: float
    ci_lower: float
    ci_upper: float
    confidence: float


@dataclass
class LinearRegressionResult:
    slope: float
    intercept: float
    r_squared: float
    p_value: float
    ci_lower: float
    ci_upper: float
    significant: bool


def mann_kendall_test(values: List[float], alpha: float = TREND_ALPHA) -> MannKendallResult:
    """
    Mann-Kendall trend test with Sen's slope estimator.
    Returns tau, p-value, and trend direction.
    """
    n = len(values)
    if n < 3:
        return MannKendallResult(
            tau=0.0, p_value=1.0, s=0, var_s=0.0, z=0.0,
            significant=False, trend="insufficient_data"
        )

    # Calculate S statistic
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            if values[j] > values[i]:
                s += 1
            elif values[j] < values[i]:
                s -= 1

    # Calculate variance of S (accounting for ties)
    # Count ties
    unique_values = {}
    for v in values:
        unique_values[v] = unique_values.get(v, 0) + 1

    tie_correction = 0
    for count in unique_values.values():
        if count > 1:
            tie_correction += count * (count - 1) * (2 * count + 5)

    var_s = (n * (n - 1) * (2 * n + 5) - tie_correction) / 18

    if var_s == 0:
        return MannKendallResult(
            tau=0.0, p_value=1.0, s=s, var_s=var_s, z=0.0,
            significant=False, trend="no_trend"
        )

    # Calculate Z
    if s > 0:
        z = (s - 1) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(var_s)
    else:
        z = 0.0

    # Two-tailed p-value
    p_value = 2 * (1 - _normal_cdf(abs(z)))

    # Tau
    tau = s / (n * (n - 1) / 2)

    # Determine trend
    if p_value < alpha:
        trend = "increasing" if s > 0 else "decreasing"
        significant = True
    else:
        trend = "no trend"
        significant = False

    return MannKendallResult(
        tau=tau, p_value=p_value, s=s, var_s=var_s, z=z,
        significant=significant, trend=trend
    )


def _normal_cdf(x: float) -> float:
    """Standard normal CDF approximation."""
    # Abramowitz and Stegun approximation
    t = 1 / (1 + 0.2316419 * x)
    poly = ((((1.330274429 * t - 1.821255978) * t + 1.781477937) * t
             - 0.356563782) * t + 0.31938153) * t
    return 1 - poly * math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def _normal_ppf(p: float) -> float:
    """Standard normal percent point function (inverse CDF)."""
    # Approximation from Peter John Acklam
    if p <= 0 or p >= 1:
        raise ValueError("p must be between 0 and 1")

    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]

    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    elif p > 0.97575:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    else:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5])*q / \
               (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)


def sen_slope(values: List[float], years: List[int], confidence: float = 0.95) -> SenSlopeResult:
    """
    Sen's slope estimator (Theil-Sen estimator) with confidence interval.
    """
    n = len(values)
    if n < 2:
        return SenSlopeResult(0.0, 0.0, 0.0, 0.0, confidence)

    # All pairwise slopes
    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            if years[j] != years[i]:
                slope = (values[j] - values[i]) / (years[j] - years[i])
                slopes.append(slope)

    if not slopes:
        return SenSlopeResult(0.0, values[0], 0.0, 0.0, confidence)

    slopes.sort()
    median_slope = slopes[len(slopes) // 2]

    # Intercept (median of y - slope * x)
    intercepts = [values[i] - median_slope * years[i] for i in range(n)]
    intercepts.sort()
    median_intercept = intercepts[len(intercepts) // 2]

    # Confidence interval for slope
    alpha = 1 - confidence
    z = _normal_ppf(1 - alpha / 2)

    # Variance of S for Kendall's tau
    n_slopes = len(slopes)
    # C = number of pairs
    C = n * (n - 1) / 2

    # Approximate variance of Sen's slope
    # Using Sen's method: find ranks for confidence interval
    Ru = int(C / 2 - z * math.sqrt(C * (2 * n + 5) / 18))
    Rl = int(C / 2 + z * math.sqrt(C * (2 * n + 5) / 18))

    Ru = max(0, min(Ru, n_slopes - 1))
    Rl = max(0, min(Rl, n_slopes - 1))

    ci_lower = slopes[Ru]
    ci_upper = slopes[Rl]

    return SenSlopeResult(
        slope=median_slope,
        intercept=median_intercept,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        confidence=confidence,
    )


def linear_regression(values: List[float], years: List[int], alpha: float = TREND_ALPHA) -> LinearRegressionResult:
    """
    Ordinary least squares linear regression with confidence intervals.
    """
    n = len(values)
    if n < 3:
        return LinearRegressionResult(
            slope=0.0, intercept=0.0, r_squared=0.0, p_value=1.0,
            ci_lower=0.0, ci_upper=0.0, significant=False
        )

    x = [float(y) for y in years]
    y = values

    # Means
    x_mean = sum(x) / n
    y_mean = sum(y) / n

    # Sums
    sxx = sum((xi - x_mean) ** 2 for xi in x)
    sxy = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))

    if sxx == 0:
        return LinearRegressionResult(
            slope=0.0, intercept=y_mean, r_squared=0.0, p_value=1.0,
            ci_lower=0.0, ci_upper=0.0, significant=False
        )

    slope = sxy / sxx
    intercept = y_mean - slope * x_mean

    # Predictions and residuals
    y_pred = [intercept + slope * xi for xi in x]
    residuals = [y[i] - y_pred[i] for i in range(n)]

    # R-squared
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    ss_res = sum(r ** 2 for r in residuals)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Standard error of slope
    mse = ss_res / (n - 2)  # Mean squared error
    se_slope = math.sqrt(mse / sxx)

    # t-statistic for slope
    t_stat = slope / se_slope if se_slope > 0 else 0

    # Two-tailed p-value (using t-distribution approximation with normal)
    # For n=8, df=6. Using normal approximation for simplicity.
    p_value = 2 * (1 - _normal_cdf(abs(t_stat)))

    # Confidence interval for slope
    z = _normal_ppf(1 - alpha / 2)
    ci_lower = slope - z * se_slope
    ci_upper = slope + z * se_slope

    significant = p_value < alpha

    return LinearRegressionResult(
        slope=slope,
        intercept=intercept,
        r_squared=r_squared,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        significant=significant,
    )


def run_trend_analysis(
    values: List[float],
    years: List[int],
    variable: str
) -> Dict[str, Any]:
    """Run complete trend analysis and return formatted results."""
    mk = mann_kendall_test(values)
    sen = sen_slope(values, years)
    lr = linear_regression(values, years)

    # Generate interpretation
    warnings = []
    if len(values) <= TREND_WARNING_N:
        warnings.append(
            f"WARNING: Only {len(values)} data points (n={len(values)}). "
            f"Statistical power is very low. Results should be interpreted with extreme caution."
        )

    if mk.significant:
        trend_desc = f"significant {mk.trend} trend (p={mk.p_value:.4f}, τ={mk.tau:.3f})"
    else:
        trend_desc = f"no significant trend (p={mk.p_value:.4f}, τ={mk.tau:.3f})"

    if lr.significant:
        lr_desc = f"Linear regression: slope={lr.slope:.4f}/yr (p={lr.p_value:.4f}, R²={lr.r_squared:.3f})"
    else:
        lr_desc = f"Linear regression: slope={lr.slope:.4f}/yr (not significant, p={lr.p_value:.4f}, R²={lr.r_squared:.3f})"

    interpretation = (
        f"{variable.capitalize()} shows a {trend_desc}. "
        f"Sen's slope: {sen.slope:.4f}/yr (95% CI: {sen.ci_lower:.4f} to {sen.ci_upper:.4f}). "
        f"{lr_desc}."
    )

    if warnings:
        interpretation += " " + " ".join(warnings)

    return {
        "variable": variable,
        "years": years,
        "values": values,
        "mann_kendall": {
            "tau": mk.tau,
            "p_value": mk.p_value,
            "s": mk.s,
            "var_s": mk.var_s,
            "z": mk.z,
            "significant": mk.significant,
            "trend": mk.trend,
        },
        "sen_slope": {
            "slope": sen.slope,
            "intercept": sen.intercept,
            "ci_lower": sen.ci_lower,
            "ci_upper": sen.ci_upper,
            "confidence": sen.confidence,
        },
        "linear_regression": {
            "slope": lr.slope,
            "intercept": lr.intercept,
            "r_squared": lr.r_squared,
            "p_value": lr.p_value,
            "ci_lower": lr.ci_lower,
            "ci_upper": lr.ci_upper,
            "significant": lr.significant,
        },
        "interpretation": interpretation,
        "warnings": warnings,
    }


# =============================================================================
# TEST FUNCTIONS (for verification)
# =============================================================================
def test_mann_kendall():
    """Test against known example."""
    # Example from Hirsch et al. 1982: no trend
    values = [1, 2, 3, 4, 5, 6, 7, 8]
    years = [1, 2, 3, 4, 5, 6, 7, 8]
    result = run_trend_analysis(values, years, "test")
    assert result["mann_kendall"]["tau"] == 1.0
    assert result["mann_kendall"]["significant"] is True
    print("✓ Increasing trend test passed")

    # No trend
    values = [5, 5, 5, 5, 5, 5, 5, 5]
    result = run_trend_analysis(values, years, "test")
    assert result["mann_kendall"]["tau"] == 0.0
    assert result["mann_kendall"]["significant"] is False
    print("✓ No trend test passed")

    # Decreasing trend
    values = [8, 7, 6, 5, 4, 3, 2, 1]
    result = run_trend_analysis(values, years, "test")
    assert result["mann_kendall"]["tau"] == -1.0
    assert result["mann_kendall"]["significant"] is True
    print("✓ Decreasing trend test passed")

    print("All trend tests passed!")


if __name__ == "__main__":
    test_mann_kendall()