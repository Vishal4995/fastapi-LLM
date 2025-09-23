from pydantic import BaseModel, Field

class ItemBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=500)

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=500)

class ItemOut(ItemBase):
    id: int

    class Config:
        from_attributes = True  # for SQLAlchemy objects
