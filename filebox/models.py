import uuid
import math
from django.db import models
from datetime import datetime
from django.contrib.auth.models import User


class File(models.Model):
    user = models.ForeignKey(User, verbose_name='User', on_delete=models.CASCADE)
    name = models.CharField(verbose_name='Name', max_length=255)
    file = models.FileField(verbose_name='File')

    def __str__(self):
        return self.name


class Task(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    type = models.CharField(verbose_name='Tipo', max_length=255)
    user = models.ForeignKey(User, verbose_name='User', null=True, on_delete=models.CASCADE)
    message = models.CharField(verbose_name='Message', max_length=255, null=True)
    file = models.CharField(verbose_name='File', max_length=255, null=True)
    total = models.IntegerField(verbose_name='Total', default=0)
    partial = models.IntegerField(verbose_name='Parcial', default=0)
    error = models.TextField(verbose_name='Erro', null=True)
    start = models.DateTimeField(verbose_name='Início', auto_now=True)
    end = models.DateTimeField(verbose_name='Fim', null=True)
    notify = models.BooleanField(default=False)
    url = models.CharField(verbose_name='Redirect URL', max_length=524, default='')

    objects = models.Manager()

    def get_absolute_url(self):
        return '/task/{}/'.format(self.pk)

    @property
    def percent(self):
        return math.floor(self.partial * 100 / (self.total or self.partial or 1))

    def count(self, *iterables):
        for iterable in iterables:
            self.total += len(iterable)
        Task.objects.filter(pk=self.pk).update(total=self.total)

    def start_progress(self, total=100):
        self.total = total
        Task.objects.filter(pk=self.pk).update(total=total)

    def update_progress(self, percent):
        Task.objects.filter(pk=self.pk).update(partial=percent)

    def iterate(self, iterable):
        if not self.total:
            self.total = len(iterable)
            Task.objects.filter(pk=self.pk).update(total=self.total)
        partial = self.partial
        previous_percent = 0
        for i, obj in enumerate(iterable):
            self.partial = partial + i
            each_five_percent = math.floor(self.partial * 20 / self.total)
            if previous_percent < each_five_percent or i == self.total:
                previous_percent = each_five_percent
                Task.objects.filter(pk=self.pk).update(partial=self.partial)
            yield obj

    def finalize(self, message, url='', error=False, file_path=None):
        if not self.url:
            self.url = url
        if error:
            self.error = message
            self.message = f'Ocorreu um <a href="{self.get_absolute_url()}">erro</a> '
        else:
            self.partial = self.total
            self.message = message
        self.end = datetime.now()
        Task.objects.filter(pk=self.pk).update(error=self.error, message=self.message, file=self.file, end=self.end, partial=self.partial, url=self.url)
        obj = Task.objects.filter(pk=self.pk).first()
        if obj and obj.notify:
            self.send_notification()

    def get_progress(self):
        progress = 0
        if self.total:
            progress = int(self.partial * 100 / self.total)
        return progress > 100 and 100 or progress

    def __str__(self):
        return 'Task #{}'.format(self.id)
