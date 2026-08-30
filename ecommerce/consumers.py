import json

from channels.generic.websocket import AsyncWebsocketConsumer


class StoreNotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        user = self.scope.get("user")

        if not user or user.is_anonymous:
            await self.close()
            return

        try:
            company = user.profile.company
            store = company.store
        except Exception:
            await self.close()
            return

        self.store = store
        self.store_group_name = f"store_notifications_{store.id}"

        await self.channel_layer.group_add(
            self.store_group_name,
            self.channel_name,
        )

        await self.accept()

        print(
            "WEBSOCKET CONNECTED:",
            user.username,
            "STORE:",
            store.id,
        )


    async def disconnect(self, close_code):

        if hasattr(self, "store_group_name"):

            await self.channel_layer.group_discard(
                self.store_group_name,
                self.channel_name,
            )

        print(
            "WEBSOCKET DISCONNECTED:",
            close_code,
        )


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