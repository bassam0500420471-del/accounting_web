"""
ZATCA QR Code Service
=====================

إنشاء QR Code الخاص بالفاتورة الإلكترونية.

يعتمد QR في الفاتورة السعودية على TLV:

Tag 1 = اسم البائع
Tag 2 = الرقم الضريبي
Tag 3 = تاريخ ووقت الفاتورة
Tag 4 = إجمالي الفاتورة شامل الضريبة
Tag 5 = إجمالي ضريبة القيمة المضافة

ثم يتم تحويل TLV إلى Base64.

مهم:
لا يتم وضع نص QR عشوائي.
المحتوى النهائي هو TLV Base64.
"""

from __future__ import annotations

import base64
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


# =========================================================
# أدوات داخلية
# =========================================================

def _to_text(value: Any) -> str:
    """
    تحويل القيمة إلى نص آمن.
    """

    if value is None:
        return ""

    return str(value).strip()


def _decimal_text(value: Any) -> str:
    """
    تنسيق المبالغ المالية إلى رقم عشري مناسب للـ QR.
    """

    if value is None:
        return "0.00"

    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(
            f"Invalid decimal value for QR: {value}"
        )

    return format(decimal_value, ".2f")


def _datetime_text(value: Any) -> str:
    """
    تحويل التاريخ والوقت إلى ISO 8601.
    """

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return datetime.combine(
            value,
            datetime.min.time(),
        ).isoformat()

    value = _to_text(value)

    if not value:
        raise ValueError(
            "Invoice date/time is required for ZATCA QR."
        )

    return value


# =========================================================
# TLV
# =========================================================

def encode_tlv(tag: int, value: Any) -> bytes:
    """
    إنشاء عنصر TLV واحد.

    الصيغة:
        Tag
        Length
        Value

    باستخدام UTF-8.
    """

    if not isinstance(tag, int):
        raise TypeError("TLV tag must be an integer.")

    if tag < 1 or tag > 255:
        raise ValueError("TLV tag must be between 1 and 255.")

    value_bytes = _to_text(value).encode("utf-8")

    if len(value_bytes) > 255:
        raise ValueError(
            f"TLV value for tag {tag} is too long."
        )

    return bytes([
        tag,
        len(value_bytes),
    ]) + value_bytes


def build_tlv(
    seller_name: Any,
    vat_number: Any,
    invoice_datetime: Any,
    invoice_total: Any,
    vat_total: Any,
) -> bytes:
    """
    بناء TLV الكامل الخاص بـ ZATCA.
    """

    seller_name = _to_text(seller_name)
    vat_number = _to_text(vat_number)

    if not seller_name:
        raise ValueError(
            "Seller name is required for ZATCA QR."
        )

    if not vat_number:
        raise ValueError(
            "VAT number is required for ZATCA QR."
        )

    invoice_datetime = _datetime_text(invoice_datetime)
    invoice_total = _decimal_text(invoice_total)
    vat_total = _decimal_text(vat_total)

    parts = [
        encode_tlv(1, seller_name),
        encode_tlv(2, vat_number),
        encode_tlv(3, invoice_datetime),
        encode_tlv(4, invoice_total),
        encode_tlv(5, vat_total),
    ]

    return b"".join(parts)


# =========================================================
# Base64
# =========================================================

def tlv_to_base64(tlv_data: bytes) -> str:
    """
    تحويل TLV إلى Base64.
    """

    if not isinstance(tlv_data, bytes):
        raise TypeError(
            "TLV data must be bytes."
        )

    return base64.b64encode(
        tlv_data
    ).decode("ascii")


def generate_qr_code(
    seller_name: Any,
    vat_number: Any,
    invoice_datetime: Any,
    invoice_total: Any,
    vat_total: Any,
) -> str:
    """
    إنشاء القيمة النهائية التي توضع داخل QR Code.

    Returns:
        Base64 string
    """

    tlv_data = build_tlv(
        seller_name=seller_name,
        vat_number=vat_number,
        invoice_datetime=invoice_datetime,
        invoice_total=invoice_total,
        vat_total=vat_total,
    )

    return tlv_to_base64(tlv_data)


# =========================================================
# أسماء بديلة للتوافق مع المشروع
# =========================================================

