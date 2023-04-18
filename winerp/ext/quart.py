import asyncio
import functools
import inspect
from types import FunctionType
from winerp.client import Client
from winerp.lib.errors import InvalidRouteType, UnauthorizedError
from winerp.server import Server
from threading import Thread


class WinerpQuart(Client):
    def __init__(self, app=None,
                 local_name: str = None,
                 host: str = '127.0.0.1',
                 port: int = 13254,
                 run_server_thread=False):
        super().__init__(local_name=local_name, host=host, port=port)
        self.local_name = local_name
        self.host = host
        self.port = port
        self.run_server_thread = run_server_thread
        self.server = None
        self.UnauthorizedError = UnauthorizedError

        if self.run_server_thread:
            self.server = Server(self.host, self.port)
            self.thread = Thread(target=self.server.start)
            self.thread.start()
            print(f'Winerp Server has started at {self.host}:{self.port}.')

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        This callback is for Quart to initialize the extension. It is called by Quart when the extension is registered to the application.
        Shouldn't be called manually.

        Parameters
        ----------
        app

        Returns
        -------

        """
        app.before_serving(self.start)
        print(f'Winerp Client has started to listen at {self.host}:{self.port} with {self.local_name} local name.')

    def request_decorator(self, route: str, source: str, timeout: int = 60, **kwargs):
        """|coro|

        Requests the server for a response. Resolves when the response is received matching the UUID. This is
        designed as a decorator, it should be below @app.route() decorator as it supports positional parameters of
        the route such as <example>. You don't need to declare positional parameter in the |coro| for the route. You
        should declare as a keyword argument in the request decorator.

        Also, `data` is the keyword will be used to pass the data from the IPC request to the route function. Anything
        else will be passed to the request function.


        Usage
        ------
        @app.route('/test/<guild_id>')
        @winerp.request_decorator(source='bot', route='get_guild_data', gid='<guild_id>')
        async def handle_request(data):
            if data is not None:
                print('ipc data arrived', data)
                return data
            else:
                return 'no ipc data error'


        Parameters
        -----------
        route: :class:`str`
            The route to request to.
        source: :class:`str`
            The destination
        timeout: :class:`int`
            Time to wait before raising :class:`~asyncio.TimeoutError`.

        Raises
        -------
            ClientNotReadyError
                The client is currently not ready to send or accept requests.
            UnauthorizedError
                The client isn't authorized by the server.
            ValueError:
                Missing either route or source or both.
            RuntimeError
                If the UUID is not found.
            asyncio.TimeoutError
                If the response is not received within the timeout.

        Returns
        --------
            :class:`any`
                The data associated with the message.
        """

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **func_kwargs):
                # Create a copy of kwargs and replace any placeholders with values from the URL
                request_kwargs = {}
                for k, v in kwargs.items():
                    for fk, fv in func_kwargs.items():
                        if v == f'<{fk}>':
                            request_kwargs[k] = fv
                            break
                    else:

                        request_kwargs[k] = v
                data = await self.request(route, source, timeout, **request_kwargs)
                return await func(*args, **func_kwargs, data=data)

            return wrapper

        return decorator
