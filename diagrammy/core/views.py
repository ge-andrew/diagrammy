from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return HttpResponse("<h1>Welcome! Dummy home page here</h1>")

def home2(request):
    return HttpResponse("<h1>Welcome again!</h1>")

def landing(request):
    return render(request, "core/landing.html")

def about(request):
    return render(request, "core/about.html")
