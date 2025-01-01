import sqlite3
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path='inventory.db'):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize database with schema"""
        try:
            with open('database/schema.sql', 'r') as f:
                schema = f.read()
                
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema)
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            print(f"Error executing query: {e}")
            return []

    def execute_update(self, query, params=None):
        """Execute an update query within a transaction"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return True
        except Exception as e:
            print(f"Error executing update: {e}")
            return False

    def execute_transaction(self, queries):
        """Execute multiple queries in a single transaction"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for query, params in queries:
                    cursor.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            print(f"Error executing transaction: {e}")
            return False