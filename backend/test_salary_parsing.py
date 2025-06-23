#!/usr/bin/env python3
"""
Test salary parsing functionality after fixes.
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from scrapers.utils import salary_parser

def test_salary_parsing():
    """Test salary parsing with various formats."""
    
    test_cases = [
        ("$120,000 - $150,000 per year", {"min": 120000, "max": 150000}),
        ("$75/hour", {"min": 75, "period": "hourly"}),
        ("Up to $200K annually", {"max": 200000}),
        ("Starting from $90,000", {"min": 90000}),
        ("Competitive salary", {"min": None, "max": None}),
        ("$100K - $130K", {"min": 100000, "max": 130000}),
        ("From $85,000 to $110,000", {"min": 85000, "max": 110000})
    ]
    
    print("🧪 Testing Salary Parsing After Fixes\n")
    
    all_passed = True
    
    for i, (salary_text, expected) in enumerate(test_cases, 1):
        result = salary_parser.parse_salary(salary_text)
        
        # Check expectations
        passed = True
        issues = []
        
        if expected.get("min") is not None:
            if result.get("min") != expected["min"]:
                passed = False
                issues.append(f"min: got {result.get('min')}, expected {expected['min']}")
        
        if expected.get("max") is not None:
            if result.get("max") != expected["max"]:
                passed = False
                issues.append(f"max: got {result.get('max')}, expected {expected['max']}")
        
        if expected.get("period") is not None:
            if result.get("period") != expected["period"]:
                passed = False
                issues.append(f"period: got {result.get('period')}, expected {expected['period']}")
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{i}. {status} '{salary_text}'")
        print(f"   Result: Min={result.get('min')}, Max={result.get('max')}, Period={result.get('period')}")
        
        if not passed:
            print(f"   Issues: {', '.join(issues)}")
            all_passed = False
        
        print()
    
    if all_passed:
        print("🎉 All salary parsing tests passed!")
    else:
        print("⚠️  Some salary parsing tests failed.")
    
    return all_passed

if __name__ == "__main__":
    test_salary_parsing()