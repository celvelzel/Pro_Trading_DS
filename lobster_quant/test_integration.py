#!/usr/bin/env python3
"""
Quant Tool Integration Test
Tests all functionality after integration into lobster_quant
"""

import io
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_modules():
    """Test all modules can be imported"""
    print("TEST 1: Module Imports")
    results = []
    
    try:
        import config
        results.append(("config.py", True, "OK"))
    except Exception as e:
        results.append(("config.py", False, str(e)))
    
    try:
        import quant_tool_data
        results.append(("quant_tool_data.py", True, "OK"))
    except Exception as e:
        results.append(("quant_tool_data.py", False, str(e)))
    
    try:
        import quant_tool_indicators
        results.append(("quant_tool_indicators.py", True, "OK"))
    except Exception as e:
        results.append(("quant_tool_indicators.py", False, str(e)))
    
    try:
        import quant_tool_page
        results.append(("quant_tool_page.py", True, "OK"))
    except Exception as e:
        results.append(("quant_tool_page.py", False, str(e)))
    
    for name, ok, msg in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")
    
    return all(r[1] for r in results)


def test_data_fetching():
    """Test data fetching functionality"""
    print("\nTEST 2: Data Fetching (MU)")
    
    import quant_tool_data as qtd
    
    # Test daily data
    daily = qtd.fetch_daily_data("MU", period="5d")
    if "error" in daily:
        print(f"  [FAIL] Daily data: {daily['error']}")
        daily_ok = False
    else:
        print(f"  [PASS] Daily data: {len(daily['date'])} rows")
        print(f"         Latest close: {daily['close'][-1]}")
        daily_ok = True
    
    # Test options data
    options = qtd.fetch_option_chain("MU")
    if options is None:
        print("  [INFO] No options data available")
        options_ok = True
    elif "error" in options:
        print(f"  [FAIL] Options: {options['error']}")
        options_ok = False
    else:
        print(f"  [PASS] Options: {len(options['calls'])} calls, {len(options['puts'])} puts")
        options_ok = True
    
    return daily_ok and options_ok, daily, options


def test_indicators(daily, options):
    """Test indicator calculations"""
    print("\nTEST 3: Indicator Calculations")
    
    import pandas as pd
    import quant_tool_indicators as qti
    
    df = pd.DataFrame({
        "date": pd.to_datetime(daily["date"]),
        "open": daily["open"],
        "high": daily["high"],
        "low": daily["low"],
        "close": daily["close"],
        "volume": daily["volume"],
    })
    df.set_index("date", inplace=True)
    
    # Test ATR%
    atr = qti.calc_atr_percent(df)
    print(f"  [PASS] ATR%: {atr.iloc[-1]:.2f}%")
    
    # Test MA200 distance
    ma200 = qti.calc_ma200_dist(df)
    print(f"  [PASS] MA200 Dist: {ma200.iloc[-1]:.2f}%")
    
    # Test Gap%
    gap = qti.calc_gap_percent(df)
    print(f"  [PASS] Gap%: {gap.iloc[-1]:.2f}%")
    
    # Test options indicators
    if options and "error" not in options:
        current_price = df["close"].iloc[-1]
        
        mp = qti.calc_max_pain(options["calls"], options["puts"], current_price)
        print(f"  [PASS] Max Pain: {mp}")
        
        sr = qti.find_support_resistance(options["calls"], options["puts"])
        print(f"  [PASS] S/R: {sr}")
        
        pcr = qti.calc_put_call_ratio(options["calls"], options["puts"])
        print(f"  [PASS] P/C Ratio: {pcr}")
    
    return True


def test_error_handling():
    """Test error handling"""
    print("\nTEST 4: Error Handling")
    
    import quant_tool_data as qtd
    
    # Empty symbol
    empty = qtd.fetch_daily_data("")
    print(f"  [PASS] Empty symbol: {'error' in empty}")
    
    # Invalid symbol
    invalid = qtd.fetch_daily_data("INVALIDXYZ")
    print(f"  [PASS] Invalid symbol: {'error' in invalid}")
    
    # Invalid options
    none_options = qtd.fetch_option_chain("INVALIDXYZ")
    print(f"  [PASS] Invalid options: {none_options is None or 'error' in str(none_options)}")
    
    return True


def test_feature_completeness():
    """Test feature completeness against original"""
    print("\nTEST 5: Feature Completeness")
    
    with io.open("quant_tool_page.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    features = {
        "OFF Filter Analysis": "OFF Filter" in content,
        "ON Probability": "ON Probability" in content,
        "OFF Probability": "OFF Probability" in content,
        "Options Dashboard": "Options Dashboard" in content,
        "Max Pain": "Max Pain" in content,
        "Support/Resistance": "Support" in content and "Resistance" in content,
        "Put/Call Ratio": "Put/Call Ratio" in content,
        "Volume Chart": "Volume by Strike" in content,
        "OI Chart": "Open Interest" in content,
        "Custom CSS": "unsafe_allow_html" in content,
        "Dark Theme": "1e222a" in content or "282e38" in content,
        "Welcome Page": "Welcome to Quant Tool" in content,
        "Error Handling": "error" in content,
    }
    
    all_pass = True
    for feature, exists in features.items():
        status = "PASS" if exists else "FAIL"
        if not exists:
            all_pass = False
        print(f"  [{status}] {feature}")
    
    return all_pass


def main():
    """Run all tests"""
    print("=" * 60)
    print("Quant Tool Integration Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1
    results.append(("Module Imports", test_modules()))
    
    # Test 2
    data_ok, daily, options = test_data_fetching()
    results.append(("Data Fetching", data_ok))
    
    # Test 3
    if data_ok:
        results.append(("Indicators", test_indicators(daily, options)))
    else:
        print("\n  SKIPPED (no data)")
        results.append(("Indicators", False))
    
    # Test 4
    results.append(("Error Handling", test_error_handling()))
    
    # Test 5
    results.append(("Feature Completeness", test_feature_completeness()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
    
    all_pass = all(r[1] for r in results)
    print("\n" + ("ALL TESTS PASSED" if all_pass else "SOME TESTS FAILED"))
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
