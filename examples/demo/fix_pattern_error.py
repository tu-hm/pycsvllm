import re

from src.file_processing.csv import CSVLoader

correct_data = CSVLoader('../public/company-purchasing-dataset/spend_analysis_dataset.csv')
schema_data = correct_data.generate_schema()

print(schema_data.json_schema)

dirty_data = CSVLoader('../public/company-purchasing-dataset/messy_pattern_spend_analysis_dataset.csv')
dirty_data.set_schema(schema_data.json_schema)

list_improve, error = dirty_data.fix_regex_pattern_error('TransactionID')
dirty_data.apply_improvements(list_improve)
print(len(list_improve))
dirty_data.data.to_csv('../public/company-purchasing-dataset/clean_pattern_data.csv', index=False)

valid_pattern = 0
total_value = 0
pattern = schema_data.json_schema['properties']['TransactionID']['pattern']
for value in dirty_data.data['TransactionID']:
    total_value += 1
    if re.fullmatch(pattern, value, 0) is not None:
        valid_pattern += 1

print(f"Match pattern rate: {valid_pattern / total_value * 100}%")

from benchmark.benchmark import benchmark_data_cleaning

result = benchmark_data_cleaning(
    clean_path="../public/company-purchasing-dataset/spend_analysis_dataset.csv",
    messy_path="../public/company-purchasing-dataset/messy_pattern_spend_analysis_dataset.csv",
    cleaned_path="../public/company-purchasing-dataset/clean_pattern_data.csv",
)

print(f"Correction Rate: {result['correction_rate']:.2f}%")
print(f"Remaining Errors: {result['remaining_errors']}")
print(f"Corrected Errors: {result['corrected_errors']}")