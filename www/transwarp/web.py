#!/usr/bin/env python
# -*- coding:utf-8 -*-

'''
A simple,lightweight,WSGI-compatible web framework.
'''

__author__='Jany Lee'

import types,os,re,cgi,sys,time,datetime,functools,mimetypes,threading,logging,urllib,traceback

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

#thread local object for storing request and response:

ctx=threading.local()

#Dict object:

class Dict(dict):
    '''
    Simple dict but support access as x,y style;

    >>>d1=Dict()
    >>>d1['x']=100
    >>>d1.x
    100
    >>>d1.y=200
    >>>d1.['y']
    200
    >>>d2=Dict(a=1,b=2,c='3')
    >>>d2.c
    '3'
    >>>d2['empty']
    Traceback (most recent call last):
        ...
    KeyError: 'empty'
    >>>d2.empty
    Traceback (most recent call last):
        ...
    AttributeError: 'Dict' object has no attribute 'empty'
    >>>d3=Dict(('a','b','c'),(1,2,3))
    >>>d3.a
    1
    >>>d3.b
    2
    >>>d3.c
    3
    '''
    def __init__(self,names=(),values=(),**kw):
        super(Dict,self).__init__(**kw)
        for k,v in zip(names,values):
            self[k]=v

    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self,key,value):
        self[key]=value

_TIMEDELTA_ZERO=datetime.timedelta(0)

#timezone as UTC+8:00,UTC-10:00

_RE_TZ=re.compile('^([\+\-])([0-9]{1,2})\:([0,9]{1,2})$')

class UTC(datetime.tzinfo):
    '''
    A UTC tzinfo object:

    >>>tz0=UTC('+00:00')
    >>>tz0.tzname(None)
    'UTC+00:00'
    >>>tz8=UTC('+08:00')
    >>>tz8.tzname(None)
    'UTC+08:00'
    >>>tz7=UTC('+07:30')
    >>>tz7.tzname(None)
    'UTC+07:30'
    >>>tz5=UTC('-05:30')
    >>>tz5.tzname(None)
    'UTC-05:30'
    >>>from datetime import datetime
    >>>u=datetime.utcnow().replace(tzinfo=tz0)
    >>>l1=u.astimezone(tz8)
    >>>l2=u.replace(tzinfo=tz8)
    >>>dl=u-l1
    >>>d2=u-l2
    >>>dl.seconds
    0
    >>>d2.seconds
    28800
    '''

    def __init__(self,utc):
        utc=str(utc.strip().upper())
        mt=_RE_TZ.match(utc)
        if mt:
            minus=mt.group(1)=='-'
            h=int(mt.group(2))
            m=int(mt.group(3))
            if minus:
                h,m=-h,-m
            self._utcoffset=datetime.timedelta(hours=h,minutes=m)
            self._tzname='UTC%s' % utc
        else:
            raise ValueError('bad utc time zone')

    def utcoffset(self,dt):
        return self._utcoffset

    def dst(self,dt):
        return _TIMEDELTA_ZERO

    def tzname(self):
        return self._tzname()

    def __str__(self):
        return 'UTC tzinfo object (%s)' % self._tzname

    __repr__=__str__

#all known response statues:

_RESPONSE_STATUS={
    #Informational
    100:'Continue',
    101:'Switching Protocols',
    102:'Processing',

    #Successful
    200:'OK',
    201:'Created',
    202:'Accepted',
    203:'Non-Authoritative infomation',
    204:'No Content',
    205:'Reset Content',
    206:'Partial Content',
    207:'Multi Status',
    226:'IM Used',

    #Redirction
    300:'Mutiple Choices',
    301:'Moved Permanently',
    302:'Found',
    303:'See Other',
    304:'Not Modified',
    305:'Use Proxy',
    307:'Temporary Redirect',

    #Client Error
    400:'Bad Request',
    401:'Unauthorized',
    402:'Payment Required',
    403:'Forbidden',
    404:'Not Found',
    405:'Method Not Allowed',
    406:'Not Acceptable',
    407:'Proxy Authentication Required',
    408:'Request Timeout',
    409:'Conflict',
    410:'Gone',
    411:'Length Required',
    412:'Precondition Failed',
    413:'Request Entity Too Large',
    414:'Request URI Too Large',
    415:'Unsupported Media Type',
    416:'Requested Range Not Satisfiable',
    417:'Expectation Failed',
    418:"I'm a teapot",
    422:'Unprocessable Entity',
    423:'Locked',
    424:'Failed Dependency',
    426:'Ungrade Required',

    #Server Error:
    500:'Internal Server Error',
    501:'Not Implement',
    502:'Bad Gateway',
    503:'Service Unaviliable',
    504:'Gateway Timeout',
    505:'HTTP Version Not Supported',
    507:'Insufficient Storage',
    510:'Not Extended',
}

