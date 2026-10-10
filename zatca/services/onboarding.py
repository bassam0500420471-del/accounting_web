import os
import uuid

from django.conf import settings

from zatca.models import ZatcaSettings
from company.models import CompanyInfo

from .api_client import ZatcaAPI
from .csr_generator import generate_and_save_zatca_files
from .key_manager import generate_public_key

def start_onboarding(company):


    try:
        company_info = CompanyInfo.objects.get(
            company=company
        )
    except CompanyInfo.DoesNotExist:
        raise Exception(
            "ط¨ظٹط§ظ†ط§طھ ط§ظ„ط´ط±ظƒط© ط؛ظٹط± ظ…ظˆط¬ظˆط¯ط©."
        )

    zatca_settings, created = (
        ZatcaSettings.objects.get_or_create(
            company=company
        )
    )

    if zatca_settings.csr:

        if not zatca_settings.device_uuid:
            zatca_settings.device_uuid = str(
                uuid.uuid4()
            )

            zatca_settings.save(
                update_fields=[
                    "device_uuid",
                    "updated_at",
                ]
            )

        return zatca_settings

    tax_number = (
        company.vat_no or ""
    ).strip()

    if not tax_number:
        raise Exception(
            "ط§ظ„ط±ظ‚ظ… ط§ظ„ط¶ط±ظٹط¨ظٹ ط؛ظٹط± ظ…ظˆط¬ظˆط¯ ظپظٹ ط¨ظٹط§ظ†ط§طھ ط§ظ„ط´ط±ظƒط©."
        )

    company_name = (
        company_info.name
        or company.name
        or ""
    ).strip()

    if not company_name:
        raise Exception(
            "ط§ط³ظ… ط§ظ„ط´ط±ظƒط© ط؛ظٹط± ظ…ظˆط¬ظˆط¯."
        )

    organization_unit = (
        company_info.name
        or company.name
        or ""
    ).strip()

    if not organization_unit:
        raise Exception(
            "Organization Unit ط؛ظٹط± ظ…ظˆط¬ظˆط¯."
        )

    location = (
        company_info.city
        or company_info.national_address
        or ""
    ).strip()

    if not location:
        raise Exception(
            "ظ…ط¯ظٹظ†ط© ط§ظ„ط´ط±ظƒط© ط£ظˆ ط§ظ„ط¹ظ†ظˆط§ظ† ط؛ظٹط± ظ…ظˆط¬ظˆط¯."
        )

    industry = "Trading"

    if zatca_settings.device_uuid:
        device_uuid = (
            zatca_settings.device_uuid
        )
    else:
        device_uuid = str(
            uuid.uuid4()
        )

        zatca_settings.device_uuid = (
            device_uuid
        )

        zatca_settings.save(
            update_fields=[
                "device_uuid",
                "updated_at",
            ]
        )

    egs_serial_number = (
        f"1-ERP|2-Django|3-{device_uuid}"
    )

    files = generate_and_save_zatca_files(
        company_id=company.id,
        company_name=company_name,
        common_name=tax_number,
        vat_number=tax_number,
        commercial_number=company_info.commercial_number,
        media_root=settings.MEDIA_ROOT,
        organization_unit=organization_unit,
        country="SA",
        invoice_type="1100",
        location=location,
        industry=industry,
        egs_serial_number=egs_serial_number,
        certificate_template="PREZATCA-Code-Signing",
    )

    private_key_path = files[
        "private_key_path"
    ]

    csr_path = files[
        "csr_path"
    ]

    public_key_path = os.path.join(
        os.path.dirname(
            private_key_path
        ),
        "public_key.pem",
    )

    generate_public_key(
        private_key_path,
        public_key_path,
    )

    with open(
        private_key_path,
        "r",
        encoding="utf-8",
    ) as f:
        private_key_content = f.read()

    with open(
        csr_path,
        "r",
        encoding="utf-8",
    ) as f:
        csr_content = f.read()

    with open(
        public_key_path,
        "r",
        encoding="utf-8",
    ) as f:
        public_key_content = f.read()

    zatca_settings.device_uuid = (
        device_uuid
    )

    zatca_settings.status = (
        "csr_created"
    )

    zatca_settings.private_key = (
        private_key_content
    )

    zatca_settings.csr = (
        csr_content
    )

    zatca_settings.public_key = (
        public_key_content
    )

    zatca_settings.private_key_path = (
        private_key_path
    )

    zatca_settings.csr_path = (
        csr_path
    )

    zatca_settings.public_key_path = (
        public_key_path
    )

    zatca_settings.is_enabled = False

    zatca_settings.save()

    return zatca_settings

