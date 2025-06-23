#!/usr/bin/env python3
"""
Interactive Indeed Scraper Playground

Try out different features of the scraper system interactively!
"""

import asyncio
import sys
import os
from typing import Dict, Any

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

def print_header():
    """Print a fun header."""
    print("🎮" + "=" * 58 + "🎮")
    print("🚀 Welcome to the Indeed Scraper Playground! 🚀")
    print("🎮" + "=" * 58 + "🎮")
    print()
    print("Choose what you'd like to try:")
    print("1. 🔍 Build search URLs")
    print("2. 📍 Test location normalization") 
    print("3. 💰 Parse salary strings")
    print("4. 🛠️  Extract skills from job descriptions")
    print("5. 📊 Score job relevance for MBA roles")
    print("6. 🏗️  Create and validate job data")
    print("7. ⚙️  Test scraper configuration")
    print("8. 🎯 Generate random MBA job data")
    print("9. 🔀 Try everything with sample data")
    print("0. 👋 Exit")
    print()

async def play_search_urls():
    """Let user build search URLs."""
    print("🔍 Search URL Builder")
    print("-" * 30)
    
    scraper = IndeedScraper()
    
    print("Let's build some Indeed search URLs!")
    
    # Get user input
    query = input("Enter job title/keywords (e.g., 'Product Manager'): ").strip()
    if not query:
        query = "Product Manager"
    
    location = input("Enter location (e.g., 'San Francisco' or leave empty): ").strip()
    if not location:
        location = None
    
    print("\nOptional filters (press Enter to skip):")
    salary_min = input("Minimum salary (e.g., 80000): ").strip()
    job_type = input("Job type (full_time/part_time/contract): ").strip()
    remote_only = input("Remote only? (y/n): ").strip().lower() == 'y'
    
    # Build parameters
    kwargs = {}
    if salary_min.isdigit():
        kwargs['salary_min'] = int(salary_min)
    if job_type:
        kwargs['job_type'] = job_type
    if remote_only:
        kwargs['remote_only'] = True
    
    params = scraper._build_search_params(query, location, **kwargs)
    
    from urllib.parse import urlencode
    search_url = f"{scraper._base_search_url}?{urlencode(params)}"
    
    print(f"\n✅ Generated Search URL:")
    print(f"🔗 {search_url}")
    print(f"\n📋 Parameters breakdown:")
    for key, value in params.items():
        print(f"   • {key}: {value}")
    print()

def play_location_normalization():
    """Let user test location normalization."""
    print("📍 Location Normalization Playground")
    print("-" * 40)
    
    print("Try entering different location formats!")
    print("Examples: 'sf', 'nyc', 'remote', 'boston, ma', 'Seattle, WA'")
    print("(Enter 'done' to finish)")
    print()
    
    while True:
        location = input("Enter location to normalize: ").strip()
        
        if location.lower() == 'done':
            break
        
        if not location:
            continue
            
        normalized = location_normalizer.normalize_location(location)
        is_remote = location_normalizer.is_remote_location(location)
        
        print(f"  📍 '{location}' → '{normalized}'")
        print(f"  🏠 Remote job: {'Yes' if is_remote else 'No'}")
        print()

def play_salary_parsing():
    """Let user test salary parsing."""
    print("💰 Salary Parsing Playground")
    print("-" * 35)
    
    print("Try entering different salary formats!")
    print("Examples:")
    print("  • '$120,000 - $150,000 per year'")
    print("  • '$75/hour'") 
    print("  • 'Up to $200K annually'")
    print("  • 'Starting from $90,000'")
    print("  • '$100K - $130K'")
    print("(Enter 'done' to finish)")
    print()
    
    while True:
        salary_text = input("Enter salary text to parse: ").strip()
        
        if salary_text.lower() == 'done':
            break
            
        if not salary_text:
            continue
            
        result = salary_parser.parse_salary(salary_text)
        
        print(f"  💰 Input: '{salary_text}'")
        print(f"  📊 Parsed:")
        print(f"     • Min: ${result.get('min'):,}" if result.get('min') else "     • Min: Not specified")
        print(f"     • Max: ${result.get('max'):,}" if result.get('max') else "     • Max: Not specified")
        print(f"     • Currency: {result.get('currency')}")
        print(f"     • Period: {result.get('period') or 'Not specified'}")
        print()

