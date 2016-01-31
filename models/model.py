from models.basemodel import BaseModel
from telepat import TelepatAppSchema

class Model(TelepatAppSchema, BaseModel):
    _ignored_fields = ["object_id", "model"]
