import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from ecommerce.models import Store


class StoreNotificationConsumer(AsyncWebsocketConsumer):

    # ==========================================================
    # اتصال WebSocket
    # ==========================================================

    async def connect(self):

        print("========================================")
        print("WEBSOCKET CONNECT ATTEMPT")
        print("========================================")

        user = self.scope.get("user")

        print("USER:", user)
        print(
            "AUTHENTICATED:",
            getattr(user, "is_authenticated", None),
        )
        print(
            "USERNAME:",
            getattr(user, "username", None),
        )

        if not user or user.is_anonymous:

            print("WEBSOCKET REJECT: USER ANONYMOUS")

            await self.close()
            return

        # ======================================================
        # الحصول على متجر المستخدم
        # ======================================================

        try:

            print("STEP 1: Getting store...")

            store = await self.get_user_store(user)

            if not store:

                print("WEBSOCKET REJECT: STORE NOT FOUND")

                await self.close()
                return

            print("STORE:", store)
            print("STORE ID:", store.id)

        except Exception as e:

            print("========================================")
            print("WEBSOCKET CONNECT ERROR")
            print("ERROR TYPE:", type(e).__name__)
            print("ERROR:", str(e))
            print("========================================")

            await self.close()
            return

        # ======================================================
        # حفظ بيانات المتجر
        # ======================================================

        self.store = store

        self.store_group_name = (
            f"store_notifications_{store.id}"
        )

        print(
            "STEP 2: STORE GROUP:",
            self.store_group_name,
        )

        # ======================================================
        # Redis / Channels
        # ======================================================

        try:

            await self.channel_layer.group_add(
                self.store_group_name,
                self.channel_name,
            )

            print("STEP 3: GROUP ADD OK")

            await self.accept()

            print("========================================")
            print("WEBSOCKET ACCEPTED")
            print("USER:", user.username)
            print("STORE:", store.id)
            print("GROUP:", self.store_group_name)
            print("CHANNEL:", self.channel_name)
            print("========================================")

        except Exception as e:

            print("========================================")
            print("WEBSOCKET CHANNEL ERROR")
            print("ERROR TYPE:", type(e).__name__)
            print("ERROR:", str(e))
            print("========================================")

            await self.close()

    # ==========================================================
    # استقبال رسائل من المتصفح
    # ==========================================================

    async def receive(self, text_data=None, bytes_data=None):

        print("========================================")
        print("WEBSOCKET RECEIVE")
        print("TEXT:", text_data)
        print("BYTES:", bytes_data)
        print("========================================")

        if text_data:

            try:

                data = json.loads(text_data)

                # ------------------------------------------------
                # Ping من المتصفح
                # ------------------------------------------------

                if data.get("type") == "ping":

                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "pong"
                            },
                            ensure_ascii=False,
                        )
                    )

                    print("PING -> PONG")

            except json.JSONDecodeError:

                print("INVALID JSON")

    # ==========================================================
    # جلب متجر المستخدم
    # ==========================================================

    @database_sync_to_async
    def get_user_store(self, user):

        try:

            profile = user.profile

            company = profile.company

            print("COMPANY:", company)
            print("COMPANY ID:", company.id)

            store = (
                Store.objects
                .filter(company=company)
                .first()
            )

            return store

        except Exception as e:

            print(
                "GET USER STORE ERROR:",
                type(e).__name__,
                str(e),
            )

            return None

    # ==========================================================
    # استقبال إشعار طلب جديد
    # ==========================================================

    async def new_order(self, event):

        print("========================================")
        print("NEW ORDER EVENT")
        print("EVENT:", event)
        print("========================================")

        await self.send(
            text_data=json.dumps(
                {
                    "type": "new_order",

                    "notification_id":
                        event.get("notification_id"),

                    "title":
                        event.get(
                            "title",
                            "طلب جديد 🛒",
                        ),

                    "message":
                        event.get(
                            "message",
                            "تم استلام طلب جديد",
                        ),

                    "order_id":
                        event.get("order_id"),

                    "order_no":
                        event.get("order_no"),

                },
                ensure_ascii=False,
            )
        )

    # ==========================================================
    # قطع الاتصال
    # ==========================================================

    async def disconnect(self, close_code):

        print("========================================")
        print("WEBSOCKET DISCONNECT")
        print("CLOSE CODE:", close_code)
        print("========================================")

        if hasattr(self, "store_group_name"):

            try:

                await self.channel_layer.group_discard(
                    self.store_group_name,
                    self.channel_name,
                )

                print("GROUP DISCARD OK")

            except Exception as e:

                print(
                    "WEBSOCKET GROUP DISCARD ERROR:",
                    type(e).__name__,
                    str(e),
                )
