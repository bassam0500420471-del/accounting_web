import os

from cryptography import x509
from cryptography.x509.oid import NameOID, ObjectIdentifier
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


# =========================================================
# OIDs المستخدمة في CSR الخاص بـ ZATCA
# =========================================================

ORGANIZATION_IDENTIFIER_OID = ObjectIdentifier(
    "2.5.4.97"
)

EGS_SERIAL_OID = ObjectIdentifier(
    "2.5.4.4"
)

USER_ID_OID = ObjectIdentifier(
    "0.9.2342.19200300.100.1.1"
)

INVOICE_TYPE_OID = ObjectIdentifier(
    "2.5.4.12"
)

REGISTERED_ADDRESS_OID = ObjectIdentifier(
    "2.5.4.26"
)

BUSINESS_CATEGORY_OID = ObjectIdentifier(
    "2.5.4.15"
)

CERTIFICATE_TEMPLATE_OID = ObjectIdentifier(
    "1.3.6.1.4.1.311.20.2"
)


# =========================================================
# إنشاء ECC Private Key
# =========================================================

def generate_private_key():
    """
    إنشاء مفتاح خاص ECC باستخدام secp256k1
    وفق متطلبات ZATCA.
    """

    return ec.generate_private_key(
        ec.SECP256K1()
    )
# =========================================================
# إنشاء DER PrintableString
# =========================================================

def _der_printable_string(value):
    """
    تحويل النص إلى ASN.1 PrintableString بصيغة DER.
    """

    data = value.encode("ascii")

    length = len(data)

    if length < 128:
        length_bytes = bytes([length])

    else:
        length_bytes = bytes(
            [0x80 | ((length.bit_length() + 7) // 8)]
        ) + length.to_bytes(
            (length.bit_length() + 7) // 8,
            "big",
        )

    return (
        b"\x13"
        + length_bytes
        + data
    )


# =========================================================
# إنشاء CSR
# =========================================================

def generate_csr(
    private_key,
    company_name,
    common_name,
    vat_number,
    organization_unit,
    country="SA",
    invoice_type="1100",
    location="",
    industry="",
    egs_serial_number="",
    certificate_template="PREZATCA-Code-Signing",
):
    """
    إنشاء CSR متوافق مع متطلبات ZATCA.

    الحقول الأساسية:

    CN
        اسم / معرف Solution Unit

    O
        اسم المكلف / الشركة

    OU
        اسم الفرع / الوحدة التنظيمية

    C
        SA

    organizationIdentifier
        الرقم الضريبي

    SAN DirectoryName
        EGS Serial Number
        VAT Number
        Invoice Type
        Location
        Industry
    """

    # =====================================================
    # التحقق من الرقم الضريبي
    # =====================================================

    if not vat_number:
        raise ValueError(
            "الرقم الضريبي مطلوب لإنشاء CSR."
        )

    vat_number = str(
        vat_number
    ).strip()

    if len(vat_number) != 15:
        raise ValueError(
            "الرقم الضريبي يجب أن يكون 15 رقمًا."
        )

    if not vat_number.isdigit():
        raise ValueError(
            "الرقم الضريبي يجب أن يحتوي على أرقام فقط."
        )

    if (
        not vat_number.startswith("3")
        or not vat_number.endswith("3")
    ):
        raise ValueError(
            "الرقم الضريبي يجب أن يبدأ بالرقم 3 وينتهي بالرقم 3."
        )

    # =====================================================
    # التحقق من EGS Serial Number
    # =====================================================

    if not egs_serial_number:
        raise ValueError(
            "EGS Serial Number مطلوب لإنشاء CSR."
        )

    egs_serial_number = str(
        egs_serial_number
    ).strip()

    serial_parts = egs_serial_number.split("|")

    if len(serial_parts) != 3:
        raise ValueError(
            "EGS Serial Number يجب أن يكون بالشكل: "
            "1-Manufacturer|2-Model|3-SerialNumber"
        )

    for part, prefix in zip(
        serial_parts,
        ("1-", "2-", "3-"),
    ):
        if not part.startswith(prefix):
            raise ValueError(
                "EGS Serial Number يجب أن يكون بالشكل: "
                "1-Manufacturer|2-Model|3-SerialNumber"
            )

        if not part[len(prefix):].strip():
            raise ValueError(
                "بيانات EGS Serial Number غير مكتملة."
            )

    # =====================================================
    # التحقق من Organization Unit
    # =====================================================

    if not organization_unit:
        raise ValueError(
            "Organization Unit مطلوب لإنشاء CSR."
        )

    organization_unit = str(
        organization_unit
    ).strip()

    # =====================================================
    # التحقق من الدولة
    # =====================================================

    if country != "SA":
        raise ValueError(
            "رمز الدولة يجب أن يكون SA."
        )

    # =====================================================
    # التحقق من Invoice Type
    # =====================================================

    if (
        len(invoice_type) != 4
        or not invoice_type.isdigit()
        or any(
            digit not in "01"
            for digit in invoice_type
        )
    ):
        raise ValueError(
            "Invoice Type يجب أن يكون 4 أرقام من 0 و1 مثل 1100."
        )

    # =====================================================
    # التحقق من Location
    # =====================================================

    if not location:
        raise ValueError(
            "Location مطلوب لإنشاء CSR."
        )

    location = str(
        location
    ).strip()

    # =====================================================
    # التحقق من Industry
    # =====================================================

    if not industry:
        raise ValueError(
            "Industry مطلوب لإنشاء CSR."
        )

    industry = str(
        industry
    ).strip()

    # =====================================================
    # التحقق من اسم الشركة
    # =====================================================

    if not company_name:
        raise ValueError(
            "اسم الشركة مطلوب لإنشاء CSR."
        )

    # =====================================================
    # التحقق من Common Name
    # =====================================================

    if not common_name:
        raise ValueError(
            "Common Name مطلوب لإنشاء CSR."
        )

    # =====================================================
    # التحقق من Certificate Template
    # =====================================================

    allowed_templates = {
        "PREZATCA-Code-Signing",
        "ZATCA-Code-Signing",
        "TSTZATCA-Code-Signing",
    }

    if certificate_template not in allowed_templates:
        raise ValueError(
            "Certificate Template غير صحيح."
        )

    # =====================================================
    # Subject
    # =====================================================

    subject = x509.Name(
        [
            x509.NameAttribute(
                NameOID.COMMON_NAME,
                str(common_name).strip(),
            ),

            x509.NameAttribute(
                ORGANIZATION_IDENTIFIER_OID,
                vat_number,
            ),

            x509.NameAttribute(
                NameOID.ORGANIZATIONAL_UNIT_NAME,
                organization_unit,
            ),

            x509.NameAttribute(
                NameOID.ORGANIZATION_NAME,
                str(company_name).strip(),
            ),

            x509.NameAttribute(
                NameOID.COUNTRY_NAME,
                country,
            ),
        ]
    )

    # =====================================================
    # Subject Alternative Name
    #
    # ZATCA يستخدم DirectoryName داخل SAN
    # =====================================================

    san_name = x509.Name(
        [
            x509.NameAttribute(
                EGS_SERIAL_OID,
                egs_serial_number,
            ),

            x509.NameAttribute(
                USER_ID_OID,
                vat_number,
            ),

            x509.NameAttribute(
                INVOICE_TYPE_OID,
                invoice_type,
            ),

            x509.NameAttribute(
                REGISTERED_ADDRESS_OID,
                location,
            ),

            x509.NameAttribute(
                BUSINESS_CATEGORY_OID,
                industry,
            ),
        ]
    )

    # =====================================================
    # بناء CSR
    # =====================================================

    csr_builder = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(subject)
    )

    # =====================================================
    # إضافة SAN
    # =====================================================

    csr_builder = csr_builder.add_extension(
        x509.SubjectAlternativeName(
            [
                x509.DirectoryName(
                    san_name
                )
            ]
        ),
        critical=False,
    )

    # =====================================================
    # Certificate Template Name
    #
    # OID:
    # 1.3.6.1.4.1.311.20.2
    # =====================================================

    csr_builder = csr_builder.add_extension(
        x509.UnrecognizedExtension(
            CERTIFICATE_TEMPLATE_OID,
            _der_printable_string(
                certificate_template
            ),
        ),
        critical=False,
    )

    # =====================================================
    # توقيع CSR
    # =====================================================

    csr = csr_builder.sign(
        private_key,
        hashes.SHA256(),
    )

    return csr


# =========================================================
# حفظ Private Key
# =========================================================

def save_private_key(
    private_key,
    path,
):
    """
    حفظ المفتاح الخاص بصيغة PEM.
    """

    with open(
        path,
        "wb",
    ) as f:

        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )


# =========================================================
# حفظ CSR
# =========================================================

def save_csr(
    csr,
    path,
):
    """
    حفظ CSR بصيغة PEM.
    """

    with open(
        path,
        "wb",
    ) as f:

        f.write(
            csr.public_bytes(
                serialization.Encoding.PEM
            )
        )


# =========================================================
# إنشاء وحفظ ملفات ZATCA
# =========================================================

def generate_and_save_zatca_files(
    company_id,
    company_name,
    common_name,
    vat_number,
    commercial_number=None,
    media_root=None,
    organization_unit=None,
    country="SA",
    invoice_type="1100",
    location=None,
    industry=None,
    egs_serial_number=None,
    certificate_template="PREZATCA-Code-Signing",
):
    """
    إنشاء وحفظ Private Key و CSR الخاصين بـ ZATCA.
    """

    if not media_root:
        raise ValueError(
            "MEDIA_ROOT غير محدد."
        )

    if not organization_unit:
        organization_unit = company_name

    if not location:
        raise ValueError(
            "Location مطلوب."
        )

    if not industry:
        raise ValueError(
            "Industry مطلوب."
        )

    if not egs_serial_number:
        raise ValueError(
            "EGS Serial Number مطلوب."
        )

    # =====================================================
    # مجلد الشركة
    # =====================================================

    zatca_path = os.path.join(
        media_root,
        "zatca",
        f"company_{company_id}",
    )

    os.makedirs(
        zatca_path,
        exist_ok=True,
    )

    # =====================================================
    # إنشاء المفتاح
    # =====================================================

    private_key = generate_private_key()

    # =====================================================
    # إنشاء CSR
    # =====================================================

    csr = generate_csr(
        private_key=private_key,
        company_name=company_name,
        common_name=common_name,
        vat_number=vat_number,
        organization_unit=organization_unit,
        country=country,
        invoice_type=invoice_type,
        location=location,
        industry=industry,
        egs_serial_number=egs_serial_number,
        certificate_template=certificate_template,
    )

    # =====================================================
    # المسارات
    # =====================================================

    private_key_path = os.path.join(
        zatca_path,
        "private_key.pem",
    )

    csr_path = os.path.join(
        zatca_path,
        "csr.pem",
    )

    # =====================================================
    # الحفظ
    # =====================================================

    save_private_key(
        private_key,
        private_key_path,
    )

    save_csr(
        csr,
        csr_path,
    )

    return {
        "private_key_path": private_key_path,
        "csr_path": csr_path,
    }