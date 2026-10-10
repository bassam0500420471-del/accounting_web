"""
ZATCA XML Signature Service
===========================

مسؤول عن إنشاء التوقيع الرقمي المتوافق مع متطلبات ZATCA
للفواتير الإلكترونية.

التسلسل الذي ينفذه هذا الملف:

1. تجهيز نسخة الفاتورة الخاصة بحساب Invoice Hash.
2. حساب SHA-256 + Base64 للـ Invoice Hash.
3. توقيع Invoice Hash باستخدام ECDSA.
4. حساب SHA-256 للشهادة الرقمية.
5. إنشاء XAdES SignedProperties.
6. حساب Hash لـ SignedProperties.
7. إنشاء XMLDSig SignedInfo.
8. إنشاء ECDSA XML Signature.
9. وضع التوقيع داخل UBLDocumentSignatures.
10. إضافة X509Certificate داخل KeyInfo.
11. التحقق محليًا من البنية والتوقيع.

مهم:
- هذا الملف لا يرسل الفاتورة إلى ZATCA.
- هذا الملف لا يبني QR النهائي.
- هذا الملف لا ينشئ CSR.
- هذا الملف مسؤول عن التوقيع فقط.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from lxml import etree


# =========================================================
# Namespaces
# =========================================================

DS_NS = "http://www.w3.org/2000/09/xmldsig#"

XADES_NS = "http://uri.etsi.org/01903/v1.3.2"

EXT_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:"
    "CommonExtensionComponents-2"
)

SIG_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:"
    "CommonSignatureComponents-2"
)

SAC_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:"
    "SignatureAggregateComponents-2"
)

# بعض تطبيقات UBL تستخدم CommonSignatureAggregateComponents-2.
# ZATCA XPath المنشور يستخدم sac:SignatureInformation.
# لذلك نستخدم namespace الصحيح الخاص بـ SignatureAggregateComponents.
SAC_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:"
    "SignatureAggregateComponents-2"
)

CBC_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:"
    "CommonBasicComponents-2"
)

CAC_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:"
    "CommonAggregateComponents-2"
)


NSMAP = {
    "ds": DS_NS,
    "xades": XADES_NS,
    "ext": EXT_NS,
    "sig": SIG_NS,
    "sac": SAC_NS,
    "cbc": CBC_NS,
    "cac": CAC_NS,
}


# =========================================================
# XML helpers
# =========================================================

XMLInput = Union[
    str,
    bytes,
    etree._Element,
    etree._ElementTree,
]


def _parse_xml(xml: XMLInput) -> etree._Element:
    """
    تحويل XML إلى lxml Element.

    يتم تعطيل external entities والشبكة لمنع XXE
    وأي تحميل خارجي غير مطلوب.
    """

    if isinstance(xml, etree._ElementTree):
        return xml.getroot()

    if isinstance(xml, etree._Element):
        return xml

    if isinstance(xml, str):
        xml = xml.encode("utf-8")

    if isinstance(xml, bytes):
        parser = etree.XMLParser(
            resolve_entities=False,
            no_network=True,
            remove_blank_text=False,
            huge_tree=False,
        )

        return etree.fromstring(
            xml,
            parser=parser,
        )

    raise TypeError(
        "xml must be str, bytes, lxml Element, or ElementTree"
    )


def _read_file(path: Union[str, Path]) -> bytes:
    """
    قراءة ملف Binary.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {path}"
        )

    return path.read_bytes()


# =========================================================
# Namespace helpers
# =========================================================

