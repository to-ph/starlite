from starlite import Parameter, WebSocket, create_test_client, websocket


def test_handle_websocket_params_parsing():
    @websocket(path="/{socket_id:int}")
    async def websocket_handler(
        socket: WebSocket,
        headers: dict,
        query: dict,
        cookies: dict,
        socket_id: int,
        qp: int,
        hp: str = Parameter(header="some-header"),
    ) -> None:
        assert socket_id
        assert headers
        assert query
        assert cookies
        assert qp
        assert hp
        await socket.accept()
        data = await socket.receive_json()
        assert data
        await socket.send_json({"data": "123"})
        await socket.close()

    client = create_test_client(route_handlers=websocket_handler)

    with client.websocket_connect("/1?qp=1", headers={"some-header": "abc"}, cookies={"cookie": "yum"}) as ws:
        ws.send_json({"data": "123"})
        data = ws.receive_json()
        assert data
