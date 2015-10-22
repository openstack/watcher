# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


class ASTNode(object):
    visited = False
    inline = False

    def __init__(self):
        pass

    def children(self):
        for c in self._children:
            yield c

    def __str__(self):
        pass


class Condition(ASTNode):
    def __init__(self, what, operator, _on):
        self.what = what
        self._on = "'" + str(_on) + "'"
        self.operator = operator

    def __str__(self):
        s = self.what + ' ' + self.operator + ' ' + self._on
        if self.inline:
            s = '' + s + ''
        return s


class BinaryNode(ASTNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return '({left} {middle} {right})'.format(
            left=self.left,
            middle=self.middle,
            right=self.right
        )


class And(BinaryNode):
    middle = 'AND'


class Or(BinaryNode):
    middle = 'OR'


class List(ASTNode):
    def __init__(self, *args):
        for arg in args:
            if hasattr(arg, 'inline'):
                arg.inline = True
        self.items = args

    def __str__(self):
        lst = ', '.join(map(lambda x: str(x), self.items))
        if self.inline:
            lst = '(' + lst + ')'
        return lst


class Set(ASTNode):
    def __init__(self, **kwargs):
        self.items = kwargs

    def __str__(self):
        return ', '.join(
            ['{0}={1}'.format(key, val) for key, val in self.items.items()])


class Returning(ASTNode):
    def __init__(self, _list='*'):
        self._list = _list

    def __str__(self):
        return 'RETURNING {_list}'.format(_list=self._list)


class Limit(ASTNode):
    def __init__(self, limit):
        if hasattr(limit, 'inline'):
            limit.inline = True
        self.limit = limit

    def __str__(self):
        return " LIMIT " + str(self.limit)


class Where(ASTNode):
    def __init__(self, logic):
        if hasattr(logic, 'inline'):
            logic.inline = True
        self.logic = logic

    def __str__(self):
        return "WHERE " + str(self.logic)


class GroupBy(ASTNode):
    def __init__(self, logic):
        if hasattr(logic, 'inline'):
            logic.inline = True
        self.logic = logic

    def __str__(self):
        return " group by " + str(self.logic)


class From(ASTNode):
    def __init__(self, _from):
        if hasattr(_from, 'inline'):
            _from.inline = True
        self._from = _from

    def __str__(self):
        return 'FROM {_from}'.format(_from=self._from)


class Select(ASTNode):
    def __init__(self, _from, what='*', where='', groupby='',
                 limit=''):
        self._from = "\"" + _from + "\""
        self.what = what
        self.where = where and Where(where)
        self.groupby = groupby
        self.limit = limit and Limit(limit)
        self.inlint = False

    def __str__(self):
        s = 'SELECT ' + str(self.what) + ' FROM ' + str(
            self._from) + ' ' + str(self.where) + str(self.groupby) + str(
            self.limit)
        if self.inline:
            s = '(' + s + ')'
        return s