def _qname(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _local_name(element: etree._Element) -> str:
    return etree.QName(element).localname


# =========================================================
# Signature discovery
# =========================================================

def _find_signature(
    root: etree._Element,
) -> etree._Element | None:
    """
    البحث عن ds:Signature داخل UBLDocumentSignatures.
    """

    signatures = root.xpath(
        ".//*[local-name()='UBLDocumentSignatures']"
        "//*[local-name()='Signature']"
    )

    if signatures:
        return signatures[0]

    # fallback
    signatures = root.xpath(
        ".//*[local-name()='Signature']"
    )

    return signatures[0] if signatures else None


def _remove_existing_signature(
    root: etree._Element,
) -> None:
    """
    حذف أي توقيع سابق.

    مهم جدًا لأن وجود Signature قد يغير Invoice Hash.
    """

    signatures = root.xpath(
        ".//*[local-name()='Signature']"
    )

    for signature in signatures:
        parent = signature.getparent()

        if parent is not None:
            parent.remove(signature)


# =========================================================
# QR reference handling
# =========================================================

def _is_qr_reference(
    element: etree._Element,
) -> bool:
    """
    تحديد AdditionalDocumentReference الخاص بالـ QR.
    """

    if _local_name(element) != "AdditionalDocumentReference":
        return False

    ids = element.xpath(
        "./*[local-name()='ID']/text()"
    )

    return bool(
        ids
        and ids[0].strip().upper() == "QR"
    )


def _remove_qr_references(
    root: etree._Element,
) -> None:
    """
    إزالة AdditionalDocumentReference/ID=QR
    من نسخة الـ XML المستخدمة في Invoice Hash.
    """

    references = root.xpath(
        ".//*[local-name()='AdditionalDocumentReference']"
    )

    for reference in references:
        if _is_qr_reference(reference):
            parent = reference.getparent()

            if parent is not None:
                parent.remove(reference)


# =========================================================
# Invoice Hash preparation
# =========================================================

def _prepare_invoice_for_hash(
    xml: XMLInput,
) -> etree._Element:
    """
    تجهيز XML حسب خطوات ZATCA المنشورة لحساب Invoice Hash.

    يتم حذف:

    - UBLExtensions
    - QR AdditionalDocumentReference
    - Signature

    ثم يتم التعامل مع XML بدون XML declaration.
    """

    root = _parse_xml(xml)

    # لا نعدل الأصل مباشرة.
    root = etree.fromstring(
        etree.tostring(
            root,
            encoding="utf-8",
        )
    )

    # -----------------------------------------------------
    # 1. إزالة UBLExtensions
    # -----------------------------------------------------

    extensions = root.xpath(
        "./*[local-name()='UBLExtensions']"
    )

    for extension in extensions:
        root.remove(extension)

    # -----------------------------------------------------
    # 2. إزالة QR
    # -----------------------------------------------------

    _remove_qr_references(root)

    # -----------------------------------------------------
    # 3. إزالة Signature
    # -----------------------------------------------------

    _remove_existing_signature(root)

    return root


def _canonicalize_c14n11(
    element: etree._Element,
) -> bytes:
    """
    Canonical XML باستخدام C14N 1.1.
    """

    return etree.tostring(
        element,
        method="c14n",
        exclusive=False,
        with_comments=False,
    )


def calculate_invoice_hash(
    xml: XMLInput,
) -> str:
    """
    حساب Invoice Hash حسب خطوات ZATCA:

    XML
      ↓
    إزالة UBLExtensions / QR / Signature
      ↓
    C14N 1.1
      ↓
    SHA-256
      ↓
    Base64

    Returns
    -------
    str
        Base64 encoded SHA-256 digest.
    """

    prepared = _prepare_invoice_for_hash(
        xml
    )

    canonical_xml = _canonicalize_c14n11(
        prepared
    )

    digest = hashlib.sha256(
        canonical_xml
    ).digest()

    return base64.b64encode(
        digest
    ).decode("ascii")


# =========================================================
# Certificate handling
# =========================================================

def _load_certificate(
    certificate_path: Union[str, Path],
) -> tuple[x509.Certificate, bytes, str]:
    """
    تحميل شهادة X.509.

    Returns
    -------
    certificate
    der_bytes
    base64_der
    """

    certificate_data = _read_file(
        certificate_path
    )

    certificate_data = certificate_data.strip()

    try:
        certificate = x509.load_pem_x509_certificate(
            certificate_data
        )

    except ValueError:
        certificate = x509.load_der_x509_certificate(
            certificate_data
        )

    der_bytes = certificate.public_bytes(
        serialization.Encoding.DER
    )

    certificate_base64 = base64.b64encode(
        der_bytes
    ).decode("ascii")

    return (
        certificate,
        der_bytes,
        certificate_base64,
    )


def _certificate_hash_base64(
    certificate_der: bytes,
) -> str:
    """
    SHA-256 للشهادة DER ثم Base64.
    """

    digest = hashlib.sha256(
        certificate_der
    ).digest()

    return base64.b64encode(
        digest
    ).decode("ascii")


# =========================================================
# Private key
# =========================================================

def _load_private_key(
    private_key_path: Union[str, Path],
):
    """
    تحميل Private Key.

    يجب أن يكون المفتاح ECC.
    """

    key_data = _read_file(
        private_key_path
    )

    private_key = serialization.load_pem_private_key(
        key_data,
        password=None,
    )

    if not isinstance(
        private_key,
        ec.EllipticCurvePrivateKey,
    ):
        raise ValueError(
            "ZATCA signing key must be an EC/ECDSA private key."
        )

    return private_key


# =========================================================
# XAdES SignedProperties
# =========================================================

def _create_signed_properties(
    certificate: x509.Certificate,
    certificate_hash_base64: str,
    signing_time: datetime,
) -> etree._Element:
    """
    إنشاء xades:SignedProperties.

    يحتوي على:

    - SigningTime
    - SigningCertificate
    - CertDigest
    - X509IssuerName
    - X509SerialNumber
    """

    signed_properties = etree.Element(
        _qname(
            XADES_NS,
            "SignedProperties",
        ),
        nsmap={
            "xades": XADES_NS,
            "ds": DS_NS,
        },
    )

    signed_properties.set(
        "Id",
        "xades-SignedProperties",
    )

    signed_signature_properties = etree.SubElement(
        signed_properties,
        _qname(
            XADES_NS,
            "SignedSignatureProperties",
        ),
    )

    # -----------------------------------------------------
    # SigningTime
    # -----------------------------------------------------

    signing_time_element = etree.SubElement(
        signed_signature_properties,
        _qname(
            XADES_NS,
            "SigningTime",
        ),
    )

    signing_time_element.text = (
        signing_time.astimezone(
            timezone.utc
        )
        .isoformat(
            timespec="seconds"
        )
        .replace(
            "+00:00",
            "Z",
        )
    )

    # -----------------------------------------------------
    # SigningCertificate
    # -----------------------------------------------------

    signing_certificate = etree.SubElement(
        signed_signature_properties,
        _qname(
            XADES_NS,
            "SigningCertificate",
        ),
    )

    cert = etree.SubElement(
        signing_certificate,
        _qname(
            XADES_NS,
            "Cert",
        ),
    )

    cert_digest = etree.SubElement(
        cert,
        _qname(
            XADES_NS,
            "CertDigest",
        ),
    )

    digest_method = etree.SubElement(
        cert_digest,
        _qname(
            DS_NS,
            "DigestMethod",
        ),
    )

    digest_method.set(
        "Algorithm",
        "http://www.w3.org/2001/04/xmlenc#sha256",
    )

    digest_value = etree.SubElement(
        cert_digest,
        _qname(
            DS_NS,
            "DigestValue",
        ),
    )

    digest_value.text = certificate_hash_base64

    # -----------------------------------------------------
    # IssuerSerial
    # -----------------------------------------------------

    issuer_serial = etree.SubElement(
        cert,
        _qname(
            XADES_NS,
            "IssuerSerial",
        ),
    )

    issuer_name = etree.SubElement(
        issuer_serial,
        _qname(
            DS_NS,
            "X509IssuerName",
        ),
    )

    issuer_name.text = (
        certificate.issuer.rfc4514_string()
    )

    serial_number = etree.SubElement(
        issuer_serial,
        _qname(
            DS_NS,
            "X509SerialNumber",
        ),
    )

    serial_number.text = str(
        certificate.serial_number
    )

    return signed_properties


# =========================================================
# SignedProperties hash
# =========================================================

def _calculate_signed_properties_hash(
    signed_properties: etree._Element,
) -> str:
    """
    حساب SHA-256 لـ SignedProperties
    ثم Base64.

    ZATCA تعتمد Hash الخاص بـ SignedProperties
    داخل Reference URI="#xades-SignedProperties".
    """

    canonical_properties = _canonicalize_c14n11(
        signed_properties
    )

    digest = hashlib.sha256(
        canonical_properties
    ).digest()

    return base64.b64encode(
        digest
    ).decode("ascii")


# =========================================================
# XAdES QualifyingProperties
# =========================================================

def _create_qualifying_properties(
    signed_properties: etree._Element,
) -> etree._Element:
    """
    إنشاء:

    xades:QualifyingProperties
        xades:SignedProperties
    """

    qualifying_properties = etree.Element(
        _qname(
            XADES_NS,
            "QualifyingProperties",
        ),
        nsmap={
            "xades": XADES_NS,
        },
    )

    qualifying_properties.set(
        "Target",
        "#signature",
    )

    qualifying_properties.append(
        signed_properties
    )

    return qualifying_properties


# =========================================================
# XMLDSig helpers
# =========================================================

def _create_signed_info(
    invoice_hash_base64: str,
    signed_properties_hash_base64: str,
) -> etree._Element:
    """
    إنشاء ds:SignedInfo.

    References:

    1. invoice-SignedData
    2. xades-SignedProperties
    """

    signed_info = etree.Element(
        _qname(
            DS_NS,
            "SignedInfo",
        ),
        nsmap={
            "ds": DS_NS,
        },
    )

    # -----------------------------------------------------
    # CanonicalizationMethod
    # -----------------------------------------------------

    canonicalization_method = etree.SubElement(
        signed_info,
        _qname(
            DS_NS,
            "CanonicalizationMethod",
        ),
    )

    canonicalization_method.set(
        "Algorithm",
        "http://www.w3.org/2006/12/xml-c14n11",
    )

    # -----------------------------------------------------
    # SignatureMethod
    # -----------------------------------------------------

    signature_method = etree.SubElement(
        signed_info,
        _qname(
            DS_NS,
            "SignatureMethod",
        ),
    )

    signature_method.set(
        "Algorithm",
        "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256",
    )

    # =====================================================
    # Reference: Invoice
    # =====================================================

    invoice_reference = etree.SubElement(
        signed_info,
        _qname(
            DS_NS,
            "Reference",
        ),
    )

    invoice_reference.set(
        "Id",
        "invoice-SignedData",
    )

    invoice_reference.set(
        "URI",
        "",
    )

    invoice_digest_method = etree.SubElement(
        invoice_reference,
        _qname(
            DS_NS,
            "DigestMethod",
        ),
    )

    invoice_digest_method.set(
        "Algorithm",
        "http://www.w3.org/2001/04/xmlenc#sha256",
    )

    invoice_digest_value = etree.SubElement(
        invoice_reference,
        _qname(
            DS_NS,
            "DigestValue",
        ),
    )

    invoice_digest_value.text = (
        invoice_hash_base64
    )

    # =====================================================
    # Reference: SignedProperties
    # =====================================================

    properties_reference = etree.SubElement(
        signed_info,
        _qname(
            DS_NS,
            "Reference",
        ),
    )

    properties_reference.set(
        "Type",
        "http://uri.etsi.org/01903#SignedProperties",
    )

    properties_reference.set(
        "URI",
        "#xades-SignedProperties",
    )

    properties_digest_method = etree.SubElement(
        properties_reference,
        _qname(
            DS_NS,
            "DigestMethod",
        ),
    )

    properties_digest_method.set(
        "Algorithm",
        "http://www.w3.org/2001/04/xmlenc#sha256",
    )

    properties_digest_value = etree.SubElement(
        properties_reference,
        _qname(
            DS_NS,
            "DigestValue",
        ),
    )

    properties_digest_value.text = (
        signed_properties_hash_base64
    )

    return signed_info


# =========================================================
# ECDSA XML Signature
# =========================================================

def _ecdsa_sign(
    private_key,
    data: bytes,
) -> bytes:
    """
    توقيع البيانات باستخدام ECDSA + SHA256.

    XMLDSig ECDSA SignatureValue يستخدم
    concatenation:

        r || s

    وليس PEM أو Base64 داخل هذه الدالة.
    """

    if not isinstance(
        private_key,
        ec.EllipticCurvePrivateKey,
    ):
        raise ValueError(
            "Private key must be an EC private key."
        )

    der_signature = private_key.sign(
        data,
        ec.ECDSA(
            hashes.SHA256()
        ),
    )

    r, s = decode_dss_signature(
        der_signature
    )

    key_size = (
        private_key.curve.key_size
    )

    component_size = (
        (key_size + 7) // 8
    )

    raw_signature = (
        r.to_bytes(
            component_size,
            "big",
        )
        +
        s.to_bytes(
            component_size,
            "big",
        )
    )

    return raw_signature


def _ecdsa_verify(
    public_key,
    data: bytes,
    raw_signature: bytes,
) -> bool:
    """
    التحقق من XMLDSig ECDSA SignatureValue
    بصيغة r || s.
    """

    if not isinstance(
        public_key,
        ec.EllipticCurvePublicKey,
    ):
        return False

    key_size = (
        public_key.curve.key_size
    )

    component_size = (
        (key_size + 7) // 8
    )

    expected_size = (
        component_size * 2
    )

    if len(raw_signature) != expected_size:
        return False

    r = int.from_bytes(
        raw_signature[:component_size],
        "big",
    )

    s = int.from_bytes(
        raw_signature[component_size:],
        "big",
    )

    der_signature = encode_dss_signature(
        r,
        s,
    )

    try:
        public_key.verify(
            der_signature,
            data,
            ec.ECDSA(
                hashes.SHA256()
            ),
        )

        return True

    except Exception:
        return False


# =========================================================
# UBL Signature wrapper
# =========================================================

def _create_ubl_signature_container(
    root: etree._Element,
) -> etree._Element:
    """
    إنشاء البنية:

    ext:UBLExtensions
        ext:UBLExtension
            ext:ExtensionContent
                sig:UBLDocumentSignatures
                    sac:SignatureInformation
                        ds:Signature
    """

    extensions = root.find(
        _qname(
            EXT_NS,
            "UBLExtensions",
        )
    )

    if extensions is None:
        extensions = etree.Element(
            _qname(
                EXT_NS,
                "UBLExtensions",
            ),
            nsmap={
                "ext": EXT_NS,
            },
        )

        root.insert(
            0,
            extensions,
        )

    # -----------------------------------------------------
    # لا نضيف Extension ثانية للتوقيع إذا كانت موجودة
    # -----------------------------------------------------

    ubl_signature_container = extensions.xpath(
        "./*[local-name()='UBLExtension']"
        "/*[local-name()='ExtensionContent']"
        "/*[local-name()='UBLDocumentSignatures']"
    )

    if ubl_signature_container:
        ubl_document_signatures = (
            ubl_signature_container[0]
        )

        signature_information = etree.SubElement(
            ubl_document_signatures,
            _qname(
                SAC_NS,
                "SignatureInformation",
            ),
        )

        return signature_information

    extension = etree.SubElement(
        extensions,
        _qname(
            EXT_NS,
            "UBLExtension",
        ),
    )

    extension_content = etree.SubElement(
        extension,
        _qname(
            EXT_NS,
            "ExtensionContent",
        ),
    )

    ubl_document_signatures = etree.SubElement(
        extension_content,
        _qname(
            SIG_NS,
            "UBLDocumentSignatures",
        ),
        nsmap={
            "sig": SIG_NS,
            "sac": SAC_NS,
            "ds": DS_NS,
            "xades": XADES_NS,
        },
    )

    signature_information = etree.SubElement(
        ubl_document_signatures,
        _qname(
            SAC_NS,
            "SignatureInformation",
        ),
    )

    return signature_information


# =========================================================
# Complete signing
# =========================================================

def sign_invoice_xml(
    xml: XMLInput,
    private_key_path: Union[str, Path],
    certificate_path: Union[str, Path],
    signing_time: datetime | None = None,
) -> bytes:
    """
    إنشاء التوقيع الكامل للفاتورة.

    Parameters
    ----------
    xml:
        XML الفاتورة قبل التوقيع.

    private_key_path:
        private_key.pem

    certificate_path:
        شهادة EGS/CSID.

    signing_time:
        وقت التوقيع.
        إذا لم يتم تمريره يتم استخدام UTC الحالي.

    Returns
    -------
    bytes
        Signed XML.
    """

    root = _parse_xml(xml)

    # -----------------------------------------------------
    # تأكد من وجود Invoice
    # -----------------------------------------------------

    if _local_name(root) != "Invoice":
        raise ValueError(
            "The XML root element must be Invoice."
        )

    # -----------------------------------------------------
    # لا نسمح بتوقيع XML موقع مسبقًا
    # -----------------------------------------------------

    _remove_existing_signature(
        root
    )

    # -----------------------------------------------------
    # تحميل المفتاح
    # -----------------------------------------------------

    private_key = _load_private_key(
        private_key_path
    )

    # -----------------------------------------------------
    # تحميل الشهادة
    # -----------------------------------------------------

    (
        certificate,
        certificate_der,
        certificate_base64,
    ) = _load_certificate(
        certificate_path
    )

    # -----------------------------------------------------
    # تحقق أساسي من توافق المفتاح والشهادة
    # -----------------------------------------------------

    certificate_public_key = (
        certificate.public_key()
    )

    private_public_key = (
        private_key.public_key()
    )

    if (
        private_public_key.public_numbers()
        != certificate_public_key.public_numbers()
    ):
        raise ValueError(
            "Private key and certificate do not belong "
            "to the same public key."
        )

    # -----------------------------------------------------
    # Signing time
    # -----------------------------------------------------

    if signing_time is None:
        signing_time = datetime.now(
            timezone.utc
        )

    if signing_time.tzinfo is None:
        signing_time = signing_time.replace(
            tzinfo=timezone.utc
        )

    # =====================================================
    # STEP 1
    # Invoice Hash
    # =====================================================

    invoice_hash_base64 = calculate_invoice_hash(
        root
    )

    # =====================================================
    # STEP 3
    # Certificate Hash
    # =====================================================

    certificate_hash_base64 = (
        _certificate_hash_base64(
            certificate_der
        )
    )

    # =====================================================
    # STEP 4
    # SignedProperties
    # =====================================================

    signed_properties = (
        _create_signed_properties(
            certificate=certificate,
            certificate_hash_base64=certificate_hash_base64,
            signing_time=signing_time,
        )
    )

    # =====================================================
    # STEP 5
    # SignedProperties Hash
    # =====================================================

    signed_properties_hash_base64 = (
        _calculate_signed_properties_hash(
            signed_properties
        )
    )

    # =====================================================
    # إنشاء SignedInfo
    # =====================================================

    signed_info = _create_signed_info(
        invoice_hash_base64=invoice_hash_base64,
        signed_properties_hash_base64=(
            signed_properties_hash_base64
        ),
    )

    # =====================================================
    # Canonicalize SignedInfo
    # =====================================================

    canonical_signed_info = (
        _canonicalize_c14n11(
            signed_info
        )
    )

    # =====================================================
    # توقيع SignedInfo
    # =====================================================

    raw_signature = _ecdsa_sign(
        private_key,
        canonical_signed_info,
    )

    signature_value_base64 = (
        base64.b64encode(
            raw_signature
        ).decode("ascii")
    )

    # =====================================================
    # إنشاء ds:Signature
    # =====================================================

    signature = etree.Element(
        _qname(
            DS_NS,
            "Signature",
        ),
        nsmap={
            "ds": DS_NS,
            "xades": XADES_NS,
        },
    )

    signature.set(
        "Id",
        "signature",
    )

    # -----------------------------------------------------
    # SignedInfo
    # -----------------------------------------------------

    signature.append(
        signed_info
    )

    # -----------------------------------------------------
    # SignatureValue
    # -----------------------------------------------------

    signature_value = etree.SubElement(
        signature,
        _qname(
            DS_NS,
            "SignatureValue",
        ),
    )

    signature_value.text = (
        signature_value_base64
    )

    # -----------------------------------------------------
    # KeyInfo
    # -----------------------------------------------------

    key_info = etree.SubElement(
        signature,
        _qname(
            DS_NS,
            "KeyInfo",
        ),
    )

    x509_data = etree.SubElement(
        key_info,
        _qname(
            DS_NS,
            "X509Data",
        ),
    )

    x509_certificate = etree.SubElement(
        x509_data,
        _qname(
            DS_NS,
            "X509Certificate",
        ),
    )

    x509_certificate.text = (
        certificate_base64
    )

    # -----------------------------------------------------
    # XAdES Object
    # -----------------------------------------------------

    object_element = etree.SubElement(
        signature,
        _qname(
            DS_NS,
            "Object",
        ),
    )

    qualifying_properties = (
        _create_qualifying_properties(
            signed_properties
        )
    )

    object_element.append(
        qualifying_properties
    )

    # =====================================================
    # إدخال التوقيع في UBL
    # =====================================================

    signature_information = (
        _create_ubl_signature_container(
            root
        )
    )

    signature_information.append(
        signature
    )

    # =====================================================
    # Final XML
    # =====================================================

    return etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )


