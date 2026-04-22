from django.db import models


class NotificationType(models.TextChoices):
    HB_KIDS = 'hb_kids', 'HB Kids'
