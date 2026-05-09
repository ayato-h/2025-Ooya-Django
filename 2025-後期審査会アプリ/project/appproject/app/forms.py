from django import forms
from .models import ScoreLog, Song

class ScoreLogForm(forms.ModelForm):
    custom_track_name = forms.CharField(
        max_length=200, required=False, label="自由入力曲名"
    )

    class Meta:
        model = ScoreLog
        fields = ['song', 'score', 'custom_track_name']  

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')  
        super().__init__(*args, **kwargs)
        self.fields['song'].queryset = Song.objects.filter(favorited_by=user)
        self.fields['song'].required = False  
