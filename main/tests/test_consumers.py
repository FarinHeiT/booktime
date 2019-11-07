import asyncio
from django.contrib.auth.models import Group
from django.test import TestCase
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from main import consumers
from main import factories


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
