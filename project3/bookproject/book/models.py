from django.db import models
from .consts import MAX_RATE

CATEGORY = (('business','ビジネス'), ('life','生活'), ('other','その他'))

class Book(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField()
    thumbnail = models.ImageField(null=True, blank=True)
    category = models.CharField(
        max_length=100,
        choices = CATEGORY
    )
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)

    def __str__(self):
        return self.title
    
class Hero(models.Model):
    name = models.CharField(max_length=50)
    hp = models.IntegerField()
    mp = models.IntegerField()
    atk = models.IntegerField()
    defense = models.IntegerField()
    spd = models.IntegerField()
    mag = models.IntegerField()
    heal_time = models.IntegerField()
    attack_buff = models.IntegerField()
    poison_time = models.IntegerField()
    poison_turn = models.IntegerField()
    sleep_turn = models.IntegerField()
    lv = models.IntegerField()
    luck = models.IntegerField()
    round_turn = models.IntegerField()

    def __str__(self):
        return self.name

RATE_CHOICES = [(x, str(x)) for x in range(0, MAX_RATE + 1)]

class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    text = models.TextField()
    rate = models.IntegerField(choices=RATE_CHOICES)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)

    def __str__(self):
        return self.title