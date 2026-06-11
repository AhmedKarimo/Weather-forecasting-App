from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FavoriteCreate(BaseModel):
    city: str = Field(min_length=2, max_length=100)
    country_code: str = Field(default="", max_length=10)


class FavoriteUpdate(BaseModel):
    city: str | None = Field(default=None, min_length=2, max_length=100)
    country_code: str | None = Field(default=None, max_length=10)


class FavoriteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city: str
    country_code: str
    created_at: datetime
    updated_at: datetime


class SearchHistoryCreate(BaseModel):
    city: str = Field(min_length=2, max_length=100)
    country_code: str = Field(default="", max_length=10)
    requested_days: int = Field(default=3, ge=1, le=5)


class SearchHistoryUpdate(BaseModel):
    city: str | None = Field(default=None, min_length=2, max_length=100)
    country_code: str | None = Field(default=None, max_length=10)
    requested_days: int | None = Field(default=None, ge=1, le=5)


class SearchHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city: str
    country_code: str
    requested_days: int
    created_at: datetime


class DeleteResponse(BaseModel):
    message: str
