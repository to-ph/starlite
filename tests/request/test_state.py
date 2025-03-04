from typing import Dict

from starlette.types import ASGIApp, Receive, Scope, Send

from starlite import MiddlewareProtocol, Request, create_test_client, get


class BeforeRequestMiddleWare(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["state"]["main"] = "Success!"
        await self.app(scope, receive, send)


def before_request(request: Request):
    assert request.state.main == "Success!"
    request.state.main = "Success! x2"


def test_state():
    @get(path="/")
    async def get_state(request: Request) -> Dict[str, str]:
        return {"state": request.state.main}

    with create_test_client(
        route_handlers=[get_state], middleware=[BeforeRequestMiddleWare], before_request=before_request
    ) as client:
        response = client.get("/")
        assert response.json() == {"state": "Success! x2"}
