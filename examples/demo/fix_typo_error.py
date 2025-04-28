from src.file_processing.csv import CSVLoader

correct_data = CSVLoader('../public/company-purchasing-dataset/spend_analysis_dataset.csv')
schema = correct_data.generate_schema().json_schema
print(schema)

incorrect_data = CSVLoader('../public/company-purchasing-dataset/messy_typo_spend_analysis_dataset.csv')
list_improve, error = incorrect_data.fix_typography_data(['ItemName', 'Category'])

incorrect_data.apply_improvements(list_improve)
incorrect_data.data.to_csv('../public/company-purchasing-dataset/cleaned_typo_data.csv', index=False)

from benchmark.benchmark import benchmark_data_cleaning

result = benchmark_data_cleaning(
    clean_path="../public/company-purchasing-dataset/spend_analysis_dataset.csv",
    messy_path="../public/company-purchasing-dataset/messy_typo_spend_analysis_dataset.csv",
    cleaned_path="../public/company-purchasing-dataset/cleaned_typo_data.csv",
)

print(f"Correction Rate: {result['correction_rate']:.2f}%")
print(f"Remaining Errors: {result['remaining_errors']}")
print(f"Corrected Errors: {result['corrected_errors']}")