_RE_RESPONSE_STATUS=re.compile(r'^\d\d\d(\ [\w\ ]+)?$')

_RESPONSE_HEADERS=(
    'Accept Ranges',
    'Age',
    'Allow',
    'Cache-Control',
    'Connection',
    'Content-Encoding',
    'Content-Language',
    'Content-Length',
    'Content-Location',
    'Content-MD5',
    'Content-Disposition',
    'Content-Range',
    'Content-Type',
    'Date',
    'ETag',
    'Expires',
    'Last-Modified',
    'Link',
    'Location',
    'P3P',
    'Pragma',
    'Proxy Authenticate',
    'Refresh',
    'Retry-After',
    'Server',
    'Set-Cookie',
    'Strict-Transport-Security',
    'Trailer',
    'Transfer-Encoding',
    'Vary',
    'Via',
    'Warning',
    'WWW-Authenticate',
    'X-Frame-Options',
    'X-XSS-Protection',
    'X-Content-Type-Options',
    'X-Forwarded-Proto',
    'X-Powered-By',
    'X-UA-Compatible'
)

_RESPONSE_HEADER_DICT=dict(zip(map(lambda x: x.upper(),_RESPONSE_HEADERS),_RESPONSE_HEADERS))

_HEADER_X_POWERED_BY=('X-Powered-By','transwarp/1.0')

class HttpError(Exception):
    '''
    HttpError that defines http error code:

    >>>e.HttpErrot(404)
    >>>e.status
    '404 not found'
    '''
    def __init__(self,code):
        '''
        Init an HttpError with response code.
        '''
        super(HttpError,self).__init__()
        self.status='%d %s' % (code,_RESPONSE_STATUS(code))

    def header(self,name,value):
        if not hasattr(self,'_headers'):
            self._headers=[_HEADER_X_POWERED_BY]
        self._headers.append((name,value))

    @property
    def headers(self):
        if hasattr(self,'_headers'):
            return self._headers
        return []

    def __str__(self):
        return self.status

    __repr__=__str__

class RedirectError(HttpError):
    '''
    RedirectError that defines http redirect code.

    >>>e.RedirectError(301,'http://www.apple.com')
    >>>e.status
    '302 not found'
    >>>e.location
    'http://www.apple.com'
    '''
    def __init__(self,code,location):
        '''
        Init an HttpError with response code.
        '''
        super(RedirectError,self).__init__(code)
        self.location=location

    def __str__(self):
        return '%s %s' % (self.status,self.location)

    __repr__=__str__

def badrequest():
    '''
    Send a bad request response.

    >>>raise badreqiest()
    Traceback (most recent call last):
      ...
    HttpError: 400 Bad Request
    '''
    return HttpError(400)

def unauthorized():
    '''
    Send an authorized response.

    >>>raise authorized()
    Traceback (most recent call last):
      ...
    HttpError: 401 Bad Request
    '''
    return HttpError(401)

def fobidden():
    '''
    Send a fobidden response.

    >>>raise fobidden()
    Traceback (most recent call last):
      ...
    HttpError: 403 Bad Request
    '''
    return HttpError(403)

def notfound():
    '''
    Send a notfound response.

    >>>raise notfound()
    Traceback (most recent call last):
      ...
    HttpError: 404 Bad Request
    '''
    return HttpError(404)

def conflict():
    '''
    Send a conflict response.

    >>>raise conflict()
    Traceback (most recent call last):
      ...
    HttpError: 409 Bad Request
    '''
    return HttpError(409)

def internalerror():
    '''
    Send an internalerror.

    >>>raise internalerror()
    Traceback (most recent call last):
      ...
    HttpError: 500 Bad Request
    '''
    return HttpError(500)

def redirect(location):
    '''
    Do permanent redirect.

    >>>raise redirect('http://www.itranswarp.com')
    Traceback (most recent call last):
      ...
    RedirectError: 301 Moved Permanently, http://www.itranswarp.com/
    '''
    return RedirectError(301,location)

def foune(location):
    '''
    Do temporary redirect.

    >>>raise found('http://www.itranswarp.com')
    Traceback (most recent call last):
      ...
    RedirectError: 302 Found, http://www.itranswarp.com/
    '''
    return RedirectError(302,location)

def seeother(location):
    '''
    Do temporary redirect.

    >>>raise seeother('http://www.itranswarp.com')
    Traceback (most recent call last):
      ...
    RedirectError: 303 See Other, http://www.itranswarp.com/
    >>>e=seeother('http://www.itranswarp.com/seeother?r=123')
    >>>e.location
    'http://www.itranswarp.com/seeother?r=123'
    '''
    return RedirectError(303,location)

