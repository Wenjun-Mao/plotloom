"""Typed deterministic preparation lineage, distinct from native generation."""
from typing import Literal
from pydantic import Field, model_validator
from .domain import CamelModel
from .contract_hash import stable_hash

HASH = r"^[a-f0-9]{64}$"
RECIPE_VERSION = "center-cover-rgb-lanczos-png.v1"


class GeometryRuntime(CamelModel):
    pillow_version: str
    transform_hash: str = Field(pattern=HASH)


class GeometryPolicy(CamelModel):
    recipe_version: Literal[RECIPE_VERSION] = RECIPE_VERSION
    runtime: GeometryRuntime


class GeometryAsset(CamelModel):
    asset_id: str
    original_hash: str = Field(pattern=HASH)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class GeometryRecipe(CamelModel):
    version: Literal[RECIPE_VERSION] = RECIPE_VERSION
    exif_orientation: int = Field(ge=1, le=8)
    oriented_width: int = Field(gt=0)
    oriented_height: int = Field(gt=0)
    crop_box: tuple[float, float, float, float]
    target_width: int = Field(ge=64, le=4096)
    target_height: int = Field(ge=64, le=4096)

    @model_validator(mode="after")
    def centered_cover(self):
        w, h = self.oriented_width, self.oriented_height
        if w * self.target_height > h * self.target_width:
            cw, ch = h * self.target_width / self.target_height, float(h)
        else:
            cw, ch = float(w), w * self.target_height / self.target_width
        expected = ((w-cw)/2, (h-ch)/2, (w+cw)/2, (h+ch)/2)
        if self.crop_box != expected:
            raise ValueError("geometry recipe must describe the exact centered cover crop")
        return self


class GeometrySource(CamelModel):
    asset: GeometryAsset
    checkpoint_id: str
    decision_id: str
    candidate_id: str
    job_id: str
    request_hash: str = Field(pattern=HASH)
    delivery_row_id: str
    delivery_id: str
    manifest_hash: str = Field(pattern=HASH)
    execution_pin: dict[str, str]


class GeometryPreparation(CamelModel):
    version: Literal["geometry-preparation.v1"] = "geometry-preparation.v1"
    preparation_id: str = Field(pattern=HASH)
    project_id: str
    run_id: str
    policy_hash: str = Field(pattern=HASH)
    claim: str = Field(min_length=1)
    shot_id: str
    source: GeometrySource
    recipe: GeometryRecipe
    recipe_hash: str = Field(pattern=HASH)
    runtime: GeometryRuntime
    output: GeometryAsset
    preparation_hash: str = Field(pattern=HASH)

    @model_validator(mode="after")
    def hashes_and_geometry(self):
        raw = self.model_dump(mode="json", by_alias=True, exclude={"preparation_hash"})
        if stable_hash(self.recipe.model_dump(mode="json", by_alias=True)) != self.recipe_hash or stable_hash(raw) != self.preparation_hash:
            raise ValueError("geometry preparation hashes changed")
        if (self.output.width, self.output.height) != (self.recipe.target_width, self.recipe.target_height):
            raise ValueError("geometry output must match exact frozen dimensions")
        expected = (self.source.asset.height, self.source.asset.width) if self.recipe.exif_orientation >= 5 else (self.source.asset.width, self.source.asset.height)
        if expected != (self.recipe.oriented_width, self.recipe.oriented_height):
            raise ValueError("geometry orientation differs from raw dimensions")
        return self
