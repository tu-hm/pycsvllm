from src.file_processing.csv import CSVLoader

correct_data = CSVLoader('../public/company-purchasing-dataset/spend_analysis_dataset.csv')
incorrect_datetime_data = CSVLoader('../public/company-purchasing-dataset/messy_datetime_spend_analysis_dataset.csv')

schema = correct_data.generate_schema()

list_improvements, error = incorrect_datetime_data.fix_datetime_error(column_list=['PurchaseDate'], formation=[('PurchaseDate', 'YYYY-MM-DD')],few_shot_context=[
    ('19/04/2024', '2024-04-19'),
    ('12:00:00 AM, 21/01/24', '2024-01-21'),
    ('10 9 24', '2024-09-10')
])

print(len(list_improvements))

incorrect_datetime_data.apply_improvements(list_improvements)
incorrect_datetime_data.data.to_csv('../public/company-purchasing-dataset/cleaned_datetime_data.csv', index=False)

from benchmark.benchmark import benchmark_data_cleaning

result = benchmark_data_cleaning(
    clean_path="../public/company-purchasing-dataset/spend_analysis_dataset.csv",
    messy_path="../public/company-purchasing-dataset/messy_datetime_spend_analysis_dataset.csv",
    cleaned_path="../public/company-purchasing-dataset/cleaned_datetime_data.csv",
)

print(f"Correction Rate: {result['correction_rate']:.2f}%")
print(f"Remaining Errors: {result['remaining_errors']}")
print(f"Corrected Errors: {result['corrected_errors']}")