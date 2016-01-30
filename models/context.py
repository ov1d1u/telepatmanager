from models.basemodel import BaseModel
from telepat import TelepatContext

class Context(TelepatContext, BaseModel):
    _ignored_fields = ["object_id", "model"]
    