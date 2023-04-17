import asyncio
import functools
from types import FunctionType
from winerp.client import Client
from winerp.lib.errors import InvalidRouteType


class WinerpQuart(Client):
    def __init__(self, app=None, local_name: str = None, host: str = '127.0.0.1', port: int = 13254, run_server_thread=False):
        super().__init__(local_name=local_name, host=host, port=port)
        self.local_name = local_name
        self.host = host
        self.port = port
        self.run_server_thread = run_server_thread


        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.before_first_request(self.start)

    def ipc_route(self, name: str = None):
        """
        A decorator to register your route. The route name should be unique.

        Raises
        -------
            ValueError
                Route name already exists.
            InvalidRouteType
                The function passed is not a coro.
        """

        def route_decorator(_route_func):
            if (name is None and _route_func.__name__ in self.__routes) or (name is not None and name in self.__routes):
                raise ValueError("Route name is already registered!")

            if not asyncio.iscoroutinefunction(_route_func):
                raise InvalidRouteType("Route function must be a coro.")

            self.__routes[name or _route_func.__name__] = _route_func
            return _route_func

        if isinstance(name, FunctionType):
            _route_func = name
            name = name.__name__
            return route_decorator(_route_func)
        else:
            return route_decorator

    def request_decorator(self, route: str, source: str, timeout: int = 60, **kwargs):
        """|coro|

        Requests the server for a response.
        Resolves when the response is received matching the UUID.
        This is designed as a decorator, it should be below @app.route() decorator as it supports positional parameters of the route such as <example>.
        You don't need to declare positional parameter in the |coro| for the route. You should declare as a keyword argument in the request decorator.

        Usage
        ------
        @app.route('/test/<guild_id>')
        @app.ipc_.request(source='bot', route='get_guild_data', gid='<guild_id>')
        async def handle_request(ipc_data):
            if ipc_data is not None:
                print('ipc data arrived', ipc_data)
                return ipc_data
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
                            del func_kwargs[fk]
                            break
                    else:
                        request_kwargs[k] = v
                ipc_data = await self.request(route, source, timeout, **request_kwargs)
                return await func(*args, ipc_data=ipc_data, **func_kwargs)

            return wrapper

        return decorator




