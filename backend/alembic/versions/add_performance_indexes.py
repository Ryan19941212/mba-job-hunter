"""Add performance indexes for production optimization

Revision ID: perf_indexes_001
Revises: 0001_create_job_table
Create Date: 2024-06-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'perf_indexes_001'
down_revision = '0001_create_job_table'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes for production optimization."""
    
    # Job table indexes for search optimization
    op.create_index(
        'idx_jobs_title_search',
        'jobs',
        ['title'],
        postgresql_using='gin',
        postgresql_ops={'title': 'gin_trgm_ops'}
    )
    
    op.create_index(
        'idx_jobs_company_search',
        'jobs',
        ['company'],
        postgresql_using='gin',
        postgresql_ops={'company': 'gin_trgm_ops'}
    )
    
    op.create_index(
        'idx_jobs_location_search',
        'jobs',
        ['location'],
        postgresql_using='gin',
        postgresql_ops={'location': 'gin_trgm_ops'}
    )
    
    # Full-text search index for job description
    op.create_index(
        'idx_jobs_description_fulltext',
        'jobs',
        ['description'],
        postgresql_using='gin',
        postgresql_ops={'description': 'gin_trgm_ops'}
    )
    
    # Composite indexes for common query patterns
    op.create_index(
        'idx_jobs_status_created_at',
        'jobs',
        ['status', 'created_at']
    )
    
    op.create_index(
        'idx_jobs_source_created_at',
        'jobs',
        ['source', 'created_at']
    )
    
    op.create_index(
        'idx_jobs_salary_range',
        'jobs',
        ['salary_min', 'salary_max']
    )
    
    # Index for job URL uniqueness and lookups
    op.create_index(
        'idx_jobs_url_unique',
        'jobs',
        ['url'],
        unique=True
    )
    
    # Index for job posting date for time-based queries
    op.create_index(
        'idx_jobs_posted_date',
        'jobs',
        ['posted_date']
    )
    
    # Partial index for active jobs only
    op.execute("""
        CREATE INDEX idx_jobs_active_status 
        ON jobs (created_at, title) 
        WHERE status = 'active'
    """)
    
    # Company table indexes
    if op.get_bind().dialect.has_table(op.get_bind(), 'companies'):
        op.create_index(
            'idx_companies_name_search',
            'companies',
            ['name'],
            postgresql_using='gin',
            postgresql_ops={'name': 'gin_trgm_ops'}
        )
        
        op.create_index(
            'idx_companies_industry',
            'companies',
            ['industry']
        )
        
        op.create_index(
            'idx_companies_size',
            'companies',
            ['size']
        )
    
    # Analysis table indexes
    if op.get_bind().dialect.has_table(op.get_bind(), 'job_analysis'):
        op.create_index(
            'idx_analysis_job_id',
            'job_analysis',
            ['job_id']
        )
        
        op.create_index(
            'idx_analysis_match_score',
            'job_analysis',
            ['match_score']
        )
        
        op.create_index(
            'idx_analysis_created_at',
            'job_analysis',
            ['created_at']
        )
        
        # Composite index for high-scoring matches
        op.create_index(
            'idx_analysis_high_scores',
            'job_analysis',
            ['match_score', 'created_at'],
            postgresql_where='match_score >= 0.7'
        )
    
    # Enable pg_trgm extension for trigram similarity searches
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    
    # Enable btree_gin extension for composite indexes
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gin')
    
    # Create materialized view for job statistics
    op.execute("""
        CREATE MATERIALIZED VIEW job_stats_mv AS
        SELECT 
            DATE(created_at) as date,
            source,
            COUNT(*) as jobs_count,
            AVG(CASE WHEN salary_min > 0 THEN salary_min END) as avg_salary_min,
            AVG(CASE WHEN salary_max > 0 THEN salary_max END) as avg_salary_max,
            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_jobs,
            COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_jobs
        FROM jobs
        GROUP BY DATE(created_at), source
        ORDER BY date DESC, source
    """)
    
    # Create index on materialized view
    op.create_index(
        'idx_job_stats_mv_date_source',
        'job_stats_mv',
        ['date', 'source']
    )
    
    # Create function to refresh materialized view
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_job_stats()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY job_stats_mv;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade():
    """Remove performance indexes."""
    
    # Drop materialized view and function
    op.execute('DROP FUNCTION IF EXISTS refresh_job_stats()')
    op.execute('DROP MATERIALIZED VIEW IF EXISTS job_stats_mv')
    
    # Drop job table indexes
    op.drop_index('idx_jobs_active_status')
    op.drop_index('idx_jobs_posted_date')
    op.drop_index('idx_jobs_url_unique')
    op.drop_index('idx_jobs_salary_range')
    op.drop_index('idx_jobs_source_created_at')
    op.drop_index('idx_jobs_status_created_at')
    op.drop_index('idx_jobs_description_fulltext')
    op.drop_index('idx_jobs_location_search')
    op.drop_index('idx_jobs_company_search')
    op.drop_index('idx_jobs_title_search')
    
    # Drop company table indexes if they exist
    try:
        op.drop_index('idx_companies_size')
        op.drop_index('idx_companies_industry')
        op.drop_index('idx_companies_name_search')
    except:
        pass
    
    # Drop analysis table indexes if they exist
    try:
        op.drop_index('idx_analysis_high_scores')
        op.drop_index('idx_analysis_created_at')
        op.drop_index('idx_analysis_match_score')
        op.drop_index('idx_analysis_job_id')
    except:
        pass