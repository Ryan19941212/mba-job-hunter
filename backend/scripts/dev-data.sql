-- MBA Job Hunter Development Data
-- This script inserts sample data for development and testing

-- Insert sample companies (if tables exist)
-- Note: This script will only run if the application tables have been created by Alembic migrations

DO $$
BEGIN
    -- Check if companies table exists before inserting data
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'companies') THEN
        -- Insert sample companies
        INSERT INTO companies (id, name, description, website, size, industry, location, logo_url, created_at, updated_at) 
        VALUES 
            (gen_random_uuid(), 'Tech Innovators Inc', 'Leading technology company', 'https://techinnovators.com', 'Large', 'Technology', 'San Francisco, CA', NULL, NOW(), NOW()),
            (gen_random_uuid(), 'Global Consulting Group', 'Premier management consulting', 'https://globalconsulting.com', 'Large', 'Consulting', 'New York, NY', NULL, NOW(), NOW()),
            (gen_random_uuid(), 'FinTech Solutions', 'Financial technology startup', 'https://fintechsolutions.com', 'Medium', 'Finance', 'Austin, TX', NULL, NOW(), NOW())
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Sample companies inserted successfully';
    ELSE
        RAISE NOTICE 'Companies table does not exist yet. Run migrations first.';
    END IF;
    
    -- Check if job_postings table exists before inserting data
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'job_postings') THEN
        -- Insert sample job postings (assuming companies exist)
        WITH sample_companies AS (
            SELECT id FROM companies LIMIT 3
        )
        INSERT INTO job_postings (
            id, title, description, requirements, salary_min, salary_max, 
            location, remote_allowed, employment_type, experience_level,
            company_id, source, source_job_id, url, status, 
            posted_date, expires_date, created_at, updated_at
        )
        SELECT 
            gen_random_uuid(),
            title,
            description,
            requirements,
            salary_min,
            salary_max,
            location,
            remote_allowed,
            employment_type,
            experience_level,
            sc.id,
            'manual',
            'dev-' || generate_short_id(),
            'https://example.com/job/' || generate_short_id(),
            'active'::job_status,
            NOW() - INTERVAL '1 day',
            NOW() + INTERVAL '30 days',
            NOW(),
            NOW()
        FROM sample_companies sc,
        (VALUES 
            ('Senior Product Manager', 'Lead product strategy and development for our flagship products', 'MBA preferred, 5+ years product management experience', 120000, 180000, 'San Francisco, CA', true, 'Full-time', 'Senior'),
            ('Management Consultant', 'Drive strategic initiatives for Fortune 500 clients', 'MBA required, top-tier consulting experience', 150000, 220000, 'New York, NY', false, 'Full-time', 'Mid-level'),
            ('Business Development Manager', 'Expand market presence and develop strategic partnerships', 'MBA preferred, 3+ years BD experience', 90000, 140000, 'Austin, TX', true, 'Full-time', 'Mid-level')
        ) AS jobs(title, description, requirements, salary_min, salary_max, location, remote_allowed, employment_type, experience_level)
        LIMIT 3
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Sample job postings inserted successfully';
    ELSE
        RAISE NOTICE 'Job postings table does not exist yet. Run migrations first.';
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error inserting development data: %', SQLERRM;
END $$;