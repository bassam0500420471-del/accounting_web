import uuid
import os

from django.conf import settings

from zatca.models import ZatcaSettings
from company.models import CompanyInfo

from .csr_generator import (
    generate_and_save_zatca_files,
)

from .key_manager import generate_public_key


def start_onboarding(company):

    try:
        company_info = CompanyInfo.objects.get(
            company=company
        )
    except CompanyInfo.DoesNotExist:
        raise Exception(
            "بيانات الشركة غير موجودة"
        )

    if not company_info.tax_number:
        raise Exception(
            "الرقم الضريبي غير موجود"
        )

    device_uuid = str(uuid.uuid4())

    files = generate_and_save_zatca_files(
        company_id=company.id,
        company_name=company_info.name,
        common_name=company_info.tax_number,
        vat_number=company_info.tax_number,
        commercial_number=company_info.commercial_number,
        media_root=settings.MEDIA_ROOT,
    )

    private_key_path = files["private_key_path"]

    csr_path = files["csr_path"]

    public_key_path = os.path.join(
        os.path.dirname(private_key_path),
        "public_key.pem"
    )


    generate_public_key(
        private_key_path,
        public_key_path
    )


    zatca_settings, created = ZatcaSettings.objects.get_or_create(
        company=company
    )

    zatca_settings.device_uuid = device_uuid

    zatca_settings.status = "csr_created"

    # حفظ محتوى/مسارات الملفات
    zatca_settings.private_key = private_key_path
    zatca_settings.csr = csr_path
    zatca_settings.public_key = public_key_path

    # حفظ المسارات في الحقول الجديدة
    zatca_settings.private_key_path = private_key_path
    zatca_settings.csr_path = csr_path
    zatca_settings.public_key_path = public_key_path

    zatca_settings.save()

    return zatca_settings