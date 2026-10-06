import base64

import requests


class ZatcaAPI:

    def __init__(self, environment="sandbox"):

        self.environment = environment

        if environment == "sandbox":
            self.base_url = (
                "https://gw-fatoora.zatca.gov.sa/"
                "e-invoicing/developer-portal"
            )

        elif environment == "simulation":
            self.base_url = (
                "https://gw-fatoora.zatca.gov.sa/"
                "e-invoicing/simulation"
            )

        elif environment == "production":
            self.base_url = (
                "https://gw-fatoora.zatca.gov.sa/"
                "e-invoicing/core"
            )

        else:
            raise ValueError(
                "Unknown ZATCA environment"
            )

    # =====================================================
    # الطلب العام
    # =====================================================

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

    # =====================================================
    # Compliance CSID
    #
    # POST /compliance
    # =====================================================

    def request_compliance_csid(
        self,
        csr,
        otp,
    ):

        if not csr:
            raise ValueError(
                "CSR غير موجود."
            )

        if not otp:
            raise ValueError(
                "OTP غير موجود."
            )

        endpoint = "/compliance"

        csr = str(csr).strip()

        csr_base64 = base64.b64encode(
            csr.encode("utf-8")
        ).decode("utf-8")

        headers = {
            "Accept": "application/json",
            "Accept-Version": "V2",
            "OTP": str(otp).strip(),
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

    # =====================================================
    # Production CSID
    #
    # POST /production/csid
    #
    # يحتاج Compliance CSID صالح
    # =====================================================

    def request_production_csid(
        self,
        current_csid,
        csr,
    ):

        if not current_csid:
            raise ValueError(
                "Compliance CSID غير موجود."
            )

        if not csr:
            raise ValueError(
                "CSR غير موجود."
            )

        endpoint = "/production/csids"

        csr = str(csr).strip()

        csr_base64 = base64.b64encode(
            csr.encode("utf-8")
        ).decode("utf-8")

        headers = {
            "Accept": "application/json",
            "Accept-Version": "V2",
            "currentCSID": str(
                current_csid
            ).strip(),
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