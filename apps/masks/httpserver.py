import asyncio
import logging
import pickle

from aiohttp import web

from honeybadgermpc.utils.misc import print_exception_callback


class HTTPServer:
    """HTTP server to handle requests from clients."""

    def __init__(
        self, sid, myid, *, http_host="0.0.0.0", http_port=8080, sharestore,
    ):
        """
        Parameters
        ----------
        sid: int
            Session id.
        myid: int
            Client id.
        """
        self.sid = sid
        self.myid = myid
        self._init_tasks()
        self._http_host = http_host
        self._http_port = http_port
        self.sharestore = sharestore

    # TODO put in utils
    def _create_task(self, coro, *, name=None):
        task = asyncio.create_task(coro)
        task.add_done_callback(print_exception_callback)
        return task

    def _init_tasks(self):
        self._http_server = self._create_task(self._request_handler_loop())

    async def start(self):
        await self._http_server

    async def _request_handler_loop(self):
        """ Task 2. Handling client input

        .. todo:: if a client requests a share, check if it is
            authorized and if so send it along

        """
        routes = web.RouteTableDef()

        @routes.get("/inputmasks/{idx}")
        async def _handler(request):
            idx = int(request.match_info.get("idx"))
            try:
                _inputmasks = self.sharestore[b"inputmasks"]
            except KeyError:
                inputmasks = []
            else:
                inputmasks = pickle.loads(_inputmasks)
            try:
                inputmask = inputmasks[idx]
            except IndexError:
                logging.error(f"No input mask at index {idx}")
                raise

            data = {
                "inputmask": inputmask,
                "server_id": self.myid,
                "server_port": self._http_port,
            }
            return web.json_response(data)

        app = web.Application()
        app.add_routes(routes)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=self._http_host, port=self._http_port)
        await site.start()
        print(f"======= Serving on http://{self._http_host}:{self._http_port}/ ======")
        # pause here for very long time by serving HTTP requests and
        # waiting for keyboard interruption
        await asyncio.sleep(100 * 3600)
