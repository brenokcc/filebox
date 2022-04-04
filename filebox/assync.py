import sys
import threading
import traceback
from filebox.models import Task
from filebox.assync import serialization
from django.conf import settings
from celery.result import AsyncResult
from django.http import HttpResponseRedirect, HttpResponse

from filebox import celery_app as app


@app.task
def error_handler(uuid):
    result = AsyncResult(uuid)
    Task.objects.get(uuid=uuid).finalize(result.traceback, '..', error=True)


@app.task
def execute_task(module_name, func_name, *args, **kwargs):
    module = __import__(module_name, fromlist=module_name.split('.'))
    getattr(module, func_name)(*args, **kwargs)


class Thread(threading.Thread):
    def __init__(self, task=None, targs=None, tkwargs=None, *args, **kwargs):
        self._task = task
        self._targs = targs or ()
        self._tkwargs = tkwargs or {}
        self._target = kwargs['target']
        super(Thread, self).__init__(*args, **kwargs)

    def run(self):
        try:
            self._target(*self._targs, **self._tkwargs)
        except BaseException:
            self._task.finalize(traceback.format_exc(), '..', error=True)


# Decorator
def task(name, method=None):

    def assincrono(func):

        use_celery = getattr(settings, 'USE_CELERY', False)
        queues = getattr(settings, 'CELERY_TASK_QUEUES', {})
        is_suap_server = 'worker' not in sys.argv

        def decorate_suap(*args, **kwargs):
            tarefa = Task.objects.create(type=name, user=None)
            kwargs['task'] = tarefa

            args = (serialization.serialize(arg) for arg in args)
            all_args = [func.__module__, func.__name__]
            func_qual_name = '.'.join(all_args)
            for arg in args:
                all_args.append(arg)

            queue = 'geral'
            for key, value in queues.items():
                if func_qual_name == key:
                    queue = value

            new_kwargs = {}
            for key, value in list(kwargs.items()):
                new_kwargs[key] = serialization.serialize(value)
            execute_task.apply_async(args=tuple(all_args), kwargs=new_kwargs, link_error=error_handler.s(), countdown=2, queue=queue)
            tarefa.save()
            return HttpResponseRedirect('/process/{}/'.format(tarefa.uuid))

        def decorate_celery(*args, **kwargs):
            args = (serialization.deserialize(arg) for arg in args)
            new_kwargs = {}
            for key, value in list(kwargs.items()):
                new_kwargs[key] = serialization.deserialize(value)
            # force deserialize
            if 'task' in new_kwargs and new_kwargs['task'] is None:
                new_kwargs['task'] = serialization.deserialize(kwargs['task'])
            func(*args, **new_kwargs)
            return None

        def decorate_thread(*args, **kwargs):
            tarefa = Task.objects.create(type=name, user=None)
            kwargs['task'] = tarefa
            Thread(target=func, task=tarefa, targs=args, tkwargs=kwargs).start()
            return HttpResponseRedirect('/process/{}/'.format(tarefa.uuid))

        retorno = decorate_thread
        if use_celery and not method == 'thread':
            if is_suap_server:
                retorno = decorate_suap
            else:
                retorno = decorate_celery

        return retorno

    return assincrono


def file_response(task):
    try:
        content = task.file.read()
    except Exception:
        return HttpResponse('/', 'Arquivo expirado.', 'error')
    if task.file.endswith('.xls'):
        response = HttpResponse(content, content_type='application/ms-excel')
        response['Content-Disposition'] = 'inline; filename=Relatorio.xls'
    elif task.file.endswith('.xlsx'):
        response = HttpResponse(content, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'inline; filename=Relatorio.xlsx'
    elif task.file.endswith('.zip'):
        response = HttpResponse(content, content_type='application/zip')
        response['Content-Disposition'] = 'inline; filename=Arquivo.zip'
    elif task.file.endswith('.pdf'):
        response = HttpResponse(content, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename=Documento.pdf'
    elif task.file.endswith('.csv'):
        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = 'inline; filename=Relatorio.csv'
    elif task.file.endswith('.txt'):
        response = HttpResponse(content, content_type='text/txt')
        response['Content-Disposition'] = 'inline; filename=Relatorio.txt'
    elif task.file.endswith('.html'):
        response = HttpResponse(content)
    elif task.file.endswith('.zip'):
        response = HttpResponse(content, content_type='application/zip')
        response['Content-Disposition'] = 'inline; filename=Arquivo.zip'
    else:
        response = HttpResponse(content, content_type='application/octet-stream')
        response['Content-Disposition'] = 'inline; filename=Arquivo.txt'
    return response