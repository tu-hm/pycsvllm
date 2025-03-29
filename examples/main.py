import pandas

from benchmark.benchmark import benchmark_data_cleaning
from file_processing.csv import CSVLoader

data = CSVLoader(
    filepath='public/economy_delivery_data/reference_data.csv',
    name='true_data',
)

schema = data.generate_schema()

print(schema)

data1 = CSVLoader(
    filepath='public/economy_delivery_data/real_data_messy.csv',
    name='real_data_messy',
)

list_error = CSVLoader.validate_dataset(df=data1.data, schema=schema)
# print(list_error)
# print(data1._fix_error_for_item(schema=schema, list_items_to_fix=list_error[0:30]))
list_improvements = data1.fix_error_schema(schema=schema, list_items_to_fix=list_error)

data1.apply_improvements(list_improvements)
# print(data1.data)
data1.data.to_csv('public/economy_delivery_data/messy_data1.csv', index=False)

result = benchmark_data_cleaning(
    clean_path="public/economy_delivery_data/real_data.csv",
    messy_path="public/economy_delivery_data/real_data_messy.csv",
    cleaned_path="public/economy_delivery_data/messy_data1.csv",
)

print(f"Correction Rate: {result['correction_rate']:.2f}%")
print(f"Remaining Errors: {result['remaining_errors']}")
print(f"Corrected Errors: {result['corrected_errors']}")