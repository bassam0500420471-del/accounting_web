import requests
import base64
from django.conf import settings


class ZatcaAPI:

    def __init__(self, environment="sandbox"):
        self.environment = environment

        if environment == "sandbox":
            self.base_url = (
                "https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal"
            )

        elif environment == "simulation":
            self.base_url = (
                "https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation"
            )

        elif environment == "production":
            self.base_url = (
                "https://gw-fatoora.zatca.gov.sa/e-invoicing/core"
            )

        else:
            raise ValueError("Unknown ZATCA environment")


    def request(
        self,
        method,
        endpoint,
        headers=None,
        data=None,
    ):

        if headers is None:
            headers = {}

        url = self.base_url + endpoint

        print("URL:", url)
        print("HEADERS:", headers)

        response = requests.request(
            method,
            url,
            headers=headers,
            json=data,
            timeout=30,
        )

        try:
            response_data = response.json()

        except ValueError:
            response_data = response.text

        return {
            "status_code": response.status_code,
            "response": response_data,
        }


    def request_compliance_csid(
        self,
        csr,
        otp,
    ):

        endpoint = "/compliance"

        csr_base64 = base64.b64encode(
            csr.encode("utf-8")
        ).decode("utf-8")

        headers = {
            "accept": "application/json",
            "Accept-Version": "V2",
            "OTP": str(otp),
            "Content-Type": "application/json",
        }

        data = {
            "csr": csr_base64,
        }

        return self.request(
            method="POST",
            endpoint=endpoint,
            headers=headers,
            data=data,
        )