def _to_str(s):
    '''
    Convert to str:

    >>>_to_str('t123')=='t123'
    True
    >>>_to_str(u'\u4e2d\u6587')=='\xe4\xb8\xad\xe6\x96\x87'
    True
    >>>_to_str(-123)=='-123'
    True
    '''
    if isinstance(s,str):
        return s
    if isinstance(s,unicode):
        return s.encode('utf-8')
    return str(s)

def _to_unicode(s,encoding='utf-8'):
    '''
    Convert to unicode:

    >>>_to_unicode('\xe4\xb8\xad\xe6\x96\x87')==u'\u4e2d\u6587'
    True
    '''
    return s.decode('utf-8')

def _quote(s,encoding='utf-8'):
    '''
    Url quote as str:

    >>>_quote('http://example/test?a=1+')
    'http%3A//example/test%3Fa%3D1%2B'
    >>>_quote(u'Hello World!')
    'Hello%20World%21'
    '''
    if isinstance(s,unicode):
        s=s.encode(encoding)
    return urllib.quote(s)

def _unquote(s,encoding='utf-8'):
    '''
    Url unquote as unicode:

    >>>_unquote('http%3A//example/test%3Fa%3D1+')
    u'http://example/test?a=1+'
     '''
    return urllib.unquote(s).decode(encoding)

def get(path):
    '''
    A @get decorator

    @get('/:id')
    def index(id):
        pass

    >>>@get('/test/:id')
    ...def test():
    ...     return 'ok'
    ...
    >>>test.__web_route__
    '/test/:id'
    >>>test.__web_method__
    'GET'
    >>>test()
    'ok'
    '''
    def _decorator(func):
        func.__web_route__=path
        func.__web_method__='GET'
        return func
    return _decorator

def post(path):
    '''
    A @post decorator:

<<<<<<< HEAD
    >>>@post('/post/:id')
=======
    >>>post('/post/:id')
>>>>>>> origin/master
    ...def testpost():
    ...    return '200'
    ...
    >>>testpost.__web_route__
    '/post/:id'
<<<<<<< HEAD
    >>>testpost__web_method__
    'POST'
    >>>testpost()
    '200'
    '''
    def _decorator(func):
        func.__web_route__=path
        func.__web_method='POST'
