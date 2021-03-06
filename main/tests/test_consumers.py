import asyncio
import json
from django.contrib.auth.models import Group
from django.test import TestCase
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator, HttpCommunicator
from main import consumers
from main import factories
from unittest.mock import MagicMock, patch


class TestConsumers(TestCase):
    def test_chat_between_two_users_works(self):
        def init_db():
            user = factories.UserFactory(
                email='soap@task.force',
                first_name='Top',
                last_name='Secret',
            )
            order = factories.OrderFactory(user=user)
            cs_user = factories.UserFactory(
                email='price@task.force',
                first_name='Off',
                last_name='Records',
                is_staff=True,
            )
            employees, _ = Group.objects.get_or_create(
                name='Employees'
            )
            cs_user.groups.add(employees)

            return user, order, cs_user

        async def test_body():
            user, order, cs_user = await database_sync_to_async(
                init_db
            )()

            communicator = WebsocketCommunicator(
                consumers.ChatConsumer,
                f'/ws/customer-service/{order.id}/',
            )
            communicator.scope['user'] = user
            communicator.scope['url_route'] = {
                'kwargs': {'order_id': order.id}
            }
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            cs_communicator = WebsocketCommunicator(
                consumers.ChatConsumer,
                f'/ws/customer-service/{order.id}/',
            )
            cs_communicator.scope['user'] = cs_user
            cs_communicator.scope['url_route'] = {
                'kwargs': {'order_id': order.id}
            }
            connected, _ = await cs_communicator.connect()
            self.assertTrue(connected)

            await communicator.send_json_to(
                {
                    'type': 'message',
                    'message': 'hello task force 141',
                }
            )

            await asyncio.sleep(1)

            await cs_communicator.send_json_to(
                {'type': 'message', 'message': 'hello rangers'}
            )

            self.assertEqual(
                await communicator.receive_json_from(),
                {'type': 'chat_join', 'username': 'Top Secret'},
            )

            self.assertEqual(
                await communicator.receive_json_from(),
                {'type': 'chat_join', 'username': 'Off Records'},
            )

            self.assertEqual(
                await communicator.receive_json_from(),
                {
                    'type': 'chat_message',
                    'username': 'Top Secret',
                    'message': 'hello task force 141',
                }
            )

            self.assertEqual(
                await communicator.receive_json_from(),
                {
                    'type': 'chat_message',
                    'username': 'Off Records',
                    'message': 'hello rangers',
                }
            )

            await communicator.disconnect()
            await cs_communicator.disconnect()

            order.refresh_from_db()
            self.assertEqual(order.last_spoken_to, cs_user)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_body())

    def test_chat_presence_works(self):
        def init_db():
            user = factories.UserFactory(
                email="user2@site.com",
                first_name="John",
                last_name="Smith",
            )
            order = factories.OrderFactory(user=user)
            cs_user = factories.UserFactory(
                email="customerservice2@booktime.domain",
                first_name="Adam",
                last_name="Ford",
                is_staff=True,
            )
            employees, _ = Group.objects.get_or_create(
                name="Employees"
            )
            cs_user.groups.add(employees)

            return user, order, cs_user

        async def test_body():
            user, order, notify_user = await database_sync_to_async(
                init_db
            )()

            communicator = WebsocketCommunicator(
                consumers.ChatConsumer,
                "/ws/customer-service/%d/" % order.id,
            )
            communicator.scope["user"] = user
            communicator.scope["url_route"] = {
                "kwargs": {"order_id": order.id}
            }
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await communicator.send_json_to(
                {"type": "heartbeat"}
            )
            await communicator.disconnect()

            communicator = WebsocketCommunicator(
                consumers.ChatNotifyConsumer,
                "ws/customer-service/notify/",
            )
            communicator.scope["user"] = notify_user

            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            response = await communicator.receive_json_from()

            self.assertEqual(
                response,
                [
                    {
                        "link": f"/customer-service/{order.id}/",
                        "text": f"{order.id} (user2@site.com)",
                    }
                ]
            )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_body())

    def test_order_tracker_works(self):
        def init_db():
            user = factories.UserFactory(
                email='mobiletracker@site.com'
            )
            order = factories.OrderFactory(user=user)
            return user, order

        async def test_body():
            user, order = await database_sync_to_async(
                init_db
            )()

            awaitable_requestor = asyncio.coroutine(
                MagicMock(return_value=b'SHIPPED')
            )

            with patch.object(
                consumers.OrderTrackerConsumer, 'query_remote_server'
            ) as mock_requestor:
                mock_requestor.side_effect = awaitable_requestor
                communicator = HttpCommunicator(
                    consumers.OrderTrackerConsumer,
                    'GET',
                    f'/mobile-api/my-orders/{order.id}/tracker/'
                )
                communicator.scope['user'] = user
                communicator.scope['url_route'] = {
                    'kwargs': {'order_id': order.id}
                }
                response = await communicator.get_response()
                data = response['body'].decode('utf8')

                mock_requestor.assert_called_once()
                self.assertEqual(
                    data,
                    'SHIPPED'
                )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_body())