def play_skill_extraction():
    """Let user test skill extraction."""
    print("🛠️ Skill Extraction Playground")
    print("-" * 35)
    
    print("Enter a job description and see what skills are extracted!")
    print("(Enter 'sample' for a sample description, 'done' to finish)")
    print()
    
    sample_description = """
Senior Product Manager - MBA Preferred

We're seeking an experienced Product Manager to lead our SaaS platform strategy.

Requirements:
• MBA from top-tier business school
• 5+ years product management experience  
• Proficiency in SQL, Python, and data analysis
• Experience with Tableau, PowerBI, or similar BI tools
• Strong project management skills (Agile/Scrum)
• Excellent communication and leadership abilities
• Strategic thinking and business strategy experience
• Financial modeling and consulting background preferred

Join our innovative team at a leading tech company!
"""
    
    while True:
        print("Enter job description (or 'sample'/'done'):")
        description = input("> ").strip()
        
        if description.lower() == 'done':
            break
        elif description.lower() == 'sample':
            description = sample_description
            print("Using sample description...")
        elif not description:
            continue
        
        skills = skill_extractor.extract_skills(description)
        
        print(f"\n🛠️ Extracted {len(skills)} skills:")
        for i, skill in enumerate(skills, 1):
            print(f"  {i:2d}. {skill}")
        print()

def play_relevance_scoring():
    """Let user test job relevance scoring."""
    print("📊 MBA Job Relevance Scoring")
    print("-" * 35)
    
    print("Create job data and see how relevant it is for MBA job hunters!")
    print()
    
    while True:
        print("Enter job details (or 'done' to finish):")
        
        title = input("Job title: ").strip()
        if title.lower() == 'done':
            break
        if not title:
            continue
            
        company = input("Company name: ").strip() or "Unknown Company"
        description = input("Job description (brief): ").strip() or "No description"
        
        # Optional fields
        salary_min_str = input("Min salary (optional): ").strip()
        salary_min = int(salary_min_str) if salary_min_str.isdigit() else None
        
        skills_str = input("Required skills (comma-separated, optional): ").strip()
        skills = [s.strip() for s in skills_str.split(',')] if skills_str else []
        
        # Create job data
        job_data = {
            'title': title,
            'company_name': company,
            'description': description,
            'salary_min': salary_min,
            'skills_required': skills
        }
        
        # Calculate relevance
        score = calculate_job_relevance_score(job_data)
        
        print(f"\n📊 MBA Relevance Analysis:")
        print(f"  🎯 Overall Score: {score:.2f} ({score*100:.1f}%)")
        
        if score >= 0.8:
            print("  🔥 Excellent match for MBA roles!")
        elif score >= 0.6:
            print("  ✅ Good match for MBA roles")
        elif score >= 0.4:
            print("  ⚠️  Moderate match for MBA roles")
        else:
            print("  ❌ Low match for MBA roles")
        
        print()

async def play_job_creation():
    """Let user create and validate job data."""
    print("🏗️ Job Data Creation & Validation")
    print("-" * 40)
    
    print("Let's create a complete JobData object!")
    print()
    
    title = input("Job title: ").strip() or "Product Manager"
    company = input("Company name: ").strip() or "Tech Corp"
    location = input("Location: ").strip() or "San Francisco, CA"
    description = input("Job description: ").strip() or "Exciting PM role at fast-growing startup"
    
    print("\nSalary information:")
    salary_min_str = input("Min salary: ").strip()
    salary_max_str = input("Max salary: ").strip()
    
    salary_min = int(salary_min_str) if salary_min_str.isdigit() else None
    salary_max = int(salary_max_str) if salary_max_str.isdigit() else None
    
    is_remote = input("Remote job? (y/n): ").strip().lower() == 'y'
    
    # Create JobData object
    job = JobData(
        title=title,
        company_name=company,
        location=location,
        description=description,
        salary_min=salary_min,
        salary_max=salary_max,
        source="indeed",
        source_url="https://indeed.com/viewjob?jk=example123",
        is_remote=is_remote
    )
    
    # Validate
    job_dict = {
        'title': job.title,
        'company_name': job.company_name,
        'description': job.description,
        'location': job.location,
        'source': job.source
    }
    
    is_valid = await validate_job_data(job_dict)
    relevance = calculate_job_relevance_score(job_dict)
    
    print(f"\n🏗️ Created JobData:")
    print(f"  📝 Title: {job.title}")
    print(f"  🏢 Company: {job.company_name}")
    print(f"  📍 Location: {job.location}")
    print(f"  💰 Salary: {f'${job.salary_min:,}' if job.salary_min else 'N/A'} - {f'${job.salary_max:,}' if job.salary_max else 'N/A'}")
    print(f"  🏠 Remote: {'Yes' if job.is_remote else 'No'}")
    print(f"  ✅ Valid: {'Yes' if is_valid else 'No'}")
    print(f"  🎯 MBA Relevance: {relevance:.2f}")
    print()

