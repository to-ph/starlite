import pytest
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from starlite import HttpMethod
from starlite.handlers import HTTPRouteHandler


@pytest.mark.parametrize(
    "http_method, expected_status_code",
    [
        (HttpMethod.POST, HTTP_201_CREATED),
        (HttpMethod.DELETE, HTTP_204_NO_CONTENT),
        (HttpMethod.GET, HTTP_200_OK),
        (HttpMethod.PUT, HTTP_200_OK),
        (HttpMethod.PATCH, HTTP_200_OK),
        ([HttpMethod.POST], HTTP_201_CREATED),
        ([HttpMethod.DELETE], HTTP_204_NO_CONTENT),
        ([HttpMethod.GET], HTTP_200_OK),
        ([HttpMethod.PUT], HTTP_200_OK),
        ([HttpMethod.PATCH], HTTP_200_OK),
    ],
)
def test_route_handler_default_status_code(http_method, expected_status_code):
    route_handler = HTTPRouteHandler(http_method=http_method)
    assert route_handler.status_code == expected_status_code
