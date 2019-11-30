from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import main.routing
from django.urls import re_path
from channels.http import AsgiHandler

application = ProtocolTypeRouter(
    {
        'websocket': AuthMiddlewareStack(
            URLRouter(main.routing.websocket_urlpatterns)
        ),
        'http': URLRouter(
            main.routing.http_urlpatterns
            + [re_path(r'', AsgiHandler)]
        )
    }
)
