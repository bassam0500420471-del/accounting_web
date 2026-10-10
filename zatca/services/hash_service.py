import base64
import copy

from lxml import etree
import xmlsec


# =========================================================
# NAMESPACES
# =========================================================

CAC_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:"
    "CommonAggregateComponents-2"
)

CBC_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:"
    "CommonBasicComponents-2"
)

EXT_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:"
    "CommonExtensionComponents-2"
)

DS_NS = "http://www.w3.org/2000/09/xmldsig#"


NS = {
    "cac": CAC_NS,
    "cbc": CBC_NS,
    "ext": EXT_NS,
    "ds": DS_NS,
}


# =========================================================
# FIRST INVOICE PREVIOUS HASH
# =========================================================

FIRST_INVOICE_HASH = (
    "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0Njcy"
    "OWQ3M2EyN2ZiNTdlOQ=="
)


# =========================================================
# XML PARSER
# =========================================================

def _parse_xml(xml):
    """
    Convert XML input into an lxml ElementTree.

    Supported input:
        - str
        - bytes
        - lxml Element
        - lxml ElementTree
    """

    if isinstance(xml, etree._ElementTree):
        return copy.deepcopy(xml)

    if isinstance(xml, etree._Element):
        return etree.ElementTree(copy.deepcopy(xml))

    if isinstance(xml, str):
        xml = xml.encode("utf-8")

    if not isinstance(xml, (bytes, bytearray)):
        raise TypeError(
            "xml must be str, bytes, lxml Element, or lxml ElementTree"
        )

    parser = etree.XMLParser(
        remove_blank_text=False,
        resolve_entities=False,
        no_network=True,
    )

    root = etree.fromstring(bytes(xml), parser)

    return etree.ElementTree(root)


# =========================================================
# REMOVE UBLEXTENSIONS
# =========================================================

def _remove_ubl_extensions(root):
    """
    ZATCA hashing rule:

        Remove Invoice/UBLExtensions before hashing.

    Important:
        Invoice itself is normally the root element.
        Therefore the XPath must include the root's
        descendants without requiring Invoice to be
        a child of itself.
    """

    nodes = root.xpath(
        ".//*[local-name()='UBLExtensions']"
    )

    for node in nodes:
        parent = node.getparent()

        if parent is not None:
            parent.remove(node)


# =========================================================
# REMOVE QR REFERENCE
# =========================================================

def _remove_qr_reference(root):
    """
    ZATCA hashing rule:

        Remove AdditionalDocumentReference where
        cbc:ID = QR.
    """

    nodes = root.xpath(
        ".//*[local-name()='AdditionalDocumentReference']"
    )

    for node in nodes:
        qr_ids = node.xpath(
            "./*[local-name()='ID'][normalize-space(text())='QR']"
        )

        if not qr_ids:
            continue

        parent = node.getparent()

        if parent is not None:
            parent.remove(node)


# =========================================================
# REMOVE SIGNATURE
# =========================================================

def _remove_signature(root):
    """
    ZATCA hashing rule:

        Remove Signature before hashing.

    The XPath intentionally searches for Signature
    descendants regardless of namespace prefix.
    """

    nodes = root.xpath(
        ".//*[local-name()='Signature']"
    )

    for node in nodes:
        parent = node.getparent()

        if parent is not None:
            parent.remove(node)


# =========================================================
# PREPARE XML FOR ZATCA HASH
# =========================================================

def prepare_invoice_for_hash(xml):
    """
    Prepare invoice according to ZATCA hashing rules.

    Removes:

        1. UBLExtensions
        2. QR AdditionalDocumentReference
        3. Signature

    After removing the excluded nodes, normalize only the
    whitespace-only text/tail nodes that remain around the
    removed structures.

    Real text values inside the invoice are preserved.
    """

    tree = _parse_xml(xml)

    root = tree.getroot()

    # -----------------------------------------------------
    # Remove ZATCA-excluded elements
    # -----------------------------------------------------

    _remove_ubl_extensions(root)
    _remove_qr_reference(root)
    _remove_signature(root)


    return tree
# =========================================================
# XMLDSIG C14N11 + SHA256
# =========================================================

