from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

User = settings.AUTH_USER_MODEL

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

    groups = models.ManyToManyField(
        Group,
        related_name="customuser_set",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_set",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    favorites = models.ManyToManyField(
        'app.Song',
        related_name='favorited_by',
        blank=True
    )

    CATCHPHRASE_CHOICES = [
        ('none', 'なし'),
        ('beginner', '初心者'),
        ('intermediate', '中級者'),   
        ('advanced', '上級者'),  
    ]

    THEME_CHOICES = [
        ('white', '白'),
        ('black', '黒'),
    ]
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='white')
    bio = models.TextField(blank=True, null=True, max_length=500)
    points = models.IntegerField(default=0)
    catchphrase = models.CharField(
        max_length=255,
        choices=CATCHPHRASE_CHOICES,
        default='none'
    )

    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        default='avatars/default.png' 
    )

    is_public = models.BooleanField(default=True, verbose_name="公開設定")
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

class PurchasedCatchphrase(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='purchased_catchphrases')
    catchphrase = models.CharField(max_length=255, choices=CustomUser.CATCHPHRASE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'catchphrase')

    def __str__(self):
        return f"{self.user.email} - {self.catchphrase}"

@receiver(post_save, sender=CustomUser)
def create_default_catchphrases(sender, instance, created, **kwargs):
        if created:
            PurchasedCatchphrase.objects.bulk_create([
                PurchasedCatchphrase(user=instance, catchphrase='none'),
                PurchasedCatchphrase(user=instance, catchphrase='beginner'),
            ])

class Friendship(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='friends'
    )
    friend = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='friends_of'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'friend')

    def __str__(self):
        return f'{self.user} ↔ {self.friend}'
    
class FriendRequest(models.Model):
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_friend_requests'
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_friend_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')