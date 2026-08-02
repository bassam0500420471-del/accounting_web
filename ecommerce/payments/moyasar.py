import requests
from decimal import Decimal, ROUND_HALF_UP

MOYASAR_API_URL = "https://api.moyasar.com/v1/payments"


def create_payment(
    amount,
    description,
    secret_key,
    callback_url,
    token,
):
    """
    إنشاء عملية دفع في Moyasar باستخدام Card Token
    """

    amount = (
        Decimal(str(amount))
        .quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )

    amount_halalas = int(amount * 100)

    print("==============================")
    print("MOYASAR AMOUNT:", amount)
    print("MOYASAR HALALAS:", amount_halalas)
    print("==============================")

    data = {
        "amount": amount_halalas,
        "currency": "SAR",
        "description": description,
        "callback_url": callback_url,
        "source[type]": "token",
        "source[token]": token,
    }

    try:
        response = requests.post(
            MOYASAR_API_URL,
            auth=(secret_key, ""),
            data=data,
            timeout=15,
        )

        response.raise_for_status()

    except requests.RequestException as e:

        print("==============================")
        print("MOYASAR CONNECTION ERROR")
        print(e)
        print("==============================")

        return {
            "success": False,
            "error": str(e),
        }

    payment = response.json()

    print("==============================")
    print("MOYASAR RESPONSE")
    print(payment)
    print("==============================")

    return {
        "success": True,
        "id": payment.get("id"),
        "status": payment.get("status"),
        "redirect": payment.get("source", {}).get("transaction_url"),
        "payment": payment,
    }


def verify_payment(payment_id, secret_key):
    """
    التحقق من عملية الدفع مباشرة من سيرفر Moyasar
    """

    try:

        response = requests.get(
            f"{MOYASAR_API_URL}/{payment_id}",
            auth=(secret_key, ""),
            timeout=15,
        )

        response.raise_for_status()

    except requests.RequestException as e:

        print("==============================")
        print("VERIFY PAYMENT ERROR")
        print(e)
        print("==============================")

        return {
            "success": False,
            "error": str(e),
        }

    payment = response.json()

    return {
        "success": True,
        "payment": payment,
        "status": payment.get("status"),
        "amount": payment.get("amount"),
        "currency": payment.get("currency"),
        "source_type": payment.get("source", {}).get("type"),
    }