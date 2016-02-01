from models.basemodel import BaseModel
from telepat import TelepatBaseObject

class MetaObject(TelepatBaseObject, BaseModel):
    _ignored_fields = ["object_id", "model"]
