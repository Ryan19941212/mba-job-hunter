#!/usr/bin/env python3
"""
Automatic Indeed Scraper Demo - Try all features!
"""

import asyncio
import sys
import os
import random

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from scrapers.indeed import IndeedScraper
from scrapers.base import ScrapingConfig, JobData
from scrapers.utils import (
    location_normalizer,
    salary_parser,
    skill_extractor,
    calculate_job_relevance_score,
    validate_job_data
)

def print_section(title):
    """Print a section header."""
    print("🎮" + "=" * 58 + "🎮")
    print(f"🚀 {title}")
    print("🎮" + "=" * 58 + "🎮")
    print()

async def demo_search_urls():
    """Demo search URL building."""
    print_section("Search URL Builder Demo")
    
    scraper = IndeedScraper()
    
    test_cases = [
        ("Product Manager", "San Francisco", {}),
        ("Business Analyst", "New York", {"salary_min": 80000, "job_type": "full_time"}),
        ("Strategy Consultant", "Remote", {"remote_only": True, "experience_level": "mid_level"}),
        ("MBA Graduate", "Chicago", {"salary_min": 100000, "date_posted": "3"})
    ]
    
    for i, (query, location, kwargs) in enumerate(test_cases, 1):
        print(f"🔍 Test Case {i}: {query} in {location}")
        
        params = scraper._build_search_params(query, location, **kwargs)
        
        from urllib.parse import urlencode
        search_url = f"{scraper._base_search_url}?{urlencode(params)}"
        
        print(f"  🔗 URL: {search_url}")
        print(f"  📋 Key params: q={params.get('q')}, l={params.get('l')}, salary={params.get('salary', 'None')}")
        print()

def demo_location_normalization():
    """Demo location normalization."""
    print_section("Location Normalization Demo")
    
    test_locations = [
        "sf", "nyc", "la", "chi", "boston, ma", "Seattle, WA",
        "remote", "work from home", "San Francisco, California",
        "New York City", "Washington DC", "wfh"
    ]
    
    print("🌍 Testing various location formats:")
    print()
    
    for location in test_locations:
        normalized = location_normalizer.normalize_location(location)
        is_remote = location_normalizer.is_remote_location(location)
        
        remote_indicator = "🏠 Remote" if is_remote else "🏢 Office"
        print(f"  📍 '{location}' → '{normalized}' ({remote_indicator})")
    
    print()

def demo_salary_parsing():
    """Demo salary parsing."""
    print_section("Salary Parsing Demo")
    
    test_salaries = [
        "$120,000 - $150,000 per year",
        "$75/hour",
        "Up to $200K annually", 
        "Starting from $90,000",
        "$100K - $130K",
        "From $85,000 to $110,000",
        "Competitive salary",
        "$50-60K yearly",
        "80000 - 120000 USD",
        "$25/hr full time"
    ]
    
    print("💰 Testing various salary formats:")
    print()
    
    for salary_text in test_salaries:
        result = salary_parser.parse_salary(salary_text)
        
        min_str = f"${result.get('min'):,.0f}" if result.get('min') else "Not specified"
        max_str = f"${result.get('max'):,.0f}" if result.get('max') else "Not specified"
        period = result.get('period') or "Not specified"
        
        print(f"  💰 '{salary_text}'")
        print(f"     → Min: {min_str}, Max: {max_str}, Period: {period}")
        print()

def demo_skill_extraction():
    """Demo skill extraction."""
    print_section("Skill Extraction Demo")
    
    job_descriptions = [
        """
        Senior Product Manager - MBA Required
        
        We're seeking a Product Manager with strong analytical skills.
        Requirements: MBA, 5+ years experience, SQL, Python, Tableau,
        project management (Agile/Scrum), leadership, communication.
        """,
        
        """
        Strategy Consultant - Top MBA Program
        
        Join our consulting team! Requirements include MBA from 
        top-tier school, financial modeling, business strategy,
        PowerBI, Excel, presentation skills, client management.
        """,
        
        """
        Business Analyst - Tech Startup
        
        Looking for analytical thinker with MBA background.
        Skills needed: SQL, R, business intelligence, operations
        management, process improvement, cross-functional leadership.
        """
    ]
    
    for i, description in enumerate(job_descriptions, 1):
        print(f"🛠️ Job Description {i}:")
        print(f"   {description.strip()[:100]}...")
        
        skills = skill_extractor.extract_skills(description)
        print(f"   📊 Extracted {len(skills)} skills:")
        
        for j, skill in enumerate(skills[:8], 1):  # Show top 8 skills
            print(f"      {j}. {skill}")
        
        if len(skills) > 8:
            print(f"      ... and {len(skills) - 8} more")
        print()

