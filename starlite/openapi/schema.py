from dataclasses import is_dataclass
from decimal import Decimal
from enum import Enum, EnumMeta
from typing import Any, List, Optional, Type, Union

from openapi_schema_pydantic import Example, Schema
from openapi_schema_pydantic.util import PydanticSchema
from pydantic import (
    BaseModel,
    ConstrainedBytes,
    ConstrainedDecimal,
    ConstrainedFloat,
    ConstrainedInt,
    ConstrainedList,
    ConstrainedSet,
    ConstrainedStr,
)
from pydantic.fields import FieldInfo, ModelField, Undefined
from pydantic_factories import ModelFactory
from pydantic_factories.utils import is_optional, is_pydantic_model, is_union

from starlite.openapi.constants import (
    EXTRA_TO_OPENAPI_PROPERTY_MAP,
    PYDANTIC_FIELD_SHAPE_MAP,
    PYDANTIC_TO_OPENAPI_PROPERTY_MAP,
    TYPE_MAP,
)
from starlite.openapi.enums import OpenAPIType
from starlite.utils.model import convert_dataclass_to_model, create_parsed_model_field


def normalize_example_value(value: Any) -> Any:
    """Normalize the example value to make it look a bit prettier"""
    if isinstance(value, (Decimal, float)):
        value = round(float(value), 2)
    if isinstance(value, Enum):
        value = value.value
    if is_dataclass(value):
        value = convert_dataclass_to_model(value)
    if isinstance(value, BaseModel):
        value = value.dict()
    if isinstance(value, (list, set)):
        value = [normalize_example_value(v) for v in value]
    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = normalize_example_value(v)
    return value


class ExampleFactory(ModelFactory[BaseModel]):
    """A factory that always returns values"""

    __model__ = BaseModel
    __allow_none_optionals__ = False


def create_numerical_constrained_field_schema(
    field_type: Union[Type[ConstrainedFloat], Type[ConstrainedInt], Type[ConstrainedDecimal]]
) -> Schema:
    """
    Create Schema from Constrained Int/Float/Decimal field
    """
    schema = Schema(type=OpenAPIType.INTEGER if issubclass(field_type, int) else OpenAPIType.NUMBER)
    if field_type.le is not None:
        schema.maximum = field_type.le
    if field_type.lt is not None:
        schema.exclusiveMaximum = field_type.lt
    if field_type.ge is not None:
        schema.minimum = field_type.ge
    if field_type.gt is not None:
        schema.exclusiveMinimum = field_type.gt
    if field_type.multiple_of is not None:
        schema.multipleOf = field_type.multiple_of
    return schema


def create_string_constrained_field_schema(field_type: Union[Type[ConstrainedStr], Type[ConstrainedBytes]]) -> Schema:
    """
    Create Schema from Constrained Str/Bytes field
    """
    schema = Schema(type=OpenAPIType.STRING)
    if field_type.min_length:
        schema.minLength = field_type.min_length
    if field_type.max_length:
        schema.maxLength = field_type.max_length
    if issubclass(field_type, ConstrainedStr):
        schema.pattern = field_type.regex
    if field_type.to_lower:
        schema.description = "must be in lower case"
    return schema


def create_collection_constrained_field_schema(
    field_type: Union[Type[ConstrainedList], Type[ConstrainedSet]],
    sub_fields: Optional[List[ModelField]],
) -> Schema:
    """
    Create Schema from Constrained List/Set field
    """
    schema = Schema(type=OpenAPIType.ARRAY)
    if field_type.min_items:
        schema.minItems = field_type.min_items
    if field_type.max_items:
        schema.maxItems = field_type.max_items
    if issubclass(field_type, ConstrainedSet):
        schema.uniqueItems = True
    if sub_fields:
        schema.items = [create_schema(field=sub_field, generate_examples=False) for sub_field in sub_fields]
    else:
        parsed_model_field = create_parsed_model_field(field_type.item_type)
        schema.items = create_schema(field=parsed_model_field, generate_examples=False)
    return schema