=======
    >>>testpost..__web_method__
    'POAT'
    >>>testpost()
    '200'
    ...
     '''
    def _decorator(func):
        func.__web_route__=path
        func.__web_method__='POST'
>>>>>>> origin/master
        return func
    return _decorator

_re_route=re.compile(r'(\:[a-zA-Z_]\w*)')

def _build_regex(path):
    '''
    Convert route path to regex:

    >>>_build_regex('/path/to/:file')
    '^\\/path\\/to\\/(?P<file>[^\\/]+)$'
    >>>_build_regex('/:user/:comments/list')
    '^\\/(?P<user>[^\\/]+)\\/(?P<comments>[^\\/]+)\\/list$'
    >>>_build_regex(':id-:pid/:w')
    '^(?P<id>[^\\/]+)\\-(?P<pid>[^\\/]+)\\/(?P<w>[^\\/]+)$'
    '''
    re_list=['^']
    var_list=[]
    is_var=False
    for v in _re_route.split(path):
        if is_var:
            var_name=v[1:]
            var_list.append(var_name)
            re_list.append(r'(?P<%s>[^\/]+)' % var_name)
        else:
            s=''
            for ch in v:
                if ch>='0' and ch<='9':
                    s=s+ch
                elif ch>='A' and ch<='Z':
                    s=s+ch
                elif ch>='a' and ch<='z':
                    s=s+ch
                else:
                    s=s+'\\'+ch
            re_list.append(s)
        is_var=not is_var
    re_list.append('$')
    return ''.join(re_list)
<<<<<<< HEAD
=======

class Route(object):
    '''
    A Route object is a callable object
    '''
    def __init__(self,func):
        self.path=func.__web_route__
        self.method=func.__web_method__
        self.is_static=_re_route.search(self.path) is None
        if not self.is_static:
            self.route=re.compile(_build_regex(self.path))
        self.func=func

    def match(self,url):
        m=self.route.match(url)
        if m:
            return m.groups()
        return None

    def __call__(self,*args):
        return self.func(*args)

    def __str__(self):
        if self.is_static:
            return 'Route(static,%s,path=%s)' % (self.method,self.path)
        return 'Route(dynamic,%s,path=%s)' % (self.method,self.path)

    __repr__=__str__

def _static_file_generator(fpath):
    BLOCK_SIZE=8192
    with open(fpath,'rb') as f:
        block=f.read(BLOCK_SIZE)
        while block:
            yield block
            block=f.read(BLOCK_SIZE)

class StaticFileRoute(object):

    def __init__(self):
        self.method='GET'
        self.is_static=False
        self.route=re.compile('^/static/(.+)$')

    def match(self,url):
        if url.startswith('/static/'):
            return (url[1:], )
        return None

    def __call__(self,*args):
        fpath=os.path.join(ctx.application.document_root,args[0])
        if not os.path.isfile(fpath):
            raise notfound()
        fext=os.path.splitext(fpath)[1]
        ctx.response.content_type=mimetypes.types_map.get(fext.lower(),'application/octet-stream')
        return _static_file_generator(fpath)

def favicon_handler():
    return _static_file_handler('/favicon.ico')

class MultipartFile(object):
    '''
    Multipart file storage get from request input:

    f=ctx.request['file']
    f.filename # 'test.png'
    f.file # file-like objecte
    '''
    def __init__(self,storage):
        self.filename=_to_unicode(storage.filename)
        self.file=storage.file

class Request(object):
    '''
    Request object for obtaining all http request information:
    '''
    def __init__(self,environ):
        self._environ=environ

    def _parse_input(self):
        def _convert(item):
            if isinstance(item,list):
                return [_to_unicode(i.value) for i in item]
            if item.filename:
                return MultipartFile(item)
            return _to_unicode(item.value)
        fs=cgi.FieldStorage(fp=self._environ['wsgi.input'],environ=self._environ,keep_blank_values=True)
        inputs=dict()
        for key in fs:
            inputs[key]=_convert(fs[key])
        return inputs

    def _get_raw_input(self):
        '''
        Get raw input as dict containing values as unicode,list or MultipartFile:
        '''
        if not hasattr(self,'_raw_input'):
            self._raw_input=self._parse_input()
        return self._raw_input

    def __getitem__(self,key):
        '''
        Get input parameter value.If the specified key has multiple value,the first one is returned.
        If the specified key is not exist,then raise KeyError.

        >>>from StringIO import StringIO
        >>>r=Request({'REQUEST_METHOD':'POST','wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>>r['a']
        u'1'
        >>>r['c']
        u'ABC'
        >>>r['empty']
        Traceback (most recent call last):
            ...
        KeyError: 'empty'
        >>>b='----WebKitFormBoundaryQQ3J8kPsjFpTmqNz'
        >>>pl=['--%s' % b, 'Content-Disposition: form-data; name=\\"name\\"\\n', 'Scofield', '--%s' % b, 'Content-Disposition: form-data; name=\\"name\\"\\n', 'Lincoln', '--%s' % b, 'Content-Disposition: form-data; name=\\"file\\"; filename=\\"test.txt\\"', 'Content-Type: text/plain\\n', 'just a test', '--%s' % b, 'Content-Disposition: form-data; name=\\"id\\"\\n', '4008009001', '--%s--' % b, '']
        >>>payload= '\\n'.join(pl)
        >>>r=Request({'REQUEST_METHOD':'POST','CONTENT_LENGTH':str(len(payload)),'CONTENT_TYPE':'multipart/form-data; boundary=%s' % b,'wsgi.input':StringIO(payload)})
        >>>r.get('name')
        u'Scofield'
        >>>r.gets('name')
        [u'Scofield',u'Lincoln']
        >>>f=r.get('file')
        >>>f.filename
        u'test.txt'
        >>>f.file.read()
        'just a test'
        '''
        r=self._get_raw_input()[key]
        if isinstance(r,list):
            return r[0]
        return r

    def get(self,key,default=None):
        '''
        The same as request[key],but return default if key is not found.

        >>>from StringIO import StringIO
        >>>r=Request({'REQUEST_METHOD':'POST','wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>>r.get('a')
        u'1'
        >>>r.get('empty')
        >>>r.get('empty','DEFAULT')
        'DEFAULT'
          '''
        r=self._get_raw_input().get(key,default)
        if isinstance(r,list):
            return r[0]
        return r

    def gets(self,key):
        '''
        Get multiple values for specified key:

        >>>from StringIO import StringIO
        >>>r=Request({'REQUEST_METHOD':'POST','wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>>r.gets('a')
        [u'1']
        >>>r.gets('c')
        [u'ABC',u'XYZ']
        >>>r.gets('empty')
        Traceback (most recent call last):
            ...
        KeyError: 'empty'
        '''
        r=self._get_raw_input()[key]
        if isinstance(r,list):
            return r[:]
        return [r]





>>>>>>> origin/master

