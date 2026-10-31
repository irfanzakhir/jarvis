import sqlite3
import pandas as pd

def view_brain_data():
    db_path = "assets/jarvis_memory.db"
    try:
        # Connect to Jarvis's brain
        conn = sqlite3.connect(db_path)
        
        # Pull the exact timestamp and the English fact (ignoring the massive vector numbers)
        query = "SELECT id, timestamp, fact FROM long_term_memory ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("Jarvis's memory is currently empty.")
        else:
            print("\n=== J.A.R.V.I.S. LONG-TERM MEMORY ARCHIVE ===")
            print(df.to_string(index=False))
            print("=============================================\n")
            
        conn.close()
    except Exception as e:
        print(f"Could not access memory: {e}")

if __name__ == "__main__":
    view_brain_data()