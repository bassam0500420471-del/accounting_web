"""
ZATCA XML Invoice Generator
===========================

Generates ZATCA-compatible UBL 2.1 XML for:

- SalesInvoice
- POS Invoice
- B2B Tax Invoice
- B2C Simplified Tax Invoice

Important:
This module generates the invoice XML structure and business data.

Cryptographic operations are intentionally kept outside this file:
- Previous Invoice Hash calculation
- Cryptographic Stamp / XAdES signature
- QR generation
- API submission

Those operations belong to the dedicated ZATCA services.
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from uuid import uuid4
import re
import xml.etree.ElementTree as ET

from django.utils import timezone


# =========================================================
# NAMESPACES
# =========================================================

UBL_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CAC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
EXT_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace("", UBL_NS)
ET.register_namespace("cac", CAC_NS)
ET.register_namespace("cbc", CBC_NS)
ET.register_namespace("ext", EXT_NS)
ET.register_namespace("xsi", XSI_NS)


# =========================================================
# CONSTANTS
# =========================================================

CURRENCY = "SAR"
COUNTRY = "SA"

INVOICE_TYPE_CODE = "388"

TAX_INVOICE_SUBTYPE = "0100000"
SIMPLIFIED_INVOICE_SUBTYPE = "0200000"

PROFILE_ID = "reporting:1.0"

VAT_SCHEME = "VAT"

STANDARD_TAX_CATEGORY = "S"
STANDARD_VAT_RATE = Decimal("15.00")

# ZATCA first invoice previous hash:
# Base64 encoded SHA256("0")
FIRST_INVOICE_PREVIOUS_HASH = (
    "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzlj"
    "MmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=="
)


# =========================================================
# XML HELPERS
# =========================================================

def _tag(namespace, name):
    return f"{{{namespace}}}{name}"


def _ubl(name):
    return _tag(UBL_NS, name)


def _cac(name):
    return _tag(CAC_NS, name)


def _cbc(name):
    return _tag(CBC_NS, name)


def _ext(name):
    return _tag(EXT_NS, name)


def _add(parent, namespace, name, value=None, attrib=None):
    element = ET.SubElement(
        parent,
        _tag(namespace, name),
        attrib or {},
    )

    if value is not None:
        element.text = str(value)

    return element


def _add_cbc(parent, name, value=None, attrib=None):
    return _add(parent, CBC_NS, name, value, attrib)


def _add_cac(parent, name):
    return _add(parent, CAC_NS, name)


def _decimal(value):
    if value is None:
        return Decimal("0")

    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _money(value):
    value = _decimal(value).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    return f"{value:.2f}"


def _qty(value):
    value = _decimal(value).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    return f"{value:.2f}"


def _rate(value):
    value = _decimal(value).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    return f"{value:.2f}"


def _clean(value):
    if value is None:
        return ""

    return str(value).strip()


def _digits_only(value):
    return re.sub(r"\D", "", _clean(value))


def _alphanumeric(value):
    return re.sub(r"[^A-Za-z0-9]", "", _clean(value))


def _valid_vat(value):
    value = _digits_only(value)

    return (
        len(value) == 15
        and value.startswith("3")
        and value.endswith("3")
    )


# =========================================================
# MODEL DETECTION
# =========================================================

def _is_pos_invoice(invoice):
    return invoice.__class__.__name__ == "Invoice"


def _is_sales_invoice(invoice):
    return invoice.__class__.__name__ == "SalesInvoice"


def _validate_invoice_model(invoice):
    if not (_is_pos_invoice(invoice) or _is_sales_invoice(invoice)):
        raise ValueError(
            "Unsupported invoice model. "
            "Expected SalesInvoice or POS Invoice."
        )


# =========================================================
# COMPANY
# =========================================================

def _get_company(invoice):
    company = getattr(invoice, "company", None)

    if company is None:
        raise ValueError(
            "Invoice company is missing. "
            "ZATCA XML cannot be generated without a company."
        )

    return company


def _get_company_vat(company):
    vat = _clean(getattr(company, "vat_no", ""))

    if not vat:
        raise ValueError(
            "Company VAT number is missing. "
            "ZATCA XML cannot be generated without Company.vat_no."
        )

    vat = _digits_only(vat)

    if not _valid_vat(vat):
        raise ValueError(
            "Company VAT number must contain exactly 15 digits "
            "and start/end with 3."
        )

    return vat


def _get_company_name(company):
    name = _clean(getattr(company, "name", ""))

    if not name:
        raise ValueError(
            "Company name is missing."
        )

    return name


def _get_company_commercial_record(company):
    value = _clean(
        getattr(company, "commercial_record", "")
    )

    value = _alphanumeric(value)

    return value


def _get_company_address(company):
    return {
        "street": _clean(
            getattr(company, "street", "")
        ),
        "building": _clean(
            getattr(company, "building_no", "")
        ),
        "postal": _clean(
            getattr(company, "postal_code", "")
        ),
        "city": _clean(
            getattr(company, "city", "")
        ),
        "district": _clean(
            getattr(company, "district", "")
        ),
        "additional": _clean(
            getattr(company, "additional_no", "")
        ),
        "country": COUNTRY,
    }


# =========================================================
# CUSTOMER
# =========================================================

def _get_customer(invoice):
    customer = getattr(invoice, "customer", None)

    if customer is None:
        raise ValueError(
            "Customer is missing. "
            "ZATCA XML requires a customer."
        )

    return customer


def _get_customer_type(customer):
    customer_type = _clean(
        getattr(customer, "customer_type", "")
    ).lower()

    if customer_type == "business":
        return "B2B"

    if customer_type == "individual":
        return "B2C"

    raise ValueError(
        "Customer type must be 'business' or 'individual'. "
        "business = B2B, individual = B2C."
    )


def _get_customer_name(customer):
    name = _clean(
        getattr(customer, "name", "")
    )

    if not name:
        first = _clean(
            getattr(customer, "first_name", "")
        )
        last = _clean(
            getattr(customer, "last_name", "")
        )

        name = " ".join(
            part
            for part in [first, last]
            if part
        ).strip()

    if not name:
        name = _clean(
            getattr(customer, "commercial_name", "")
        )

    if not name:
        raise ValueError(
            "Customer name is missing."
        )

    return name


def _get_customer_vat(customer):
    """
    Customer tax_number is treated as VAT number only when
    it is a valid Saudi 15-digit VAT number.
    """
    value = _clean(
        getattr(customer, "tax_number", "")
    )

    value = _digits_only(value)

    if _valid_vat(value):
        return value

    return ""


def _get_customer_other_id(customer):
    """
    Used when buyer is not VAT registered.

    Priority:
    1. CR number
    2. Tax number as TIN/other ID
    """

    cr_number = _clean(
        getattr(customer, "cr_number", "")
    )

    cr_number = _alphanumeric(cr_number)

    if cr_number:
        return cr_number, "CRN"

    tax_number = _clean(
        getattr(customer, "tax_number", "")
    )

    tax_number = _alphanumeric(tax_number)

    if tax_number:
        return tax_number, "TIN"

    return "", ""


def _get_customer_address(customer):
    return {
        "street": _clean(
            getattr(customer, "street1", "")
        )
        or _clean(
            getattr(customer, "address", "")
        ),
        "building": "",
        "postal": _clean(
            getattr(customer, "postal_code", "")
        ),
        "city": _clean(
            getattr(customer, "city", "")
        ),
        "district": _clean(
            getattr(customer, "region", "")
        ),
        "additional": _clean(
            getattr(customer, "street2", "")
        ),
        "country": (
            _clean(
                getattr(customer, "country", "")
            )
            or COUNTRY
        ),
    }


# =========================================================
# DATE / TIME
# =========================================================

def _get_issue_datetime(invoice):
    value = getattr(
        invoice,
        "created_at",
        None,
    )

    if value is None:
        value = getattr(
            invoice,
            "date_invoice",
            None,
        )

    if value is None:
        value = timezone.now()

    if isinstance(value, datetime):
        if timezone.is_naive(value):
            value = timezone.make_aware(
                value,
                timezone.get_current_timezone(),
            )

        return value

    return datetime.combine(
        value,
        datetime.min.time(),
    )


# =========================================================
# INVOICE NUMBER
# =========================================================

def _get_invoice_number(invoice):
    invoice_number = getattr(
        invoice,
        "invoice_no",
        None,
    )

    if invoice_number is None:
        raise ValueError(
            "Invoice number is missing."
        )

    return str(invoice_number)


# =========================================================
# UUID
# =========================================================

def _get_invoice_uuid(invoice):
    """
    Returns a UUID for the invoice.

    If the invoice model later receives a dedicated UUID field,
    this function can be changed to use that stored UUID.

    For now, the UUID is generated from the database invoice ID
    and invoice number so the same invoice gets the same UUID.
    """

    invoice_id = getattr(
        invoice,
        "pk",
        None,
    )

    if invoice_id is None:
        return str(uuid4())

    company = getattr(
        invoice,
        "company",
        None,
    )

    company_id = getattr(
        company,
        "pk",
        "0",
    )

    raw = (
        f"company:{company_id}|"
        f"model:{invoice.__class__.__name__}|"
        f"id:{invoice_id}|"
        f"invoice:{_get_invoice_number(invoice)}"
    )

    import uuid

    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            raw,
        )
    )


# =========================================================
# INVOICE TYPE
# =========================================================

def _get_invoice_type(customer):
    customer_type = _get_customer_type(customer)

    if customer_type == "B2B":
        return {
            "code": INVOICE_TYPE_CODE,
            "subtype": TAX_INVOICE_SUBTYPE,
            "simplified": False,
        }

    return {
        "code": INVOICE_TYPE_CODE,
        "subtype": SIMPLIFIED_INVOICE_SUBTYPE,
        "simplified": True,
    }


# =========================================================
# INVOICE LINES
# =========================================================

def _get_sales_lines(invoice):
    lines = []

    items = invoice.items.select_related(
        "product"
    ).all()

    for item in items:

        quantity = _decimal(
            getattr(item, "qty", 0)
        )

        price = _decimal(
            getattr(item, "price", 0)
        )

        discount = _decimal(
            getattr(item, "discount", 0)
        )

        tax_rate = _decimal(
            getattr(item, "tax", 0)
        )

        if quantity < 0:
            raise ValueError(
                "Invoice quantity cannot be negative."
            )

        if price < 0:
            raise ValueError(
                "Invoice price cannot be negative."
            )

        if discount < 0:
            discount = Decimal("0")

        subtotal = (
            quantity * price
        )

        if discount > subtotal:
            discount = subtotal

        after_discount = (
            subtotal - discount
        )

        tax_amount = (
            after_discount
            * tax_rate
            / Decimal("100")
        )

        total = (
            after_discount
            + tax_amount
        )

        product = getattr(
            item,
            "product",
            None,
        )

        description = _clean(
            getattr(item, "description", "")
        )

        if not description and product:
            description = (
                _clean(
                    getattr(product, "name", "")
                )
                or _clean(
                    getattr(product, "name_ar", "")
                )
                or _clean(
                    getattr(product, "name_en", "")
                )
            )

        if not description:
            description = "Item"

        lines.append(
            {
                "quantity": quantity,
                "price": price,
                "discount": discount,
                "tax_rate": tax_rate,
                "subtotal": subtotal,
                "net": after_discount,
                "tax": tax_amount,
                "total": total,
                "description": description,
                "unit": "PCE",
            }
        )

    return lines


def _get_pos_lines(invoice):
    lines = []

    items = invoice.items.select_related(
        "product"
    ).all()

    for item in items:

        quantity = _decimal(
            getattr(item, "quantity", 0)
        )

        price = _decimal(
            getattr(item, "price", 0)
        )

        discount = _decimal(
            getattr(item, "discount", 0)
        )

        discount_type = _clean(
            getattr(item, "discount_type", "")
        ).lower()

        tax_rate = _decimal(
            getattr(item, "tax", 0)
        )

        if quantity < 0:
            raise ValueError(
                "Invoice quantity cannot be negative."
            )

        if price < 0:
            raise ValueError(
                "Invoice price cannot be negative."
            )

        if discount < 0:
            discount = Decimal("0")

        subtotal = (
            quantity * price
        )

        if discount_type == "percent":
            discount_amount = (
                subtotal
                * discount
                / Decimal("100")
            )
        else:
            discount_amount = (
                discount * quantity
            )

        if discount_amount > subtotal:
            discount_amount = subtotal

        after_discount = (
            subtotal - discount_amount
        )

        tax_amount = (
            after_discount
            * tax_rate
            / Decimal("100")
        )

        total = (
            after_discount
            + tax_amount
        )

        product = getattr(
            item,
            "product",
            None,
        )

        description = ""

        if product:
            description = (
                _clean(
                    getattr(product, "name", "")
                )
                or _clean(
                    getattr(product, "name_ar", "")
                )
                or _clean(
                    getattr(product, "name_en", "")
                )
            )

        if not description:
            description = "Item"

        lines.append(
            {
                "quantity": quantity,
                "price": price,
                "discount": discount_amount,
                "tax_rate": tax_rate,
                "subtotal": subtotal,
                "net": after_discount,
                "tax": tax_amount,
                "total": total,
                "description": description,
                "unit": "PCE",
            }
        )

    return lines


def _get_invoice_lines(invoice):
    if _is_sales_invoice(invoice):
        return _get_sales_lines(invoice)

    return _get_pos_lines(invoice)


# =========================================================
# TOTALS
# =========================================================

def _calculate_totals(lines):
    taxable_total = Decimal("0")
    discount_total = Decimal("0")
    tax_total = Decimal("0")
    invoice_total = Decimal("0")

    for line in lines:

        taxable_total += line["net"]
        discount_total += line["discount"]
        tax_total += line["tax"]
        invoice_total += line["total"]

    return {
        "taxable_total": taxable_total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        ),
        "discount_total": discount_total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        ),
        "tax_total": tax_total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        ),
        "invoice_total": invoice_total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        ),
    }


# =========================================================
# ADDRESS
# =========================================================

def _add_address(
    parent,
    address,
    require_saudi_fields=False,
):
    postal_address = _add_cac(
        parent,
        "PostalAddress",
    )

    street = _clean(
        address.get("street")
    )

    building = _clean(
        address.get("building")
    )

    postal = _clean(
        address.get("postal")
    )

    city = _clean(
        address.get("city")
    )

    district = _clean(
        address.get("district")
    )

    additional = _clean(
        address.get("additional")
    )

    country = (
        _clean(
            address.get("country")
        )
        or COUNTRY
    )

    if street:
        _add_cbc(
            postal_address,
            "StreetName",
            street,
        )

    if building:
        _add_cbc(
            postal_address,
            "BuildingNumber",
            building,
        )

    if additional:
        _add_cbc(
            postal_address,
            "PlotIdentification",
            additional,
        )

    if city:
        _add_cbc(
            postal_address,
            "CityName",
            city,
        )

    if district:
        _add_cbc(
            postal_address,
            "CitySubdivisionName",
            district,
        )

    if postal:
        _add_cbc(
            postal_address,
            "PostalZone",
            postal,
        )

    country_node = _add_cac(
        postal_address,
        "Country",
    )

    _add_cbc(
        country_node,
        "IdentificationCode",
        country.upper()[:2],
    )

    if require_saudi_fields:
        missing = []

        if not street:
            missing.append("street")

        if not building:
            missing.append("building_no")

        if not postal:
            missing.append("postal_code")

        if not city:
            missing.append("city")

        if not district:
            missing.append("district")

        if missing:
            raise ValueError(
                "Saudi address is incomplete. "
                "Missing: "
                + ", ".join(missing)
            )

        if (
            not building.isdigit()
            or len(building) != 4
        ):
            raise ValueError(
                "Saudi address building number "
                "must contain exactly 4 digits."
            )

        if additional:
            if (
                not additional.isdigit()
                or len(additional) != 4
            ):
                raise ValueError(
                    "Saudi address additional number "
                    "must contain exactly 4 digits."
                )


# =========================================================
# SUPPLIER
# =========================================================

def _add_supplier_party(
    root,
    company,
):
    supplier = _add_cac(
        root,
        "AccountingSupplierParty",
    )

    party = _add_cac(
        supplier,
        "Party",
    )

    vat = _get_company_vat(
        company
    )

    commercial_record = (
        _get_company_commercial_record(
            company
        )
    )

    if not commercial_record:
        raise ValueError(
            "Company commercial record is required "
            "for ZATCA seller identification."
        )

    # Seller identification.
    # CRN must contain the commercial registration number,
    # not the VAT number.
    identification = _add_cac(
        party,
        "PartyIdentification",
    )

    _add_cbc(
        identification,
        "ID",
        commercial_record,
        {
            "schemeID": "CRN",
        },
    )

    party_name = _add_cac(
        party,
        "PartyName",
    )

    _add_cbc(
        party_name,
        "Name",
        _get_company_name(company),
    )

    _add_address(
        party,
        _get_company_address(company),
        require_saudi_fields=True,
    )

    tax_scheme = _add_cac(
        party,
        "PartyTaxScheme",
    )

    _add_cbc(
        tax_scheme,
        "CompanyID",
        vat,
    )

    tax_scheme_node = _add_cac(
        tax_scheme,
        "TaxScheme",
    )

    _add_cbc(
        tax_scheme_node,
        "ID",
        VAT_SCHEME,
    )

    legal_entity = _add_cac(
        party,
        "PartyLegalEntity",
    )

    _add_cbc(
        legal_entity,
        "RegistrationName",
        _get_company_name(company),
    )


# =========================================================
# CUSTOMER
# =========================================================

def _add_customer_party(
    root,
    customer,
):
    customer_type = _get_customer_type(
        customer
    )

    customer_party = _add_cac(
        root,
        "AccountingCustomerParty",
    )

    party = _add_cac(
        customer_party,
        "Party",
    )

    customer_vat = _get_customer_vat(
        customer
    )

    other_id, other_scheme = (
        _get_customer_other_id(
            customer
        )
    )

    # Buyer identification:
    #
    # If buyer is VAT registered, use VAT.
    # Otherwise, ZATCA requires another buyer identification
    # such as CRN/TIN/etc. where applicable.
    if customer_vat:
        identification = _add_cac(
            party,
            "PartyIdentification",
        )

        _add_cbc(
            identification,
            "ID",
            customer_vat,
            {
                "schemeID": "VAT",
            },
        )

    elif other_id:
        identification = _add_cac(
            party,
            "PartyIdentification",
        )

        _add_cbc(
            identification,
            "ID",
            other_id,
            {
                "schemeID": other_scheme,
            },
        )

    _add_address(
        party,
        _get_customer_address(customer),
        require_saudi_fields=(
            _clean(
                getattr(
                    customer,
                    "country",
                    "",
                )
            ).upper() in ("", "SA")
        ),
    )

    if customer_vat:
        tax_scheme = _add_cac(
            party,
            "PartyTaxScheme",
        )

        _add_cbc(
            tax_scheme,
            "CompanyID",
            customer_vat,
        )

        tax_scheme_node = _add_cac(
            tax_scheme,
            "TaxScheme",
        )

        _add_cbc(
            tax_scheme_node,
            "ID",
            VAT_SCHEME,
        )

    legal_entity = _add_cac(
        party,
        "PartyLegalEntity",
    )

    _add_cbc(
        legal_entity,
        "RegistrationName",
        _get_customer_name(customer),
    )


# =========================================================
# PAYMENT
# =========================================================

def _add_payment_means(root):
    payment_means = _add_cac(
        root,
        "PaymentMeans",
    )

    # 30 = Credit transfer
    # This is kept as a neutral default at XML level.
    _add_cbc(
        payment_means,
        "PaymentMeansCode",
        "30",
    )


# =========================================================
# TAX CATEGORY
# =========================================================

def _get_tax_category(tax_rate):
    tax_rate = _decimal(tax_rate)

    if tax_rate > 0:
        return {
            "id": STANDARD_TAX_CATEGORY,
            "rate": tax_rate,
        }

    # The current ERP does not yet store exemption /
    # zero-rated / out-of-scope reasons at line level.
    #
    # Therefore zero tax is represented as O (Not subject)
    # only when tax rate is actually zero.
    return {
        "id": "O",
        "rate": Decimal("0"),
    }


# =========================================================
# TAX TOTAL
# =========================================================

def _add_tax_total(
    root,
    lines,
):
    totals = _calculate_totals(lines)

    tax_total = _add_cac(
        root,
        "TaxTotal",
    )

    _add_cbc(
        tax_total,
        "TaxAmount",
        _money(
            totals["tax_total"]
        ),
        {
            "currencyID": CURRENCY,
        },
    )

    groups = {}

    for line in lines:

        category = _get_tax_category(
            line["tax_rate"]
        )

        key = (
            category["id"],
            str(
                _decimal(
                    category["rate"]
                ).quantize(
                    Decimal("0.01")
                )
            ),
        )

        if key not in groups:
            groups[key] = {
                "category": category,
                "taxable": Decimal("0"),
                "tax": Decimal("0"),
            }

        groups[key]["taxable"] += line["net"]
        groups[key]["tax"] += line["tax"]

    for group in groups.values():

        subtotal = _add_cac(
            tax_total,
            "TaxSubtotal",
        )

        _add_cbc(
            subtotal,
            "TaxableAmount",
            _money(
                group["taxable"]
            ),
            {
                "currencyID": CURRENCY,
            },
        )

        _add_cbc(
            subtotal,
            "TaxAmount",
            _money(
                group["tax"]
            ),
            {
                "currencyID": CURRENCY,
            },
        )

        category = _add_cac(
            subtotal,
            "TaxCategory",
        )

        _add_cbc(
            category,
            "ID",
            group["category"]["id"],
        )

        rate = _decimal(
            group["category"]["rate"]
        )

        if group["category"]["id"] != "O":
            _add_cbc(
                category,
                "Percent",
                _rate(rate),
            )

        tax_scheme = _add_cac(
            category,
            "TaxScheme",
        )

        _add_cbc(
            tax_scheme,
            "ID",
            VAT_SCHEME,
        )


# =========================================================
# MONETARY TOTAL
# =========================================================

def _add_monetary_total(
    root,
    lines,
):
    totals = _calculate_totals(lines)

    monetary = _add_cac(
        root,
        "LegalMonetaryTotal",
    )

    _add_cbc(
        monetary,
        "LineExtensionAmount",
        _money(
            totals["taxable_total"]
            + totals["discount_total"]
        ),
        {
            "currencyID": CURRENCY,
        },
    )

    _add_cbc(
        monetary,
        "AllowanceTotalAmount",
        _money(
            totals["discount_total"]
        ),
        {
            "currencyID": CURRENCY,
        },
    )

    _add_cbc(
        monetary,
        "TaxExclusiveAmount",
        _money(
            totals["taxable_total"]
        ),
        {
            "currencyID": CURRENCY,
        },
    )

    _add_cbc(
        monetary,
        "TaxInclusiveAmount",
        _money(
            totals["invoice_total"]
        ),
        {
            "currencyID": CURRENCY,
        },
    )

    _add_cbc(
        monetary,
        "PayableAmount",
        _money(
            totals["invoice_total"]
        ),
        {
            "currencyID": CURRENCY,
        },
    )


# =========================================================
# INVOICE LINE
# =========================================================

def _add_invoice_line(
    root,
    index,
    line,
):
    invoice_line = _add_cac(
        root,
        "InvoiceLine",
    )

    _add_cbc(
        invoice_line,
        "ID",
        str(index),
    )

    _add_cbc(
        invoice_line,
        "InvoicedQuantity",
        _qty(
            line["quantity"]
        ),
        {
            "unitCode": line.get(
                "unit",
                "PCE",
            )
        },
    )

    _add_cbc(
        invoice_line,
        "LineExtensionAmount",
        _money(
            line["net"]
        ),
        {
            "currencyID": CURRENCY,
        },
    )

    # -----------------------------------------------------
    # LINE DISCOUNT
    # -----------------------------------------------------

    if line["discount"] > 0:

        allowance = _add_cac(
            invoice_line,
            "AllowanceCharge",
        )

        _add_cbc(
            allowance,
            "ChargeIndicator",
            "false",
        )

        _add_cbc(
            allowance,
            "Amount",
            _money(
                line["discount"]
            ),
            {
                "currencyID": CURRENCY,
            },
        )

        _add_cbc(
            allowance,
            "BaseAmount",
            _money(
                line["subtotal"]
            ),
            {
                "currencyID": CURRENCY,
            },
        )

    # -----------------------------------------------------
    # ITEM
    # -----------------------------------------------------

    item = _add_cac(
        invoice_line,
        "Item",
    )

    _add_cbc(
        item,
        "Description",
        line["description"],
    )

    tax_category = _get_tax_category(
        line["tax_rate"]
    )

    classified_tax = _add_cac(
        item,
        "ClassifiedTaxCategory",
    )

    _add_cbc(
        classified_tax,
        "ID",
        tax_category["id"],
    )

    if tax_category["id"] != "O":
        _add_cbc(
            classified_tax,
            "Percent",
            _rate(
                tax_category["rate"]
            ),
        )

    tax_scheme = _add_cac(
        classified_tax,
        "TaxScheme",
    )

    _add_cbc(
        tax_scheme,
        "ID",
        VAT_SCHEME,
    )

    # -----------------------------------------------------
    # PRICE
    # -----------------------------------------------------

    price = _add_cac(
        invoice_line,
        "Price",
    )

    _add_cbc(
        price,
        "PriceAmount",
        _money(
            line["price"]
        ),
        {
            "currencyID": CURRENCY,
        },
    )


# =========================================================
# DOCUMENT LEVEL DISCOUNT
# =========================================================

def _add_document_discount(
    root,
    discount_total,
    lines,
):
    """
    Document-level discount is NOT emitted here.

    Discounts in the ERP are represented at invoice-line level.
    Emitting the same discount again at document level would
    double-count the allowance and break the ZATCA totals.

    The line-level AllowanceCharge elements are generated by
    _add_invoice_line().
    """

    return None


# =========================================================
# ADDITIONAL DOCUMENT REFERENCES
# =========================================================

def _add_icv(
    root,
    invoice_counter,
):
    """
    KSA-16 invoice counter value.

    ZATCA requires this value to contain digits only.
    """

    value = _digits_only(
        invoice_counter
    )

    if not value:
        raise ValueError(
            "Invoice counter value is required."
        )

    reference = _add_cac(
        root,
        "AdditionalDocumentReference",
    )

    _add_cbc(
        reference,
        "ID",
        "ICV",
    )

    _add_cbc(
        reference,
        "UUID",
        value,
    )


def _add_previous_invoice_hash(
    root,
    previous_invoice_hash,
):
    """
    KSA-13 Previous Invoice Hash.

    The value must be Base64 encoded SHA-256.
    """

    value = _clean(
        previous_invoice_hash
    )

    if not value:
        value = FIRST_INVOICE_PREVIOUS_HASH

    attachment_reference = _add_cac(
        root,
        "AdditionalDocumentReference",
    )

    _add_cbc(
        attachment_reference,
        "ID",
        "PIH",
    )

    attachment = _add_cac(
        attachment_reference,
        "Attachment",
    )

    embedded = _add_cbc(
        attachment,
        "EmbeddedDocumentBinaryObject",
        value,
        {
            "mimeCode": "text/plain",
        },
    )

    return embedded


def _add_qr_placeholder(root):
    """
    QR is generated by qr_service.py after hashing/signing.

    The QR element is intentionally created empty here so the
    hash/signature service can replace it later.

    QR data itself must not be included when calculating the
    invoice hash according to ZATCA rules.
    """

    reference = _add_cac(
        root,
        "AdditionalDocumentReference",
    )

    _add_cbc(
        reference,
        "ID",
        "QR",
    )

    attachment = _add_cac(
        reference,
        "Attachment",
    )

    _add_cbc(
        attachment,
        "EmbeddedDocumentBinaryObject",
        "",
        {
            "mimeCode": "text/plain",
        },
    )


# =========================================================
# MAIN XML BUILDER
# =========================================================

def build_invoice_xml(
    invoice,
    invoice_counter=None,
    previous_invoice_hash=None,
):
    """
    Build the base ZATCA UBL 2.1 XML.

    Parameters
    ----------
    invoice:
        SalesInvoice or POS Invoice.

    invoice_counter:
        KSA-16 invoice counter.
        If not supplied, the current invoice number is used
        as a temporary fallback for local XML testing.

        IMPORTANT:
        Before real ZATCA production submission, this value
        must come from the system's tamper-resistant invoice
        counter.

    previous_invoice_hash:
        KSA-13 previous invoice hash.
        If omitted, the official ZATCA first-invoice hash
        value is used.

    Returns
    -------
    xml.etree.ElementTree.Element
    """

    _validate_invoice_model(
        invoice
    )

    company = _get_company(
        invoice
    )

    customer = _get_customer(
        invoice
    )

    customer_type = _get_customer_type(
        customer
    )

    invoice_type = _get_invoice_type(
        customer
    )

    lines = _get_invoice_lines(
        invoice
    )

    if not lines:
        raise ValueError(
            "Invoice must contain at least one line."
        )

    invoice_number = _get_invoice_number(
        invoice
    )

    if invoice_counter is None:
        invoice_counter = invoice_number

    issue_datetime = _get_issue_datetime(
        invoice
    )

    # =====================================================
    # ROOT
    # =====================================================

    root = ET.Element(
        _ubl("Invoice"),
        {
            _tag(
                XSI_NS,
                "schemaLocation",
            ):
                (
                    f"{UBL_NS} "
                    "urn:oasis:names:specification:ubl:"
                    "schema:xsd:Invoice-2"
                )
        },
    )

    # =====================================================
    # BASIC INFORMATION
    # =====================================================

    _add_cbc(
        root,
        "UBLVersionID",
        "2.1",
    )

    _add_cbc(
        root,
        "ProfileID",
        PROFILE_ID,
    )

    _add_cbc(
        root,
        "ID",
        invoice_number,
    )

    _add_cbc(
        root,
        "UUID",
        _get_invoice_uuid(invoice),
    )

    _add_cbc(
        root,
        "IssueDate",
        issue_datetime.strftime(
            "%Y-%m-%d"
        ),
    )

    _add_cbc(
        root,
        "IssueTime",
        issue_datetime.strftime(
            "%H:%M:%S"
        ),
    )

    _add_cbc(
        root,
        "InvoiceTypeCode",
        invoice_type["code"],
        {
            "name": invoice_type["subtype"],
        },
    )

    _add_cbc(
        root,
        "DocumentCurrencyCode",
        CURRENCY,
    )

    _add_cbc(
        root,
        "TaxCurrencyCode",
        CURRENCY,
    )

    # =====================================================
    # SUPPLY DATE
    # =====================================================

    # ZATCA requires supply date for tax invoices.
    if not invoice_type["simplified"]:

        delivery = _add_cac(
            root,
            "Delivery",
        )

        _add_cbc(
            delivery,
            "ActualDeliveryDate",
            issue_datetime.strftime(
                "%Y-%m-%d"
            ),
        )

    # =====================================================
    # ICV / PIH / QR
    # =====================================================

    _add_icv(
        root,
        invoice_counter,
    )

    _add_previous_invoice_hash(
        root,
        previous_invoice_hash,
    )

    _add_qr_placeholder(
        root
    )

    # =====================================================
    # PARTIES
    # =====================================================

    _add_supplier_party(
        root,
        company,
    )

    _add_customer_party(
        root,
        customer,
    )

    # =====================================================
    # PAYMENT
    # =====================================================

    _add_payment_means(
        root
    )

    # =====================================================
    # TAX
    # =====================================================

    _add_tax_total(
        root,
        lines,
    )

    # =====================================================
    # TOTALS
    # =====================================================

    _add_monetary_total(
        root,
        lines,
    )

    # =====================================================
    # LINES
    # =====================================================

    for index, line in enumerate(
        lines,
        start=1,
    ):
        _add_invoice_line(
            root,
            index,
            line,
        )

    return root


# =========================================================
# SERIALIZATION
# =========================================================

def serialize_xml(root):
    """
    Serialize XML without changing the business structure.
    """

    ET.indent(
        root,
        space="  ",
    )

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )


# =========================================================
# PUBLIC API
# =========================================================

def generate_invoice_xml(
    invoice,
    invoice_counter=None,
    previous_invoice_hash=None,
):
    """
    Generate XML string for a SalesInvoice or POS Invoice.
    """

    root = build_invoice_xml(
        invoice,
        invoice_counter=invoice_counter,
        previous_invoice_hash=previous_invoice_hash,
    )

    return serialize_xml(
        root
    )


# =========================================================
# SAVE XML
# =========================================================

def save_invoice_xml(
    invoice,
    file_path,
    invoice_counter=None,
    previous_invoice_hash=None,
):
    """
    Generate and save invoice XML.
    """

    xml = generate_invoice_xml(
        invoice,
        invoice_counter=invoice_counter,
        previous_invoice_hash=previous_invoice_hash,
    )

    with open(
        file_path,
        "wb",
    ) as file:
        file.write(xml)

    return file_path