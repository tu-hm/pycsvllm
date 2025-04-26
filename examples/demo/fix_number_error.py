from src.file_processing.csv import CSVLoader


original_data = CSVLoader('../public/book/small_book_data.csv')
schema = original_data.generate_schema().json_schema

messy_data = CSVLoader('../public/book/book_messy_data_number.csv')
messy_data.set_schema(schema)

improvements, error = messy_data.fix_number_error(
    column_list=['original_price', 'current_price'],
    formation=[('original_price', '123456')],
    batch_size=80,
    few_shot_context=[
        ('1234.00', '1234'),
        ('1,234.00', '1234'),
        ('4.00e+04', '40000')
    ]
)
print(len(improvements))

messy_data.apply_improvements(improvements)
messy_data.data.to_csv('../public/book/book_messy_data_number_fixed.csv', index=False)