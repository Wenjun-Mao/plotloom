"""Typed structural editor buffers, without canonical semantic validation.

Derive field ownership from the named stage models so new canonical fields cannot
silently become arbitrary browser state. Apply still validates the original model
and exact draft receipt in the same transaction.
"""
from functools import lru_cache
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin
from pydantic import BaseModel, Field, StrictFloat, StrictInt, StrictStr, create_model
from .domain_base import CamelModel

RawInteger = StrictInt | Annotated[StrictStr, Field(max_length=100)]
RawFloat = StrictFloat | StrictInt | Annotated[StrictStr, Field(max_length=100)]


def input_annotation(annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Annotated:
        return input_annotation(args[0])
    if origin in (Union, UnionType):
        return Union[tuple(input_annotation(arg) for arg in args)]
    if origin is list:
        return list[input_annotation(args[0])]
    if origin is dict:
        return dict[args[0], input_annotation(args[1])]
    if annotation is int:
        return RawInteger
    if annotation is float:
        return RawFloat
    if annotation is str:
        return Annotated[StrictStr, Field(max_length=200_000)]
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return input_model(annotation)
    return annotation


@lru_cache(maxsize=None)
def input_model(canonical: type[BaseModel]) -> type[BaseModel]:
    fields = {}
    for name, field in canonical.model_fields.items():
        default = ... if field.is_required() else field.default
        options = {"alias": field.alias}
        if field.default_factory is not None:
            options["default_factory"] = field.default_factory
            fields[name] = (input_annotation(field.annotation), Field(**options))
        else:
            fields[name] = (input_annotation(field.annotation), Field(default, **options))
    return create_model(f"{canonical.__name__}WorkingInput", __base__=CamelModel, **fields)


def validate_stage_working_input(canonical: type[BaseModel], payload: dict[str, Any]):
    import json
    if len(json.dumps(payload, ensure_ascii=False)) > 500_000:
        raise ValueError("stage authoring input exceeds its bounded journal size")
    return input_model(canonical).model_validate(payload).model_dump(mode="json", by_alias=True)
