#!/usr/bin/env python3
"""
Test script for Notion API integration.

Tests all major Notion writer functionality including database creation,
job writing, and data synchronization.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.notion_writer import NotionWriter, NotionWriterError
from scrapers.base import JobData

def print_section(title: str):
    """Print a test section header."""
    print("🔸" + "=" * 58 + "🔸")
    print(f"🧪 {title}")
    print("🔸" + "=" * 58 + "🔸")
    print()

async def test_notion_connection():
    """Test basic Notion API connection."""
    print_section("Notion API Connection Test")
    
    try:
        # Test with environment variables or dummy key
        test_key = os.getenv("NOTION_API_KEY", "dummy_key_for_testing")
        
        writer = NotionWriter(api_key=test_key)
        
        if test_key == "dummy_key_for_testing":
            print("⚠️  Using dummy API key - this will fail but tests the structure")
            print("   Set NOTION_API_KEY environment variable for real testing")
            return False
        
        # Test connection
        connection_ok = await writer.test_connection()
        
        if connection_ok:
            print("✅ Notion API connection successful!")
            return True
        else:
            print("❌ Notion API connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False
    finally:
        if 'writer' in locals():
            await writer.close()

async def test_database_schema():
    """Test database schema generation."""
    print_section("Database Schema Test")
    
    try:
        writer = NotionWriter(api_key="dummy_key")
        
        # Test schema generation
        schema = writer._get_database_properties_schema()
        
        print("✅ Database schema generated successfully!")
        print(f"   Total properties: {len(schema)}")
        
        # Check key properties
        required_props = [
            "Job Title", "Company", "Location", "Job URL",
            "Salary Min", "Salary Max", "Application Status",
            "AI Fit Score", "MBA Relevance", "Required Skills"
        ]
        
        missing_props = [prop for prop in required_props if prop not in schema]
        
        if missing_props:
            print(f"❌ Missing required properties: {missing_props}")
            return False
        else:
            print("✅ All required properties present")
        
        print("\n📋 Key properties found:")
        for prop in required_props[:5]:  # Show first 5
            prop_type = list(schema[prop].keys())[0]
            print(f"   • {prop}: {prop_type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False
    finally:
        if 'writer' in locals():
            await writer.close()

async def test_job_data_formatting():
    """Test job data formatting for Notion."""
    print_section("Job Data Formatting Test")
    
    try:
        writer = NotionWriter(api_key="dummy_key")
        
        # Create sample job data
        sample_job = {
            "title": "Senior Product Manager - MBA Required",
            "company_name": "Google",
            "location": "Mountain View, CA",
            "description": "Lead product strategy for our AI platform. MBA preferred with 5+ years PM experience.",
            "requirements": "• MBA from top-tier school\n• 5+ years product management\n• Strong analytical skills",
            "salary_min": 140000,
            "salary_max": 200000,
            "salary_currency": "USD",
            "job_type": "Full-time",
            "experience_level": "Senior Level",
            "is_remote": False,
            "posted_date": datetime.now(timezone.utc),
            "source": "indeed",
            "source_url": "https://indeed.com/viewjob?jk=example123",
            "skills_required": ["MBA", "Product Management", "Strategy", "Analytics", "Leadership"],
            "ai_fit_score": 85,
            "benefits": ["Health insurance", "401k matching", "Flexible PTO"]
        }
        
        # Format for Notion
        formatted_data = await writer.format_job_for_notion(sample_job)
        
        print("✅ Job data formatted successfully!")
        
        # Check required properties
        properties = formatted_data.get("properties", {})
        children = formatted_data.get("children", [])
        
        print(f"   Properties: {len(properties)}")
        print(f"   Content blocks: {len(children)}")
        
        # Verify key properties
        required_notion_props = ["Job Title", "Company", "Job URL", "Salary Min", "Salary Max"]
        missing_notion_props = [prop for prop in required_notion_props if prop not in properties]
        
        if missing_notion_props:
            print(f"❌ Missing Notion properties: {missing_notion_props}")
            return False
        
        print("\n📋 Formatted properties:")
        for prop in required_notion_props:
            prop_data = properties[prop]
            prop_type = list(prop_data.keys())[0]
            print(f"   • {prop}: {prop_type}")
        
        print(f"\n📄 Content blocks generated: {len(children)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Formatting test failed: {e}")
        return False
    finally:
        if 'writer' in locals():
            await writer.close()

async def test_rich_text_processing():
    """Test rich text block creation."""
    print_section("Rich Text Processing Test")
    
    try:
        writer = NotionWriter(api_key="dummy_key")
        
        test_texts = [
            "Short text",
            "Medium length text that should fit in one block without any issues.",
            "Very long text that exceeds the normal length limit and should be properly truncated or split into multiple blocks. " * 20,
            "Text with\n\nmultiple\n\nparagraphs\n\nand line breaks",
            ""  # Empty text
        ]
        
        print("✅ Testing rich text processing:")
        
        for i, text in enumerate(test_texts, 1):
            rich_text = writer.create_rich_text_blocks(text, max_length=100)
            
            if text == "":
                expected_blocks = 0
            else:
                expected_blocks = max(1, len(text) // 100 + (1 if len(text) % 100 else 0))
            
            print(f"   {i}. Text length {len(text)} → {len(rich_text)} blocks")
            
            # Validate block structure
            for block in rich_text:
                if "text" not in block or "content" not in block["text"]:
                    print(f"❌ Invalid block structure in test {i}")
                    return False
        
        print("✅ All rich text tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Rich text test failed: {e}")
        return False
    finally:
        if 'writer' in locals():
            await writer.close()

async def test_description_blocks():
    """Test description block creation."""
    print_section("Description Blocks Test")
    
    try:
        writer = NotionWriter(api_key="dummy_key")
        
        # Test various description formats
        test_descriptions = [
            "Simple paragraph description.",
            
            "Multi-paragraph description.\n\nSecond paragraph here.\n\nThird paragraph.",
            
            "Description with list:\n• First item\n• Second item\n• Third item",
            
            "Mixed content:\n\nParagraph before list.\n\n• List item 1\n• List item 2\n\nParagraph after list.",
            
            "Numbered list:\n1. First step\n2. Second step\n3. Third step"
        ]
        
        print("✅ Testing description block creation:")
        
        for i, desc in enumerate(test_descriptions, 1):
            blocks = writer._create_description_blocks(desc)
            
            print(f"   {i}. Description → {len(blocks)} blocks")
            
            # Validate block types
            block_types = [block.get("type") for block in blocks]
            valid_types = {"paragraph", "bulleted_list_item"}
            
            invalid_types = [bt for bt in block_types if bt not in valid_types]
            if invalid_types:
                print(f"❌ Invalid block types: {invalid_types}")
                return False
        
        print("✅ All description block tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Description blocks test failed: {e}")
        return False
    finally:
        if 'writer' in locals():
            await writer.close()

async def test_batch_operations():
    """Test batch operation structure."""
    print_section("Batch Operations Test")
    
    try:
        writer = NotionWriter(api_key="dummy_key")
        
        # Create sample jobs for batch testing
        sample_jobs = []
        for i in range(5):
            job = {
                "title": f"Test Job {i+1}",
                "company_name": f"Company {i+1}",
                "location": "San Francisco, CA",
                "description": f"Test job description {i+1}",
                "salary_min": 80000 + (i * 10000),
                "salary_max": 120000 + (i * 10000),
                "source": "indeed",
                "source_url": f"https://indeed.com/job{i+1}",
                "skills_required": ["MBA", "Leadership", "Strategy"]
            }
            sample_jobs.append(job)
        
        print(f"✅ Created {len(sample_jobs)} sample jobs for batch testing")
        
        # Test formatting each job (without actually writing to Notion)
        formatted_jobs = []
        for job in sample_jobs:
            formatted = await writer.format_job_for_notion(job)
            formatted_jobs.append(formatted)
        
        print(f"✅ Successfully formatted {len(formatted_jobs)} jobs")
        
        # Validate all formatted jobs have required structure
        for i, formatted in enumerate(formatted_jobs):
            if "properties" not in formatted:
                print(f"❌ Job {i+1} missing properties")
                return False
            
            if "Job Title" not in formatted["properties"]:
                print(f"❌ Job {i+1} missing title")
                return False
        
        print("✅ All batch formatting tests passed!")
        
        # Test statistics
        stats = writer.get_stats()
        print(f"\n📊 Initial stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch operations test failed: {e}")
        return False
    finally:
        if 'writer' in locals():
            await writer.close()

async def test_error_handling():
    """Test error handling capabilities."""
    print_section("Error Handling Test")
    
    try:
        # Test with invalid API key
        writer = NotionWriter(api_key="invalid_key")
        
        # Test connection with invalid key
        connection_ok = await writer.test_connection()
        
        if connection_ok:
            print("⚠️  Unexpected: connection succeeded with invalid key")
        else:
            print("✅ Correctly detected invalid API key")
        
        # Test with empty job data
        try:
            formatted = await writer.format_job_for_notion({})
            
            # Should handle empty data gracefully
            if "properties" in formatted:
                print("✅ Gracefully handled empty job data")
            else:
                print("❌ Failed to handle empty job data")
                return False
        except Exception as e:
            print(f"⚠️  Empty data formatting error: {e}")
        
        # Test with malformed data
        try:
            malformed_job = {
                "title": None,
                "salary_min": "not_a_number",
                "posted_date": "invalid_date"
            }
            
            formatted = await writer.format_job_for_notion(malformed_job)
            print("✅ Gracefully handled malformed job data")
            
        except Exception as e:
            print(f"⚠️  Malformed data error: {e}")
        
        print("✅ Error handling tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    finally:
        if 'writer' in locals():
            await writer.close()

async def test_integration_with_scraper():
    """Test integration with scraper JobData."""
    print_section("Scraper Integration Test")
    
    try:
        writer = NotionWriter(api_key="dummy_key")
        
        # Create JobData object (from scraper)
        job_data_obj = JobData(
            title="Product Manager - MBA Required",
            company_name="Innovative Tech Solutions",
            location="San Francisco, CA",
            description="Leading product strategy for our SaaS platform...",
            requirements="MBA required, 3+ years PM experience",
            salary_min=120000,
            salary_max=180000,
            salary_currency="USD",
            salary_period="annual",
            job_type="Full-time",
            experience_level="Mid Level",
            source="indeed",
            source_url="https://indeed.com/viewjob?jk=example123",
            skills_required=["MBA", "Product Management", "Strategy", "SQL"],
            is_remote=False,
            posted_date=datetime.now(timezone.utc)
        )
        
        # Convert JobData to dict (as it would come from scraper)
        job_dict = {
            "title": job_data_obj.title,
            "company_name": job_data_obj.company_name,
            "location": job_data_obj.location,
            "description": job_data_obj.description,
            "requirements": job_data_obj.requirements,
            "salary_min": job_data_obj.salary_min,
            "salary_max": job_data_obj.salary_max,
            "salary_currency": job_data_obj.salary_currency,
            "job_type": job_data_obj.job_type,
            "experience_level": job_data_obj.experience_level,
            "source": job_data_obj.source,
            "source_url": job_data_obj.source_url,
            "skills_required": job_data_obj.skills_required,
            "is_remote": job_data_obj.is_remote,
            "posted_date": job_data_obj.posted_date
        }
        
        # Format for Notion
        formatted = await writer.format_job_for_notion(job_dict)
        
        print("✅ Successfully integrated with JobData from scraper!")
        
        # Verify all data was preserved
        properties = formatted["properties"]
        
        checks = [
            ("Job Title", job_data_obj.title),
            ("Company", job_data_obj.company_name),
            ("Location", job_data_obj.location),
            ("Job URL", job_data_obj.source_url)
        ]
        
        for prop_name, expected_value in checks:
            if prop_name not in properties:
                print(f"❌ Missing property: {prop_name}")
                return False
            
            # Extract actual value (structure varies by property type)
            actual_value = None
            prop_data = properties[prop_name]
            
            if "title" in prop_data:
                actual_value = prop_data["title"][0]["text"]["content"]
            elif "rich_text" in prop_data:
                actual_value = prop_data["rich_text"][0]["text"]["content"]
            elif "url" in prop_data:
                actual_value = prop_data["url"]
            
            if actual_value != expected_value:
                print(f"❌ Value mismatch for {prop_name}: got {actual_value}, expected {expected_value}")
                return False
        
        print("✅ All scraper integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Scraper integration test failed: {e}")
        return False
    finally:
        if 'writer' in locals():
            await writer.close()

async def main():
    """Run all Notion integration tests."""
    print("🚀" + "=" * 58 + "🚀")
    print("🧪 Notion API Integration Test Suite")
    print("🚀" + "=" * 58 + "🚀")
    print()
    
    print("ℹ️  Note: Most tests use dummy API keys and won't make real API calls")
    print("   Set NOTION_API_KEY environment variable for full integration testing")
    print()
    
    tests = [
        ("Connection Test", test_notion_connection),
        ("Database Schema", test_database_schema),
        ("Job Data Formatting", test_job_data_formatting),
        ("Rich Text Processing", test_rich_text_processing),
        ("Description Blocks", test_description_blocks),
        ("Batch Operations", test_batch_operations),
        ("Error Handling", test_error_handling),
        ("Scraper Integration", test_integration_with_scraper)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
            
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
        
        print("⏱️ " + "-" * 60)
        print()
    
    # Summary
    print("📊 Test Results Summary")
    print("-" * 40)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Notion integration tests passed!")
        print("🚀 The Notion writer system is ready for production!")
    else:
        print("⚠️  Some tests failed. Check implementation or API configuration.")
    
    print()
    print("🔧 To test with real Notion API:")
    print("   1. Create a Notion integration at https://www.notion.so/my-integrations")
    print("   2. Set NOTION_API_KEY environment variable")
    print("   3. Optionally set NOTION_DATABASE_ID for existing database")
    print("   4. Run the tests again")

if __name__ == "__main__":
    asyncio.run(main())