def _calculate_digest_with_xmlsec(tree):
    """
    Use XMLDSig through python-xmlsec to calculate the
    SHA-256 DigestValue after C14N11.

    Reference transforms:

        ENVELOPED
        C14N11

    The temporary Signature exists only in memory and is
    removed from the referenced data by the ENVELOPED
    transform.

    The resulting DigestValue is returned as Base64.
    """

    root = tree.getroot()

    # -----------------------------------------------------
    # Safety checks
    # -----------------------------------------------------

    if not hasattr(xmlsec.Transform, "C14N11"):
        raise RuntimeError(
            "Installed xmlsec does not provide C14N11."
        )

    if not hasattr(xmlsec.Transform, "ENVELOPED"):
        raise RuntimeError(
            "Installed xmlsec does not provide ENVELOPED."
        )

    if not hasattr(xmlsec.Transform, "SHA256"):
        raise RuntimeError(
            "Installed xmlsec does not provide SHA256."
        )

    if not hasattr(xmlsec.Transform, "HMAC_SHA256"):
        raise RuntimeError(
            "Installed xmlsec does not provide HMAC_SHA256."
        )

    # -----------------------------------------------------
    # Create temporary XMLDSig Signature
    # -----------------------------------------------------

    signature_node = xmlsec.template.create(
        root,
        xmlsec.Transform.C14N11,
        xmlsec.Transform.HMAC_SHA256,
        ns="ds",
    )

    root.append(signature_node)

    # -----------------------------------------------------
    # Reference the whole Invoice document
    # -----------------------------------------------------

    reference = xmlsec.template.add_reference(
        signature_node,
        xmlsec.Transform.SHA256,
        uri="",
    )

    # -----------------------------------------------------
    # Remove the temporary Signature from the referenced
    # data using the XMLDSig enveloped transform.
    # -----------------------------------------------------

    xmlsec.template.add_transform(
        reference,
        xmlsec.Transform.ENVELOPED,
    )

    # -----------------------------------------------------
    # ZATCA requires C14N 1.1
    # -----------------------------------------------------

    xmlsec.template.add_transform(
        reference,
        xmlsec.Transform.C14N11,
    )

    # -----------------------------------------------------
    # Temporary HMAC key
    #
    # This key exists only so xmlsec can execute the
    # XMLDSig signing pipeline and calculate DigestValue.
    #
    # It is never stored or returned.
    # -----------------------------------------------------

    key = xmlsec.Key.generate(
        xmlsec.KeyData.HMAC,
        256,
        xmlsec.KeyDataType.SESSION,
    )

    context = xmlsec.SignatureContext()

    context.key = key

    # -----------------------------------------------------
    # Execute XMLDSig
    # -----------------------------------------------------

    try:
        context.sign(signature_node)

        # -------------------------------------------------
        # Extract DigestValue
        # -------------------------------------------------

        digest_node = signature_node.find(
            ".//{%s}DigestValue" % DS_NS
        )

        if digest_node is None:
            raise RuntimeError(
                "xmlsec did not generate DigestValue."
            )

        digest_value = (
            digest_node.text or ""
        ).strip()

        if not digest_value:
            raise RuntimeError(
                "xmlsec generated an empty DigestValue."
            )

        return digest_value

    finally:
        # ---------------------------------------------
        # Always remove temporary Signature
        # ---------------------------------------------

        parent = signature_node.getparent()

        if parent is not None:
            parent.remove(signature_node)


# =========================================================
# PUBLIC HASH FUNCTIONS
# =========================================================

def calculate_invoice_hash_bytes(xml):
    """
    Return the SHA-256 digest as raw 32 bytes.
    """

    tree = prepare_invoice_for_hash(xml)

    digest_base64 = _calculate_digest_with_xmlsec(tree)

    try:
        return base64.b64decode(
            digest_base64,
            validate=True,
        )

    except Exception as exc:
        raise RuntimeError(
            "Invalid Base64 DigestValue generated by xmlsec."
        ) from exc


def calculate_invoice_hash(xml):
    """
    Return the ZATCA invoice hash as Base64.
    """

    tree = prepare_invoice_for_hash(xml)

    return _calculate_digest_with_xmlsec(tree)


def calculate_invoice_hash_hex(xml):
    """
    Return the SHA-256 digest as hexadecimal.
    """

    digest_bytes = calculate_invoice_hash_bytes(xml)

    return digest_bytes.hex()


# =========================================================
# XML USED FOR HASH
# =========================================================

def get_invoice_xml_for_hash(xml):
    """
    Return the prepared XML after removing:

        - UBLExtensions
        - QR
        - Signature

    This is useful for inspection/testing.

    It is NOT the canonicalized XML.
    """

    tree = prepare_invoice_for_hash(xml)

    return etree.tostring(
        tree.getroot(),
        encoding="utf-8",
        xml_declaration=False,
        with_tail=False,
    )


# =========================================================
# CANONICAL HASH HELPER
# =========================================================

def get_canonical_invoice_xml(xml):
    """
    Compatibility helper.

    lxml's normal C14N method is not used here because
    the ZATCA implementation requires C14N 1.1.

    The actual C14N11 operation is performed internally
    by xmlsec while generating DigestValue.

    Therefore this function returns the prepared XML only.

    It MUST NOT be treated as the canonical byte sequence
    used for the final ZATCA hash.
    """

    return get_invoice_xml_for_hash(xml)


# =========================================================
# FIRST INVOICE HASH
# =========================================================

def get_first_invoice_hash():
    """
    Return the official ZATCA previous-invoice hash for
    the first invoice in the chain.
    """

    return FIRST_INVOICE_HASH
