import sqlite3
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def analyze_timestamps():
    # Connect to SQLite database
    db_path = Path('db.sqlite3')
    conn = sqlite3.connect(db_path)
    
    # Get basic statistics
    cursor = conn.cursor()
    
    # Get total records
    cursor.execute("SELECT COUNT(*) FROM dashboard_sensordata")
    total_records = cursor.fetchone()[0]
    print(f"\nTotal records: {total_records}")
    
    # Get time range
    cursor.execute("""
        SELECT 
            MIN(timestamp) as first_record,
            MAX(timestamp) as last_record
        FROM dashboard_sensordata
    """)
    first_record, last_record = cursor.fetchone()
    print(f"\nTime range:")
    print(f"First record: {first_record}")
    print(f"Last record: {last_record}")
    
    # Get records per day
    cursor.execute("""
        SELECT 
            date(timestamp, 'localtime') as day,
            COUNT(*) as count
        FROM dashboard_sensordata
        GROUP BY date(timestamp, 'localtime')
        ORDER BY day
    """)
    daily_stats = cursor.fetchall()
    print("\nRecords per day:")
    for day, count in daily_stats:
        print(f"{day}: {count} records")
    
    # Get records per hour
    cursor.execute("""
        SELECT 
            strftime('%Y-%m-%d %H', datetime(timestamp, 'localtime')) as hour,
            COUNT(*) as count
        FROM dashboard_sensordata
        GROUP BY strftime('%Y-%m-%d %H', datetime(timestamp, 'localtime'))
        ORDER BY hour
    """)
    hourly_stats = cursor.fetchall()
    print("\nRecords per hour:")
    for hour, count in hourly_stats:
        print(f"{hour}: {count} records")
    
    # Calculate average time between records
    cursor.execute("""
        WITH time_diffs AS (
            SELECT 
                julianday(timestamp) - julianday(LAG(timestamp) OVER (ORDER BY timestamp)) as diff
            FROM dashboard_sensordata
        )
        SELECT AVG(diff) * 24 * 60 as avg_minutes
        FROM time_diffs
        WHERE diff IS NOT NULL
    """)
    avg_minutes = cursor.fetchone()[0]
    print(f"\nAverage time between records: {avg_minutes:.2f} minutes")
    
    # Create visualizations
    # Convert to pandas DataFrame for easier plotting
    df_daily = pd.DataFrame(daily_stats, columns=['day', 'count'])
    df_hourly = pd.DataFrame(hourly_stats, columns=['hour', 'count'])
    
    # Plot daily distribution
    plt.figure(figsize=(12, 6))
    plt.bar(df_daily['day'], df_daily['count'])
    plt.title('Records per Day')
    plt.xlabel('Date')
    plt.ylabel('Number of Records')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('daily_distribution.png')
    
    # Plot hourly distribution
    plt.figure(figsize=(15, 6))
    plt.bar(df_hourly['hour'], df_hourly['count'])
    plt.title('Records per Hour')
    plt.xlabel('Hour')
    plt.ylabel('Number of Records')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('hourly_distribution.png')
    
    conn.close()
    print("\nVisualizations saved as 'daily_distribution.png' and 'hourly_distribution.png'")

if __name__ == "__main__":
    analyze_timestamps() 