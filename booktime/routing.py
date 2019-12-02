from channels.routing import ProtocolTypeRouter, URLRouter
from .auth import TokenGetAuthMiddlewareStack
import main.routing
from django.urls import re_path
from channels.http import AsgiHandler

application = ProtocolTypeRouter(
    {
        'websocket': TokenGetAuthMiddlewareStack(
            URLRouter(main.routing.websocket_urlpatterns)
        ),
        'http': URLRouter(
            main.routing.http_urlpatterns
            + [re_path(r'', AsgiHandler)]
        )
    }
)
