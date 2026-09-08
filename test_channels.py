import os
import asyncio

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "accounting_web_project.settings"
)

import django
django.setup()

from channels.layers import get_channel_layer


async def test():
    print("1. START")

    layer = get_channel_layer()

    channel = await layer.new_channel()
    print("2. CHANNEL:", channel)

    await layer.group_add(
        "store_notifications_4",
        channel
    )
    print("3. GROUP ADD OK")

    await layer.group_send(
        "store_notifications_4",
        {
            "type": "new_order",
            "notification_id": 999999,
            "title": "اختبار WebSocket",
            "message": "HELLO",
            "order_id": 123,
            "order_no": "TEST-123",
        }
    )
    print("4. GROUP SEND OK")

    print("5. WAITING FOR MESSAGE...")

    try:
        message = await asyncio.wait_for(
            layer.receive(channel),
            timeout=10
        )

        print("6. MESSAGE RECEIVED:")
        print(message)

    except asyncio.TimeoutError:
        print("6. RECEIVE TIMEOUT")

    await layer.group_discard(
        "store_notifications_4",
        channel
    )

    print("7. GROUP DISCARD OK")


asyncio.run(test())