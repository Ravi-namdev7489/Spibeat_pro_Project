from django.db import models


class NetworkResult(models.Model):
    
    name = models.CharField(
        max_length=100
    )

    result_type = models.CharField(
        max_length=50
    )

    network_path = models.CharField(
        max_length=500
    )

    is_latest = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
