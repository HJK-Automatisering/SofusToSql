"""
Sofus Match API Client - Reference Implementation

Requirements:
    pip install requests cryptography

Usage:
    client = SofusApiClient(
        base_url="https://match.sofus.dk",
        certificate_path="/path/to/oces3_certificate.pem",
        private_key_path="/path/to/private_key.pem",
    )

    # List organizations you have access to
    organizations = client.get_organizations()

    # Get management info for an organization
    for org in organizations:
        data = client.get_management_info(org["uuid"])
"""

import base64
from datetime import datetime, timedelta, timezone

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate


class SofusApiClient:
    """Client for the Sofus Match Management Info API.

    Authentication flow:
    1. Sign "{cvr}|{timestamp}" with your OCES3 certificate's private key
    2. POST to /api/v1/access_token with cvr, timestamp, and signature
    3. Receive a Bearer token (valid for 10 minutes)
    4. Use the Bearer token for subsequent API calls

    The certificate must be a Danish OCES3 certificate registered in Sofus
    by a super admin. The certificate grants access to specific organizations.
    """

    def __init__(self, base_url, certificate_path, private_key_path, private_key_password=None):
        self.base_url = base_url.rstrip("/")
        self.certificate_path = certificate_path
        self.private_key_path = private_key_path
        self.private_key_password = private_key_password
        self._access_token = None
        self._token_expires_at = None

        self._load_credentials()

    def _load_credentials(self):
        with open(self.certificate_path, "rb") as f:
            cert_pem = f.read()
            self.certificate = load_pem_x509_certificate(cert_pem)

        with open(self.private_key_path, "rb") as f:
            self.private_key = serialization.load_pem_private_key(
                f.read(),
                password=self.private_key_password.encode() if self.private_key_password else None,
            )

        # Extract CVR from certificate subject (organizationIdentifier field)
        for attr in self.certificate.subject:
            if attr.oid.dotted_string == "2.5.4.97":  # organizationIdentifier OID
                oid_value = attr.value
                # Format: "NTRDK-12345678"
                self.cvr = "".join(c for c in oid_value if c.isdigit())
                break
        else:
            raise ValueError(
                "Certificate does not contain organizationIdentifier (CVR)")

    def _sign(self, data):
        """Sign data with the private key using SHA256."""
        signature = self.private_key.sign(
            data.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("ascii")

    def _authenticate(self):
        """Exchange certificate signature for an access token."""
        timestamp = datetime.now(timezone.utc).isoformat()
        signed_data = f"{self.cvr}|{timestamp}"
        signature = self._sign(signed_data)

        response = requests.post(
            f"{self.base_url}/api/v1/access_token",
            json={
                "cvr": self.cvr,
                "timestamp": timestamp,
                "signature": signature,
            },
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 429:
            raise RateLimitError(
                "Rate limit exceeded. Max 30 requests per minute.")

        if response.status_code != 201:
            raise AuthenticationError(
                f"Authentication failed: HTTP {response.status_code}")

        data = response.json()
        self._access_token = data["access_token"]
        self._token_expires_at = datetime.fromisoformat(data["expires_at"])
        return self._access_token

    def _get_token(self):
        """Get a valid access token, refreshing if expired."""
        if self._access_token and self._token_expires_at:
            # Refresh 30 seconds before expiry
            expires_utc = self._token_expires_at.astimezone(timezone.utc)
            if datetime.now(timezone.utc) < expires_utc - timedelta(seconds=30):
                return self._access_token

        return self._authenticate()

    def _request(self, method, path, **kwargs):
        """Make an authenticated API request."""
        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            **kwargs.pop("headers", {}),
        }

        response = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            **kwargs,
        )

        if response.status_code == 401:
            # Token might have expired, retry once
            self._access_token = None
            token = self._get_token()
            headers["Authorization"] = f"Bearer {token}"
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                **kwargs,
            )

        response.raise_for_status()
        return response.json()

    def get_organizations(self):
        """List organizations the certificate has access to.

        Returns:
            list[dict]: Each with 'uuid' and 'name' keys.

        Example response:
            [
                {"uuid": "abc-123", "name": "Hjørring Kommune"},
                {"uuid": "def-456", "name": "Aalborg Kommune"}
            ]
        """
        return self._request("GET", "/api/v1/organizations")

    def get_management_info(self, organization_uuid, start_date=None, end_date=None):
        """Get management info for an organization.

        Args:
            organization_uuid: UUID of the organization (from get_organizations).
            start_date: Optional start date filter (YYYY-MM-DD). Only used for "social" type.
                Defaults to 1 year ago server-side.
            end_date: Optional end date filter (YYYY-MM-DD). Only used for "social" type.
                Defaults to today server-side.

        Returns:
            dict: Management info with 'metadata' and 'data' keys.

        For "match" type organizations (FFA), data includes:
            - children, admissions, families, appointments,
              remunerations, consultants, grants

        For "social" type organizations (contact persons), data includes:
            - children, admissions, periods, contact_persons, visitations

        Example:
            data = client.get_management_info("abc-123", start_date="2025-01-01")
            for child in data["data"]["children"]:
                print(f"{child['name']} (CPR: {child['cpr']})")
        """
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return self._request(
            "GET",
            f"/api/v1/organizations/{organization_uuid}/management_info",
            params=params,
        )


class AuthenticationError(Exception):
    pass


class RateLimitError(Exception):
    pass


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    client = SofusApiClient(
        base_url="https://match.sofus.dk",
        certificate_path="certificate.pem",
        private_key_path="private_key.pem",
    )

    print("=== Organizations ===")
    orgs = client.get_organizations()
    for org in orgs:
        print(f"  {org['name']} ({org['uuid']})")

    print()
    for org in orgs:
        print(f"=== Management Info: {org['name']} ===")
        info = client.get_management_info(org["uuid"])
        print(f"  Type: {info['metadata']['organization']['type']}")
        print(f"  Generated: {info['metadata']['generated_at']}")

        data = info["data"]
        if "children" in data:
            print(f"  Children: {len(data['children'])}")
        if "admissions" in data:
            print(f"  Admissions: {len(data['admissions'])}")
        print()
