#!/usr/bin/env python3
"""
Demo script for Urban Green and Blue Change Monitor.
Run this to verify the backend works and see sample output.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from config import STUDY_YEARS, DISTRICTS, DEFAULT_THRESHOLDS, SEASON_WINDOWS
from schemas import AnalysisRequest, SeasonWindow, ThresholdsRequest
from gee_processor import run_analysis, initialize_gee
from trend_analysis import run_trend_analysis
from cache import get_cache


async def demo_basic_analysis():
    """Run a basic analysis for Bengaluru Urban."""
    print("=" * 60)
    print("DEMO: Basic Analysis for Bengaluru Urban (2018, 2025)")
    print("=" * 60)

    request = AnalysisRequest(
        district_id="bengaluru_urban",
        years=[2018, 2025],
        season=SeasonWindow(name="oct-dec"),
        classifier="spectral",
        thresholds=ThresholdsRequest(),
        cloud_threshold=80,
        scale=20,
    )

    print(f"District: {DISTRICTS['bengaluru_urban'].display_name}")
    print(f"Years: {request.years}")
    print(f"Season: {request.season.name}")
    print(f"Classifier: {request.classifier}")
    print(f"Scale: {request.scale}m")
    print()

    try:
        result = await run_analysis(request)
        print("✓ Analysis completed successfully!")
        print()

        # Print summary
        print("Yearly Statistics:")
        print("-" * 100)
        print(f"{'Year':<6} {'Images':<8} {'Valid km²':<12} {'Veg km²':<10} {'Water km²':<12} {'Built km²':<12} {'Veg %':<8} {'Water %':<9} {'Built %':<9} {'Mean NDVI':<10}")
        print("-" * 100)

        for stat in result["stats"]:
            print(f"{stat['year']:<6} {stat['images_used']:<8} {stat['valid_km2']:<12.2f} "
                  f"{stat['vegetation_km2']:<10.2f} {stat['water_km2']:<12.2f} "
                  f"{stat['built_bare_km2']:<12.2f} {stat['vegetation_pct']:<8.1f} "
                  f"{stat['water_pct']:<9.1f} {stat['built_bare_pct']:<9.1f} "
                  f"{stat['mean_ndvi']:<10.3f}")

        print("-" * 100)
        print()

        # Print changes
        if len(result["stats"]) == 2:
            first = result["stats"][0]
            last = result["stats"][1]
            print("Changes (2018 → 2025):")
            for cls, label in [("vegetation", "Vegetation"), ("water", "Water"), ("built_bare", "Built-up/Bare")]:
                km2_first = first[f"{cls}_km2"]
                km2_last = last[f"{cls}_km2"]
                pct_first = first[f"{cls}_pct"]
                pct_last = last[f"{cls}_pct"]
                change_km2 = km2_last - km2_first
                change_pct = (change_km2 / km2_first * 100) if km2_first > 0 else 0
                direction = "gain" if change_km2 > 0 else "loss"
                print(f"  {label}: {km2_first:.2f} → {km2_last:.2f} km² ({pct_first:.1f}% → {pct_last:.1f}%) | "
                      f"{direction} {abs(change_km2):.2f} km² ({abs(change_pct):.1f}%)")

            ndvi_change = last["mean_ndvi"] - first["mean_ndvi"]
            print(f"  Mean NDVI: {first['mean_ndvi']:.3f} → {last['mean_ndvi']:.3f} | "
                  f"change: {ndvi_change:+.3f}")

        # Quality summary
        print()
        print("Quality Summary:")
        qs = result["quality_summary"]
        print(f"  Years with warnings: {qs['years_with_warnings']}")
        print(f"  Outlier years: {qs['outlier_years']}")
        print(f"  Recommended baseline: {result['recommended_baseline_year']}")

        return result

    except Exception as e:
        print(f"✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def demo_trend_analysis():
    """Demonstrate trend analysis with sample data."""
    print("\n" + "=" * 60)
    print("DEMO: Trend Analysis (Mann-Kendall, Sen's Slope)")
    print("=" * 60)

    # Sample vegetation percentages over 8 years
    years = STUDY_YEARS
    veg_pct = [12.3, 12.8, 13.1, 12.9, 13.5, 13.2, 13.8, 14.1]  # Slight increasing trend

    print(f"Years: {years}")
    print(f"Vegetation %: {veg_pct}")

    result = run_trend_analysis(veg_pct, years, "vegetation")

    print(f"\nMann-Kendall: τ={result['mann_kendall']['tau']:.3f}, "
          f"p={result['mann_kendall']['p_value']:.4f}, "
          f"trend={result['mann_kendall']['trend']}, "
          f"significant={result['mann_kendall']['significant']}")

    print(f"Sen's Slope: {result['sen_slope']['slope']:.4f}/yr "
          f"(95% CI: {result['sen_slope']['ci_lower']:.4f} to {result['sen_slope']['ci_upper']:.4f})")

    print(f"Linear Regression: slope={result['linear_regression']['slope']:.4f}/yr, "
          f"R²={result['linear_regression']['r_squared']:.3f}, "
          f"p={result['linear_regression']['p_value']:.4f}, "
          f"significant={result['linear_regression']['significant']}")

    print(f"\nInterpretation: {result['interpretation']}")
    if result['warnings']:
        print(f"Warnings: {'; '.join(result['warnings'])}")


async def demo_cache():
    """Demonstrate caching functionality."""
    print("\n" + "=" * 60)
    print("DEMO: Cache System")
    print("=" * 60)

    cache = get_cache()

    # Store some test data
    test_params = {"district": "bengaluru_urban", "years": [2018, 2025], "classifier": "spectral"}
    test_data = {"result": "sample data", "timestamp": "2024-01-01"}

    cache.set("demo", test_params, test_data)
    print("✓ Stored test data in cache")

    # Retrieve
    retrieved = cache.get("demo", test_params)
    if retrieved:
        print("✓ Retrieved data from cache")
        print(f"  Data: {retrieved}")
    else:
        print("✗ Cache miss")

    # Stats
    stats = cache.get_stats()
    print(f"\nCache Stats: {stats}")


async def demo_config():
    """Show configuration constants."""
    print("\n" + "=" * 60)
    print("DEMO: Configuration Constants")
    print("=" * 60)

    print(f"Study Years: {STUDY_YEARS}")
    print(f"Default Season: {list(SEASON_WINDOWS.keys())[0]}")
    print(f"Season Windows: {SEASON_WINDOWS}")
    print(f"Analysis Scales: [10, 20, 30]")
    print(f"Default Scale: 20m")
    print(f"Export CRS: EPSG:32643")
    print()
    print("Districts:")
    for key, district in DISTRICTS.items():
        print(f"  {key}: {district.display_name}")
        print(f"    Asset: {district.asset_id} (feature {district.feature_index})")
        print(f"    Bounds: {district.bounds}")
    print()
    print("Default Thresholds:")
    for k, v in DEFAULT_THRESHOLDS.__dict__.items():
        print(f"  {k}: {v}")


async def main():
    """Run all demos."""
    print("Urban Green and Blue Change Monitor - Demo Script")
    print("=" * 60)

    # Initialize GEE (will use default credentials or service account)
    try:
        initialize_gee()
        print("✓ GEE initialized")
    except Exception as e:
        print(f"⚠ GEE initialization failed (expected if no credentials): {e}")
        print("  Some demos will not work without GEE access.")
        print()

    # Run demos
    await demo_config()
    await demo_cache()
    await demo_trend_analysis()

    # Only run GEE analysis if credentials available
    try:
        await demo_basic_analysis()
    except Exception as e:
        print(f"\n⚠ GEE analysis demo skipped: {e}")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())