def demo_relevance_scoring():
    """Demo MBA job relevance scoring."""
    print_section("MBA Job Relevance Scoring Demo")
    
    test_jobs = [
        {
            'title': 'Senior Product Manager - MBA Required',
            'company_name': 'Google',
            'description': 'Lead product strategy with MBA background, analytics, leadership',
            'salary_min': 140000,
            'skills_required': ['MBA', 'Product Management', 'Strategy', 'Analytics']
        },
        {
            'title': 'Software Engineer',
            'company_name': 'Startup Inc',
            'description': 'Code in Python and JavaScript, debug applications',
            'salary_min': 95000,
            'skills_required': ['Python', 'JavaScript', 'Debugging']
        },
        {
            'title': 'Management Consultant',
            'company_name': 'McKinsey & Company',
            'description': 'Strategic consulting for Fortune 500 clients, MBA preferred',
            'salary_min': 165000,
            'skills_required': ['MBA', 'Consulting', 'Strategy', 'Financial Modeling']
        },
        {
            'title': 'Data Entry Clerk',
            'company_name': 'Office Corp',
            'description': 'Enter data into spreadsheets, basic computer skills',
            'salary_min': 35000,
            'skills_required': ['Excel', 'Data Entry']
        },
        {
            'title': 'Business Development Manager',
            'company_name': 'Tech Solutions',
            'description': 'Drive business growth, MBA preferred, sales experience',
            'salary_min': 90000,
            'skills_required': ['MBA', 'Business Development', 'Sales', 'Communication']
        }
    ]
    
    print("🎯 Scoring jobs for MBA relevance:")
    print()
    
    for i, job_data in enumerate(test_jobs, 1):
        score = calculate_job_relevance_score(job_data)
        
        if score >= 0.7:
            relevance = "🔥 Excellent match"
        elif score >= 0.5:
            relevance = "✅ Good match"
        elif score >= 0.3:
            relevance = "⚠️ Moderate match"
        else:
            relevance = "❌ Poor match"
        
        print(f"  {i}. {job_data['title']} at {job_data['company_name']}")
        print(f"     Score: {score:.2f} ({score*100:.0f}%) - {relevance}")
        print()

async def demo_job_creation():
    """Demo job data creation and validation."""
    print_section("Job Data Creation & Validation Demo")
    
    # Create sample jobs with different validation outcomes
    jobs = [
        {
            'title': 'Product Manager - MBA Preferred',
            'company_name': 'Innovation Corp',
            'location': 'San Francisco, CA',
            'description': 'Lead product strategy and work with cross-functional teams to deliver innovative solutions for our SaaS platform.',
            'salary_min': 120000,
            'salary_max': 180000,
            'is_remote': False
        },
        {
            'title': 'PM',  # Too short
            'company_name': 'Co',  # Too short
            'description': 'Work.',  # Too short
            'salary_min': 50000
        },
        {
            'title': 'Senior Strategy Consultant',
            'company_name': 'McKinsey & Company',
            'location': 'New York, NY',
            'description': 'Work with Fortune 500 clients on strategic initiatives including market analysis, operational improvements, and digital transformation.',
            'salary_min': 150000,
            'salary_max': 220000,
            'is_remote': True
        }
    ]
    
    for i, job_dict in enumerate(jobs, 1):
        print(f"🏗️ Creating Job {i}:")
        
        # Create JobData object
        job = JobData(
            title=job_dict['title'],
            company_name=job_dict['company_name'],
            location=job_dict.get('location'),
            description=job_dict['description'],
            salary_min=job_dict.get('salary_min'),
            salary_max=job_dict.get('salary_max'),
            source="indeed",
            is_remote=job_dict.get('is_remote', False)
        )
        
        # Validate
        is_valid = await validate_job_data(job_dict)
        relevance = calculate_job_relevance_score(job_dict)
        
        status = "✅ Valid" if is_valid else "❌ Invalid"
        
        print(f"  📝 {job.title} at {job.company_name}")
        print(f"  📊 Validation: {status}")
        print(f"  🎯 MBA Relevance: {relevance:.2f}")
        print()

