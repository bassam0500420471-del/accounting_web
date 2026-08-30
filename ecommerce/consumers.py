import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from ecommerce.models import Store


class StoreNotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        print("========================================")
        print("WEBSOCKET CONNECT ATTEMPT")
        print("========================================")

        user = self.scope.get("user")

        print("USER:", user)
        print(
            "AUTHENTICATED:",
            getattr(user, "is_authenticated", None)
        )
        print(
            "USERNAME:",
            getattr(user, "username", None)
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
        # إعداد مجموعة الإشعارات
        # ======================================================

        self.store = store

        self.store_group_name = (
            f"store_notifications_{store.id}"
        )

        print(
            "STEP 2: STORE GROUP:",
            self.store_group_name
        )

        # ======================================================
        # الانضمام إلى مجموعة المتجر
        # ======================================================

        try:

            await self.channel_layer.group_add(
                self.store_group_name,
                self.channel_name,
            )

            print("STEP 3: GROUP ADD OK")

            await self.accept()

            print("========================================")
            print("WEBSOCKET CONNECTED SUCCESSFULLY")
            print("USER:", user.username)
            print("STORE:", store.id)
            print("GROUP:", self.store_group_name)
            print("========================================")

        except Exception as e:

            print("========================================")
            print("WEBSOCKET CHANNEL ERROR")
            print("ERROR TYPE:", type(e).__name__)
            print("ERROR:", str(e))
            print("========================================")

            await self.close()


    # ==========================================================
    # جلب المتجر المرتبط بالشركة
    # ==========================================================

    @database_sync_to_async
    def get_user_store(self, user):

        try:

            profile = user.profile

            company = profile.company

            print("COMPANY:", company)
            print("COMPANY ID:", company.id)

            store = Store.objects.filter(
                company=company
            ).first()

            return store

        except Exception as e:

            print(
                "GET USER STORE ERROR:",
                type(e).__name__,
                str(e),
            )

            return None


    # ==========================================================
    # قطع الاتصال
    # ==========================================================

    async def disconnect(self, close_code):

        if hasattr(self, "store_group_name"):

            try:

                await self.channel_layer.group_discard(
                    self.store_group_name,
                    self.channel_name,
                )

            except Exception as e:

                print(
                    "WEBSOCKET GROUP DISCARD ERROR:",
                    type(e).__name__,
                    str(e),
                )

        print(
            "WEBSOCKET DISCONNECTED:",
            close_code,
        )


    # ==========================================================
    # استقبال إشعار طلب جديد
    # ==========================================================

    async def new_order(self, event):

        await self.send(
            text_data=json.dumps(
                {
                    "type": "new_order",

                    "notification_id":
                        event.get("notification_id"),

                    "title":
                        event.get(
                            "title",
                            "طلب جديد 🛒"
                        ),

                    "message":
                        event.get(
                            "message",
                            "تم استلام طلب جديد"
                        ),

                    "order_id":
                        event.get("order_id"),

                    "order_no":
                        event.get("order_no"),

                },
                ensure_ascii=False,
            )
        )
