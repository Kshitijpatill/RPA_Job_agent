import pandas as pd
from database import engine

def export_to_excel():
    """Reads the job logs from SQLite and updates the Excel file."""
    try:
        # Read directly from the database
        df = pd.read_sql_table('job_logs', con=engine)
        
        # Format the timestamp so it looks clean in Excel
        if not df.empty:
            df['applied_on'] = pd.to_datetime(df['applied_on']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Dump it to an Excel file
        df.to_excel('Job_Applications_Tracker.xlsx', index=False, sheet_name='Applications')
        print("✅ Excel tracker updated successfully!")
    except Exception as e:
        print(f"❌ Failed to update Excel: {e}")