import pandas

from file_processing.csv import CSVLoader

data = CSVLoader(
    filepath='public/economy_delivery_data/reference_data.csv',
    name='true_data',
)

schema = data.generate_schema()

data1 = CSVLoader(
    filepath='public/economy_delivery_data/real_data_messy.csv',
    name='real_data_messy',
)

list_improves = data1.scan_error(schema=schema, batch_size=30)
# print(list_improves)

data1.apply_improvements(list_improves)
# print(data1.data)
data1.data.to_csv('public/messy_data1.csv')

