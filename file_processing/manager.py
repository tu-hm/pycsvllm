from file_processing.csv import CSVLoader


class Manager:
    main_data_source: CSVLoader
    sub_data_source: CSVLoader

    def __init__(self):
        pass

    """
    init the main data source
    """
    def init_main_data_source(self, file_path: str, name: str):
        self.main_data_source = CSVLoader(filepath=file_path, name=name)

    def add_sub_data_source(self, file_path: str, name: str):
        self.sub_data_source = CSVLoader(filepath=file_path, name=name)