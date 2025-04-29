import json

from src.file_processing.csv import CSVLoader

original_data = CSVLoader('../public/company-purchasing-dataset/spend_analysis_dataset.csv')
schema_data = original_data.generate_schema()

schema = schema_data.json_schema
beauty_schema_info = json.dumps(schema, indent=4)
print(beauty_schema_info)

print(CSVLoader.validate_dataset(original_data.data, schema))