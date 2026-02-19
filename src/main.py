from sofus_api_client import SofusApiClient
import json
from dotenv import load_dotenv
import os


def main():
    load_dotenv()

    CERT_PASSWORD = os.getenv("CERT_PASSWORD")
    if not CERT_PASSWORD:
        raise Exception("CERT_PASSWORD not found in .env")

    client = SofusApiClient(
        base_url="https://match.sofus.dk",
        certificate_path="certs/public_cert.pem",
        private_key_path="certs/private_key.pem",
        private_key_password=CERT_PASSWORD,
    )

    # Temp code to inspect API responses
    print("=== Organizations ===")
    orgs = client.get_organizations()
    with open("organizations.json", "w") as f:
        json.dump(orgs, f, indent=2)
    for org in orgs:
        print(f"  {org['name']} ({org['uuid']})")

    print()
    for org in orgs:
        print(f"=== Management Info: {org['name']} ===")
        info = client.get_management_info(org["uuid"])
        with open(f"management_info_{org['uuid']}.json", "w") as f:
            json.dump(info, f, indent=2)
        print(f"  Type: {info['metadata']['organization']['type']}")
        print(f"  Generated: {info['metadata']['generated_at']}")

        data = info["data"]
        if "children" in data:
            print(f"  Children: {len(data['children'])}")
        if "admissions" in data:
            print(f"  Admissions: {len(data['admissions'])}")
        print()


if __name__ == "__main__":
    main()