def play_scraper_config():
    """Let user play with scraper configuration."""
    print("⚙️ Scraper Configuration Playground")
    print("-" * 40)
    
    print("Let's create a custom scraper configuration!")
    print()
    
    max_pages = input("Max pages to scrape (default 10): ").strip()
    max_pages = int(max_pages) if max_pages.isdigit() else 10
    
    delay = input("Delay between requests in seconds (default 2.0): ").strip()
    delay = float(delay) if delay.replace('.', '').isdigit() else 2.0
    
    rate_limit = input("Rate limit per minute (default 30): ").strip()
    rate_limit = int(rate_limit) if rate_limit.isdigit() else 30
    
    timeout = input("Request timeout in seconds (default 30): ").strip()
    timeout = int(timeout) if timeout.isdigit() else 30
    
    # Create configuration
    config = ScrapingConfig(
        max_pages=max_pages,
        delay_between_requests=delay,
        rate_limit_per_minute=rate_limit,
        timeout_seconds=timeout,
        headless=True,
        respect_robots_txt=True
    )
    
    # Create scraper with config
    scraper = IndeedScraper(config)
    
    print(f"\n⚙️ Created scraper configuration:")
    print(f"  📄 Max pages: {scraper.config.max_pages}")
    print(f"  ⏰ Delay: {scraper.config.delay_between_requests}s")
    print(f"  🚦 Rate limit: {scraper.config.rate_limit_per_minute}/min")
    print(f"  ⏱️  Timeout: {scraper.config.timeout_seconds}s")
    print(f"  👻 Headless: {scraper.config.headless}")
    print(f"  🤖 Respect robots.txt: {scraper.config.respect_robots_txt}")
    print()

def generate_random_job():
    """Generate random MBA job data for fun."""
    import random
    
    titles = [
        "Product Manager", "Business Analyst", "Strategy Consultant",
        "Operations Manager", "Marketing Manager", "Finance Manager",
        "Program Manager", "Business Development Manager"
    ]
    
    companies = [
        "Google", "Microsoft", "Amazon", "Apple", "Meta",
        "McKinsey & Company", "Boston Consulting Group", "Bain & Company",
        "Goldman Sachs", "JPMorgan", "Salesforce", "Uber", "Airbnb"
    ]
    
    locations = [
        "San Francisco, CA", "New York, NY", "Seattle, WA",
        "Los Angeles, CA", "Chicago, IL", "Boston, MA", "Remote"
    ]
    
    descriptions = [
        "Lead product strategy and drive business growth",
        "Analyze market trends and optimize business processes", 
        "Develop strategic initiatives and manage cross-functional teams",
        "Drive operational excellence and process improvements",
        "Execute go-to-market strategies and growth initiatives"
    ]
    
    job = JobData(
        title=random.choice(titles),
        company_name=random.choice(companies),
        location=random.choice(locations),
        description=random.choice(descriptions),
        salary_min=random.randint(80, 150) * 1000,
        salary_max=random.randint(150, 250) * 1000,
        source="indeed",
        is_remote=random.choice([True, False]),
        skills_required=random.sample([
            "MBA", "Strategy", "Analytics", "SQL", "Python", 
            "Leadership", "Communication", "Project Management"
        ], k=random.randint(3, 6))
    )
    
    return job

