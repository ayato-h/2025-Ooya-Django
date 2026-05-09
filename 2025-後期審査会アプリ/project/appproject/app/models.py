from django.db import models
from django.conf import settings
from django.utils import timezone

class Song(models.Model):
    track_name = models.CharField(max_length=255)
    artist_name = models.CharField(max_length=255)
    album_name = models.CharField(max_length=255)
    artwork_url = models.URLField()
    preview_url = models.URLField(unique=True)
    genre = models.CharField(max_length=100, blank=True) 
    lyrics = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.track_name} - {self.artist_name}"

class ScoreLog(models.Model):
    DAM = 'DAM'
    JOY = 'JOY'

    KARAOKE_CHOICES = [
        (DAM, 'DAM'),
        (JOY, 'JOYSOUND'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='score_logs'
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='score_logs'
    )
    key = models.IntegerField(default=0)
    score = models.DecimalField(max_digits=6, decimal_places=3)
    karaoke_type = models.CharField(max_length=3, choices=KARAOKE_CHOICES)
    image = models.ImageField(upload_to='score_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class SongHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey('Song', on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True) 

    class Meta:
        ordering = ['-viewed_at']

class SongLater(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='later_songs'
    )
    song = models.ForeignKey(
        'Song',
        on_delete=models.CASCADE,
        related_name='later_users'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'song')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.song}'

class MonthlyMission(models.Model):
    title = models.CharField(max_length=255)
    goal = models.IntegerField()
    month = models.DateField()
    reward_points = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.month.strftime('%Y-%m')} - {self.title}"

    @classmethod
    def create_default_missions(cls):
        today = timezone.now().date()
        month_start = today.replace(day=1)

        if cls.objects.filter(month=month_start).exists():
            return

        default_missions = [
            {"title": "クイズを3問正解する", "goal": 3},
            {"title": "特定の曲で90点以上を出す", "goal": 90},
            {"title": "4曲点数更新する", "goal": 4},
        ]

        for mission in default_missions:
            cls.objects.create(
                title=mission["title"],
                goal=mission["goal"],
                month=month_start
            )

class UserMissionProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mission_progress"
    )
    mission = models.ForeignKey(
        MonthlyMission,
        on_delete=models.CASCADE,
        related_name="user_progress"
    )
    progress = models.IntegerField(default=0)
    reward_received = models.BooleanField(default=False)

    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "mission")

    @property
    def is_completed(self):
        return self.progress >= self.mission.goal

    def __str__(self):
        return f"{self.user} - {self.mission.title} ({self.progress}/{self.mission.goal})"

class ChatRoom(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL)
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255, blank=True) 

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.sender} : {self.created_at}'