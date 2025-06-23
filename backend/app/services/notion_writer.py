"""
Notion API Integration Service

Complete Notion integration for the MBA Job Hunter application.
Handles database creation, job data writing, and synchronization.
"""

import asyncio
import re
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from urllib.parse import urlparse
import json

from notion_client import AsyncClient
from notion_client.errors import APIResponseError, RequestTimeoutError
import httpx

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class NotionWriterError(Exception):
    """Base exception for Notion writer errors."""
    pass


class NotionDatabaseError(NotionWriterError):
    """Raised when database operations fail."""
    pass


class NotionPageError(NotionWriterError):
    """Raised when page operations fail."""
    pass


class NotionWriter:
    """
    Comprehensive Notion API integration service for MBA Job Hunter.
    
    Features:
    - Automatic database creation and schema management
    - Batch job data writing with error handling
    - Advanced data formatting and validation
    - Company logo upload and management
    - Duplicate detection and updates
    - Rich text processing for job descriptions
    """
    
    def __init__(self, api_key: str = None, database_id: str = None):
        """
        Initialize Notion writer.
        
        Args:
            api_key: Notion integration API key
            database_id: Target database ID (optional)
        """
        self.api_key = api_key or settings.NOTION_API_KEY
        self.database_id = database_id or settings.NOTION_DATABASE_ID
        
        if not self.api_key:
            raise NotionWriterError("Notion API key is required")
        
        # Initialize Notion client
        self.client = AsyncClient(auth=self.api_key)
        
        # HTTP client for logo downloads
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Cache for database schemas and page IDs
        self._database_cache = {}
        self._page_cache = {}
        
        # Statistics
        self._stats = {
            "jobs_written": 0,
            "jobs_updated": 0,
            "jobs_skipped": 0,
            "errors": 0,
            "last_sync": None
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
    
    # Database Management Methods
    
    async def create_job_database(self, parent_page_id: str = None) -> str:
        """
        Create a new jobs database in Notion.
        
        Args:
            parent_page_id: Parent page ID (uses user's root if None)
            
        Returns:
            str: Created database ID
            
        Raises:
            NotionDatabaseError: If database creation fails
        """
        try:
            # Define database schema
            database_schema = {
                "parent": {
                    "type": "page_id",
                    "page_id": parent_page_id
                } if parent_page_id else {
                    "type": "workspace",
                    "workspace": True
                },
                "title": [
                    {
                        "type": "text",
                        "text": {"content": "MBA Job Hunter - Jobs Database"}
                    }
                ],
                "properties": self._get_database_properties_schema()
            }
            
            response = await self.client.databases.create(**database_schema)
            database_id = response["id"]
            
            # Cache the database
            self._database_cache[database_id] = response
            
            logger.info(f"Created Notion database: {database_id}")
            return database_id
            
        except APIResponseError as e:
            logger.error(f"Failed to create Notion database: {e}")
            raise NotionDatabaseError(f"Database creation failed: {e}")
    
    async def get_or_create_database(self, database_name: str = "MBA Job Hunter") -> str:
        """
        Get existing database or create new one.
        
        Args:
            database_name: Name of the database to find/create
            
        Returns:
            str: Database ID
        """
        # If we have a configured database ID, verify it exists
        if self.database_id:
            try:
                await self.client.databases.retrieve(database_id=self.database_id)
                logger.info(f"Using configured database: {self.database_id}")
                return self.database_id
            except APIResponseError:
                logger.warning(f"Configured database {self.database_id} not accessible")
        
        # Search for existing database
        try:
            search_response = await self.client.search(
                filter={"property": "object", "value": "database"},
                query=database_name
            )
            
            for result in search_response.get("results", []):
                if result["object"] == "database":
                    title = result.get("title", [])
                    if title and title[0].get("plain_text", "").startswith(database_name):
                        database_id = result["id"]
                        logger.info(f"Found existing database: {database_id}")
                        return database_id
            
        except APIResponseError as e:
            logger.warning(f"Search failed: {e}")
        
        # Create new database
        logger.info(f"Creating new database: {database_name}")
        return await self.create_job_database()
    
    async def update_database_schema(self, database_id: str) -> None:
        """
        Update database schema to match current requirements.
        
        Args:
            database_id: Target database ID
            
        Raises:
            NotionDatabaseError: If schema update fails
        """
        try:
            # Get current database
            current_db = await self.client.databases.retrieve(database_id=database_id)
            current_properties = current_db.get("properties", {})
            
            # Get required properties
            required_properties = self._get_database_properties_schema()
            
            # Find missing properties
            missing_properties = {}
            for prop_name, prop_config in required_properties.items():
                if prop_name not in current_properties:
                    missing_properties[prop_name] = prop_config
                    logger.info(f"Adding missing property: {prop_name}")
            
            # Update database if needed
            if missing_properties:
                await self.client.databases.update(
                    database_id=database_id,
                    properties=missing_properties
                )
                logger.info(f"Updated database schema with {len(missing_properties)} properties")
            else:
                logger.info("Database schema is up to date")
                
        except APIResponseError as e:
            logger.error(f"Failed to update database schema: {e}")
            raise NotionDatabaseError(f"Schema update failed: {e}")
    
    def _get_database_properties_schema(self) -> Dict[str, Any]:
        """Get the complete database properties schema."""
        return {
            # Basic Job Info
            "Job Title": {"title": {}},
            "Company": {"rich_text": {}},
            "Location": {"rich_text": {}},
            "Job URL": {"url": {}},
            
            # Salary Info
            "Salary Min": {"number": {"format": "dollar"}},
            "Salary Max": {"number": {"format": "dollar"}},
            "Currency": {
                "select": {
                    "options": [
                        {"name": "USD", "color": "green"},
                        {"name": "EUR", "color": "blue"},
                        {"name": "GBP", "color": "purple"}
                    ]
                }
            },
            
            # Job Details
            "Job Type": {
                "select": {
                    "options": [
                        {"name": "Full-time", "color": "green"},
                        {"name": "Part-time", "color": "yellow"},
                        {"name": "Contract", "color": "orange"},
                        {"name": "Temporary", "color": "red"}
                    ]
                }
            },
            "Experience Level": {
                "select": {
                    "options": [
                        {"name": "Entry Level", "color": "green"},
                        {"name": "Mid Level", "color": "yellow"},
                        {"name": "Senior Level", "color": "orange"},
                        {"name": "Executive", "color": "red"}
                    ]
                }
            },
            "Remote Friendly": {"checkbox": {}},
            
            # Dates
            "Posted Date": {"date": {}},
            "Application Deadline": {"date": {}},
            "Date Added": {
                "created_time": {}
            },
            "Last Updated": {
                "last_edited_time": {}
            },
            
            # Source & Analysis
            "Source Platform": {
                "select": {
                    "options": [
                        {"name": "Indeed", "color": "blue"},
                        {"name": "LinkedIn", "color": "purple"},
                        {"name": "Glassdoor", "color": "green"},
                        {"name": "AngelList", "color": "orange"}
                    ]
                }
            },
            "AI Fit Score": {
                "number": {
                    "format": "percent"
                }
            },
            "MBA Relevance": {
                "select": {
                    "options": [
                        {"name": "High", "color": "green"},
                        {"name": "Medium", "color": "yellow"},
                        {"name": "Low", "color": "red"}
                    ]
                }
            },
            
            # Skills & Requirements
            "Required Skills": {"multi_select": {"options": []}},
            "Preferred Skills": {"multi_select": {"options": []}},
            
            # Application Status
            "Application Status": {
                "select": {
                    "options": [
                        {"name": "Not Applied", "color": "gray"},
                        {"name": "Applied", "color": "blue"},
                        {"name": "Interview", "color": "yellow"},
                        {"name": "Offer", "color": "green"},
                        {"name": "Rejected", "color": "red"},
                        {"name": "Withdrawn", "color": "gray"}
                    ]
                }
            },
            "Priority": {
                "select": {
                    "options": [
                        {"name": "High", "color": "red"},
                        {"name": "Medium", "color": "yellow"},
                        {"name": "Low", "color": "gray"}
                    ]
                }
            },
            
            # Notes & Analysis
            "Notes": {"rich_text": {}},
            "AI Summary": {"rich_text": {}},
            
            # Company Info
            "Company Size": {
                "select": {
                    "options": [
                        {"name": "Startup (1-50)", "color": "green"},
                        {"name": "Small (51-200)", "color": "yellow"},
                        {"name": "Medium (201-1000)", "color": "orange"},
                        {"name": "Large (1000+)", "color": "red"}
                    ]
                }
            },
            "Industry": {"rich_text": {}},
            "Company Logo": {"files": {}}
        }
    
    # Data Writing Methods
    
    async def write_job_to_notion(self, job_data: Dict) -> str:
        """
        Write a single job to Notion.
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            str: Created page ID
            
        Raises:
            NotionPageError: If page creation fails
        """
        try:
            # Ensure we have a database
            if not self.database_id:
                self.database_id = await self.get_or_create_database()
            
            # Check for existing job
            existing_page_id = await self.find_existing_job(job_data.get("source_url"))
            if existing_page_id:
                logger.info(f"Job already exists, updating: {existing_page_id}")
                await self.update_job_in_notion(existing_page_id, job_data)
                self._stats["jobs_updated"] += 1
                return existing_page_id
            
            # Format job data for Notion
            notion_data = await self.format_job_for_notion(job_data)
            
            # Create page
            response = await self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=notion_data["properties"],
                children=notion_data.get("children", [])
            )
            
            page_id = response["id"]
            
            # Cache the page
            self._page_cache[job_data.get("source_url", "")] = page_id
            
            self._stats["jobs_written"] += 1
            logger.info(f"Created job page: {page_id}")
            
            return page_id
            
        except APIResponseError as e:
            self._stats["errors"] += 1
            logger.error(f"Failed to write job to Notion: {e}")
            raise NotionPageError(f"Job creation failed: {e}")
    
    async def batch_write_jobs(self, jobs_data: List[Dict]) -> List[str]:
        """
        Write multiple jobs to Notion with batching and error handling.
        
        Args:
            jobs_data: List of job data dictionaries
            
        Returns:
            List[str]: List of created/updated page IDs
        """
        if not jobs_data:
            return []
        
        logger.info(f"Starting batch write of {len(jobs_data)} jobs")
        
        # Ensure we have a database
        if not self.database_id:
            self.database_id = await self.get_or_create_database()
        
        page_ids = []
        batch_size = 10  # Notion API rate limiting
        
        for i in range(0, len(jobs_data), batch_size):
            batch = jobs_data[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(jobs_data)-1)//batch_size + 1}")
            
            # Process batch concurrently
            tasks = [self.write_job_to_notion(job_data) for job_data in batch]
            
            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch job failed: {result}")
                        self._stats["errors"] += 1
                    else:
                        page_ids.append(result)
                
                # Rate limiting delay
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                self._stats["errors"] += len(batch)
        
        self._stats["last_sync"] = datetime.now(timezone.utc)
        logger.info(f"Batch write completed. Created/updated {len(page_ids)} jobs")
        
        return page_ids
    
    async def update_job_in_notion(self, page_id: str, job_data: Dict) -> None:
        """
        Update an existing job page in Notion.
        
        Args:
            page_id: Notion page ID to update
            job_data: Updated job data
            
        Raises:
            NotionPageError: If update fails
        """
        try:
            # Format job data for Notion
            notion_data = await self.format_job_for_notion(job_data, is_update=True)
            
            # Update page properties
            await self.client.pages.update(
                page_id=page_id,
                properties=notion_data["properties"]
            )
            
            # Update page content if needed
            if notion_data.get("children"):
                # Get existing blocks
                existing_blocks = await self.client.blocks.children.list(block_id=page_id)
                
                # Delete existing blocks (except title)
                for block in existing_blocks.get("results", []):
                    if block["type"] != "child_page":
                        try:
                            await self.client.blocks.delete(block_id=block["id"])
                        except APIResponseError:
                            pass  # Block might already be deleted
                
                # Add new blocks
                await self.client.blocks.children.append(
                    block_id=page_id,
                    children=notion_data["children"]
                )
            
            logger.info(f"Updated job page: {page_id}")
            
        except APIResponseError as e:
            logger.error(f"Failed to update job in Notion: {e}")
            raise NotionPageError(f"Job update failed: {e}")
    
    # Data Query Methods
    
    async def find_existing_job(self, job_url: str) -> Optional[str]:
        """
        Find existing job by URL.
        
        Args:
            job_url: Job source URL
            
        Returns:
            Optional[str]: Page ID if found, None otherwise
        """
        if not job_url or not self.database_id:
            return None
        
        # Check cache first
        if job_url in self._page_cache:
            return self._page_cache[job_url]
        
        try:
            # Query database for existing job
            response = await self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Job URL",
                    "url": {"equals": job_url}
                }
            )
            
            results = response.get("results", [])
            if results:
                page_id = results[0]["id"]
                # Cache the result
                self._page_cache[job_url] = page_id
                return page_id
            
            return None
            
        except APIResponseError as e:
            logger.warning(f"Failed to search for existing job: {e}")
            return None
    
    async def get_all_jobs(self, filters: Dict = None) -> List[Dict]:
        """
        Get all jobs from the database with optional filtering.
        
        Args:
            filters: Notion database filters
            
        Returns:
            List[Dict]: List of job data
        """
        if not self.database_id:
            return []
        
        try:
            query_params = {"database_id": self.database_id}
            
            if filters:
                query_params["filter"] = filters
            
            # Handle pagination
            jobs = []
            has_more = True
            start_cursor = None
            
            while has_more:
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                response = await self.client.databases.query(**query_params)
                
                jobs.extend(response.get("results", []))
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            
            logger.info(f"Retrieved {len(jobs)} jobs from Notion")
            return jobs
            
        except APIResponseError as e:
            logger.error(f"Failed to get jobs from Notion: {e}")
            return []
    
    # Utility Methods
    
    async def format_job_for_notion(self, job_data: Dict, is_update: bool = False) -> Dict:
        """
        Format job data for Notion API.
        
        Args:
            job_data: Raw job data
            is_update: Whether this is an update operation
            
        Returns:
            Dict: Formatted Notion data
        """
        # Basic properties
        properties = {
            "Job Title": {
                "title": [{"text": {"content": job_data.get("title", "Unknown Job")[:100]}}]
            },
            "Company": {
                "rich_text": [{"text": {"content": job_data.get("company_name", "Unknown Company")[:100]}}]
            },
            "Job URL": {
                "url": job_data.get("source_url", "")
            }
        }
        
        # Location
        if job_data.get("location"):
            properties["Location"] = {
                "rich_text": [{"text": {"content": str(job_data["location"])[:100]}}]
            }
        
        # Salary information
        if job_data.get("salary_min"):
            properties["Salary Min"] = {"number": float(job_data["salary_min"])}
        
        if job_data.get("salary_max"):
            properties["Salary Max"] = {"number": float(job_data["salary_max"])}
        
        if job_data.get("salary_currency"):
            properties["Currency"] = {"select": {"name": job_data["salary_currency"]}}
        
        # Job details
        if job_data.get("job_type"):
            properties["Job Type"] = {"select": {"name": job_data["job_type"]}}
        
        if job_data.get("experience_level"):
            properties["Experience Level"] = {"select": {"name": job_data["experience_level"]}}
        
        if job_data.get("is_remote") is not None:
            properties["Remote Friendly"] = {"checkbox": bool(job_data["is_remote"])}
        
        # Dates
        if job_data.get("posted_date"):
            if isinstance(job_data["posted_date"], str):
                properties["Posted Date"] = {"date": {"start": job_data["posted_date"]}}
            elif hasattr(job_data["posted_date"], "isoformat"):
                properties["Posted Date"] = {"date": {"start": job_data["posted_date"].isoformat()}}
        
        # Source platform
        if job_data.get("source"):
            source_name = job_data["source"].title()
            properties["Source Platform"] = {"select": {"name": source_name}}
        
        # AI scores
        if job_data.get("ai_fit_score") is not None:
            properties["AI Fit Score"] = {"number": float(job_data["ai_fit_score"]) / 100}
        
        # MBA relevance (calculate if not provided)
        relevance_score = job_data.get("relevance_score")
        if relevance_score is None:
            # Calculate based on job data
            from app.scrapers.utils import calculate_job_relevance_score
            relevance_score = calculate_job_relevance_score(job_data)
        
        if relevance_score >= 0.7:
            properties["MBA Relevance"] = {"select": {"name": "High"}}
        elif relevance_score >= 0.4:
            properties["MBA Relevance"] = {"select": {"name": "Medium"}}
        else:
            properties["MBA Relevance"] = {"select": {"name": "Low"}}
        
        # Skills
        if job_data.get("skills_required"):
            skills_options = []
            for skill in job_data["skills_required"][:20]:  # Limit to 20 skills
                skills_options.append({"name": str(skill)[:100]})
            properties["Required Skills"] = {"multi_select": skills_options}
        
        # Default application status for new jobs
        if not is_update:
            properties["Application Status"] = {"select": {"name": "Not Applied"}}
            properties["Priority"] = {"select": {"name": "Medium"}}
        
        # Industry (if available)
        if job_data.get("industry"):
            properties["Industry"] = {
                "rich_text": [{"text": {"content": str(job_data["industry"])[:100]}}]
            }
        
        # AI Summary
        if job_data.get("ai_summary"):
            properties["AI Summary"] = {
                "rich_text": self.create_rich_text_blocks(job_data["ai_summary"], max_length=2000)
            }
        
        # Create page children (content blocks)
        children = []
        
        # Job description
        if job_data.get("description"):
            children.extend(self._create_description_blocks(job_data["description"]))
        
        # Requirements
        if job_data.get("requirements"):
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"text": {"content": "Requirements"}}]
                }
            })
            children.extend(self._create_description_blocks(job_data["requirements"]))
        
        # Benefits
        if job_data.get("benefits"):
            children.append({
                "object": "block",
                "type": "heading_2", 
                "heading_2": {
                    "rich_text": [{"text": {"content": "Benefits"}}]
                }
            })
            
            if isinstance(job_data["benefits"], list):
                for benefit in job_data["benefits"][:10]:  # Limit benefits
                    children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"text": {"content": str(benefit)[:1000]}}]
                        }
                    })
            else:
                children.extend(self._create_description_blocks(str(job_data["benefits"])))
        
        return {
            "properties": properties,
            "children": children
        }
    
    def _create_description_blocks(self, text: str) -> List[Dict]:
        """Create Notion blocks from job description text."""
        if not text:
            return []
        
        blocks = []
        
        # Split into paragraphs
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Check if it's a list item
            if paragraph.startswith(('•', '-', '*')) or re.match(r'^\d+\.', paragraph):
                # Create bulleted list item
                content = re.sub(r'^[•\-\*\d\.]\s*', '', paragraph)
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": self.create_rich_text_blocks(content, max_length=1000)
                    }
                })
            else:
                # Create paragraph
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self.create_rich_text_blocks(paragraph, max_length=1000)
                    }
                })
        
        return blocks
    
    async def upload_company_logo(self, logo_url: str, company_name: str) -> str:
        """
        Upload company logo to Notion.
        
        Args:
            logo_url: URL of the company logo
            company_name: Name of the company
            
        Returns:
            str: Notion file URL
        """
        if not logo_url:
            return ""
        
        try:
            # Download logo
            response = await self.http_client.get(logo_url)
            response.raise_for_status()
            
            # Validate content type
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.warning(f"Invalid content type for logo: {content_type}")
                return ""
            
            # For now, return the original URL since Notion doesn't support direct file uploads via API
            # In a production environment, you'd upload to a file storage service first
            return logo_url
            
        except Exception as e:
            logger.warning(f"Failed to process company logo: {e}")
            return ""
    
    def create_rich_text_blocks(self, text: str, max_length: int = 2000) -> List[Dict]:
        """
        Create Notion rich text blocks from plain text.
        
        Args:
            text: Plain text content
            max_length: Maximum length per block
            
        Returns:
            List[Dict]: Notion rich text blocks
        """
        if not text:
            return []
        
        # Clean and truncate text
        text = str(text).strip()
        if len(text) > max_length:
            text = text[:max_length - 3] + "..."
        
        # Split into chunks if needed (Notion has a 2000 char limit per rich text block)
        chunks = []
        while text:
            chunk = text[:max_length]
            chunks.append(chunk)
            text = text[max_length:]
        
        # Create rich text objects
        rich_text_blocks = []
        for chunk in chunks:
            rich_text_blocks.append({
                "text": {"content": chunk},
                "annotations": {
                    "bold": False,
                    "italic": False,
                    "strikethrough": False,
                    "underline": False,
                    "code": False,
                    "color": "default"
                }
            })
        
        return rich_text_blocks
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Notion writer statistics."""
        return self._stats.copy()
    
    async def test_connection(self) -> bool:
        """
        Test Notion API connection.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            # Test basic API access
            await self.client.users.me()
            logger.info("Notion API connection successful")
            return True
            
        except APIResponseError as e:
            logger.error(f"Notion API connection failed: {e}")
            return False