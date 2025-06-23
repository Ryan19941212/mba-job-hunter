#!/usr/bin/env python3
"""
Complete Notion + Scraper Integration Demo

Demonstrates the full workflow from job scraping to Notion database creation
and data synchronization for the MBA Job Hunter application.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import List, Dict
import random

# Add the app directory to Python path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.notion_writer import NotionWriter
from scrapers.indeed import IndeedScraper
from scrapers.base import JobData, ScrapingConfig
from scrapers.utils import calculate_job_relevance_score

def print_banner():
    """Print demo banner."""
    print("🎯" + "=" * 58 + "🎯")
    print("🚀 MBA Job Hunter: Notion + Scraper Integration Demo")
    print("🎯" + "=" * 58 + "🎯")
    print()

async def demo_notion_database_setup():
    """Demo Notion database setup and schema."""
    print("📋 1. Notion Database Setup")
    print("-" * 40)
    
    # Check for API key
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        print("⚠️  NOTION_API_KEY not set - using demo mode")
        api_key = "dummy_key_for_demo"
    
    try:
        async with NotionWriter(api_key=api_key) as writer:
            # Test database schema
            schema = writer._get_database_properties_schema()
            
            print(f"✅ Generated database schema with {len(schema)} properties")
            
            # Show key properties
            key_props = [
                "Job Title", "Company", "Location", "Salary Min", "Salary Max",
                "Application Status", "MBA Relevance", "AI Fit Score"
            ]
            
            print("🏗️ Key database properties:")
            for prop in key_props:
                if prop in schema:
                    prop_type = list(schema[prop].keys())[0]
                    print(f"   • {prop}: {prop_type}")
            
            # Test connection if real API key
            if api_key != "dummy_key_for_demo":
                connection_ok = await writer.test_connection()
                if connection_ok:
                    print("✅ Notion API connection successful!")
                    
                    # Try to get or create database
                    try:
                        database_id = await writer.get_or_create_database("MBA Job Hunter Demo")
                        print(f"✅ Database ready: {database_id}")
                        return database_id
                    except Exception as e:
                        print(f"⚠️  Database setup failed: {e}")
                else:
                    print("❌ Notion API connection failed")
            else:
                print("📝 Demo mode - no real API calls made")
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
    
    print()
    return None

async def demo_job_scraping_simulation():
    """Demo job scraping (simulated data)."""
    print("📋 2. Job Scraping Simulation")
    print("-" * 40)
    
    try:
        # Create scraper configuration
        config = ScrapingConfig(
            max_pages=2,
            delay_between_requests=1.0,
            rate_limit_per_minute=20
        )
        
        scraper = IndeedScraper(config)
        
        print(f"✅ Created Indeed scraper:")
        print(f"   • Name: {scraper.name}")
        print(f"   • Base URL: {scraper.base_url}")
        print(f"   • Type: {scraper.scraper_type}")
        
        # Generate sample job data (simulating scraped jobs)
        sample_jobs = []
        
        job_templates = [
            {
                "title": "Senior Product Manager - MBA Required",
                "company_name": "Google",
                "location": "Mountain View, CA",
                "description": "Lead product strategy for our AI platform. Work with cross-functional teams to define product roadmap and drive growth initiatives. MBA from top-tier school required.",
                "requirements": "• MBA from top business school\n• 5+ years product management experience\n• Strong analytical and strategic thinking skills\n• Experience with data-driven decision making",
                "salary_min": 150000,
                "salary_max": 220000,
                "job_type": "Full-time",
                "experience_level": "Senior Level",
                "skills_required": ["MBA", "Product Management", "Strategy", "Analytics", "Leadership"]
            },
            {
                "title": "Management Consultant",
                "company_name": "McKinsey & Company",
                "location": "New York, NY", 
                "description": "Work with Fortune 500 clients on strategic initiatives. Conduct market analysis, develop business cases, and present recommendations to C-level executives.",
                "requirements": "• MBA from top-tier program\n• 2+ years consulting experience\n• Strong problem-solving skills\n• Excellent communication abilities",
                "salary_min": 165000,
                "salary_max": 200000,
                "job_type": "Full-time",
                "experience_level": "Mid Level",
                "skills_required": ["MBA", "Consulting", "Strategy", "Financial Modeling", "Presentation"]
            },
            {
                "title": "Business Development Manager",
                "company_name": "Salesforce",
                "location": "San Francisco, CA",
                "description": "Drive business growth through strategic partnerships and client relationships. Identify new market opportunities and develop go-to-market strategies.",
                "requirements": "• MBA preferred\n• 3+ years business development experience\n• Strong relationship building skills\n• Experience in SaaS industry",
                "salary_min": 120000,
                "salary_max": 160000,
                "job_type": "Full-time", 
                "experience_level": "Mid Level",
                "skills_required": ["MBA", "Business Development", "Sales", "Strategy", "Communication"]
            },
            {
                "title": "Strategy Analyst",
                "company_name": "Amazon",
                "location": "Seattle, WA",
                "description": "Support strategic planning initiatives across business units. Conduct competitive analysis, financial modeling, and market research to inform key business decisions.",
                "requirements": "• MBA or advanced degree\n• Strong analytical skills\n• Proficiency in Excel and SQL\n• Experience with data visualization tools",
                "salary_min": 110000,
                "salary_max": 140000,
                "job_type": "Full-time",
                "experience_level": "Entry Level",
                "skills_required": ["MBA", "Strategy", "Analytics", "SQL", "Financial Modeling"]
            },
            {
                "title": "Operations Manager",
                "company_name": "Apple",
                "location": "Cupertino, CA",
                "description": "Lead operational excellence initiatives and process improvements. Manage cross-functional projects to optimize supply chain and manufacturing operations.",
                "requirements": "• MBA in Operations or related field\n• 4+ years operations experience\n• Lean/Six Sigma certification preferred\n• Strong project management skills",
                "salary_min": 130000,
                "salary_max": 170000,
                "job_type": "Full-time",
                "experience_level": "Senior Level", 
                "skills_required": ["MBA", "Operations Management", "Process Improvement", "Project Management", "Lean"]
            }
        ]
        
        # Create JobData objects
        for i, template in enumerate(job_templates):
            job_data = JobData(
                title=template["title"],
                company_name=template["company_name"],
                location=template["location"],
                description=template["description"],
                requirements=template["requirements"],
                salary_min=template["salary_min"],
                salary_max=template["salary_max"],
                salary_currency="USD",
                salary_period="annual",
                job_type=template["job_type"],
                experience_level=template["experience_level"],
                source="indeed",
                source_job_id=f"job_{i+1}",
                source_url=f"https://indeed.com/viewjob?jk=sample_{i+1}",
                skills_required=template["skills_required"],
                is_remote=random.choice([True, False]),
                posted_date=datetime.now(timezone.utc)
            )
            
            # Convert to dict for processing
            job_dict = {
                "title": job_data.title,
                "company_name": job_data.company_name,
                "location": job_data.location,
                "description": job_data.description,
                "requirements": job_data.requirements,
                "salary_min": job_data.salary_min,
                "salary_max": job_data.salary_max,
                "salary_currency": job_data.salary_currency,
                "job_type": job_data.job_type,
                "experience_level": job_data.experience_level,
                "source": job_data.source,
                "source_url": job_data.source_url,
                "skills_required": job_data.skills_required,
                "is_remote": job_data.is_remote,
                "posted_date": job_data.posted_date
            }
            
            # Calculate relevance score
            job_dict["relevance_score"] = calculate_job_relevance_score(job_dict)
            
            sample_jobs.append(job_dict)
        
        print(f"✅ Generated {len(sample_jobs)} sample jobs")
        
        # Show job summary
        for i, job in enumerate(sample_jobs, 1):
            relevance = job["relevance_score"]
            relevance_label = "High" if relevance >= 0.7 else "Medium" if relevance >= 0.4 else "Low"
            
            print(f"   {i}. {job['title']} at {job['company_name']}")
            print(f"      💰 ${job['salary_min']:,} - ${job['salary_max']:,}")
            print(f"      🎯 MBA Relevance: {relevance:.2f} ({relevance_label})")
        
        print()
        return sample_jobs
        
    except Exception as e:
        print(f"❌ Scraping simulation failed: {e}")
        print()
        return []

async def demo_notion_integration(jobs_data: List[Dict], database_id: str = None):
    """Demo Notion integration with scraped jobs."""
    print("📋 3. Notion Integration Demo")
    print("-" * 40)
    
    if not jobs_data:
        print("⚠️  No job data available for Notion integration")
        print()
        return
    
    api_key = os.getenv("NOTION_API_KEY", "dummy_key_for_demo")
    
    try:
        async with NotionWriter(api_key=api_key, database_id=database_id) as writer:
            print(f"✅ Notion writer initialized")
            
            # Format jobs for Notion
            formatted_jobs = []
            
            print("🔄 Formatting jobs for Notion...")
            for i, job in enumerate(jobs_data, 1):
                try:
                    formatted = await writer.format_job_for_notion(job)
                    formatted_jobs.append(formatted)
                    
                    # Show formatting details
                    properties = formatted.get("properties", {})
                    children = formatted.get("children", [])
                    
                    print(f"   {i}. {job['title']}")
                    print(f"      📊 Properties: {len(properties)}")
                    print(f"      📄 Content blocks: {len(children)}")
                    
                except Exception as e:
                    print(f"   ❌ Failed to format job {i}: {e}")
            
            print(f"✅ Successfully formatted {len(formatted_jobs)} jobs")
            
            # Demo batch processing
            if api_key != "dummy_key_for_demo":
                print("\n🚀 Starting batch write to Notion...")
                try:
                    page_ids = await writer.batch_write_jobs(jobs_data)
                    print(f"✅ Successfully created {len(page_ids)} job pages")
                    
                    # Show statistics
                    stats = writer.get_stats()
                    print(f"\n📊 Notion Writer Statistics:")
                    print(f"   • Jobs written: {stats['jobs_written']}")
                    print(f"   • Jobs updated: {stats['jobs_updated']}")
                    print(f"   • Errors: {stats['errors']}")
                    print(f"   • Last sync: {stats['last_sync']}")
                    
                except Exception as e:
                    print(f"❌ Batch write failed: {e}")
            else:
                print("📝 Demo mode - jobs formatted but not written to Notion")
                print("   Set NOTION_API_KEY environment variable for real integration")
    
    except Exception as e:
        print(f"❌ Notion integration failed: {e}")
    
    print()

async def demo_end_to_end_workflow():
    """Demo complete end-to-end workflow."""
    print("📋 4. End-to-End Workflow Demo")
    print("-" * 40)
    
    print("🔄 Simulating complete MBA job hunting workflow:")
    print()
    
    # Step 1: Initialize services
    print("1️⃣ Initializing services...")
    api_key = os.getenv("NOTION_API_KEY", "dummy_key_for_demo")
    
    config = ScrapingConfig(
        max_pages=3,
        delay_between_requests=1.0,
        rate_limit_per_minute=30
    )
    
    scraper = IndeedScraper(config)
    
    print("   ✅ Scraper configured")
    print("   ✅ Notion writer ready")
    
    # Step 2: Search parameters
    print("\n2️⃣ Setting up job search parameters...")
    search_queries = ["Product Manager", "Business Analyst", "Strategy Consultant"]
    locations = ["San Francisco", "New York", "Remote"]
    
    for query in search_queries:
        for location in locations:
            params = scraper._build_search_params(query, location, salary_min=100000)
            from urllib.parse import urlencode
            url = f"{scraper.base_url}/jobs?{urlencode(params)}"
            print(f"   📋 {query} in {location}")
    
    print("   ✅ Search parameters configured")
    
    # Step 3: Simulate data processing pipeline
    print("\n3️⃣ Processing job data pipeline...")
    
    # Sample job for pipeline demo
    sample_job = {
        "title": "Senior Product Manager - MBA Program",
        "company_name": "Tech Innovators Inc",
        "location": "San Francisco, CA",
        "description": "Lead product strategy for our fintech platform. MBA from top program required.",
        "salary_min": 140000,
        "salary_max": 180000,
        "source": "indeed",
        "source_url": "https://indeed.com/viewjob?jk=pipeline_demo",
        "skills_required": ["MBA", "Product Management", "Strategy", "Fintech", "Leadership"]
    }
    
    # Step 3a: Calculate relevance
    relevance = calculate_job_relevance_score(sample_job)
    sample_job["relevance_score"] = relevance
    print(f"   📊 MBA relevance calculated: {relevance:.2f}")
    
    # Step 3b: Format for Notion
    async with NotionWriter(api_key=api_key) as writer:
        formatted = await writer.format_job_for_notion(sample_job)
        properties_count = len(formatted.get("properties", {}))
        blocks_count = len(formatted.get("children", []))
        
        print(f"   🔄 Formatted for Notion: {properties_count} properties, {blocks_count} blocks")
        
        # Step 3c: Simulate duplicate check
        existing_page = await writer.find_existing_job(sample_job["source_url"])
        if existing_page:
            print(f"   🔍 Found existing job: {existing_page}")
        else:
            print("   🆕 New job detected")
        
        print("   ✅ Pipeline processing complete")
    
    # Step 4: Show integration benefits
    print("\n4️⃣ Integration benefits:")
    print("   🎯 Automated MBA relevance scoring")
    print("   📊 Rich Notion database with structured data")
    print("   🔄 Duplicate detection and updates")
    print("   📈 Application tracking and status management")
    print("   🎨 Beautiful job descriptions with formatting")
    print("   🏷️ Skill tagging and categorization")
    
    print("\n✅ End-to-end workflow demonstration complete!")
    print()

def show_setup_instructions():
    """Show setup instructions for users."""
    print("📋 5. Setup Instructions")
    print("-" * 40)
    
    print("🚀 To use the complete MBA Job Hunter system:")
    print()
    
    print("1️⃣ Notion Setup:")
    print("   • Go to https://www.notion.so/my-integrations")
    print("   • Create a new integration")
    print("   • Copy the API key")
    print("   • Set NOTION_API_KEY environment variable")
    print()
    
    print("2️⃣ Environment Configuration:")
    print("   • Create .env file in backend directory")
    print("   • Add: NOTION_API_KEY=your_api_key_here")
    print("   • Optionally add: NOTION_DATABASE_ID=existing_database_id")
    print()
    
    print("3️⃣ Run the System:")
    print("   • python3 notion_scraper_demo.py")
    print("   • The system will create a database if none exists")
    print("   • Jobs will be automatically scraped and added to Notion")
    print()
    
    print("4️⃣ Notion Database Features:")
    print("   • 📝 Job title, company, location, description")
    print("   • 💰 Salary range with currency support")  
    print("   • 🎯 MBA relevance scoring (High/Medium/Low)")
    print("   • 📊 AI fit score and analysis")
    print("   • 🏷️ Skills tagging and requirements")
    print("   • 📋 Application status tracking")
    print("   • 📅 Posted dates and deadlines")
    print("   • 🏢 Company information and logos")
    print()
    
    print("5️⃣ Workflow Integration:")
    print("   • 🔍 Scrape jobs from Indeed (and other boards)")
    print("   • 🎯 Automatically score MBA relevance")
    print("   • 📊 Create rich Notion pages with formatted content")
    print("   • 🔄 Handle duplicates and updates intelligently")
    print("   • 📈 Track application progress")
    print("   • 🎨 Beautiful, organized job database")
    print()

async def main():
    """Run the complete Notion + Scraper integration demo."""
    print_banner()
    
    try:
        # Demo components
        database_id = await demo_notion_database_setup()
        jobs_data = await demo_job_scraping_simulation()
        await demo_notion_integration(jobs_data, database_id)
        await demo_end_to_end_workflow()
        show_setup_instructions()
        
        print("🎉 Notion + Scraper Integration Demo Complete!")
        print("🚀 Your MBA Job Hunter system is ready to use!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(main())