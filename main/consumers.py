import aioredis
import logging
from django.shortcuts import get_object_or_404
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from . import models
import asyncio
import json
from django.urls import reverse
from channels.exceptions import StopConsumer

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    EMPLOYEE = 2
    CLIENT = 1

    def get_user_type(self, user, order_id):
        order = get_object_or_404(models.Order, pk=order_id)

        if not user.is_anonymous:
            if user.is_employee:
                order.last_spoken_to = user
                order.save()
                return ChatConsumer.EMPLOYEE
            elif order.user == user:
                return ChatConsumer.CLIENT
            else:
                return None

    async def connect(self):
        self.order_id = self.scope["url_route"]["kwargs"][
            "order_id"
        ]
        self.room_group_name = (
                "customer-service_%s" % self.order_id
        )
        authorized = False
        if self.scope["user"].is_anonymous:
            await self.close()

        user_type = await database_sync_to_async(
            self.get_user_type
        )(self.scope["user"], self.order_id)

        if user_type == ChatConsumer.EMPLOYEE:
            logger.info(
                "Opening chat stream for employee %s",
                self.scope["user"],
            )
            authorized = True
        elif user_type == ChatConsumer.CLIENT:
            logger.info(
                "Opening chat stream for client %s",
                self.scope["user"],
            )
            authorized = True
        else:
            logger.info(
                "Unauthorized connection from %s",
                self.scope["user"],
            )
            await self.close()

        if authorized:
            self.r_conn = await aioredis.create_redis(
                'redis://localhost'
            )

            await self.channel_layer.group_add(
                self.room_group_name, self.channel_name
            )
            await self.accept()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_join",
                    "username": self.scope["user"].get_full_name(),
                },
            )

    async def disconnect(self, close_code):
        if not self.scope["user"].is_anonymous:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_leave",
                    "username": self.scope["user"].get_full_name(),
                },
            )
            logger.info(
                "Closing chat stream for user %s",
                self.scope["user"],
            )
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive_json(self, content):
        typ = content.get("type")
        if typ == "message":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "username": self.scope[
                        "user"
                    ].get_full_name(),
                    "message": content["message"],
                },
            )
        elif typ == "heartbeat":
            await self.r_conn.setex(
                "%s_%s"
                % (
                    self.room_group_name,
                    self.scope["user"].email,
                ),
                10,
                "1",
            )

    async def chat_message(self, event):
        await self.send_json(event)

    async def chat_join(self, event):
        await self.send_json(event)

    async def chat_leave(self, event):
        await self.send_json(event)



class ChatNotifyConsumer(AsyncJsonWebsocketConsumer):
    def is_employee_func(self, user):
        return not user.is_anonymous and user.is_employee

    async def connect(self):
        await self.accept()

        is_employee = await database_sync_to_async(
            self.is_employee_func
        )(self.scope["user"])

        if is_employee:
            logger.info(
                "Opening notify stream for user %s and params %s",
                self.scope.get("user"),
                self.scope.get("query_string"),
            )
        else:
            logger.info(
                "Unauthorized notify stream for user %s and params %s",
                self.scope.get("user"),
                self.scope.get("query_string"),
            )
            raise StopConsumer("Unauthorized")

        self.streaming = True

        r_conn = await aioredis.create_redis('redis://localhost')
        while self.streaming:
            active_chats = await r_conn.keys(
                "customer-service_*"
            )

            presences = {}
            for i in active_chats:
                _, order_id, user_email = i.decode("utf8").split(
                    "_"
                )
                if order_id in presences:
                    presences[order_id].append(user_email)
                else:
                    presences[order_id] = [user_email]

            data = []
            for order_id, emails in presences.items():
                data.append(
                    {
                        "link": reverse(
                            "cs_chat",
                            kwargs={"order_id": order_id}
                        ),
                        "text": "%s (%s)"
                                % (order_id, ", ".join(emails)),
                    }
                )

            payload = data
            logger.info(
                "Broadcasting presence info to user %s",
                self.scope["user"],
            )

            await self.send_json(payload)

    async def disconnect(self, close_code):
        logger.info(
            "Closing notify stream for user %s",
            self.scope.get("user"),
        )
        self.streaming = False