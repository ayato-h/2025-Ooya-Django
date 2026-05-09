from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView

from .forms import SignupForm, EmailAuthenticationForm

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  
            return redirect('casino:index')
    else:
        form = SignupForm()
    return render(request, 'accounts/signup.html', {'form': form})


class CustomLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = 'registration/login.html'