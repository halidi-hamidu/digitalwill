from django.shortcuts import render

# Create your views here.
def homeview(request):
    templates = "digitalwillclient/home.html"
    context = {}
    return render(request, templates, context)