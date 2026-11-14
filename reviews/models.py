from django.db import models
from django.db.models.functions import Length
from django.db.models.lookups import LessThanOrEqual

TEXT_MAX_LENGTH = 200


class Review(models.Model):
    text = models.TextField(max_length=TEXT_MAX_LENGTH)
    sentiment = models.CharField(max_length=20, blank=True, null=True)
    pub_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Enforced by the database itself, also for code that bypasses forms
            models.CheckConstraint(
                condition=LessThanOrEqual(Length('text'), TEXT_MAX_LENGTH),
                name='review_text_max_length',
            ),
        ]

    def __str__(self):
        # Short preview used in admin and shell
        return self.text[:50]