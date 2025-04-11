import pandas

from benchmark.benchmark import benchmark_data_cleaning
from file_processing.csv import CSVLoader
from file_processing.generate_messy_data import make_dataset_messy




data = CSVLoader(
    filepath='public/economy_delivery_data/true_data_table.csv',
    name='true_data_table',
)

referencing_data = CSVLoader(
    filepath='public/economy_delivery_data/reference_data_value.csv',
    name='referencing_data',
)

schema = data.generate_schema(other_info=referencing_data.data.to_dict())

print(schema)

data1 = CSVLoader(
    filepath='public/economy_delivery_data/real_data_messy.csv',
    name='real_data_messy',
)

list_improvements = data1.fix_error_schema(schema=schema)

data1.apply_improvements(list_improvements)
# print(data1.data)
data1.data.to_csv('public/economy_delivery_data/messy_data1.csv', index=False)

result = benchmark_data_cleaning(
    clean_path="public/economy_delivery_data/real_data_generate.csv",
    messy_path="public/economy_delivery_data/real_data_messy.csv",
    cleaned_path="public/economy_delivery_data/messy_data1.csv",
)

print(f"Correction Rate: {result['correction_rate']:.2f}%")
print(f"Remaining Errors: {result['remaining_errors']}")
print(f"Corrected Errors: {result['corrected_errors']}")