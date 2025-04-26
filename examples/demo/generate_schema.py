import json

from src.file_processing.csv import CSVLoader

original_data = CSVLoader('../public/book/small_book_data.csv')
reference_data = CSVLoader('../public/book/reference_data.csv')

schema_data = original_data.generate_schema(reference_data=reference_data.data)

schema = schema_data.json_schema
beauty_schema_info = json.dumps(schema, indent=4)
print(beauty_schema_info)