def create_constrained_field_schema(
    field_type: Union[
        Type[ConstrainedSet],
        Type[ConstrainedList],
        Type[ConstrainedStr],
        Type[ConstrainedBytes],
        Type[ConstrainedFloat],
        Type[ConstrainedInt],
        Type[ConstrainedDecimal],
    ],
    sub_fields: Optional[List[ModelField]],
) -> Schema:
    """
    Create Schema for Pydantic Constrained fields (created using constr(), conint() etc. or by subclassing Constrained*)
    """
    if issubclass(field_type, (ConstrainedFloat, ConstrainedInt, ConstrainedDecimal)):
        return create_numerical_constrained_field_schema(field_type=field_type)
    if issubclass(field_type, (ConstrainedStr, ConstrainedBytes)):
        return create_string_constrained_field_schema(field_type=field_type)
    return create_collection_constrained_field_schema(field_type=field_type, sub_fields=sub_fields)


def update_schema_with_field_info(schema: Schema, field_info: FieldInfo) -> Schema:
    """
    Copy values from the given instance of pydantic FieldInfo into the schema
    """
    if field_info.const and field_info.default not in [None, ..., Undefined] and schema.const is None:
        schema.const = field_info.default
    for pydantic_key, schema_key in PYDANTIC_TO_OPENAPI_PROPERTY_MAP.items():
        value = getattr(field_info, pydantic_key)
        if value not in [None, ..., Undefined]:
            setattr(schema, schema_key, value)
    for extra_key, schema_key in EXTRA_TO_OPENAPI_PROPERTY_MAP.items():
        if extra_key in field_info.extra:
            value = field_info.extra[extra_key]
            if value not in [None, ..., Undefined]:
                setattr(schema, schema_key, value)
    return schema


def get_schema_for_field_type(field: ModelField) -> Schema:
    """
    Get or create a Schema object for the given field type
    """
    field_type = field.outer_type_
    if field_type in TYPE_MAP:
        return TYPE_MAP[field_type].copy()
    if is_pydantic_model(field_type):
        return PydanticSchema(schema_class=field_type)
    if is_dataclass(field_type):
        return PydanticSchema(schema_class=convert_dataclass_to_model(field_type))
    if isinstance(field_type, EnumMeta):
        enum_values: List[Union[str, int]] = [v.value for v in field_type]  # type: ignore
        openapi_type = OpenAPIType.STRING if isinstance(enum_values[0], str) else OpenAPIType.INTEGER
        return Schema(type=openapi_type, enum=enum_values)
    # this is a failsafe to ensure we always return a value
    return Schema()  # pragma: no cover


def create_examples_for_field(field: ModelField) -> List[Example]:
    """
    Use the pydantic-factories package to create an example value for the given schema
    """
    value = normalize_example_value(ExampleFactory.get_field_value(field))
    return [Example(description=f"Example {field.name} value", value=value)]


def create_schema(field: ModelField, generate_examples: bool, ignore_optional: bool = False) -> Schema:
    """
    Create a Schema model for a given ModelField and if needed - recursively traverse its sub_fields as well.
    """

    if is_optional(field) and not ignore_optional:
        non_optional_schema = create_schema(
            field=field,
            generate_examples=False,
            ignore_optional=True,
        )
        schema = Schema(
            oneOf=[
                Schema(type=OpenAPIType.NULL),
                *(non_optional_schema.oneOf if non_optional_schema.oneOf else [non_optional_schema]),
            ]
        )
    elif is_union(field):
        schema = Schema(
            oneOf=[create_schema(field=sub_field, generate_examples=False) for sub_field in field.sub_fields or []]
        )
    elif ModelFactory.is_constrained_field(field.type_):
        # constrained fields are those created using the pydantic functions constr, conint, conlist etc.
        # or subclasses of the Constrained* pydantic classes by other means
        field.outer_type_ = field.type_
        schema = create_constrained_field_schema(field_type=field.outer_type_, sub_fields=field.sub_fields)
    elif field.sub_fields:
        # we are dealing with complex types in this case
        # the problem here is that the Python typing system is too crude to define OpenAPI objects properly
        openapi_type = PYDANTIC_FIELD_SHAPE_MAP[field.shape]
        schema = Schema(type=openapi_type)
        if openapi_type == OpenAPIType.ARRAY:
            schema.items = [create_schema(field=sub_field, generate_examples=False) for sub_field in field.sub_fields]
    else:
        # value is not a complex typing - hence we can try and get the value schema directly
        schema = get_schema_for_field_type(field=field)
    if not ignore_optional:
        schema = update_schema_with_field_info(schema=schema, field_info=field.field_info)
    if not schema.examples and generate_examples:
        schema.examples = create_examples_for_field(field=field)
    return schema
