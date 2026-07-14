import os
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_private_key():
    """
    إنشاء المفتاح الخاص
    """

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    return private_key


def generate_csr(
    private_key,
    company_name,
    common_name,
    vat_number=None,
    commercial_number=None,
):

    """
    إنشاء شهادة CSR
    """

    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(
            x509.Name(
                [
                    x509.NameAttribute(
                        NameOID.COMMON_NAME,
                        common_name,
                    ),
                    x509.NameAttribute(
                        NameOID.ORGANIZATION_NAME,
                        company_name,
                    ),
                ]
            )
        )
        .sign(
            private_key,
            hashes.SHA256()
        )
    )

    return csr


def save_private_key(private_key, path):
    """
    حفظ المفتاح الخاص
    """

    with open(path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )


def save_csr(csr, path):
    """
    حفظ CSR
    """

    with open(path, "wb") as f:
        f.write(
            csr.public_bytes(
                serialization.Encoding.PEM
            )
        )
def generate_and_save_zatca_files(
    company_id,
    company_name,
    common_name,
    vat_number=None,
    commercial_number=None,
    media_root=None,
):
    """
    إنشاء وحفظ ملفات ZATCA للشركة
    """

    zatca_path = os.path.join(
        media_root,
        "zatca",
        f"company_{company_id}"
    )

    os.makedirs(
        zatca_path,
        exist_ok=True
    )

    private_key = generate_private_key()

    csr = generate_csr(
        private_key,
        company_name,
        common_name,
        vat_number,
        commercial_number,
    )

    private_key_path = os.path.join(
        zatca_path,
        "private_key.pem"
    )

    csr_path = os.path.join(
        zatca_path,
        "csr.pem"
    )

    save_private_key(
        private_key,
        private_key_path
    )

    save_csr(
        csr,
        csr_path
    )

    return {
        "private_key_path": private_key_path,
        "csr_path": csr_path,
    }