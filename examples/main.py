import pandas

from file_processing.csv import CSVLoader

data = CSVLoader(
    filepath='public/true_data.csv',
    name='true_data',
)

schema = data.generate_schema()

data1 = CSVLoader(
    filepath='public/messy_data.csv',
    name='messy_data',
)

list_improves = data1.scan_error(schema=schema)
print(list_improves)

data1.apply_improvements(list_improves)
print(data1.data)
data1.data.to_csv('public/messy_data1.csv')