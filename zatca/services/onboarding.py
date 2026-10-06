import os
import uuid

from django.conf import settings

from zatca.models import ZatcaSettings
from company.models import CompanyInfo

from .api_client import ZatcaAPI
from .csr_generator import (
    generate_and_save_zatca_files,
)
from .key_manager import generate_public_key


def start_onboarding(company):

    # =====================================================
    # بيانات الشركة
    # =====================================================

    try:
        company_info = CompanyInfo.objects.get(
            company=company
        )

    except CompanyInfo.DoesNotExist:
        raise Exception(
            "بيانات الشركة غير موجودة."
        )

    # =====================================================
    # الرقم الضريبي
    # =====================================================

    tax_number = (
        company_info.tax_number or ""
    ).strip()

    if not tax_number:
        raise Exception(
            "الرقم الضريبي غير موجود."
        )

    # =====================================================
    # بيانات مطلوبة للـ CSR
    # =====================================================

    company_name = (
        company_info.name
        or company.name
        or ""
    ).strip()

    if not company_name:
        raise Exception(
            "اسم الشركة غير موجود."
        )

    organization_unit = (
        company_info.name
        or company.name
        or ""
    ).strip()

    location = (
        company_info.city
        or company_info.national_address
        or ""
    ).strip()

    if not location:
        raise Exception(
            "مدينة الشركة أو العنوان غير موجود."
        )

    industry = "Trading"

    # =====================================================
    # EGS Serial Number
    # =====================================================

    zatca_settings, created = (
        ZatcaSettings.objects.get_or_create(
            company=company
        )
    )

    if zatca_settings.device_uuid:
        device_uuid = zatca_settings.device_uuid

    else:
        device_uuid = str(
            uuid.uuid4()
        )

    egs_serial_number = (
        f"1-ERP|2-Django|3-{device_uuid}"
    )

    # =====================================================
    # إنشاء ملفات ZATCA
    # =====================================================

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

    # =====================================================
    # المسارات
    # =====================================================

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

    # =====================================================
    # إنشاء Public Key
    # =====================================================

    generate_public_key(
        private_key_path,
        public_key_path,
    )

    # =====================================================
    # قراءة محتوى الملفات
    # =====================================================

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

    # =====================================================
    # حفظ بيانات ZATCA
    # =====================================================

    zatca_settings.device_uuid = device_uuid
    zatca_settings.status = "csr_created"

    # =====================================================
    # حفظ المحتوى داخل قاعدة البيانات
    # =====================================================

    zatca_settings.private_key = (
        private_key_content
    )

    zatca_settings.csr = (
        csr_content
    )

    zatca_settings.public_key = (
        public_key_content
    )

    # =====================================================
    # حفظ المسارات
    # =====================================================

    zatca_settings.private_key_path = (
        private_key_path
    )

    zatca_settings.csr_path = (
        csr_path
    )

    zatca_settings.public_key_path = (
        public_key_path
    )

    zatca_settings.save()

    return zatca_settings


