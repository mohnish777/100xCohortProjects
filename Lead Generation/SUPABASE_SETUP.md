# Supabase Setup Guide

## 1. Create a Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Sign up or log in to your account
3. Click "New Project"
4. Choose your organization
5. Fill in project details:
   - Name: `lead-generation` (or any name you prefer)
   - Database Password: Create a strong password
   - Region: Choose the closest region to your users
6. Click "Create new project"

## 2. Get Your Project Credentials

1. Once your project is created, go to the project dashboard
2. Click on "Settings" in the left sidebar
3. Click on "API" under Settings
4. Copy the following values:
   - **Project URL** (looks like: `https://your-project-id.supabase.co`)
   - **anon public key** (starts with `eyJ...`)

## 3. Update Your Environment Variables

1. Open your `.env` file
2. Replace the placeholder values with your actual Supabase credentials:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_anon_public_key_here
```

## 4. Create the Database Table

1. In your Supabase dashboard, click on "SQL Editor" in the left sidebar
2. Click "New query"
3. Copy and paste the entire content from `supabase_schema.sql`
4. Click "Run" to execute the SQL

This will create:
- The `customers` table with all required columns
- Indexes for better performance
- Automatic timestamp updates
- Row Level Security (optional)

## 5. Install Dependencies

Run the following command to install the required packages:

```bash
pip install -r requirements.txt
```

## 6. Test the Connection

1. Start your FastAPI server:
```bash
python main.py
```

2. Start your Streamlit UI:
```bash
streamlit run ui.py
```

3. Try adding a customer through the UI to test the database connection

## 7. Verify Data in Supabase

1. Go to your Supabase dashboard
2. Click on "Table Editor" in the left sidebar
3. Select the "customers" table
4. You should see any customers you've added through the API

## Troubleshooting

### Common Issues:

1. **Connection Error**: Make sure your SUPABASE_URL and SUPABASE_KEY are correct
2. **Table Not Found**: Ensure you've run the SQL schema in the Supabase SQL Editor
3. **Permission Denied**: Check your Row Level Security policies if enabled

### Environment Variables Not Loading:

Make sure your `.env` file is in the same directory as your `main.py` file and that you're using `python-dotenv` to load them.

## Security Notes

- The current setup uses the `anon` key which is safe for client-side use
- Row Level Security is enabled but with a permissive policy for testing
- For production, consider implementing proper authentication and more restrictive RLS policies
- Never commit your `.env` file to version control

## Next Steps

- Set up proper authentication if needed
- Implement data validation and error handling
- Add backup and migration strategies
- Monitor usage and performance in the Supabase dashboard
