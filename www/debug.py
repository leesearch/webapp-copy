#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time   : 2017/10/17 21:46
# @Author : lijunjiang
# @File   : test.py

def hello():
    return 'hello'

if __name__ == '__main__':
    print('###' * 10)
    name = raw_input("Please input your name: ")
    print(hello() + name)
    print('###' * 10)