def complete_compliance(
    zatca_settings,
    otp,
):
    """
    إرسال CSR إلى ZATCA للحصول على Compliance CSID.
    """

    if not zatca_settings:
        raise Exception(
            "إعدادات ZATCA غير موجودة."
        )

    if not zatca_settings.csr:
        raise Exception(
            "CSR غير موجود."
        )

    if not otp:
        raise Exception(
            "OTP غير موجود."
        )

    # =====================================================
    # إنشاء عميل ZATCA
    # =====================================================

    api = ZatcaAPI(
        zatca_settings.environment
    )

    # =====================================================
    # إرسال طلب Compliance
    # =====================================================

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

    # =====================================================
    # التحقق من الاستجابة
    # =====================================================

    if status_code != 200:

        raise Exception(
            f"فشل طلب Compliance من ZATCA "
            f"(HTTP {status_code}): "
            f"{response_data}"
        )

    if not isinstance(
        response_data,
        dict,
    ):
        raise Exception(
            "استجابة ZATCA غير صحيحة."
        )

    # =====================================================
    # استخراج بيانات Compliance
    # =====================================================

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

    # =====================================================
    # التحقق من البيانات
    # =====================================================

    if not request_id:
        raise Exception(
            "استجابة ZATCA لا تحتوي على requestID."
        )

    if not binary_security_token:
        raise Exception(
            "استجابة ZATCA لا تحتوي على binarySecurityToken."
        )

    if not secret:
        raise Exception(
            "استجابة ZATCA لا تحتوي على secret."
        )

    # =====================================================
    # حفظ Compliance في الحقول الجديدة
    # =====================================================

    zatca_settings.compliance_request_id = (
        request_id
    )

    zatca_settings.compliance_binary_security_token = (
        binary_security_token
    )

    zatca_settings.compliance_secret = (
        secret
    )

    # =====================================================
    # الحفاظ على الحقول القديمة للتوافق
    # =====================================================

    zatca_settings.binary_security_token = (
        binary_security_token
    )

    zatca_settings.secret = (
        secret
    )

    zatca_settings.status = "compliance"

    zatca_settings.save()

    # =====================================================
    # إرجاع النتيجة
    # =====================================================

    return {
        "request_id": request_id,
        "binary_security_token": binary_security_token,
        "secret": secret,
        "disposition_message": disposition_message,
        "status": zatca_settings.status,
    }


def complete_production_csid(
    zatca_settings,
):
    """
    طلب Production CSID بعد نجاح Compliance.

    يستخدم Compliance CSID الموجود في:
    compliance_binary_security_token
    """

    if not zatca_settings:
        raise Exception(
            "إعدادات ZATCA غير موجودة."
        )

    # =====================================================
    # التحقق من Compliance CSID
    # =====================================================

    if not zatca_settings.compliance_binary_security_token:
        raise Exception(
            "Compliance CSID غير موجود."
        )

    # =====================================================
    # التحقق من CSR
    # =====================================================

    if not zatca_settings.csr:
        raise Exception(
            "CSR غير موجود."
        )

    # =====================================================
    # إنشاء عميل ZATCA
    # =====================================================

    api = ZatcaAPI(
        zatca_settings.environment
    )

    # =====================================================
    # إرسال طلب Production CSID
    # =====================================================

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

    # =====================================================
    # التحقق من الاستجابة
    # =====================================================

    if status_code != 200:

        raise Exception(
            f"فشل طلب Production CSID من ZATCA "
            f"(HTTP {status_code}): "
            f"{response_data}"
        )

    if not isinstance(
        response_data,
        dict,
    ):
        raise Exception(
            "استجابة Production CSID غير صحيحة."
        )

    # =====================================================
    # استخراج بيانات Production CSID
    # =====================================================

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

    # =====================================================
    # التحقق من البيانات
    # =====================================================

    if not production_security_token:
        raise Exception(
            "استجابة ZATCA لا تحتوي على Production CSID."
        )

    if not production_secret:
        raise Exception(
            "استجابة ZATCA لا تحتوي على Production Secret."
        )

    # =====================================================
    # حفظ Production CSID بشكل منفصل
    # =====================================================

    zatca_settings.production_request_id = (
        production_request_id
    )

    zatca_settings.production_binary_security_token = (
        production_security_token
    )

    zatca_settings.production_secret = (
        production_secret
    )

    # =====================================================
    # تحديث الحالة
    # =====================================================

    zatca_settings.status = "active"
    zatca_settings.is_enabled = True

    zatca_settings.save()

    # =====================================================
    # إرجاع النتيجة
    # =====================================================

    return {
        "request_id": production_request_id,
        "binary_security_token": (
            production_security_token
        ),
        "secret": production_secret,
        "disposition_message": disposition_message,
        "status": zatca_settings.status,
    }