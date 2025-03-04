import json

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from starlite import (
    HTTPException,
    MediaType,
    Request,
    Response,
    Starlite,
    TestClient,
    create_test_client,
    get,
)
from starlite.exceptions import InternalServerException


def test_default_handle_http_exception_handling():
    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception", extra={"key": "value"}),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": {"key": "value"},
    }

    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        StarletteHTTPException(detail="starlite_exception", status_code=HTTP_500_INTERNAL_SERVER_ERROR),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
    }

    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}), AttributeError("oops")
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": repr(AttributeError("oops")),
    }


def test_using_custom_http_exception_handler():
    @get("/{param:int}")
    def my_route_handler(param: int) -> None:
        ...

    def my_custom_handler(req: Request, exc: Exception) -> Response:
        return Response(content="custom message", media_type=MediaType.TEXT, status_code=HTTP_400_BAD_REQUEST)

    with create_test_client(my_route_handler, exception_handlers={HTTP_400_BAD_REQUEST: my_custom_handler}) as client:
        response = client.get("/abc")
        assert response.text == "custom message"
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_uses_starlette_debug_responses():
    @get("/")
    def my_route_handler() -> None:
        raise InternalServerException()

    app = Starlite(route_handlers=[my_route_handler], debug=True)
    client = TestClient(app=app)

    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert "text/html" in response.headers["content-type"]
