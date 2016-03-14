#    Copyright 2015 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime
import gettext

import iso8601
import netaddr
from oslo_utils import timeutils
import six

from watcher.objects import base
from watcher.objects import utils
from watcher.tests import base as test_base

gettext.install('watcher')


class MyObj(base.WatcherObject):
    VERSION = '1.0'

    fields = {'foo': int,
              'bar': str,
              'missing': str,
              }

    def obj_load_attr(self, attrname):
        setattr(self, attrname, 'loaded!')

    def query(cls, context):
        obj = cls(context)
        obj.foo = 1
        obj.bar = 'bar'
        obj.obj_reset_changes()
        return obj

    def marco(self, context):
        return 'polo'

    def update_test(self, context):
        if context.project_id == 'alternate':
            self.bar = 'alternate-context'
        else:
            self.bar = 'updated'

    def save(self, context):
        self.obj_reset_changes()

    def refresh(self, context):
        self.foo = 321
        self.bar = 'refreshed'
        self.obj_reset_changes()

    def modify_save_modify(self, context):
        self.bar = 'meow'
        self.save()
        self.foo = 42


class MyObj2(object):
    @classmethod
    def obj_name(cls):
        return 'MyObj'

    def get(cls, *args, **kwargs):
        pass


class DummySubclassedObject(MyObj):
    fields = {'new_field': str}


class TestMetaclass(test_base.TestCase):
    def test_obj_tracking(self):

        @six.add_metaclass(base.WatcherObjectMetaclass)
        class NewBaseClass(object):
            fields = {}

            @classmethod
            def obj_name(cls):
                return cls.__name__

        class Test1(NewBaseClass):
            @staticmethod
            def obj_name():
                return 'fake1'

        class Test2(NewBaseClass):
            pass

        class Test2v2(NewBaseClass):
            @staticmethod
            def obj_name():
                return 'Test2'

        expected = {'fake1': [Test1], 'Test2': [Test2, Test2v2]}

        self.assertEqual(expected, NewBaseClass._obj_classes)
        # The following should work, also.
        self.assertEqual(expected, Test1._obj_classes)
        self.assertEqual(expected, Test2._obj_classes)


class TestUtils(test_base.TestCase):

    def test_datetime_or_none(self):
        naive_dt = datetime.datetime.now()
        dt = timeutils.parse_isotime(timeutils.isotime(naive_dt))
        self.assertEqual(dt, utils.datetime_or_none(dt))
        self.assertEqual(naive_dt.replace(tzinfo=iso8601.iso8601.Utc(),
                                          microsecond=0),
                         utils.datetime_or_none(dt))
        self.assertIsNone(utils.datetime_or_none(None))
        self.assertRaises(ValueError, utils.datetime_or_none, 'foo')

    def test_datetime_or_str_or_none(self):
        dts = timeutils.isotime()
        dt = timeutils.parse_isotime(dts)
        self.assertEqual(dt, utils.datetime_or_str_or_none(dt))
        self.assertIsNone(utils.datetime_or_str_or_none(None))
        self.assertEqual(dt, utils.datetime_or_str_or_none(dts))
        self.assertRaises(ValueError, utils.datetime_or_str_or_none, 'foo')

    def test_int_or_none(self):
        self.assertEqual(1, utils.int_or_none(1))
        self.assertEqual(1, utils.int_or_none('1'))
        self.assertIsNone(utils.int_or_none(None))
        self.assertRaises(ValueError, utils.int_or_none, 'foo')

    def test_str_or_none(self):
        class Obj(object):
            pass
        self.assertEqual('foo', utils.str_or_none('foo'))
        self.assertEqual('1', utils.str_or_none(1))
        self.assertIsNone(utils.str_or_none(None))

    def test_ip_or_none(self):
        ip4 = netaddr.IPAddress('1.2.3.4', 4)
        ip6 = netaddr.IPAddress('1::2', 6)
        self.assertEqual(ip4, utils.ip_or_none(4)('1.2.3.4'))
        self.assertEqual(ip6, utils.ip_or_none(6)('1::2'))
        self.assertIsNone(utils.ip_or_none(4)(None))
        self.assertIsNone(utils.ip_or_none(6)(None))
        self.assertRaises(netaddr.AddrFormatError, utils.ip_or_none(4), 'foo')
        self.assertRaises(netaddr.AddrFormatError, utils.ip_or_none(6), 'foo')

    def test_dt_serializer(self):
        class Obj(object):
            foo = utils.dt_serializer('bar')

        obj = Obj()
        obj.bar = timeutils.parse_isotime('1955-11-05T00:00:00Z')
        self.assertEqual('1955-11-05T00:00:00Z', obj.foo())
        obj.bar = None
        self.assertIsNone(obj.foo())
        obj.bar = 'foo'
        self.assertRaises(AttributeError, obj.foo)

    def test_dt_deserializer(self):
        dt = timeutils.parse_isotime('1955-11-05T00:00:00Z')
        self.assertEqual(dt, utils.dt_deserializer(timeutils.isotime(dt)))
        self.assertIsNone(utils.dt_deserializer(None))
        self.assertRaises(ValueError, utils.dt_deserializer, 'foo')

    def test_obj_to_primitive_list(self):
        class MyList(base.ObjectListBase, base.WatcherObject):
            pass
        mylist = MyList(self.context)
        mylist.objects = [1, 2, 3]
        self.assertEqual([1, 2, 3], base.obj_to_primitive(mylist))

    def test_obj_to_primitive_dict(self):
        myobj = MyObj(self.context)
        myobj.foo = 1
        myobj.bar = 'foo'
        self.assertEqual({'foo': 1, 'bar': 'foo'},
                         base.obj_to_primitive(myobj))

    def test_obj_to_primitive_recursive(self):
        class MyList(base.ObjectListBase, base.WatcherObject):
            pass

        mylist = MyList(self.context)
        mylist.objects = [MyObj(self.context), MyObj(self.context)]
        for i, value in enumerate(mylist):
            value.foo = i
        self.assertEqual([{'foo': 0}, {'foo': 1}],
                         base.obj_to_primitive(mylist))


