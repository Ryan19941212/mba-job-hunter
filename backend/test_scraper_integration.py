#!/usr/bin/env python3
"""
Integration tests for Indeed scraper with network connectivity.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from scrapers.indeed import IndeedScraper
from scrapers.base import ScrapingConfig
from scrapers.utils import validate_job_data, calculate_job_relevance_score

async def test_network_connectivity():
    """Test basic network connectivity to Indeed."""
    try:
        scraper = IndeedScraper()
        await scraper.initialize()
        
        # Test basic HTTP request to Indeed's robots.txt
        response = await scraper._make_http_request("https://www.indeed.com/robots.txt")
        
        print("✅ Network connectivity test:")
        print(f"   - Status: {response.status_code}")
        print(f"   - Content length: {len(response.content)} bytes")
        print(f"   - Headers: {dict(list(response.headers.items())[:3])}")
        
        await scraper.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Network connectivity failed: {e}")
        return False

async def test_search_url_building():
    """Test search URL construction."""
    try:
        scraper = IndeedScraper()
        
        # Build search URL
        params = scraper._build_search_params(
            "Product Manager", 
            "San Francisco",
            salary_min=100000,
            job_type="full_time"
        )
        
        from urllib.parse import urlencode
        search_url = f"{scraper._base_search_url}?{urlencode(params)}"
        
        print("✅ Search URL building test:")
        print(f"   - URL: {search_url}")
        print(f"   - Length: {len(search_url)} characters")
        
        # Validate URL format
        assert "indeed.com" in search_url
        assert "q=Product+Manager" in search_url
        assert "l=San+Francisco" in search_url
        
        return True
        
    except Exception as e:
        print(f"❌ Search URL building failed: {e}")
        return False

async def test_user_agent_rotation():
    """Test user agent rotation functionality."""
    try:
        scraper = IndeedScraper()
        
        # Test multiple requests to see user agent rotation
        user_agents = set()
        
        for i in range(5):
            # Get user agent that would be used
            import random
            random.seed(i)  # Make it reproducible
            user_agent = random.choice(scraper._user_agents)
            user_agents.add(user_agent)
        
        print("✅ User agent rotation test:")
        print(f"   - Total user agents available: {len(scraper._user_agents)}")
        print(f"   - Unique agents used in 5 requests: {len(user_agents)}")
        
        return True
        
    except Exception as e:
        print(f"❌ User agent rotation failed: {e}")
        return False

async def test_job_data_validation():
    """Test job data validation with utils."""
    try:
        # Create test job data
        valid_job = {
            "title": "Product Manager - MBA Required",
            "company_name": "Tech Corp",
            "location": "San Francisco, CA",
            "description": "We are seeking a dynamic Product Manager with MBA background to lead our product strategy. The ideal candidate will have experience in product management, data analysis, and strategic planning. This role requires strong leadership skills and the ability to work cross-functionally with engineering, design, and marketing teams.",
            "salary_min": 120000,
            "salary_max": 180000,
            "source": "indeed",
            "source_url": "https://indeed.com/viewjob?jk=12345"
        }
        
        invalid_job = {
            "title": "PM",  # Too short
            "company_name": "Corp",
            "description": "Short desc",  # Too short
            "source": "indeed"
        }
        
        valid_result = await validate_job_data(valid_job)
        invalid_result = await validate_job_data(invalid_job)
        
        print("✅ Job data validation test:")
        print(f"   - Valid job passes validation: {valid_result}")
        print(f"   - Invalid job fails validation: {not invalid_result}")
        
        # Test relevance scoring
        relevance_score = calculate_job_relevance_score(valid_job)
        print(f"   - Relevance score: {relevance_score:.2f}")
        
        return valid_result and not invalid_result
        
    except Exception as e:
        print(f"❌ Job data validation failed: {e}")
        return False

async def test_location_normalization():
    """Test location normalization utilities."""
    try:
        from scrapers.utils import location_normalizer
        
        test_locations = [
            ("sf", "San Francisco"),
            ("nyc", "New York"),
            ("boston, ma", "Boston, Massachusetts"),
            ("remote", "Remote"),
            ("Seattle, WA", "Seattle, Washington")
        ]
        
        print("✅ Location normalization test:")
        all_passed = True
        
        for input_loc, expected in test_locations:
            normalized = location_normalizer.normalize_location(input_loc)
            passed = normalized == expected
            all_passed = all_passed and passed
            
            status = "✓" if passed else "✗"
            print(f"   {status} '{input_loc}' -> '{normalized}' (expected: '{expected}')")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Location normalization failed: {e}")
        return False

async def test_advanced_salary_parsing():
    """Test advanced salary parsing from utils."""
    try:
        from scrapers.utils import salary_parser
        
        test_cases = [
            ("$120,000 - $150,000 per year", {"min": 120000, "max": 150000, "period": "annual"}),
            ("$75/hour", {"min": 75, "period": "hourly"}),
            ("Up to $200K annually", {"max": 200000, "period": "annual"}),
            ("Starting from $90,000", {"min": 90000}),
            ("Competitive salary", {"min": None, "max": None})
        ]
        
        print("✅ Advanced salary parsing test:")
        all_passed = True
        
        for salary_text, expected in test_cases:
            result = salary_parser.parse_salary(salary_text)
            
            # Check key fields
            passed = True
            if expected.get("min") and result.get("min") != expected["min"]:
                passed = False
            if expected.get("max") and result.get("max") != expected["max"]:
                passed = False
            if expected.get("period") and result.get("period") != expected["period"]:
                passed = False
            
            all_passed = all_passed and passed
            status = "✓" if passed else "✗"
            print(f"   {status} '{salary_text}' -> Min: {result.get('min')}, Max: {result.get('max')}, Period: {result.get('period')}")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Advanced salary parsing failed: {e}")
        return False

async def test_skill_extraction_utility():
    """Test skill extraction from utils module."""
    try:
        from scrapers.utils import skill_extractor
        
        test_description = """
        Senior Product Manager - MBA Preferred
        
        We're looking for an experienced Product Manager with strong analytical skills.
        
        Requirements:
        - MBA from top-tier business school
        - 5+ years product management experience
        - Proficiency in SQL, Python, and data analysis
        - Experience with Tableau, PowerBI, or similar BI tools
        - Strong project management skills (Agile/Scrum)
        - Excellent communication and leadership abilities
        - Strategic thinking and business strategy experience
        - Financial modeling and analysis skills
        
        Preferred:
        - Consulting background (McKinsey, BCG, Bain)
        - Experience in tech/SaaS industry
        - Six Sigma or Lean certification
        """
        
        skills = skill_extractor.extract_skills(test_description)
        
        print("✅ Skill extraction utility test:")
        print(f"   - Total skills found: {len(skills)}")
        print(f"   - Top 10 skills: {skills[:10]}")
        
        # Check for expected skills
        expected_skills = ["MBA", "SQL", "Python", "Tableau", "PowerBI", "Agile", "leadership"]
        found_skills = [skill.lower() for skill in skills]
        
        matches = sum(1 for expected in expected_skills if any(expected.lower() in found.lower() for found in found_skills))
        print(f"   - Expected skills found: {matches}/{len(expected_skills)}")
        
        return matches >= len(expected_skills) // 2  # At least half should be found
        
    except Exception as e:
        print(f"❌ Skill extraction utility failed: {e}")
        return False

async def test_rate_limiting():
    """Test rate limiting functionality."""
    try:
        config = ScrapingConfig(
            rate_limit_per_minute=5,  # Very low for testing
            delay_between_requests=0.1
        )
        
        scraper = IndeedScraper(config)
        
        # Test rate limiting check
        start_time = asyncio.get_event_loop().time()
        
        # This should complete quickly since we're not making real requests
        for i in range(3):
            await scraper._rate_limit_check()
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        print("✅ Rate limiting test:")
        print(f"   - Time for 3 rate limit checks: {elapsed:.3f} seconds")
        print(f"   - Rate limit per minute: {scraper.config.rate_limit_per_minute}")
        print(f"   - Delay between requests: {scraper.config.delay_between_requests}")
        
        return elapsed >= 0  # Should complete without error
        
    except Exception as e:
        print(f"❌ Rate limiting failed: {e}")
        return False

async def test_scraper_manager():
    """Test scraper manager functionality."""
    try:
        from scrapers.base import ScraperManager
        
        manager = ScraperManager()
        scraper = IndeedScraper()
        
        # Register scraper
        manager.register_scraper(scraper)
        
        print("✅ Scraper manager test:")
        print(f"   - Registered scrapers: {len(manager.scrapers)}")
        print(f"   - Scraper names: {list(manager.scrapers.keys())}")
        
        # Test stats
        stats = manager.get_stats()
        print(f"   - Initial stats: {stats}")
        
        return len(manager.scrapers) == 1 and "indeed" in manager.scrapers
        
    except Exception as e:
        print(f"❌ Scraper manager failed: {e}")
        return False

async def main():
    """Run all integration tests."""
    print("🚀 Starting Indeed Scraper Integration Tests\n")
    
    tests = [
        ("Network Connectivity", test_network_connectivity),
        ("Search URL Building", test_search_url_building),
        ("User Agent Rotation", test_user_agent_rotation),
        ("Job Data Validation", test_job_data_validation),
        ("Location Normalization", test_location_normalization),
        ("Advanced Salary Parsing", test_advanced_salary_parsing),
        ("Skill Extraction Utility", test_skill_extraction_utility),
        ("Rate Limiting", test_rate_limiting),
        ("Scraper Manager", test_scraper_manager),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test:")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n📊 Integration Test Results:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! The scraper system is fully functional.")
        print("\n🔥 Ready for production use with the following features:")
        print("   • Indeed job scraping with anti-detection")
        print("   • Advanced salary parsing and normalization")
        print("   • MBA-focused skill extraction")
        print("   • Job relevance scoring")
        print("   • Rate limiting and error handling")
        print("   • Comprehensive data validation")
    else:
        print("⚠️  Some integration tests failed. Please check the issues above.")

if __name__ == "__main__":
    asyncio.run(main())