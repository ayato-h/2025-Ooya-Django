from django.http import HttpResponse
from django.views.generic import TemplateView

def helloworldfunc(request):
    responseobject = HttpResponse('hello world')
    return responseobject

class HelloWorldClass(TemplateView):
    template_name = 'hello.html'