import pytest

from starlite import ImproperlyConfiguredException, Provide, Starlite, get


def first_method(query_param: int):
    assert isinstance(query_param, int)
    return query_param


def second_method(path_param: str):
    assert isinstance(path_param, str)
    return path_param


def test_dependency_validation():
    @get(
        path="/{path_param:int}",
        dependencies={
            "first": Provide(first_method),
            "second": Provide(second_method),
        },
    )
    def test_function(first: int, second: str, third: int) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(
            route_handlers=[test_function],
            dependencies={
                "third": Provide(first_method),
            },
        )
