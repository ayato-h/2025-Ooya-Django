from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _  
from .models import CustomUser

class SignupForm(UserCreationForm):
    username = forms.CharField(
        label=_("ユーザーID"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label=_("メールアドレス"),
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label=_("パスワード"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label=_("パスワード確認"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    PUBLIC_CHOICES = (
        (True, _("公開")),
        (False, _("非公開")),
    )
    is_public = forms.ChoiceField(
        choices=PUBLIC_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label=_("プロフィール公開設定"),
        initial=True
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2', 'is_public')

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_('Email'),  
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget.attrs.update({'class': 'form-control'})
