"""
Tests for Notion Writer service.

Tests database creation, job writing, data formatting,
and error handling for the Notion integration service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.services.notion_writer import (
    NotionWriter, 
    NotionWriterError, 
    NotionDatabaseError, 
    NotionPageError
)


@pytest.mark.notion
@pytest.mark.unit
class TestNotionWriter:
    """Test NotionWriter functionality."""
    
    def test_initialization_with_api_key(self):
        """Test NotionWriter initialization with API key."""
        writer = NotionWriter(api_key="test_key", database_id="test_db_id")
        
        assert writer.api_key == "test_key"
        assert writer.database_id == "test_db_id"
        assert writer.client is not None
        assert writer._stats["jobs_written"] == 0
    
    def test_initialization_without_api_key(self):
        """Test NotionWriter initialization without API key raises error."""
        with patch('app.services.notion_writer.get_settings') as mock_settings:
            mock_settings.return_value.NOTION_API_KEY = None
            
            with pytest.raises(NotionWriterError, match="API key is required"):
                NotionWriter()
    
    def test_database_properties_schema(self):
        """Test database properties schema generation."""
        writer = NotionWriter(api_key="test_key")
        
        schema = writer._get_database_properties_schema()
        
        # Check required properties exist
        required_props = [
            "Job Title", "Company", "Location", "Job URL",
            "Salary Min", "Salary Max", "Application Status",
            "MBA Relevance", "Required Skills"
        ]
        
        for prop in required_props:
            assert prop in schema
        
        # Check property types
        assert schema["Job Title"]["title"] == {}
        assert schema["Company"]["rich_text"] == {}
        assert schema["Salary Min"]["number"]["format"] == "dollar"
        assert "options" in schema["Application Status"]["select"]
    
    async def test_format_job_for_notion_basic(self, sample_job_data):
        """Test basic job data formatting for Notion."""
        writer = NotionWriter(api_key="test_key")
        
        formatted = await writer.format_job_for_notion(sample_job_data)
        
        assert "properties" in formatted
        assert "children" in formatted
        
        properties = formatted["properties"]
        
        # Check title property
        assert "Job Title" in properties
        title_content = properties["Job Title"]["title"][0]["text"]["content"]
        assert title_content == sample_job_data["title"]
        
        # Check company property
        assert "Company" in properties
        company_content = properties["Company"]["rich_text"][0]["text"]["content"]
        assert company_content == sample_job_data["company_name"]
        
        # Check URL property
        assert "Job URL" in properties
        assert properties["Job URL"]["url"] == sample_job_data["source_url"]
    
    async def test_format_job_for_notion_with_salary(self, sample_job_data):
        """Test job formatting with salary information."""
        writer = NotionWriter(api_key="test_key")
        
        formatted = await writer.format_job_for_notion(sample_job_data)
        properties = formatted["properties"]
        
        # Check salary properties
        assert "Salary Min" in properties
        assert "Salary Max" in properties
        assert "Currency" in properties
        
        assert properties["Salary Min"]["number"] == sample_job_data["salary_min"]
        assert properties["Salary Max"]["number"] == sample_job_data["salary_max"]
        assert properties["Currency"]["select"]["name"] == sample_job_data["salary_currency"]
    
    async def test_format_job_for_notion_with_skills(self, sample_job_data):
        """Test job formatting with skills."""
        writer = NotionWriter(api_key="test_key")
        
        formatted = await writer.format_job_for_notion(sample_job_data)
        properties = formatted["properties"]
        
        # Check skills property
        assert "Required Skills" in properties
        skills_options = properties["Required Skills"]["multi_select"]
        
        skill_names = [option["name"] for option in skills_options]
        for skill in sample_job_data["skills_required"]:
            assert skill in skill_names
    
    async def test_format_job_for_notion_with_dates(self, sample_job_data):
        """Test job formatting with date information."""
        writer = NotionWriter(api_key="test_key")
        
        formatted = await writer.format_job_for_notion(sample_job_data)
        properties = formatted["properties"]
        
        # Check date properties
        if sample_job_data.get("posted_date"):
            assert "Posted Date" in properties
            assert "date" in properties["Posted Date"]
    
    async def test_format_job_for_notion_mba_relevance(self, sample_job_data):
        """Test MBA relevance scoring in formatting."""
        writer = NotionWriter(api_key="test_key")
        
        # Test with high relevance job
        high_relevance_job = sample_job_data.copy()
        high_relevance_job["relevance_score"] = 0.8
        
        formatted = await writer.format_job_for_notion(high_relevance_job)
        properties = formatted["properties"]
        
        assert "MBA Relevance" in properties
        assert properties["MBA Relevance"]["select"]["name"] == "High"
        
        # Test with medium relevance job
        medium_relevance_job = sample_job_data.copy()
        medium_relevance_job["relevance_score"] = 0.5
        
        formatted = await writer.format_job_for_notion(medium_relevance_job)
        properties = formatted["properties"]
        
        assert properties["MBA Relevance"]["select"]["name"] == "Medium"
    
    def test_create_rich_text_blocks(self):
        """Test rich text block creation."""
        writer = NotionWriter(api_key="test_key")
        
        # Test normal text
        text = "This is a test description."
        blocks = writer.create_rich_text_blocks(text, max_length=100)
        
        assert len(blocks) == 1
        assert blocks[0]["text"]["content"] == text
        assert blocks[0]["annotations"]["bold"] is False
        
        # Test long text (should be truncated)
        long_text = "A" * 500
        blocks = writer.create_rich_text_blocks(long_text, max_length=100)
        
        assert len(blocks) == 1
        assert len(blocks[0]["text"]["content"]) <= 100
        assert blocks[0]["text"]["content"].endswith("...")
        
        # Test empty text
        blocks = writer.create_rich_text_blocks("")
        assert len(blocks) == 0
    
    def test_create_description_blocks(self):
        """Test description block creation."""
        writer = NotionWriter(api_key="test_key")
        
        # Test with paragraphs
        text = "First paragraph.\n\nSecond paragraph."
        blocks = writer._create_description_blocks(text)
        
        assert len(blocks) == 2
        assert all(block["type"] == "paragraph" for block in blocks)
        
        # Test with list items
        list_text = "Requirements:\n• First requirement\n• Second requirement"
        blocks = writer._create_description_blocks(list_text)
        
        # Should have at least one paragraph and list items
        assert len(blocks) > 1
        list_blocks = [b for b in blocks if b["type"] == "bulleted_list_item"]
        assert len(list_blocks) >= 2
    
    @patch('app.services.notion_writer.AsyncClient')
    async def test_test_connection_success(self, mock_client_class, mock_notion_client):
        """Test successful Notion API connection."""
        mock_client_class.return_value = mock_notion_client
        
        writer = NotionWriter(api_key="test_key")
        writer.client = mock_notion_client
        
        result = await writer.test_connection()
        
        assert result is True
        mock_notion_client.users.me.assert_called_once()
    
    @patch('app.services.notion_writer.AsyncClient')
    async def test_test_connection_failure(self, mock_client_class):
        """Test failed Notion API connection."""
        mock_client = AsyncMock()
        mock_client.users.me.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client
        
        writer = NotionWriter(api_key="test_key")
        writer.client = mock_client
        
        result = await writer.test_connection()
        
        assert result is False
    
    async def test_create_job_database(self, mock_notion_client):
        """Test creating a new job database."""
        writer = NotionWriter(api_key="test_key")
        writer.client = mock_notion_client
        
        database_id = await writer.create_job_database()
        
        assert database_id == "test_database_id"
        mock_notion_client.databases.create.assert_called_once()
        
        # Check that the call included the correct schema
        call_args = mock_notion_client.databases.create.call_args
        assert "properties" in call_args.kwargs
        assert "title" in call_args.kwargs
    
    async def test_create_job_database_with_parent(self, mock_notion_client):
        """Test creating database with parent page."""
        writer = NotionWriter(api_key="test_key")
        writer.client = mock_notion_client
        
        parent_id = "parent_page_123"
        database_id = await writer.create_job_database(parent_id)
        
        assert database_id == "test_database_id"
        
        # Check parent was set correctly
        call_args = mock_notion_client.databases.create.call_args
        assert call_args.kwargs["parent"]["page_id"] == parent_id
    
    async def test_get_or_create_database_existing(self, mock_notion_client):
        """Test getting existing database."""
        writer = NotionWriter(api_key="test_key", database_id="existing_db")
        writer.client = mock_notion_client
        
        database_id = await writer.get_or_create_database()
        
        assert database_id == "existing_db"
        mock_notion_client.databases.retrieve.assert_called_once_with(database_id="existing_db")
    
    async def test_get_or_create_database_not_found(self, mock_notion_client):
        """Test creating database when existing one not found."""
        writer = NotionWriter(api_key="test_key", database_id="nonexistent_db")
        writer.client = mock_notion_client
        
        # Mock retrieve to raise error (database not found)
        mock_notion_client.databases.retrieve.side_effect = Exception("Not found")
        
        database_id = await writer.get_or_create_database()
        
        assert database_id == "test_database_id"
        mock_notion_client.databases.create.assert_called_once()
    
    async def test_find_existing_job_found(self, mock_notion_client):
        """Test finding existing job by URL."""
        writer = NotionWriter(api_key="test_key", database_id="test_db")
        writer.client = mock_notion_client
        
        # Mock query response with existing job
        mock_notion_client.databases.query.return_value = {
            "results": [{"id": "existing_page_id"}],
            "has_more": False
        }
        
        page_id = await writer.find_existing_job("https://example.com/job123")
        
        assert page_id == "existing_page_id"
        
        # Check query was called with correct filter
        call_args = mock_notion_client.databases.query.call_args
        assert call_args.kwargs["database_id"] == "test_db"
        assert "filter" in call_args.kwargs
    
    async def test_find_existing_job_not_found(self, mock_notion_client):
        """Test finding non-existent job."""
        writer = NotionWriter(api_key="test_key", database_id="test_db")
        writer.client = mock_notion_client
        
        # Mock empty query response
        mock_notion_client.databases.query.return_value = {
            "results": [],
            "has_more": False
        }
        
        page_id = await writer.find_existing_job("https://example.com/nonexistent")
        
        assert page_id is None
    
    async def test_write_job_to_notion_new(self, mock_notion_client, sample_job_data):
        """Test writing new job to Notion."""
        writer = NotionWriter(api_key="test_key", database_id="test_db")
        writer.client = mock_notion_client
        
        # Mock no existing job
        mock_notion_client.databases.query.return_value = {"results": []}
        
        page_id = await writer.write_job_to_notion(sample_job_data)
        
        assert page_id == "test_page_id"
        assert writer._stats["jobs_written"] == 1
        mock_notion_client.pages.create.assert_called_once()
    
    async def test_write_job_to_notion_existing(self, mock_notion_client, sample_job_data):
        """Test updating existing job in Notion."""
        writer = NotionWriter(api_key="test_key", database_id="test_db")
        writer.client = mock_notion_client
        
        # Mock existing job found
        mock_notion_client.databases.query.return_value = {
            "results": [{"id": "existing_page_id"}]
        }
        
        page_id = await writer.write_job_to_notion(sample_job_data)
        
        assert page_id == "existing_page_id"
        assert writer._stats["jobs_updated"] == 1
        mock_notion_client.pages.update.assert_called_once()
    
    async def test_batch_write_jobs(self, mock_notion_client, sample_job_list):
        """Test batch writing multiple jobs."""
        writer = NotionWriter(api_key="test_key", database_id="test_db")
        writer.client = mock_notion_client
        
        # Mock no existing jobs
        mock_notion_client.databases.query.return_value = {"results": []}
        
        page_ids = await writer.batch_write_jobs(sample_job_list)
        
        assert len(page_ids) == len(sample_job_list)
        assert writer._stats["jobs_written"] == len(sample_job_list)
        assert mock_notion_client.pages.create.call_count == len(sample_job_list)
    
    async def test_batch_write_jobs_empty_list(self, mock_notion_client):
        """Test batch writing with empty job list."""
        writer = NotionWriter(api_key="test_key")
        writer.client = mock_notion_client
        
        page_ids = await writer.batch_write_jobs([])
        
        assert page_ids == []
        assert writer._stats["jobs_written"] == 0
    
    async def test_update_job_in_notion(self, mock_notion_client, sample_job_data):
        """Test updating existing job page."""
        writer = NotionWriter(api_key="test_key")
        writer.client = mock_notion_client
        
        # Mock existing blocks response
        mock_notion_client.blocks.children.list.return_value = {
            "results": [{"id": "block1", "type": "paragraph"}]
        }
        
        await writer.update_job_in_notion("test_page_id", sample_job_data)
        
        mock_notion_client.pages.update.assert_called_once()
        mock_notion_client.blocks.children.append.assert_called_once()
    
    async def test_get_all_jobs(self, mock_notion_client):
        """Test getting all jobs from database."""
        writer = NotionWriter(api_key="test_key", database_id="test_db")
        writer.client = mock_notion_client
        
        # Mock paginated response
        mock_notion_client.databases.query.side_effect = [
            {
                "results": [{"id": "job1"}, {"id": "job2"}],
                "has_more": True,
                "next_cursor": "cursor1"
            },
            {
                "results": [{"id": "job3"}],
                "has_more": False,
                "next_cursor": None
            }
        ]
        
        jobs = await writer.get_all_jobs()
        
        assert len(jobs) == 3
        assert mock_notion_client.databases.query.call_count == 2
    
    async def test_get_all_jobs_with_filters(self, mock_notion_client):
        """Test getting jobs with filters."""
        writer = NotionWriter(api_key="test_key", database_id="test_db")
        writer.client = mock_notion_client
        
        filters = {
            "property": "MBA Relevance",
            "select": {"equals": "High"}
        }
        
        await writer.get_all_jobs(filters)
        
        call_args = mock_notion_client.databases.query.call_args
        assert call_args.kwargs["filter"] == filters
    
    async def test_upload_company_logo(self, mock_httpx_client):
        """Test company logo upload handling."""
        writer = NotionWriter(api_key="test_key")
        writer.http_client = mock_httpx_client
        
        # Mock successful image download
        mock_httpx_client.get.return_value.headers = {"content-type": "image/png"}
        mock_httpx_client.get.return_value.content = b"fake_image_data"
        
        logo_url = await writer.upload_company_logo(
            "https://example.com/logo.png", 
            "Test Company"
        )
        
        # For now, should return original URL
        assert logo_url == "https://example.com/logo.png"
    
    async def test_upload_company_logo_invalid_content(self, mock_httpx_client):
        """Test logo upload with invalid content type."""
        writer = NotionWriter(api_key="test_key")
        writer.http_client = mock_httpx_client
        
        # Mock non-image response
        mock_httpx_client.get.return_value.headers = {"content-type": "text/html"}
        
        logo_url = await writer.upload_company_logo(
            "https://example.com/notanimage.html", 
            "Test Company"
        )
        
        assert logo_url == ""
    
    def test_get_stats(self):
        """Test getting writer statistics."""
        writer = NotionWriter(api_key="test_key")
        
        # Modify some stats
        writer._stats["jobs_written"] = 5
        writer._stats["jobs_updated"] = 2
        writer._stats["errors"] = 1
        
        stats = writer.get_stats()
        
        assert stats["jobs_written"] == 5
        assert stats["jobs_updated"] == 2
        assert stats["errors"] == 1
        assert "last_sync" in stats
    
    async def test_context_manager(self, mock_httpx_client):
        """Test NotionWriter as async context manager."""
        async with NotionWriter(api_key="test_key") as writer:
            assert writer.api_key == "test_key"
            assert writer.http_client is not None
        
        # After exiting context, should be properly cleaned up
        # (http_client would be closed in real implementation)


@pytest.mark.notion
@pytest.mark.integration
class TestNotionWriterIntegration:
    """Integration tests for NotionWriter."""
    
    async def test_full_job_workflow(self, mock_notion_client, sample_job_data):
        """Test complete job writing workflow."""
        writer = NotionWriter(api_key="test_key")
        writer.client = mock_notion_client
        
        # Test database creation
        database_id = await writer.create_job_database()
        assert database_id == "test_database_id"
        
        # Test job writing
        writer.database_id = database_id
        mock_notion_client.databases.query.return_value = {"results": []}
        
        page_id = await writer.write_job_to_notion(sample_job_data)
        assert page_id == "test_page_id"
        
        # Test job update
        updated_data = sample_job_data.copy()
        updated_data["ai_fit_score"] = 95
        
        mock_notion_client.databases.query.return_value = {
            "results": [{"id": page_id}]
        }
        
        updated_page_id = await writer.write_job_to_notion(updated_data)
        assert updated_page_id == page_id
        assert writer._stats["jobs_updated"] == 1
    
    async def test_error_handling_workflow(self, mock_notion_client, sample_job_data):
        """Test error handling in various operations."""
        writer = NotionWriter(api_key="test_key")
        writer.client = mock_notion_client
        
        # Test database creation error
        mock_notion_client.databases.create.side_effect = Exception("API Error")
        
        with pytest.raises(NotionDatabaseError):
            await writer.create_job_database()
        
        # Test job writing error
        mock_notion_client.pages.create.side_effect = Exception("Page Error")
        writer.database_id = "test_db"
        mock_notion_client.databases.query.return_value = {"results": []}
        
        with pytest.raises(NotionPageError):
            await writer.write_job_to_notion(sample_job_data)
        
        assert writer._stats["errors"] > 0