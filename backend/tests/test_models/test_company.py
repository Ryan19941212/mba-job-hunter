"""
Tests for Company model.

Tests database operations, model validations, and properties
for the Company model.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.company import Company


@pytest.mark.database
@pytest.mark.unit
class TestCompanyModel:
    """Test Company model functionality."""
    
    async def test_create_company(self, test_db, sample_company_data):
        """Test creating a company with valid data."""
        company = Company(
            name=sample_company_data["name"],
            industry=sample_company_data["industry"],
            size=sample_company_data["size"],
            location=sample_company_data["location"],
            website=sample_company_data["website"],
            description=sample_company_data["description"],
            logo_url=sample_company_data["logo_url"],
            linkedin_url=sample_company_data["linkedin_url"],
            glassdoor_rating=sample_company_data["glassdoor_rating"],
            founded_year=sample_company_data["founded_year"]
        )
        
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)
        
        assert company.id is not None
        assert company.name == sample_company_data["name"]
        assert company.industry == sample_company_data["industry"]
        assert company.created_at is not None
        assert company.updated_at is not None
        assert company.is_active is True
    
    async def test_company_required_fields(self, test_db):
        """Test that required fields are enforced."""
        # Test missing name
        with pytest.raises(IntegrityError):
            company = Company(
                industry="Technology",
                size="1000-5000"
            )
            test_db.add(company)
            await test_db.commit()
    
    async def test_company_unique_name(self, test_db):
        """Test that company name is unique."""
        # Create first company
        company1 = Company(
            name="TechCorp Inc",
            industry="Technology",
            size="1000-5000"
        )
        test_db.add(company1)
        await test_db.commit()
        
        # Try to create second company with same name
        with pytest.raises(IntegrityError):
            company2 = Company(
                name="TechCorp Inc",  # Same name
                industry="Finance",
                size="500-1000"
            )
            test_db.add(company2)
            await test_db.commit()
    
    async def test_company_glassdoor_rating_validation(self, test_db):
        """Test Glassdoor rating validation constraints."""
        # Test invalid rating (> 5.0)
        with pytest.raises(IntegrityError):
            company = Company(
                name="Test Company",
                industry="Technology",
                glassdoor_rating=6.0  # Invalid: > 5.0
            )
            test_db.add(company)
            await test_db.commit()
        
        # Test invalid rating (< 0.0)
        with pytest.raises(IntegrityError):
            company = Company(
                name="Test Company 2",
                industry="Technology",
                glassdoor_rating=-1.0  # Invalid: < 0.0
            )
            test_db.add(company)
            await test_db.commit()
        
        # Test valid rating
        company = Company(
            name="Test Company 3",
            industry="Technology",
            glassdoor_rating=4.5
        )
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)
        
        assert company.glassdoor_rating == 4.5
    
    async def test_company_founded_year_validation(self, test_db):
        """Test founded year validation."""
        current_year = datetime.now().year
        
        # Test invalid year (too old)
        with pytest.raises(IntegrityError):
            company = Company(
                name="Old Company",
                industry="Technology",
                founded_year=1799  # Before 1800
            )
            test_db.add(company)
            await test_db.commit()
        
        # Test invalid year (future)
        with pytest.raises(IntegrityError):
            company = Company(
                name="Future Company",
                industry="Technology",
                founded_year=current_year + 10  # Too far in future
            )
            test_db.add(company)
            await test_db.commit()
        
        # Test valid year
        company = Company(
            name="Valid Company",
            industry="Technology",
            founded_year=2010
        )
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)
        
        assert company.founded_year == 2010
    
    async def test_company_properties(self, test_db, sample_company_data):
        """Test Company model properties."""
        company = Company(
            name=sample_company_data["name"],
            industry=sample_company_data["industry"],
            size=sample_company_data["size"],
            founded_year=2010,
            glassdoor_rating=4.2
        )
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)
        
        # Test company_age property
        current_year = datetime.now().year
        expected_age = current_year - 2010
        assert company.company_age == expected_age
        
        # Test is_well_rated property
        assert company.is_well_rated is True  # 4.2 >= 4.0
        
        # Test company with low rating
        low_rated_company = Company(
            name="Low Rated Company",
            industry="Technology",
            glassdoor_rating=3.5
        )
        test_db.add(low_rated_company)
        await test_db.commit()
        await test_db.refresh(low_rated_company)
        
        assert low_rated_company.is_well_rated is False
    
    async def test_company_without_rating(self, test_db):
        """Test company properties without rating."""
        company = Company(
            name="No Rating Company",
            industry="Technology",
            size="100-500"
        )
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)
        
        # Should not be considered well rated without rating
        assert company.is_well_rated is False
    
    async def test_company_without_founded_year(self, test_db):
        """Test company age calculation without founded year."""
        company = Company(
            name="Unknown Age Company",
            industry="Technology"
        )
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)
        
        # Should return None for company_age
        assert company.company_age is None
    
    async def test_company_repr(self, test_db):
        """Test Company string representation."""
        company = Company(
            name="Test Company",
            industry="Technology"
        )
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)
        
        repr_str = repr(company)
        assert "Test Company" in repr_str
        assert str(company.id) in repr_str
    
    async def test_company_timestamps(self, test_db):
        """Test automatic timestamp handling."""
        company = Company(
            name="Timestamp Test Company",
            industry="Technology"
        )
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)
        
        created_time = company.created_at
        updated_time = company.updated_at
        
        assert created_time is not None
        assert updated_time is not None
        
        # Update the company
        company.description = "Updated description"
        await test_db.commit()
        await test_db.refresh(company)
        
        # created_at should remain the same, updated_at should change
        assert company.created_at == created_time
        assert company.updated_at > updated_time
    
    async def test_query_companies(self, test_db):
        """Test querying companies from database."""
        # Add multiple companies
        companies_data = [
            {"name": "Tech Company A", "industry": "Technology", "size": "1000+"},
            {"name": "Finance Company B", "industry": "Finance", "size": "500-1000"},
            {"name": "Healthcare Company C", "industry": "Healthcare", "size": "100-500"},
            {"name": "Tech Company D", "industry": "Technology", "size": "50-100"}
        ]
        
        for comp_data in companies_data:
            company = Company(
                name=comp_data["name"],
                industry=comp_data["industry"],
                size=comp_data["size"]
            )
            test_db.add(company)
        
        await test_db.commit()
        
        # Query all companies
        result = await test_db.execute(select(Company))
        all_companies = result.scalars().all()
        
        assert len(all_companies) == len(companies_data)
        
        # Query companies by industry
        result = await test_db.execute(
            select(Company).where(Company.industry == "Technology")
        )
        tech_companies = result.scalars().all()
        
        assert len(tech_companies) == 2  # Tech Company A and D
        for company in tech_companies:
            assert company.industry == "Technology"
        
        # Query companies by size
        result = await test_db.execute(
            select(Company).where(Company.size.like("%1000%"))
        )
        large_companies = result.scalars().all()
        
        assert len(large_companies) == 2  # 1000+ and 500-1000
    
    async def test_company_url_validation(self, test_db):
        """Test URL field formats."""
        # Valid URLs should work
        company = Company(
            name="URL Test Company",
            industry="Technology",
            website="https://example.com",
            linkedin_url="https://linkedin.com/company/example",
            logo_url="https://example.com/logo.png"
        )
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)
        
        assert company.website == "https://example.com"
        assert company.linkedin_url == "https://linkedin.com/company/example"
        assert company.logo_url == "https://example.com/logo.png"
    
    async def test_company_search_functionality(self, test_db):
        """Test company search and filtering capabilities."""
        # Create companies with different attributes
        companies = [
            Company(
                name="Apple Inc",
                industry="Technology",
                location="Cupertino, CA",
                size="10000+",
                glassdoor_rating=4.5,
                founded_year=1976
            ),
            Company(
                name="Google LLC",
                industry="Technology",
                location="Mountain View, CA",
                size="10000+",
                glassdoor_rating=4.4,
                founded_year=1998
            ),
            Company(
                name="Goldman Sachs",
                industry="Finance",
                location="New York, NY",
                size="5000-10000",
                glassdoor_rating=4.0,
                founded_year=1869
            )
        ]
        
        for company in companies:
            test_db.add(company)
        await test_db.commit()
        
        # Test location-based search
        result = await test_db.execute(
            select(Company).where(Company.location.contains("CA"))
        )
        ca_companies = result.scalars().all()
        assert len(ca_companies) == 2
        
        # Test rating-based search
        result = await test_db.execute(
            select(Company).where(Company.glassdoor_rating >= 4.4)
        )
        high_rated = result.scalars().all()
        assert len(high_rated) == 2
        
        # Test size-based search
        result = await test_db.execute(
            select(Company).where(Company.size == "10000+")
        )
        large_companies = result.scalars().all()
        assert len(large_companies) == 2
        
        # Test combined filters
        result = await test_db.execute(
            select(Company).where(
                (Company.industry == "Technology") &
                (Company.glassdoor_rating >= 4.4) &
                (Company.location.contains("CA"))
            )
        )
        filtered_companies = result.scalars().all()
        assert len(filtered_companies) == 2