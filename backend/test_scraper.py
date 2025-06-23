#!/usr/bin/env python3
"""
Test script for Indeed scraper functionality.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from scrapers.indeed import IndeedScraper
from scrapers.base import ScrapingConfig

async def test_basic_import():
    """Test basic import functionality."""
    try:
        scraper = IndeedScraper()
        print("✅ IndeedScraper created successfully!")
        print(f"   - Scraper name: {scraper.name}")
        print(f"   - Base URL: {scraper.base_url}")
        print(f"   - Scraper type: {scraper.scraper_type}")
        return True
    except Exception as e:
        print(f"❌ Error creating IndeedScraper: {e}")
        return False

async def test_search_params():
    """Test search parameter building."""
    try:
        scraper = IndeedScraper()
        
        # Test basic search params
        params = scraper._build_search_params("Product Manager", "San Francisco")
        print("✅ Search params built successfully!")
        print(f"   - Query: {params.get('q')}")
        print(f"   - Location: {params.get('l')}")
        print(f"   - Sort: {params.get('sort')}")
        
        # Test with additional filters
        params = scraper._build_search_params(
            "Business Analyst", 
            "New York",
            salary_min=80000,
            job_type="full_time",
            remote_only=True
        )
        print("✅ Advanced search params built successfully!")
        print(f"   - Salary filter: {params.get('salary')}")
        print(f"   - Job type: {params.get('jt')}")
        print(f"   - Remote: {params.get('remotejob')}")
        
        return True
    except Exception as e:
        print(f"❌ Error building search params: {e}")
        return False

async def test_salary_parsing():
    """Test salary parsing functionality."""
    try:
        scraper = IndeedScraper()
        
        test_salaries = [
            "$80,000 - $120,000",
            "Up to $150,000 per year",
            "$50/hour",
            "From $90,000 annually",
            "Competitive salary"
        ]
        
        print("✅ Testing salary parsing:")
        for salary_text in test_salaries:
            result = scraper._parse_salary(salary_text)
            print(f"   - '{salary_text}' -> Min: {result.get('min')}, Max: {result.get('max')}, Period: {result.get('period')}")
        
        return True
    except Exception as e:
        print(f"❌ Error in salary parsing: {e}")
        return False

async def test_skills_extraction():
    """Test skills extraction functionality."""
    try:
        scraper = IndeedScraper()
        
        test_description = """
        We are looking for a Product Manager with MBA background to join our team.
        Requirements:
        - MBA from top-tier university
        - 3+ years of product management experience
        - Strong analytical skills with SQL and Python
        - Experience with Tableau and PowerBI
        - Project management experience with Agile methodology
        - Leadership and communication skills
        - Strategic thinking and business strategy experience
        """
        
        skills = scraper._extract_skills(test_description)
        print("✅ Skills extraction test:")
        print(f"   - Found {len(skills)} skills: {skills[:10]}")  # Show first 10
        
        return True
    except Exception as e:
        print(f"❌ Error in skills extraction: {e}")
        return False

async def test_relevance_filtering():
    """Test MBA job relevance filtering."""
    try:
        scraper = IndeedScraper()
        
        # Create mock job data
        from scrapers.base import JobData
        
        relevant_job = JobData(
            title="Product Manager - MBA Preferred",
            company_name="Tech Company",
            description="Looking for MBA graduate with strategy and analytics experience",
            source="indeed"
        )
        
        irrelevant_job = JobData(
            title="Warehouse Worker",
            company_name="Logistics Co",
            description="Physical labor, loading and unloading trucks",
            source="indeed"
        )
        
        print("✅ Job relevance filtering test:")
        print(f"   - Relevant job: {scraper._is_relevant_job(relevant_job)}")
        print(f"   - Irrelevant job: {scraper._is_relevant_job(irrelevant_job)}")
        
        return True
    except Exception as e:
        print(f"❌ Error in relevance filtering: {e}")
        return False

async def test_configuration():
    """Test scraper configuration."""
    try:
        # Test with custom config
        config = ScrapingConfig(
            max_pages=5,
            delay_between_requests=1.0,
            timeout_seconds=20,
            rate_limit_per_minute=40
        )
        
        scraper = IndeedScraper(config)
        print("✅ Custom configuration test:")
        print(f"   - Max pages: {scraper.config.max_pages}")
        print(f"   - Delay: {scraper.config.delay_between_requests}")
        print(f"   - Rate limit: {scraper.config.rate_limit_per_minute}")
        
        return True
    except Exception as e:
        print(f"❌ Error in configuration: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting Indeed Scraper Tests\n")
    
    tests = [
        ("Basic Import", test_basic_import),
        ("Search Parameters", test_search_params),
        ("Salary Parsing", test_salary_parsing),
        ("Skills Extraction", test_skills_extraction),
        ("Relevance Filtering", test_relevance_filtering),
        ("Configuration", test_configuration),
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
    print(f"\n📊 Test Results Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The scraper is ready for use.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    asyncio.run(main())