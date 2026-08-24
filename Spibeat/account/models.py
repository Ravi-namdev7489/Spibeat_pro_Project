from django.db import models

class Ragistration(models.Model):
    username = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=15)
    institude = models.CharField(max_length=300)
    is_approved = models.BooleanField(default=False)
    def __str__(self):
        return self.email