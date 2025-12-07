-- Create customers table in Supabase
-- Run this SQL in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    country VARCHAR(100),
    address TEXT,
    
    -- Qualification inputs
    goal TEXT,
    budget VARCHAR(20) CHECK (budget IN ('company', 'self')),
    webinar_join TIMESTAMPTZ,
    webinar_leave TIMESTAMPTZ,
    asked_q BOOLEAN DEFAULT FALSE,
    referred BOOLEAN DEFAULT FALSE,
    past_touchpoints INTEGER DEFAULT 0,
    
    -- Derived outputs
    engaged_mins INTEGER,
    score INTEGER CHECK (score >= 0 AND score <= 100),
    reasoning TEXT,
    status VARCHAR(20) CHECK (status IN ('Qualified', 'Nurture')),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create an index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);

-- Create an index on status for filtering
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a trigger to automatically update updated_at
CREATE TRIGGER update_customers_updated_at 
    BEFORE UPDATE ON customers 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS) - optional but recommended
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows all operations for authenticated users
-- You can modify this based on your security requirements
CREATE POLICY "Enable all operations for authenticated users" ON customers
    FOR ALL USING (auth.role() = 'authenticated');

-- If you want to allow anonymous access (for testing), use this policy instead:
-- CREATE POLICY "Enable all operations for all users" ON customers FOR ALL USING (true);
