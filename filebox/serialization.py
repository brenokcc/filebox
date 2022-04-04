# -*- coding: utf-8 -*-
import base64
import datetime
import json
import pickle
import zlib
from decimal import Decimal
from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core import signing
from django.db import models
from django.http import HttpRequest, QueryDict


def dumps_queryset(queryset):
    serialized_str = base64.b64encode(zlib.compress(pickle.dumps(queryset.query))).decode()
    payload = {'model_label': queryset.model._meta.label, 'query': serialized_str}
    signed_data = signing.dumps(payload)
    return signed_data


def dumps_model(o):
    payload = {'label': o._meta.label, 'pk': o.pk}
    signed_data = signing.dumps(payload)
    return signed_data


def loads_queryset(data):
    payload = signing.loads(data)
    model = apps.get_model(payload['model_label'])
    query = pickle.loads(zlib.decompress(base64.b64decode(payload['query'].encode())))
    queryset = model.objects.none()
    queryset.query = query
    return queryset


def loads_model(data):
    try:
        payload = signing.loads(data)
        model = apps.get_model(payload['label'])
        return model.objects.filter(pk=payload['pk'])[0]
    except Exception as e:
        raise Exception('pk:{}. label:{}. Erro:{}.'.format(payload['pk'], payload['label'], e))


def dump_datetime(data):
    return data.isoformat()


def load_datetime(data):
    return datetime.datetime.fromisoformat(data)


def get_serializable_meta(meta):
    cleaned_meta = {}
    included_keys = ['REMOTE_ADDR', 'QUERY_STRING', 'REQUEST_METHOD', 'CONTENT_TYPE', 'CONTENT_LENGTH']
    for key, value in meta.items():
        if key in included_keys or key.startswith('HTTP_') or key.startswith('REQUEST_'):
            try:
                json.dumps(value)
                cleaned_meta[key] = value
            except Exception:
                pass
    return cleaned_meta


def dump_request(request):
    meta_str = get_serializable_meta(request.META)
    get_str = request.GET
    post_str = request.POST
    session_key = hasattr(request, 'session') and request.session.session_key or ''
    return signing.dumps({
        'meta': meta_str,
        'get': get_str,
        'post': post_str,
        'user_id': request.user.id,
        'session_key': session_key,
        'method': request.method
    })


def load_request(data):
    request = HttpRequest()
    request_data = signing.loads(data)
    request.META = request_data['meta']
    get_query_dict = QueryDict(mutable=True)
    get_query_dict.update(request_data['get'])
    request.GET = get_query_dict
    post_query_dict = QueryDict(mutable=True)
    post_query_dict.update(request_data['post'])
    request.POST = post_query_dict
    request.user = User.objects.get(pk=request_data['user_id'])
    request.method = request_data['method']
    session_key = request_data['session_key']
    if session_key:
        session = import_module(settings.SESSION_ENGINE).SessionStore(session_key=session_key)
    else:
        session = {}

    request.session = session
    return request


def dump_bytes(o):
    return base64.b64encode(o).decode()


def load_bytes(o):
    return base64.b64decode(o)


def serialize(o):
    return json.dumps(o, cls=JsonEncoder)


class JsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, models.QuerySet):
            return {'QuerySet': dumps_queryset(o)}
        elif isinstance(o, models.Model):
            return {'Model': dumps_model(o)}
        elif isinstance(o, datetime.datetime):
            return {'Datetime': dump_datetime(o)}
        elif isinstance(o, datetime.date):
            return {'Date': dump_datetime(o)}
        elif isinstance(o, HttpRequest):
            return {'HttpRequest': dump_request(o)}
        elif isinstance(o, Decimal):
            return {'Decimal': str(o)}
        elif isinstance(o, bytes):
            return {'Bytes': dump_bytes(o)}
        elif isinstance(o, AnonymousUser):
            return {'AnonymousUser': None}
        return json.JSONEncoder.default(self, o)


def deserialize(o):
    return json.loads(o, cls=JsonDecoder)


class JsonDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)
        self.scan_once = json.scanner.py_make_scanner(self)

    def object_hook(self, o):
        if type(o) == dict:
            for key, value in o.items():
                if key == 'QuerySet':
                    return loads_queryset(value)
                elif key == 'Model':
                    return loads_model(value)
                elif key == 'Datetime':
                    return load_datetime(value)
                elif key == 'Date':
                    return load_datetime(value).date()
                elif key == 'HttpRequest':
                    return load_request(value)
                elif key == 'Decimal':
                    return Decimal(value)
                elif key == 'Bytes':
                    return load_bytes(value)
                elif key == 'AnonymousUser':
                    return AnonymousUser()
        return o
