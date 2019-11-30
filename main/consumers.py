import asyncio
import logging

import aioredis
import aiohttp
from channels.db import database_sync_to_async
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.generic.http import AsyncHttpConsumer
from django.shortcuts import get_object_or_404
from django.urls import reverse

from . import models

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('consumers.log')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

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
        self.employee = False

        if self.scope["user"].is_anonymous:
            await self.close()

        self.user_type = await database_sync_to_async(
            self.get_user_type
        )(self.scope["user"], self.order_id)

        if self.user_type == ChatConsumer.EMPLOYEE:
            logger.info(
                "Opening chat stream for employee %s",
                self.scope["user"],
            )
            authorized = True

        elif self.user_type == ChatConsumer.CLIENT:
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
                "{}_{}_{}".format(
                    self.room_group_name,
                    self.scope["user"].email,
                    'Operator' if self.user_type == 2 else 'Customer'
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

        r_conn = await aioredis.create_redis_pool('redis://localhost')
        while self.streaming:
            active_chats = await r_conn.keys(
                "customer-service_*"
            )

            presences = {}
            for i in active_chats:
                _, order_id, user_email, status = i.decode("utf8").split(
                    "_"
                )

                if order_id in presences:
                    presences[order_id]['emails'].append(user_email)
                    # If there already is an operator - do not change the state of chat
                    if presences[order_id]['status'] != 'Operator':
                        presences[order_id]['status'] = status
                else:
                    presences[order_id] = {'emails': [user_email], 'status': status}

            payload = []
            for order_id, data in presences.items():
                payload.append(
                    {
                        "link": reverse(
                            "cs_chat",
                            kwargs={"order_id": order_id}
                        ),
                        "text": "%s (%s)"
                                % (order_id, ", ".join(data['emails'])),
                        "status": data['status'],
                    }
                )

            logger.info(
                "Broadcasting presence info to user %s",
                self.scope["user"],
            )

            await self.send_json(payload)
            await asyncio.sleep(5)

    async def disconnect(self, close_code):
        logger.info(
            "Closing notify stream for user %s",
            self.scope.get("user"),
        )
        self.streaming = False


class OrderTrackerConsumer(AsyncHttpConsumer):

    @database_sync_to_async
    def verify_user(self, user, order_id):
        order = get_object_or_404(models.Order, pk=order_id)
        return order.user == user

    async def query_remote_server(self, order_id):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://pastebin.com/raw/b2Niddnk'
            ) as resp:
                return await resp.read()

    async def handle(self, body):
        self.order_id = self.scope['url_route']['kwargs'][
            'order_id'
        ]

        is_authorized = await self.verify_user(self.scope['user'], self.order_id)

        if is_authorized:
            logger.info(
                f'Order tracking request for user '
                f'{self.scope.get("user")} and'
                f' order {self.order_id}',
            )
            payload = await self.query_remote_server(self.order_id)
            logger.info(
                f'Order tracking response {payload}'
                f' for user {self.scope.get("user")} and'
                f' order {self.order_id}',
            )
            await self.send_response(200, payload)
        else:
            logger.error(
                f'Unauthorized user tracking attempt. OrderID: {self.order_id}. User: {self.scope["cookies"]["username"]}'
            )
            raise StopConsumer()