def create_qr_code(
    seller_name: Any,
    vat_number: Any,
    invoice_datetime: Any,
    invoice_total: Any,
    vat_total: Any,
) -> str:
    """
    Alias.
    """

    return generate_qr_code(
        seller_name=seller_name,
        vat_number=vat_number,
        invoice_datetime=invoice_datetime,
        invoice_total=invoice_total,
        vat_total=vat_total,
    )


def generate_zatca_qr(
    seller_name: Any,
    vat_number: Any,
    invoice_datetime: Any,
    invoice_total: Any,
    vat_total: Any,
) -> str:
    """
    Alias باسم واضح لخدمة ZATCA.
    """

    return generate_qr_code(
        seller_name=seller_name,
        vat_number=vat_number,
        invoice_datetime=invoice_datetime,
        invoice_total=invoice_total,
        vat_total=vat_total,
    )


# =========================================================
# استخراج بيانات QR من كائن الفاتورة
# =========================================================

def generate_qr_from_invoice(invoice) -> str:
    """
    إنشاء QR مباشرة من كائن الفاتورة.

    يحاول قراءة:
        invoice.company
        invoice.created_at / invoice.invoice_date / invoice.date
        invoice.total / invoice.grand_total / invoice.total_amount
        invoice.vat_amount / invoice.tax_amount

    ويستخدم Company.vat_no للرقم الضريبي.
    """

    company = getattr(invoice, "company", None)

    if company is None:
        raise ValueError(
            "Invoice company is required for ZATCA QR."
        )

    seller_name = _to_text(
        getattr(company, "name", None)
    )

    vat_number = _to_text(
        getattr(company, "vat_no", None)
    )

    if not vat_number:
        raise ValueError(
            "Company.vat_no is required for ZATCA QR."
        )

    # -----------------------------------------------------
    # التاريخ والوقت
    # -----------------------------------------------------

    invoice_datetime = None

    for field_name in (
        "created_at",
        "invoice_datetime",
        "invoice_date",
        "date",
        "issued_at",
    ):
        value = getattr(invoice, field_name, None)

        if value:
            invoice_datetime = value
            break

    if invoice_datetime is None:
        raise ValueError(
            "Invoice date/time could not be found."
        )

    # -----------------------------------------------------
    # الإجمالي
    # -----------------------------------------------------

    invoice_total = None

    for field_name in (
        "total",
        "grand_total",
        "total_amount",
        "payable_amount",
        "total_with_tax",
    ):
        value = getattr(invoice, field_name, None)

        if value is not None:
            invoice_total = value
            break

    if invoice_total is None:
        raise ValueError(
            "Invoice total could not be found."
        )

    # -----------------------------------------------------
    # الضريبة
    # -----------------------------------------------------

    vat_total = None

    for field_name in (
        "vat_amount",
        "tax_amount",
        "total_tax",
        "tax",
    ):
        value = getattr(invoice, field_name, None)

        if value is not None:
            vat_total = value
            break

    if vat_total is None:
        vat_total = Decimal("0.00")

    return generate_qr_code(
        seller_name=seller_name,
        vat_number=vat_number,
        invoice_datetime=invoice_datetime,
        invoice_total=invoice_total,
        vat_total=vat_total,
    )


# =========================================================
# فك QR للفحص والاختبار
# =========================================================

def decode_qr_data(qr_data: str) -> dict[int, str]:
    """
    فك Base64 الخاص بـ ZATCA QR إلى Tags.

    مفيد للاختبار فقط.
    """

    if not qr_data:
        raise ValueError(
            "QR data is empty."
        )

    try:
        raw = base64.b64decode(
            qr_data,
            validate=True,
        )
    except Exception as exc:
        raise ValueError(
            "Invalid Base64 QR data."
        ) from exc

    result: dict[int, str] = {}

    index = 0

    while index < len(raw):

        if index + 2 > len(raw):
            raise ValueError(
                "Invalid TLV data."
            )

        tag = raw[index]
        length = raw[index + 1]

        index += 2

        if index + length > len(raw):
            raise ValueError(
                "Invalid TLV length."
            )

        value = raw[
            index:index + length
        ].decode(
            "utf-8"
        )

        result[tag] = value

        index += length

    return result