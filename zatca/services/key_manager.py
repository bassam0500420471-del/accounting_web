from cryptography.hazmat.primitives import serialization


def generate_public_key(private_key_path, public_key_path):
    """
    استخراج المفتاح العام من المفتاح الخاص
    """

    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
        )


    public_key = private_key.public_key()


    with open(public_key_path, "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )


    return public_key_path