from file_processing.csv import CSVLoader

data = CSVLoader(
    filepath='public/true_data.csv'
)

print(data.generate_schema())