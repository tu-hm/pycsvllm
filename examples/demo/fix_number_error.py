from src.file_processing.csv import CSVLoader

original_data = CSVLoader('../public/book/small_book_data.csv')
schema = original_data.generate_schema().json_schema

messy_data = CSVLoader('../public/book/book_messy_data_number.csv')
messy_data.set_schema(schema)

improvements, error = messy_data.fix_number_error(
    column_list=['original_price', 'current_price'],
    formation=[('original_price', '123456'), ('current_price', '123456')],
    batch_size=100,
    few_shot_context=[
        ('1234.00', '1234'),
        ('135000,000', '135000'),
        ('4.00e+04', '40000'),
        ('9.90e+04', '99000')
    ]
)
print(len(improvements))
print(len(error))

messy_data.apply_improvements(improvements)
messy_data.data.to_csv('../public/book/book_messy_data_number_fixed.csv', index=False)

from benchmark.benchmark import benchmark_data_cleaning

result = benchmark_data_cleaning(
    clean_path="../public/book/book_messy_data_number_fixed.csv",
    messy_path="../public/book/book_messy_data_number.csv",
    cleaned_path="../public/book/small_book_data.csv",
)

print(f"Correction Rate: {result['correction_rate']:.2f}%")
print(f"Remaining Errors: {result['remaining_errors']}")
print(f"Corrected Errors: {result['corrected_errors']}")