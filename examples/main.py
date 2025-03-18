from file_processing.csv import CSVLoader
from file_processing.sql_generator import generate_create_table
from file_processing.sqlite import SQLiteProcessor

data = CSVLoader(
    filepath='public/true_data.csv',
    name='true_data',
)

print(data.generate_schema())

query = generate_create_table(data)

sqlite_client = SQLiteProcessor(
    database_name='true_data.db',
    table_name='true_data',

)