from datetime import datetime
from django.views.decorators.cache import cache_page
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.contrib import auth
from .forms import UploadFileForm, LoginForm
from .models import File, Task
from . import tasks


@cache_page(5)
def index(request):
    if request.user.is_authenticated:
        files = File.objects.filter(user=request.user)
    else:
        files = File.objects.none()
    return render(request, 'index.html', dict(files=files, now=datetime.now()))


def upload(request):
    form = UploadFileForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.instance.user = request.user
        form.save()
        return HttpResponseRedirect('/')
    return render(request, 'upload.html', dict(form=form))


def download(request):
    return tasks.download()


def login(request):
    form = LoginForm(request.POST or None)
    if form.is_valid():
        user, authenticated = form.submit()
        if authenticated:
            auth.login(request, user)
            return HttpResponseRedirect('/')
    return render(request, 'login.html', dict(form=form))


def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/')


def process(request, uuid_task):
    task = Task.objects.get(uuid=uuid_task)
    interval = 1000
    url = request.META.get('HTTP_REFERER', '/')
    title = 'Tarefa {} - {}'.format(task.id, task.type)
    return render(request, 'process.html', dict(task=task, interval=interval, url=url, title=title))

def progress(request, download, uuid_task):
    task = Task.objects.get(uuid=uuid_task)
    if int(download) and task.file:
        return file_response(task)
    return HttpResponse('{}::{}::{}::{}'.format(task.get_progress(), task.message or '', task.file or '', task.url or ''))