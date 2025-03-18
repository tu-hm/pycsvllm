from sqlalchemy import create_engine, Column, Integer, String, Text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pandas as pd

Base = declarative_base()


class SQLiteProcessor:
    def __init__(self, database_name, table_name, columns=None):
        self.database_name = database_name
        self.table_name = table_name
        self.engine = create_engine(f'sqlite:///{self.database_name}')
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Dynamically create table model if it doesn't exist
        if not inspect(self.engine).has_table(self.table_name):
            self._create_table_model(columns)
            Base.metadata.create_all(self.engine)

    def _create_table_model(self, columns):
        """Dynamically create SQLAlchemy model class"""
        attrs = {
            '__tablename__': self.table_name,
            'id': Column(Integer, primary_key=True)
        }

        # Add columns from input (example implementation)
        # You would need to implement proper column type handling
        if columns:
            for col_name, col_type in columns.items():
                attrs[col_name] = Column(col_type)

        self.TableModel = type(
            f'Dynamic{self.table_name.capitalize()}',
            (Base,),
            attrs
        )

    def import_from_pandas(self, df, if_exists='replace'):
        """Import data from pandas DataFrame"""
        df.to_sql(
            name=self.table_name,
            con=self.engine,
            if_exists=if_exists,
            index=False
        )

    def export_to_pandas(self):
        """Export table to pandas DataFrame"""
        return pd.read_sql_table(self.table_name, self.engine)

    def query(self, filter_dict=None):
        """Safe query using SQLAlchemy ORM"""
        query = self.session.query(self.TableModel)
        if filter_dict:
            for key, value in filter_dict.items():
                query = query.filter(getattr(self.TableModel, key) == value)
        return query.all()

    def update(self, filter_dict, update_dict):
        """Safe update using SQLAlchemy ORM"""
        records = self.query(filter_dict)
        for record in records:
            for key, value in update_dict.items():
                setattr(record, key, value)
        self.session.commit()

    def insert(self, data_dict):
        """Safe insert using SQLAlchemy ORM"""
        new_record = self.TableModel(**data_dict)
        self.session.add(new_record)
        self.session.commit()

    def delete(self, filter_dict):
        """Safe delete using SQLAlchemy ORM"""
        records = self.query(filter_dict)
        for record in records:
            self.session.delete(record)
        self.session.commit()

    def close(self):
        """Close the connection"""
        self.session.close()
        self.engine.dispose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