def complete_compliance(
    zatca_settings,
    otp,
    ):

    """
    ط¥ط±ط³ط§ظ„ CSR ط¥ظ„ظ‰ ZATCA ظ„ظ„ط­طµظˆظ„ ط¹ظ„ظ‰ Compliance CSID.
    """

    if not zatca_settings:
        raise Exception(
            "ط¥ط¹ط¯ط§ط¯ط§طھ ZATCA ط؛ظٹط± ظ…ظˆط¬ظˆط¯ط©."
        )

    if not zatca_settings.csr:
        raise Exception(
            "CSR ط؛ظٹط± ظ…ظˆط¬ظˆط¯."
        )

    if not otp:
        raise Exception(
            "OTP ط؛ظٹط± ظ…ظˆط¬ظˆط¯."
        )

    api = ZatcaAPI(
        zatca_settings.environment
    )

    result = api.request_compliance_csid(
        csr=zatca_settings.csr,
        otp=otp,
    )

    status_code = result.get(
        "status_code"
    )

    response_data = result.get(
        "response"
    )

    if status_code != 200:
        raise Exception(
            f"ظپط´ظ„ ط·ظ„ط¨ Compliance ظ…ظ† ZATCA "
            f"(HTTP {status_code}): "
            f"{response_data}"
        )

    if not isinstance(
        response_data,
        dict,
    ):
        raise Exception(
            "ط§ط³طھط¬ط§ط¨ط© ZATCA ط؛ظٹط± طµط­ظٹط­ط©."
        )

    request_id = response_data.get(
        "requestID"
    )

    binary_security_token = (
        response_data.get(
            "binarySecurityToken"
        )
    )

    secret = response_data.get(
        "secret"
    )

    disposition_message = (
        response_data.get(
            "dispositionMessage"
        )
    )

    if not request_id:
        raise Exception(
            "ط§ط³طھط¬ط§ط¨ط© ZATCA ظ„ط§ طھط­طھظˆظٹ ط¹ظ„ظ‰ requestID."
        )

    if not binary_security_token:
        raise Exception(
            "ط§ط³طھط¬ط§ط¨ط© ZATCA ظ„ط§ طھط­طھظˆظٹ ط¹ظ„ظ‰ binarySecurityToken."
        )

    if not secret:
        raise Exception(
            "ط§ط³طھط¬ط§ط¨ط© ZATCA ظ„ط§ طھط­طھظˆظٹ ط¹ظ„ظ‰ secret."
        )

    zatca_settings.compliance_request_id = (
        request_id
    )

    zatca_settings.compliance_binary_security_token = (
        binary_security_token
    )

    zatca_settings.compliance_secret = (
        secret
    )

    zatca_settings.binary_security_token = (
        binary_security_token
    )

    zatca_settings.secret = (
        secret
    )

    zatca_settings.status = (
        "compliance"
    )

    zatca_settings.is_enabled = False

    zatca_settings.save()

    return {
        "request_id": request_id,
        "binary_security_token": (
            binary_security_token
        ),
        "secret": secret,
        "disposition_message": (
            disposition_message
        ),
        "status": zatca_settings.status,
    }

def complete_production_csid(
    zatca_settings,
    ):

    """
    ط·ظ„ط¨ Production CSID ط¨ط¹ط¯ ظ†ط¬ط§ط­ Compliance.

    ظٹط³طھط®ط¯ظ… Compliance CSID ط§ظ„ظ…ظˆط¬ظˆط¯ ظپظٹ:
    compliance_binary_security_token
    """

    if not zatca_settings:
        raise Exception(
            "ط¥ط¹ط¯ط§ط¯ط§طھ ZATCA ط؛ظٹط± ظ…ظˆط¬ظˆط¯ط©."
        )

    if not zatca_settings.compliance_binary_security_token:
        raise Exception(
            "Compliance CSID ط؛ظٹط± ظ…ظˆط¬ظˆط¯."
        )

    if not zatca_settings.csr:
        raise Exception(
            "CSR ط؛ظٹط± ظ…ظˆط¬ظˆط¯."
        )

    api = ZatcaAPI(
        zatca_settings.environment
    )

    result = api.request_production_csid(
        current_csid=(
            zatca_settings.compliance_binary_security_token
        ),
        csr=zatca_settings.csr,
    )

    status_code = result.get(
        "status_code"
    )

    response_data = result.get(
        "response"
    )

    if status_code != 200:
        raise Exception(
            f"ظپط´ظ„ ط·ظ„ط¨ Production CSID ظ…ظ† ZATCA "
            f"(HTTP {status_code}): "
            f"{response_data}"
        )

    if not isinstance(
        response_data,
        dict,
    ):
        raise Exception(
            "ط§ط³طھط¬ط§ط¨ط© Production CSID ط؛ظٹط± طµط­ظٹط­ط©."
        )

    production_request_id = (
        response_data.get(
            "requestID"
        )
    )

    production_security_token = (
        response_data.get(
            "binarySecurityToken"
        )
    )

    production_secret = (
        response_data.get(
            "secret"
        )
    )

    disposition_message = (
        response_data.get(
            "dispositionMessage"
        )
    )

    if not production_request_id:
        raise Exception(
            "ط§ط³طھط¬ط§ط¨ط© ZATCA ظ„ط§ طھط­طھظˆظٹ ط¹ظ„ظ‰ Production requestID."
        )

    if not production_security_token:
        raise Exception(
            "ط§ط³طھط¬ط§ط¨ط© ZATCA ظ„ط§ طھط­طھظˆظٹ ط¹ظ„ظ‰ Production CSID."
        )

    if not production_secret:
        raise Exception(
            "ط§ط³طھط¬ط§ط¨ط© ZATCA ظ„ط§ طھط­طھظˆظٹ ط¹ظ„ظ‰ Production Secret."
        )

    zatca_settings.production_request_id = (
        production_request_id
    )

    zatca_settings.production_binary_security_token = (
        production_security_token
    )

    zatca_settings.production_secret = (
        production_secret
    )

    zatca_settings.status = (
        "active"
    )

    zatca_settings.is_enabled = True

    zatca_settings.save()

    return {
        "request_id": production_request_id,
        "binary_security_token": (
            production_security_token
        ),
        "secret": production_secret,
        "disposition_message": (
            disposition_message
        ),
        "status": zatca_settings.status,
    }
