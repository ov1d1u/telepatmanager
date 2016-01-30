from models.basemodel import BaseModel

class Model(BaseModel):
    readonly_fields = ["id", "application_id", "created", "modified", "type"]
    model_name = "Model"
