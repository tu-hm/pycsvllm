from src.file_processing.csv import CSVLoader

correct_data = CSVLoader('../public/company-purchasing-dataset/spend_analysis_dataset.csv')
schema = correct_data.generate_schema().json_schema
print(schema)

incorrect_data = CSVLoader('../public/company-purchasing-dataset/messy_ref_spend_analysis_dataset.csv')
incorrect_data.set_schema(schema)

ref_value_category = schema['properties']['Category']['enum']
print(type(ref_value_category))

list_improve, error = incorrect_data.fix_reference_value_error('Category', ref_value_category)
print(len(list_improve))
incorrect_data.apply_improvements(list_improve)
incorrect_data.data.to_csv('../public/company-purchasing-dataset/cleaned_ref_data.csv', index=False)

from benchmark.benchmark import benchmark_data_cleaning

result = benchmark_data_cleaning(
    clean_path="../public/company-purchasing-dataset/spend_analysis_dataset.csv",
    messy_path="../public/company-purchasing-dataset/messy_ref_spend_analysis_dataset.csv",
    cleaned_path="../public/company-purchasing-dataset/cleaned_ref_data.csv",
)

print(f"Correction Rate: {result['correction_rate']:.2f}%")
print(f"Remaining Errors: {result['remaining_errors']}")
print(f"Corrected Errors: {result['corrected_errors']}")