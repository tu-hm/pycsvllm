import sqlite3
import pandas as pd

class SQLiteManager:
    def __init__(self, db_path: str):
        """Initialize the SQLiteManager with the database path and establish a connection."""
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self._connect()

    def _connect(self):
        """Establish a connection to the database, creating the file if it doesn’t exist."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to connect to database: {e}")

    def close(self):
        """Close the database connection if it exists."""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None

    def __enter__(self):
        """Enter the context and return the SQLiteManager instance."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context and close the connection."""
        self.close()

    def create_table(self, sql: str):
        """Execute a CREATE TABLE statement."""
        try:
            self.cursor.execute(sql)
            self.connection.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to create table: {e}")

    def execute(self, sql: str, parameters: tuple = ()):
        """Execute an SQL statement with optional parameters."""
        try:
            self.cursor.execute(sql, parameters)
            self.connection.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"SQL execution failed: {e}")

    def query(self, sql: str, parameters: tuple = ()) -> list:
        """Execute a SELECT query and return the results."""
        try:
            self.cursor.execute(sql, parameters)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            raise RuntimeError(f"SQL query failed: {e}")

    def import_from_csvloader(self, csvloader: 'CSVLoader', table_name: str = None):
        """Import data from a CSVLoader into a table."""
        if table_name is None:
            table_name = csvloader.name if csvloader.name else "default_table"
        create_sql = generate_create_table(csvloader, table_name)
        self.create_table(create_sql)
        csvloader.data.to_sql(table_name, self.connection, if_exists='append', index=False)

    def export_to_dataframe(self, table_name: str) -> pd.DataFrame:
        """Export a table to a pandas DataFrame."""
        return pd.read_sql(f"SELECT * FROM {table_name}", self.connection)