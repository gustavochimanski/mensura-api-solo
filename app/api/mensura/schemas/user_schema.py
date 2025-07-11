from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: int
    username: str
    type_user: str

    model_config = ConfigDict(from_attributes=True)