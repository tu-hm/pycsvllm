from file_processing.csv import CSVLoader
from file_processing.sql_generator import generate_create_table

data = CSVLoader(
    filepath='public/true_data.csv',
    name='true_data',
)

print(data.generate_schema())

query = generate_create_table(str(data.schema), data.name, str(data.data.columns))

print(query)