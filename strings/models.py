import json
from django.db import models

# Create your models here.
class AnalyzedString(models.Model):
    value = models.TextField(unique=True)
    sha256_hash = models.CharField(max_length=64, unique=True)
    properties = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def set_properties(self, data):
        self.properties = json.dumps(data)

    def get_properties(self):
        return json.loads(self.properties)