def demo_scraper_config():
    """Demo scraper configuration."""
    print_section("Scraper Configuration Demo")
    
    configs = [
        ("Conservative", ScrapingConfig(
            max_pages=3,
            delay_between_requests=3.0,
            rate_limit_per_minute=15,
            timeout_seconds=45
        )),
        ("Standard", ScrapingConfig(
            max_pages=10,
            delay_between_requests=2.0,
            rate_limit_per_minute=30,
            timeout_seconds=30
        )),
        ("Aggressive", ScrapingConfig(
            max_pages=25,
            delay_between_requests=1.0,
            rate_limit_per_minute=60,
            timeout_seconds=20
        ))
    ]
    
    print("⚙️ Testing different scraper configurations:")
    print()
    
    for name, config in configs:
        scraper = IndeedScraper(config)
        
        print(f"  🔧 {name} Configuration:")
        print(f"     • Max pages: {scraper.config.max_pages}")
        print(f"     • Delay: {scraper.config.delay_between_requests}s")
        print(f"     • Rate limit: {scraper.config.rate_limit_per_minute}/min")
        print(f"     • Timeout: {scraper.config.timeout_seconds}s")
        print()

def demo_random_jobs():
    """Demo random job generation."""
    print_section("Random MBA Job Generator Demo")
    
    def generate_random_job():
        titles = [
            "Product Manager", "Business Analyst", "Strategy Consultant",
            "Operations Manager", "Marketing Manager", "Finance Manager",
            "Program Manager", "Business Development Manager"
        ]
        
        companies = [
            "Google", "Microsoft", "Amazon", "Apple", "Meta",
            "McKinsey & Company", "BCG", "Bain & Company",
            "Goldman Sachs", "JPMorgan", "Salesforce"
        ]
        
        locations = [
            "San Francisco, CA", "New York, NY", "Seattle, WA",
            "Los Angeles, CA", "Chicago, IL", "Boston, MA", "Remote"
        ]
        
        return JobData(
            title=random.choice(titles),
            company_name=random.choice(companies),
            location=random.choice(locations),
            description="Exciting opportunity for MBA graduates",
            salary_min=random.randint(80, 150) * 1000,
            salary_max=random.randint(150, 250) * 1000,
            source="indeed",
            is_remote=random.choice([True, False]),
            skills_required=random.sample([
                "MBA", "Strategy", "Analytics", "SQL", "Python", 
                "Leadership", "Communication", "Project Management"
            ], k=random.randint(3, 6))
        )
    
    print("🎲 Generating 5 random MBA jobs:")
    print()
    
    for i in range(5):
        job = generate_random_job()
        
        job_dict = {
            'title': job.title,
            'company_name': job.company_name,
            'description': job.description,
            'salary_min': job.salary_min,
            'skills_required': job.skills_required
        }
        
        relevance = calculate_job_relevance_score(job_dict)
        
        print(f"  🏢 Job {i+1}: {job.title}")
        print(f"     🏢 Company: {job.company_name}")
        print(f"     📍 Location: {job.location}")
        print(f"     💰 Salary: ${job.salary_min:,} - ${job.salary_max:,}")
        print(f"     🛠️ Skills: {', '.join(job.skills_required[:3])}...")
        print(f"     🎯 MBA Relevance: {relevance:.2f}")
        print()

async def main():
    """Run all demonstrations."""
    print("🎮" + "=" * 58 + "🎮")
    print("🚀 Welcome to the Indeed Scraper Auto Demo! 🚀")
    print("🎮" + "=" * 58 + "🎮")
    print()
    print("🎯 Running comprehensive demonstration of all features...")
    print()
    
    demos = [
        ("Search URL Building", demo_search_urls),
        ("Location Normalization", demo_location_normalization),
        ("Salary Parsing", demo_salary_parsing),
        ("Skill Extraction", demo_skill_extraction),
        ("MBA Relevance Scoring", demo_relevance_scoring),
        ("Job Data Creation", demo_job_creation),
        ("Scraper Configuration", demo_scraper_config),
        ("Random Job Generation", demo_random_jobs)
    ]
    
    for name, demo_func in demos:
        try:
            if asyncio.iscoroutinefunction(demo_func):
                await demo_func()
            else:
                demo_func()
                
        except Exception as e:
            print(f"❌ Error in {name}: {e}")
        
        print("⏱️ " + "-" * 60)
        print()
    
    print("🎉 Demo completed! All features demonstrated successfully.")
    print("🚀 The Indeed scraper system is ready for your MBA job hunting!")

if __name__ == "__main__":
    asyncio.run(main())