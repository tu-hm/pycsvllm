import pandas

from file_processing.csv import CSVLoader

data = CSVLoader(
    filepath='public/true_data.csv',
    name='true_data',
)

schema = data.generate_schema()

df = pandas.read_csv('public/messy_data.csv')
list_errors = CSVLoader.validate_dataset(df, schema)
print(list_errors)