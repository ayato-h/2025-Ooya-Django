from django.db import models

class BaccaratResult(models.Model):
    PLAYER = 'player'
    BANKER = 'banker'
    TIE = 'tie'

    RESULT_CHOICES = [
        (PLAYER, '⚫︎'),
        (BANKER, '✖︎'),
        (TIE, '△'),
    ]

    result = models.CharField(
        max_length=10,
        choices=RESULT_CHOICES,
        default=PLAYER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_result_display()} ({self.created_at})"