def play_random_job():
    """Generate and analyze random job data."""
    print("🎯 Random MBA Job Generator")
    print("-" * 35)
    
    count = input("How many random jobs to generate? (default 3): ").strip()
    count = int(count) if count.isdigit() else 3
    
    print(f"\n🎲 Generating {count} random MBA jobs...\n")
    
    for i in range(count):
        job = generate_random_job()
        
        job_dict = {
            'title': job.title,
            'company_name': job.company_name,
            'description': job.description,
            'salary_min': job.salary_min,
            'skills_required': job.skills_required
        }
        
        relevance = calculate_job_relevance_score(job_dict)
        
        print(f"🏢 Job {i+1}:")
        print(f"  📝 {job.title} at {job.company_name}")
        print(f"  📍 {job.location}")
        print(f"  💰 ${job.salary_min:,} - ${job.salary_max:,}")
        print(f"  🛠️  Skills: {', '.join(job.skills_required[:3])}...")
        print(f"  🎯 MBA Relevance: {relevance:.2f}")
        print()

async def play_everything():
    """Try all features with sample data."""
    print("🔀 Everything Demo with Sample Data")
    print("-" * 40)
    
    # Sample data
    sample_jobs = [
        {
            'title': 'Senior Product Manager',
            'company_name': 'Google',
            'location': 'Mountain View, CA',
            'description': 'Lead product strategy for our AI platform. MBA preferred with 5+ years PM experience.',
            'salary_min': 140000,
            'salary_max': 200000,
            'skills_required': ['MBA', 'Product Management', 'Strategy', 'SQL', 'Leadership']
        },
        {
            'title': 'Management Consultant',
            'company_name': 'McKinsey & Company',
            'location': 'New York, NY',
            'description': 'Work with Fortune 500 clients on strategic initiatives. Top MBA required.',
            'salary_min': 165000,
            'salary_max': 220000,
            'skills_required': ['MBA', 'Consulting', 'Strategy', 'Financial Modeling', 'Communication']
        }
    ]
    
    print("🎯 Analyzing sample MBA jobs...\n")
    
    for i, job_data in enumerate(sample_jobs, 1):
        print(f"📋 Job {i}: {job_data['title']} at {job_data['company_name']}")
        
        # Location normalization
        normalized_location = location_normalizer.normalize_location(job_data['location'])
        print(f"  📍 Location: {job_data['location']} → {normalized_location}")
        
        # Salary parsing
        salary_text = f"${job_data['salary_min']:,} - ${job_data['salary_max']:,}"
        salary_result = salary_parser.parse_salary(salary_text)
        print(f"  💰 Salary: {salary_text} → Min: ${salary_result.get('min'):,}, Max: ${salary_result.get('max'):,}")
        
        # Skills
        skills = skill_extractor.extract_skills(job_data['description'])
        print(f"  🛠️  Extracted skills: {skills[:5]}")
        
        # Validation and relevance
        is_valid = await validate_job_data(job_data)
        relevance = calculate_job_relevance_score(job_data)
        print(f"  ✅ Valid: {is_valid}, MBA Relevance: {relevance:.2f}")
        print()

async def main():
    """Main interactive loop."""
    while True:
        print_header()
        
        choice = input("Enter your choice (0-9): ").strip()
        print()
        
        try:
            if choice == '1':
                await play_search_urls()
            elif choice == '2':
                play_location_normalization()
            elif choice == '3':
                play_salary_parsing()
            elif choice == '4':
                play_skill_extraction()
            elif choice == '5':
                play_relevance_scoring()
            elif choice == '6':
                await play_job_creation()
            elif choice == '7':
                play_scraper_config()
            elif choice == '8':
                play_random_job()
            elif choice == '9':
                await play_everything()
            elif choice == '0':
                print("👋 Thanks for playing with the Indeed scraper!")
                print("🚀 Happy job hunting!")
                break
            else:
                print("❌ Invalid choice. Please try again.")
                continue
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Oops! Something went wrong: {e}")
            print("Let's try again...\n")
        
        input("Press Enter to continue...")
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())