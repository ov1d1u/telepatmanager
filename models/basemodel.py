class BaseModel:
    _readonly_fields = ["id", "application_id", "created", "modified", "type"]
    _ignored_fields = []
    _model_name = "Context"

    def isReadOnly(self, field_name):
        return field_name in self._readonly_fields

    def isIgnored(self, field_name):
        return field_name in self._ignored_fields

    def modelName(self):
        return self._model_name