class TestObjectListBase(test_base.TestCase):

    def test_list_like_operations(self):
        class Foo(base.ObjectListBase, base.WatcherObject):
            pass

        objlist = Foo(self.context)
        objlist._context = 'foo'
        objlist.objects = [1, 2, 3]
        self.assertEqual(list(objlist), objlist.objects)
        self.assertEqual(3, len(objlist))
        self.assertIn(2, objlist)
        self.assertEqual([1], list(objlist[:1]))
        self.assertEqual('foo', objlist[:1]._context)
        self.assertEqual(3, objlist[2])
        self.assertEqual(1, objlist.count(1))
        self.assertEqual(1, objlist.index(2))

    def test_serialization(self):
        class Foo(base.ObjectListBase, base.WatcherObject):
            pass

        class Bar(base.WatcherObject):
            fields = {'foo': str}

        obj = Foo(self.context)
        obj.objects = []
        for i in 'abc':
            bar = Bar(self.context)
            bar.foo = i
            obj.objects.append(bar)

        obj2 = base.WatcherObject.obj_from_primitive(obj.obj_to_primitive())
        self.assertFalse(obj is obj2)
        self.assertEqual([x.foo for x in obj],
                         [y.foo for y in obj2])

    def _test_object_list_version_mappings(self, list_obj_class):
        # Figure out what sort of object this list is for
        list_field = list_obj_class.fields['objects']
        item_obj_field = list_field._type._element_type
        item_obj_name = item_obj_field._type._obj_name

        # Look through all object classes of this type and make sure that
        # the versions we find are covered by the parent list class
        for item_class in base.WatcherObject._obj_classes[item_obj_name]:
            self.assertIn(
                item_class.VERSION,
                list_obj_class.child_versions.values())

    def test_object_version_mappings(self):
        # Find all object list classes and make sure that they at least handle
        # all the current object versions
        for obj_classes in base.WatcherObject._obj_classes.values():
            for obj_class in obj_classes:
                if issubclass(obj_class, base.ObjectListBase):
                    self._test_object_list_version_mappings(obj_class)

    def test_list_changes(self):
        class Foo(base.ObjectListBase, base.WatcherObject):
            pass

        class Bar(base.WatcherObject):
            fields = {'foo': str}

        obj = Foo(self.context, objects=[])
        self.assertEqual(set(['objects']), obj.obj_what_changed())
        obj.objects.append(Bar(self.context, foo='test'))
        self.assertEqual(set(['objects']), obj.obj_what_changed())
        obj.obj_reset_changes()
        # This should still look dirty because the child is dirty
        self.assertEqual(set(['objects']), obj.obj_what_changed())
        obj.objects[0].obj_reset_changes()
        # This should now look clean because the child is clean
        self.assertEqual(set(), obj.obj_what_changed())


class TestObjectSerializer(test_base.TestCase):

    def test_serialize_entity_primitive(self):
        ser = base.WatcherObjectSerializer()
        for thing in (1, 'foo', [1, 2], {'foo': 'bar'}):
            self.assertEqual(thing, ser.serialize_entity(None, thing))

    def test_deserialize_entity_primitive(self):
        ser = base.WatcherObjectSerializer()
        for thing in (1, 'foo', [1, 2], {'foo': 'bar'}):
            self.assertEqual(thing, ser.deserialize_entity(None, thing))

    def test_object_serialization(self):
        ser = base.WatcherObjectSerializer()
        obj = MyObj(self.context)
        primitive = ser.serialize_entity(self.context, obj)
        self.assertTrue('watcher_object.name' in primitive)
        obj2 = ser.deserialize_entity(self.context, primitive)
        self.assertIsInstance(obj2, MyObj)
        self.assertEqual(self.context, obj2._context)

    def test_object_serialization_iterables(self):
        ser = base.WatcherObjectSerializer()
        obj = MyObj(self.context)
        for iterable in (list, tuple, set):
            thing = iterable([obj])
            primitive = ser.serialize_entity(self.context, thing)
            self.assertEqual(1, len(primitive))
            for item in primitive:
                self.assertFalse(isinstance(item, base.WatcherObject))
            thing2 = ser.deserialize_entity(self.context, primitive)
            self.assertEqual(1, len(thing2))
            for item in thing2:
                self.assertIsInstance(item, MyObj)
