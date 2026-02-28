import logging
import os
import re
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus


class DatabaseHandler:

    @staticmethod
    def get_db_engine():
        load_dotenv()

        DB_USERNAME = os.getenv("DB_USERNAME")
        DB_PASSWORD = os.getenv("DB_PASSWORD")
        DB_SERVER = os.getenv("DB_SERVER")
        DB_PORT = os.getenv("DB_PORT")
        DB_DATABASE = os.getenv("DB_DATABASE")
        DB_TRUST_SERVER_CERT = os.getenv("DB_TRUST_SERVER_CERT", "yes")

        if not DB_SERVER or not DB_PORT or not DB_DATABASE:
            raise Exception(
                "DB_SERVER, DB_PORT, DB_DATABASE not found in .env")

        encoded_password = quote_plus(DB_PASSWORD)

        DB_CONNECTION_STRING = (
            f"mssql+pyodbc://{DB_USERNAME}:{encoded_password}"
            f"@{DB_SERVER}:{DB_PORT}/{DB_DATABASE}"
            f"?driver=ODBC+Driver+18+for+SQL+Server"
            f"&TrustServerCertificate={DB_TRUST_SERVER_CERT}"
        )

        return create_engine(DB_CONNECTION_STRING)

    @staticmethod
    def save_organizations_to_sql(db_engine, organizations) -> None:
        logging.info("Saving organizations to sql...")

        for organization in organizations:
            match organization['metadata']['organization']['type']:
                case "social":
                    DatabaseHandler._upload_social_organization_(
                        db_engine, organization)
                case "match":
                    DatabaseHandler._upload_match_organization_(
                        db_engine, organization)
                case _:
                    raise Exception(
                        f"Unknown organization type: {organization['metadata']['organization']['type']}")

        logging.info("Organizations saved")

    @staticmethod
    def _upload_social_organization_(db_engine, organization):
        logging.info(
            f"Saving organization {organization['metadata']['organization']['name']} to sql...")

        org_name = DatabaseHandler._get_organization_table_name(organization)

        social_data_tables = ["children", "admissions",
                              "periods", "contact_persons", "visitations"]

        for table in social_data_tables:
            if table in organization["data"]:
                DatabaseHandler._normalize_and_upload(
                    db_engine, organization["data"][table], table, f"{table}_{org_name}")
            else:
                logging.warning(
                    f"No {table} data for organization {organization['metadata']['organization']['name']}")

        logging.info(
            f"Organization {organization['metadata']['organization']['name']} saved")

    @staticmethod
    def _upload_match_organization_(db_engine, organization):
        logging.info(
            f"Saving organization {organization['metadata']['organization']['name']} to sql...")

        org_name = DatabaseHandler._get_organization_table_name(organization)

        match_data_tables = ["children", "admissions", "families", "appointments",
                             "remunerations", "consultants", "grants"]

        for table in match_data_tables:
            if table in organization["data"]:
                DatabaseHandler._normalize_and_upload(
                    db_engine, organization["data"][table], table, f"{table}_{org_name}")
            else:
                logging.warning(
                    f"No {table} data for organization {organization['metadata']['organization']['name']}")

        logging.info(
            f"Organization {organization['metadata']['organization']['name']} saved")

    @staticmethod
    def _get_organization_table_name(organization):
        name = organization['metadata']['organization']['name']
        name = name.lower()
        name = name.replace(' ', '_')
        name = name.strip('_')

        return f"{organization['metadata']['organization']['type']}_{name}"

    @staticmethod
    def _normalize_and_upload(db_engine, data, data_name, table_name):
        logging.info(f"Saving {data_name} to sql...")

        df = pd.json_normalize(data)

        result = df.to_sql(name=table_name, con=db_engine,
                           if_exists="replace", index=False)

        if not result:
            raise Exception(f"Error saving {data_name} to SQL")

        logging.info(f"{data_name} saved")
