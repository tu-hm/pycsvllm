from file_processing.csv import CSVLoader
from llm_providers.prompts import find_simple_json_schema_message


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

    def init(self):
        if self.main_data_source.schema is None:
            self.main_data_source.set_schema()
        self.sub_data_source.set_schema(prompt=find_simple_json_schema_message)

