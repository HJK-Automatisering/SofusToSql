import logging
import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine


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

        # username and password can be omitted if using trusted connection

        DB_CONNECTION_STRING = (
            f"mssql+pyodbc://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_DATABASE}"
            f"?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate={DB_TRUST_SERVER_CERT}"
        )

        return create_engine(DB_CONNECTION_STRING)

    @staticmethod
    def save_json_to_sql(json, db_engine) -> None:
        logging.info("Saving jobs to sql...")

        df = pd.json_normalize(json)
        result = df.to_sql(
            name="sofus", con=db_engine, if_exists="replace", index=False
        )

        if not result:
            raise Exception("Error saving to SQL")

        logging.info("Jobs saved")
