from django.urls import path
from channels.auth import AuthMiddlewareStack
from . import consumers

websocket_urlpatterns = [
    path(
        "ws/customer-service/<int:order_id>/",
        consumers.ChatConsumer
    ),
    path(
        "ws/customer-service/notify/",
        consumers.ChatNotifyConsumer
    )
]

http_urlpatterns = [
    path(
        "mobile-api/my-orders/<int:order_id>/tracker/",
        AuthMiddlewareStack(consumers.OrderTrackerConsumer),
    )
]
