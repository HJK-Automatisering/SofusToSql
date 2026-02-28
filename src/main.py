from database_handler import DatabaseHandler
from sofus_api_client import SofusApiClient
from dotenv import load_dotenv
import os
import logging


def main():
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    CERT_PASSWORD = os.getenv("CERT_PASSWORD")
    if not CERT_PASSWORD:
        raise Exception("CERT_PASSWORD not found in .env")

    client = SofusApiClient(
        base_url="https://match.sofus.dk",
        certificate_path="certs/public_cert.pem",
        private_key_path="certs/private_key.pem",
        private_key_password=CERT_PASSWORD,
    )

    orgs = client.get_organizations()
    orgs_info = [client.get_management_info(org["uuid"]) for org in orgs]

    db_engine = DatabaseHandler.get_db_engine()
    DatabaseHandler.save_organizations_to_sql(db_engine, orgs_info)


if __name__ == "__main__":
    main()
