from django.db import models

class Diagram(models.Model):
    title = models.CharField(max_length = 1000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