# =========================================================
# File helper
# =========================================================

def sign_invoice_xml_file(
    xml_path: Union[str, Path],
    output_path: Union[str, Path],
    private_key_path: Union[str, Path],
    certificate_path: Union[str, Path],
) -> Path:
    """
    قراءة XML وتوقيعه وحفظ النتيجة.
    """

    xml_path = Path(
        xml_path
    )

    output_path = Path(
        output_path
    )

    xml = _read_file(
        xml_path
    )

    signed_xml = sign_invoice_xml(
        xml=xml,
        private_key_path=private_key_path,
        certificate_path=certificate_path,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        signed_xml
    )

    return output_path


# =========================================================
# Signature inspection
# =========================================================

def get_signature_components(
    xml: XMLInput,
) -> dict:
    """
    استخراج العناصر المهمة من التوقيع
    لأغراض الاختبار والفحص.

    لا ترسل هذه البيانات إلى ZATCA.
    """

    root = _parse_xml(xml)

    signature = _find_signature(
        root
    )

    if signature is None:
        raise ValueError(
            "No XML Signature found."
        )

    invoice_reference = signature.xpath(
        "./*[local-name()='SignedInfo']"
        "/*[local-name()='Reference' "
        "and @Id='invoice-SignedData']"
    )

    properties_reference = signature.xpath(
        "./*[local-name()='SignedInfo']"
        "/*[local-name()='Reference' "
        "and @URI='#xades-SignedProperties']"
    )

    signature_value = signature.xpath(
        "./*[local-name()='SignatureValue']/text()"
    )

    certificate = signature.xpath(
        "./*[local-name()='KeyInfo']"
        "/*[local-name()='X509Data']"
        "/*[local-name()='X509Certificate']/text()"
    )

    signed_properties = signature.xpath(
        ".//*[local-name()='SignedProperties']"
    )

    return {
        "has_signature": True,
        "invoice_reference_count": len(
            invoice_reference
        ),
        "properties_reference_count": len(
            properties_reference
        ),
        "has_signature_value": bool(
            signature_value
            and signature_value[0].strip()
        ),
        "has_certificate": bool(
            certificate
            and certificate[0].strip()
        ),
        "has_signed_properties": bool(
            signed_properties
        ),
        "invoice_hash": (
            invoice_reference[0]
            .xpath(
                "./*[local-name()='DigestValue']/text()"
            )[0]
            if invoice_reference
            and invoice_reference[0].xpath(
                "./*[local-name()='DigestValue']/text()"
            )
            else None
        ),
        "signed_properties_hash": (
            properties_reference[0]
            .xpath(
                "./*[local-name()='DigestValue']/text()"
            )[0]
            if properties_reference
            and properties_reference[0].xpath(
                "./*[local-name()='DigestValue']/text()"
            )
            else None
        ),
    }


# =========================================================
# Verify XML Signature
# =========================================================

def verify_invoice_signature(
    xml: XMLInput,
) -> bool:
    """
    التحقق محليًا من:

    1. وجود Signature.
    2. وجود invoice-SignedData.
    3. وجود xades-SignedProperties.
    4. إعادة حساب Invoice Hash.
    5. مقارنة Invoice Hash مع DigestValue.
    6. إعادة حساب SignedProperties Hash.
    7. مقارنة SignedProperties Hash.
    8. استخراج الشهادة.
    9. التحقق من ECDSA SignatureValue.

    هذه الدالة لا تثبت قبول ZATCA للفاتورة.
    """
    
    try:
        root = _parse_xml(
            xml
        )

        signature = _find_signature(
            root
        )

        if signature is None:
            return False

        # -------------------------------------------------
        # SignedInfo
        # -------------------------------------------------

        signed_info_list = signature.xpath(
            "./*[local-name()='SignedInfo']"
        )

        if not signed_info_list:
            return False

        signed_info = signed_info_list[0]

        # -------------------------------------------------
        # Invoice reference
        # -------------------------------------------------

        invoice_reference_list = signed_info.xpath(
            "./*[local-name()='Reference' "
            "and @Id='invoice-SignedData']"
        )

        if len(invoice_reference_list) != 1:
            return False

        invoice_reference = (
            invoice_reference_list[0]
        )

        invoice_digest_values = invoice_reference.xpath(
            "./*[local-name()='DigestValue']/text()"
        )

        if len(invoice_digest_values) != 1:
            return False

        expected_invoice_hash = (
            invoice_digest_values[0].strip()
        )

        actual_invoice_hash = (
            calculate_invoice_hash(
                root
            )
        )

        if (
            expected_invoice_hash
            != actual_invoice_hash
        ):
            return False

        # -------------------------------------------------
        # SignedProperties
        # -------------------------------------------------

        signed_properties_list = signature.xpath(
            ".//*[local-name()='SignedProperties']"
        )

        if len(signed_properties_list) != 1:
            return False

        signed_properties = (
            signed_properties_list[0]
        )

        properties_reference_list = signed_info.xpath(
            "./*[local-name()='Reference' "
            "and @URI='#xades-SignedProperties']"
        )

        if len(properties_reference_list) != 1:
            return False

        properties_reference = (
            properties_reference_list[0]
        )

        properties_digest_values = (
            properties_reference.xpath(
                "./*[local-name()='DigestValue']/text()"
            )
        )

        if len(properties_digest_values) != 1:
            return False

        expected_properties_hash = (
            properties_digest_values[0].strip()
        )

        actual_properties_hash = (
            _calculate_signed_properties_hash(
                signed_properties
            )
        )

        if (
            expected_properties_hash
            != actual_properties_hash
        ):
            return False

        # -------------------------------------------------
        # Certificate
        # -------------------------------------------------

        certificate_values = signature.xpath(
            "./*[local-name()='KeyInfo']"
            "/*[local-name()='X509Data']"
            "/*[local-name()='X509Certificate']/text()"
        )

        if len(certificate_values) != 1:
            return False

        certificate_der = base64.b64decode(
            "".join(
                certificate_values[0].split()
            ),
            validate=True,
        )

        certificate = (
            x509.load_der_x509_certificate(
                certificate_der
            )
        )

        # -------------------------------------------------
        # SignatureValue
        # -------------------------------------------------

        signature_values = signature.xpath(
            "./*[local-name()='SignatureValue']/text()"
        )

        if len(signature_values) != 1:
            return False

        raw_signature = base64.b64decode(
            "".join(
                signature_values[0].split()
            ),
            validate=True,
        )

        # -------------------------------------------------
        # Canonicalize SignedInfo
        # -------------------------------------------------

        canonical_signed_info = (
            _canonicalize_c14n11(
                signed_info
            )
        )

        # -------------------------------------------------
        # Verify
        # -------------------------------------------------

        return _ecdsa_verify(
            certificate.public_key(),
            canonical_signed_info,
            raw_signature,
        )

    except Exception:
        return False


# =========================================================
# Detailed verification report
# =========================================================

def validate_signature_structure(
    xml: XMLInput,
) -> dict:
    """
    فحص تفصيلي لبنية التوقيع.

    الهدف منه الاختبار أثناء التطوير.
    """

    result = {
        "valid": False,
        "errors": [],
        "checks": {},
    }

    try:
        root = _parse_xml(
            xml
        )

        signature = _find_signature(
            root
        )

        result["checks"][
            "signature_exists"
        ] = signature is not None

        if signature is None:
            result["errors"].append(
                "XML Signature is missing."
            )
            return result

        signed_info = signature.xpath(
            "./*[local-name()='SignedInfo']"
        )

        result["checks"][
            "signed_info_exists"
        ] = bool(signed_info)

        signature_value = signature.xpath(
            "./*[local-name()='SignatureValue']"
        )

        result["checks"][
            "signature_value_exists"
        ] = bool(signature_value)

        key_info = signature.xpath(
            "./*[local-name()='KeyInfo']"
        )

        result["checks"][
            "key_info_exists"
        ] = bool(key_info)

        certificate = signature.xpath(
            "./*[local-name()='KeyInfo']"
            "/*[local-name()='X509Data']"
            "/*[local-name()='X509Certificate']"
        )

        result["checks"][
            "certificate_exists"
        ] = bool(certificate)

        signed_properties = signature.xpath(
            ".//*[local-name()='SignedProperties']"
        )

        result["checks"][
            "signed_properties_exists"
        ] = bool(signed_properties)

        invoice_reference = signature.xpath(
            "./*[local-name()='SignedInfo']"
            "/*[local-name()='Reference' "
            "and @Id='invoice-SignedData']"
        )

        result["checks"][
            "invoice_reference_exists"
        ] = len(invoice_reference) == 1

        properties_reference = signature.xpath(
            "./*[local-name()='SignedInfo']"
            "/*[local-name()='Reference' "
            "and @URI='#xades-SignedProperties']"
        )

        result["checks"][
            "signed_properties_reference_exists"
        ] = len(properties_reference) == 1

        result["checks"][
            "invoice_hash_valid"
        ] = False

        result["checks"][
            "signed_properties_hash_valid"
        ] = False

        result["checks"][
            "cryptographic_signature_valid"
        ] = False

        if len(invoice_reference) == 1:
            expected = invoice_reference[0].xpath(
                "./*[local-name()='DigestValue']/text()"
            )

            if expected:
                actual = calculate_invoice_hash(
                    root
                )

                result["checks"][
                    "invoice_hash_valid"
                ] = (
                    expected[0].strip()
                    == actual
                )

        if len(
            properties_reference
        ) == 1 and signed_properties:

            expected = properties_reference[0].xpath(
                "./*[local-name()='DigestValue']/text()"
            )

            actual = (
                _calculate_signed_properties_hash(
                    signed_properties[0]
                )
            )

            if expected:
                result["checks"][
                    "signed_properties_hash_valid"
                ] = (
                    expected[0].strip()
                    == actual
                )

        result["checks"][
            "cryptographic_signature_valid"
        ] = verify_invoice_signature(
            root
        )

        required_checks = [
            "signature_exists",
            "signed_info_exists",
            "signature_value_exists",
            "key_info_exists",
            "certificate_exists",
            "signed_properties_exists",
            "invoice_reference_exists",
            "signed_properties_reference_exists",
            "invoice_hash_valid",
            "signed_properties_hash_valid",
            "cryptographic_signature_valid",
        ]

        result["valid"] = all(
            result["checks"].get(
                check,
                False,
            )
            for check in required_checks
        )

        if not result["valid"]:
            for check in required_checks:
                if not result["checks"].get(
                    check,
                    False,
                ):
                    result["errors"].append(
                        f"Signature check failed: {check}"
                    )

        return result

    except Exception as exc:
        result["errors"].append(
            str(exc)
        )

        return result