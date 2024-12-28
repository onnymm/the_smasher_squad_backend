from pydantic import BaseModel

class BaseRecord(BaseModel):
    user: str | None = None
    name: str | None = None

class BaseUser(BaseModel):
    user: str
    name: str

class UserNewData(BaseModel):
    user: str | None = None
    name: str | None = None

class UserData(BaseUser):
    password: str

class UserInDB(UserData, BaseRecord):
    id: int
