"""Create job table with AI analysis fields

Revision ID: 0001
Revises: 
Create Date: 2025-06-23 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('job_level', sa.String(length=50), nullable=True),
        sa.Column('employment_type', sa.String(length=50), nullable=True),
        sa.Column('remote_friendly', sa.Boolean(), nullable=False),
        sa.Column('posted_date', sa.DateTime(), nullable=True),
        sa.Column('expires_date', sa.DateTime(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('source_platform', sa.String(length=50), nullable=False),
        sa.Column('company_logo_url', sa.Text(), nullable=True),
        sa.Column('ai_fit_score', sa.Integer(), nullable=True),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('extracted_skills', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Constraints
        sa.UniqueConstraint('source_url', name='uq_job_source_url'),
        sa.CheckConstraint('ai_fit_score >= 0 AND ai_fit_score <= 100', name='ck_job_ai_fit_score_range'),
        sa.CheckConstraint("employment_type IN ('Full-time', 'Part-time', 'Contract') OR employment_type IS NULL", name='ck_job_employment_type_valid'),
        sa.CheckConstraint("source_platform IN ('linkedin', 'indeed', 'levelfyi')", name='ck_job_source_platform_valid'),
    )
    
    # Create indexes
    op.create_index('idx_job_title', 'jobs', ['title'])
    op.create_index('idx_job_company_name', 'jobs', ['company_name'])
    op.create_index('idx_job_location', 'jobs', ['location'])
    op.create_index('idx_job_salary_range', 'jobs', ['salary_min', 'salary_max'])
    op.create_index('idx_job_employment_type', 'jobs', ['employment_type'])
    op.create_index('idx_job_remote_friendly', 'jobs', ['remote_friendly'])
    op.create_index('idx_job_posted_date', 'jobs', ['posted_date'])
    op.create_index('idx_job_source_platform', 'jobs', ['source_platform'])
    op.create_index('idx_job_ai_fit_score', 'jobs', ['ai_fit_score'])
    op.create_index('idx_job_is_active', 'jobs', ['is_active'])
    op.create_index('idx_job_created_at', 'jobs', ['created_at'])
    
    # Composite indexes
    op.create_index('idx_job_active_posted', 'jobs', ['is_active', 'posted_date'])
    op.create_index('idx_job_platform_active', 'jobs', ['source_platform', 'is_active'])
    op.create_index('idx_job_company_active', 'jobs', ['company_name', 'is_active'])
    op.create_index('idx_job_location_remote', 'jobs', ['location', 'remote_friendly'])
    
    # Set default values
    op.execute("ALTER TABLE jobs ALTER COLUMN currency SET DEFAULT 'USD'")
    op.execute("ALTER TABLE jobs ALTER COLUMN remote_friendly SET DEFAULT false")
    op.execute("ALTER TABLE jobs ALTER COLUMN is_active SET DEFAULT true")


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_job_location_remote', table_name='jobs')
    op.drop_index('idx_job_company_active', table_name='jobs')
    op.drop_index('idx_job_platform_active', table_name='jobs')
    op.drop_index('idx_job_active_posted', table_name='jobs')
    op.drop_index('idx_job_created_at', table_name='jobs')
    op.drop_index('idx_job_is_active', table_name='jobs')
    op.drop_index('idx_job_ai_fit_score', table_name='jobs')
    op.drop_index('idx_job_source_platform', table_name='jobs')
    op.drop_index('idx_job_posted_date', table_name='jobs')
    op.drop_index('idx_job_remote_friendly', table_name='jobs')
    op.drop_index('idx_job_employment_type', table_name='jobs')
    op.drop_index('idx_job_salary_range', table_name='jobs')
    op.drop_index('idx_job_location', table_name='jobs')
    op.drop_index('idx_job_company_name', table_name='jobs')
    op.drop_index('idx_job_title', table_name='jobs')
    
    # Drop table
    op.drop_table('jobs')