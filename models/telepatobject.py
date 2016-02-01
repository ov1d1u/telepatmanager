from models.basemodel import BaseModel
from telepat import TelepatBaseObject


# A generic object to be used with native Telepat.io objects
class TelepatObject(TelepatBaseObject, BaseModel):
    _ignored_fields = ["object_id", "model", "application_id",
    	"context_id", "id", "modified", "type"]
