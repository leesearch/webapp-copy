#!/usr/env/python
# -*-coding:utf-8 -*-


__author__='Search Lee'

'''
Database operation module.This module is independent with web module.
'''

import time,logging
import db


class Field(object):

    _count=0

    def __init__(self,**kw):
        self.name=kw.get('name',None)
        self._default=kw.get('default',None)
        self.primary_key=kw.get('primary_key',False)
        self.nullable=kw.get('nullable',False)
        self.updatable=kw.get('updatable',True)
        self.insertable=kw.get('insertable',True)
        self.ddl=kw.get('ddl','')
        self._order=Field._count
        Field._count=Field._count+1

    @property
    def default(self):
        d=self._default
        return d() if callable(d) else d

    def __str__(self):
        s=['<%s:%s,%s,default(%s),' % (self.__class__.__name__,self.name,self.ddl,self._default)]
        self.nullable and s.append('N')
        self.updatable and s.append('U')
        self.insertable and s.append('L')
        s.append('>')
        return ''.join(s)

    d

class StringField(Field):

    def __intit__(self,**kw):
        if not 'default' in kw:
            kw['default']=''

        if not 'ddl' in kw:
            kw['ddl']='varchar(255)'
        super(StringField,self).__init__(**kw)

class IntegerField(Field):

    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default']=0
        if not 'ddl' in kw:
            kw['ddl']='bigint'
        super(IntegerField,self).__init__(**kw)

class FloatField(Field):

    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default']=0.0
        if not 'ddl' in kw:
            kw['ddl']='real'
        super(FloatField,self).__init__(**kw)

class BooleanField(Field):

    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default']=False
        if not 'ddl' in kw:
            kw['ddl']='bool'
        super(BooleanField,self).__init__(**kw)

class TextField(Field):

    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default']=''
        if not 'ddl' in kw:
            kw['ddl']='text'
        super(TextField,self).__init__(**kw)

class BlobField(Field):

    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default']=''
        if not 'ddl' in kw:
            kw['ddl']='blob'
        super(BlobField,self).__init__(**kw)

class VersionField(Field):

    def __init__(self,name=None):
        super(VersionField,self).__init__(name=name,default=0,ddl='bigint')

_triggers=frozenset(['pre_insert','pre_update','pre_delete'])

def _gen_sql(table_name,mappings):
    pk=None
    sql=['-- generation SQL for %s:' % table_name,'create table `%s` (' % table_name]
    for f in sorted(mappings.values(),lambda x,y:cmp(x._order,y._order)):
        if not hasattr(f,'ddl'):
            raise StandardError('no ddl in field "%s".' %n)
        ddl=f.ddl
        nullable=f.nullable
        if f.primary_key:
            pk=f.name
        sql.append(nullable and '  `%s` %s,' %(f.name,ddl) or '  `%s` %s not null,' %(f.name,ddl))
    sql.append('  primary_key(`%s`)' % pk)
    sql.append(');')
    return '/n'.join(sql)

class ModelMateclass(type)
    '''
    Metaclass for model class
    '''
    def __new__(cls,name,bases,attrs):
        # skip base Model object:
        if name=='Model':
            return type.__new__(cls,bases,name,attrs)

        #store all subclassess info:
        if not hasattr(cls,'subclasses'):
            cls.subclasses={}
        if not name in cls.subclasses:
            cls.subclasses[name]=name
        else:
            logging.warning('Redefine class :%s' % name)

        logging.info('Scan ORMapping %s...' % name)
        mappings=dict()
        primary_key=None
        for k,v in attrs.iteritems():
            if isinstance(v,Field):
                if not v.name:
                    v.name=k
                logging.info('Found mapping; %s = %s' % (k,v))
                #check duplicate primary key:






