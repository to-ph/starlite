import pytest

from starlite import ImproperlyConfiguredException, Starlite, get, post
from starlite.exceptions import MethodNotAllowedException
from starlite.routing import HTTPRoute


@get(path="/")
def my_get_handler() -> None:
    pass


@post(path="/")
def my_post_handler() -> None:
    pass


@pytest.mark.asyncio
async def test_http_route_raises_for_unsupported_method():
    route = HTTPRoute(path="/", route_handlers=[my_get_handler, my_post_handler])

    with pytest.raises(MethodNotAllowedException):
        await route.handle(scope={"method": "DELETE"}, receive=lambda x: x, send=lambda x: x)


def test_register_validation_duplicate_handlers_for_same_route_and_method():
    @get(path="/first")
    def first_route_handler() -> None:
        pass

    @get(path="/first")
    def second_route_handler() -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[first_route_handler, second_route_handler])
