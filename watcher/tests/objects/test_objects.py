#    Copyright 2013 IBM Corp.
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

import contextlib
import datetime
import gettext
from unittest import mock

from oslo_versionedobjects import base as object_base
from oslo_versionedobjects import exception as object_exception
from oslo_versionedobjects import fixture as object_fixture

from watcher.common import context
from watcher.objects import base
from watcher.objects import fields
from watcher.tests import base as test_base

gettext.install('watcher')


@base.WatcherObjectRegistry.register
class MyObj(base.WatcherPersistentObject, base.WatcherObject,
            base.WatcherObjectDictCompat):
    VERSION = '1.5'

    fields = {'foo': fields.IntegerField(),
              'bar': fields.StringField(),
              'missing': fields.StringField()}

    def obj_load_attr(self, attrname):
        setattr(self, attrname, 'loaded!')

    @object_base.remotable_classmethod
    def query(cls, context):
        obj = cls(context)
        obj.foo = 1
        obj.bar = 'bar'
        obj.obj_reset_changes()
        return obj

    @object_base.remotable
    def marco(self, context=None):
        return 'polo'

    @object_base.remotable
    def update_test(self, context=None):
        if context and context.user == 'alternate':
            self.bar = 'alternate-context'
        else:
            self.bar = 'updated'

    @object_base.remotable
    def save(self, context=None):
        self.obj_reset_changes()

    @object_base.remotable
    def refresh(self, context=None):
        self.foo = 321
        self.bar = 'refreshed'
        self.obj_reset_changes()

    @object_base.remotable
    def modify_save_modify(self, context=None):
        self.bar = 'meow'
        self.save()
        self.foo = 42


class MyObj2(object):
    @classmethod
    def obj_name(cls):
        return 'MyObj'

    @object_base.remotable_classmethod
    def get(cls, *args, **kwargs):
        pass


@base.WatcherObjectRegistry.register_if(False)
class WatcherTestSubclassedObject(MyObj):
    fields = {'new_field': fields.StringField()}


class _LocalTest(test_base.TestCase):
    def setUp(self):
        super(_LocalTest, self).setUp()
        # Just in case
        base.WatcherObject.indirection_api = None


@contextlib.contextmanager
def things_temporarily_local():
    # Temporarily go non-remote so the conductor handles
    # this request directly
    _api = base.WatcherObject.indirection_api
    base.WatcherObject.indirection_api = None
    yield
    base.WatcherObject.indirection_api = _api


class _TestObject(object):
    def test_hydration_type_error(self):
        primitive = {'watcher_object.name': 'MyObj',
                     'watcher_object.namespace': 'watcher',
                     'watcher_object.version': '1.5',
                     'watcher_object.data': {'foo': 'a'}}
        self.assertRaises(ValueError, MyObj.obj_from_primitive, primitive)

    def test_hydration(self):
        primitive = {'watcher_object.name': 'MyObj',
                     'watcher_object.namespace': 'watcher',
                     'watcher_object.version': '1.5',
                     'watcher_object.data': {'foo': 1}}
        obj = MyObj.obj_from_primitive(primitive)
        self.assertEqual(1, obj.foo)

    def test_hydration_bad_ns(self):
        primitive = {'watcher_object.name': 'MyObj',
                     'watcher_object.namespace': 'foo',
                     'watcher_object.version': '1.5',
                     'watcher_object.data': {'foo': 1}}
        self.assertRaises(object_exception.UnsupportedObjectError,
                          MyObj.obj_from_primitive, primitive)

    def test_dehydration(self):
        expected = {'watcher_object.name': 'MyObj',
                    'watcher_object.namespace': 'watcher',
                    'watcher_object.version': '1.5',
                    'watcher_object.data': {'foo': 1}}
        obj = MyObj(self.context)
        obj.foo = 1
        obj.obj_reset_changes()
        self.assertEqual(expected, obj.obj_to_primitive())

    def test_get_updates(self):
        obj = MyObj(self.context)
        self.assertEqual({}, obj.obj_get_changes())
        obj.foo = 123
        self.assertEqual({'foo': 123}, obj.obj_get_changes())
        obj.bar = 'test'
        self.assertEqual({'foo': 123, 'bar': 'test'}, obj.obj_get_changes())
        obj.obj_reset_changes()
        self.assertEqual({}, obj.obj_get_changes())

    def test_object_property(self):
        obj = MyObj(self.context, foo=1)
        self.assertEqual(1, obj.foo)

    def test_object_property_type_error(self):
        obj = MyObj(self.context)

        def fail():
            obj.foo = 'a'
        self.assertRaises(ValueError, fail)

    def test_load(self):
        obj = MyObj(self.context)
        self.assertEqual('loaded!', obj.bar)

    def test_load_in_base(self):
        @base.WatcherObjectRegistry.register_if(False)
        class Foo(base.WatcherPersistentObject, base.WatcherObject,
                  base.WatcherObjectDictCompat):
            fields = {'foobar': fields.IntegerField()}
        obj = Foo(self.context)

        self.assertRaisesRegex(
            NotImplementedError, "Cannot load 'foobar' in the base class",
            getattr, obj, 'foobar')

    def test_loaded_in_primitive(self):
        obj = MyObj(self.context)
        obj.foo = 1
        obj.obj_reset_changes()
        self.assertEqual('loaded!', obj.bar)
        expected = {'watcher_object.name': 'MyObj',
                    'watcher_object.namespace': 'watcher',
                    'watcher_object.version': '1.5',
                    'watcher_object.changes': ['bar'],
                    'watcher_object.data': {'foo': 1,
                                            'bar': 'loaded!'}}
        self.assertEqual(expected, obj.obj_to_primitive())

    def test_changes_in_primitive(self):
        obj = MyObj(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        primitive = obj.obj_to_primitive()
        self.assertIn('watcher_object.changes', primitive)
        obj2 = MyObj.obj_from_primitive(primitive)
        self.assertEqual(set(['foo']), obj2.obj_what_changed())
        obj2.obj_reset_changes()
        self.assertEqual(set(), obj2.obj_what_changed())

    def test_unknown_objtype(self):
        self.assertRaises(object_exception.UnsupportedObjectError,
                          base.WatcherObject.obj_class_from_name, 'foo', '1.0')

    def test_with_alternate_context(self):
        ctxt1 = context.RequestContext('foo', 'foo')
        ctxt2 = context.RequestContext(user='alternate')
        obj = MyObj.query(ctxt1)
        obj.update_test(ctxt2)
        self.assertEqual('alternate-context', obj.bar)

    def test_orphaned_object(self):
        obj = MyObj.query(self.context)
        obj._context = None
        self.assertRaises(object_exception.OrphanedObjectError,
                          obj.update_test)

    def test_changed_1(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.update_test(self.context)
        self.assertEqual(set(['foo', 'bar']), obj.obj_what_changed())
        self.assertEqual(123, obj.foo)

    def test_changed_2(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.save()
        self.assertEqual(set([]), obj.obj_what_changed())
        self.assertEqual(123, obj.foo)

    def test_changed_3(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.refresh()
        self.assertEqual(set([]), obj.obj_what_changed())
        self.assertEqual(321, obj.foo)
        self.assertEqual('refreshed', obj.bar)

    def test_changed_4(self):
        obj = MyObj.query(self.context)
        obj.bar = 'something'
        self.assertEqual(set(['bar']), obj.obj_what_changed())
        obj.modify_save_modify(self.context)
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        self.assertEqual(42, obj.foo)
        self.assertEqual('meow', obj.bar)

    def test_static_result(self):
        obj = MyObj.query(self.context)
        self.assertEqual('bar', obj.bar)
        result = obj.marco()
        self.assertEqual('polo', result)

    def test_updates(self):
        obj = MyObj.query(self.context)
        self.assertEqual(1, obj.foo)
        obj.update_test()
        self.assertEqual('updated', obj.bar)

    def test_base_attributes(self):
        dt = datetime.datetime(1955, 11, 5, 0, 0, tzinfo=datetime.timezone.utc)
        datatime = fields.DateTimeField()
        obj = MyObj(self.context)
        obj.created_at = dt
        obj.updated_at = dt
        expected = {'watcher_object.name': 'MyObj',
                    'watcher_object.namespace': 'watcher',
                    'watcher_object.version': '1.5',
                    'watcher_object.changes':
                        ['created_at', 'updated_at'],
                    'watcher_object.data':
                        {'created_at': datatime.stringify(dt),
                         'updated_at': datatime.stringify(dt),
                         }
                    }
        actual = obj.obj_to_primitive()
        # watcher_object.changes is built from a set and order is undefined
        self.assertEqual(sorted(expected['watcher_object.changes']),
                         sorted(actual['watcher_object.changes']))
        del expected[
            'watcher_object.changes'], actual['watcher_object.changes']
        self.assertEqual(expected, actual)

    def test_contains(self):
        obj = MyObj(self.context)
        self.assertNotIn('foo', obj)
        obj.foo = 1
        self.assertIn('foo', obj)
        self.assertNotIn('does_not_exist', obj)

    def test_obj_attr_is_set(self):
        obj = MyObj(self.context, foo=1)
        self.assertTrue(obj.obj_attr_is_set('foo'))
        self.assertFalse(obj.obj_attr_is_set('bar'))
        self.assertRaises(AttributeError, obj.obj_attr_is_set, 'bang')

    def test_get(self):
        obj = MyObj(self.context, foo=1)
        # Foo has value, should not get the default
        self.assertEqual(obj.get('foo', 2), 1)
        # Foo has value, should return the value without error
        self.assertEqual(obj.get('foo'), 1)
        # Bar is not loaded, so we should get the default
        self.assertEqual(obj.get('bar', 'not-loaded'), 'not-loaded')
        # Bar without a default should lazy-load
        self.assertEqual(obj.get('bar'), 'loaded!')
        # Bar now has a default, but loaded value should be returned
        self.assertEqual(obj.get('bar', 'not-loaded'), 'loaded!')
        # Invalid attribute should raise AttributeError
        self.assertRaises(AttributeError, obj.get, 'nothing')
        # ...even with a default
        self.assertRaises(AttributeError, obj.get, 'nothing', 3)

    def test_object_inheritance(self):
        base_fields = (
            list(base.WatcherObject.fields) +
            list(base.WatcherPersistentObject.fields))
        myobj_fields = ['foo', 'bar', 'missing'] + base_fields
        myobj3_fields = ['new_field']
        self.assertTrue(issubclass(WatcherTestSubclassedObject, MyObj))
        self.assertEqual(len(myobj_fields), len(MyObj.fields))
        self.assertEqual(set(myobj_fields), set(MyObj.fields.keys()))
        self.assertEqual(len(myobj_fields) + len(myobj3_fields),
                         len(WatcherTestSubclassedObject.fields))
        self.assertEqual(set(myobj_fields) | set(myobj3_fields),
                         set(WatcherTestSubclassedObject.fields.keys()))

    def test_get_changes(self):
        obj = MyObj(self.context)
        self.assertEqual({}, obj.obj_get_changes())
        obj.foo = 123
        self.assertEqual({'foo': 123}, obj.obj_get_changes())
        obj.bar = 'test'
        self.assertEqual({'foo': 123, 'bar': 'test'}, obj.obj_get_changes())
        obj.obj_reset_changes()
        self.assertEqual({}, obj.obj_get_changes())

    def test_obj_fields(self):
        @base.WatcherObjectRegistry.register_if(False)
        class TestObj(base.WatcherPersistentObject, base.WatcherObject,
                      base.WatcherObjectDictCompat):
            fields = {'foo': fields.IntegerField()}
            obj_extra_fields = ['bar']

            @property
            def bar(self):
                return 'this is bar'

        obj = TestObj(self.context)
        self.assertEqual(set(['created_at', 'updated_at', 'deleted_at',
                              'foo', 'bar']),
                         set(obj.obj_fields))

    def test_refresh_object(self):
        @base.WatcherObjectRegistry.register_if(False)
        class TestObj(base.WatcherPersistentObject, base.WatcherObject,
                      base.WatcherObjectDictCompat):
            fields = {'foo': fields.IntegerField(),
                      'bar': fields.StringField()}

        obj = TestObj(self.context)
        current_obj = TestObj(self.context)
        obj.foo = 10
        obj.bar = 'obj.bar'
        current_obj.foo = 2
        current_obj.bar = 'current.bar'
        obj.obj_refresh(current_obj)
        self.assertEqual(obj.foo, 2)
        self.assertEqual(obj.bar, 'current.bar')

    def test_obj_constructor(self):
        obj = MyObj(self.context, foo=123, bar='abc')
        self.assertEqual(123, obj.foo)
        self.assertEqual('abc', obj.bar)
        self.assertEqual(set(['foo', 'bar']), obj.obj_what_changed())

    def test_assign_value_without_DictCompat(self):
        class TestObj(base.WatcherObject):
            fields = {'foo': fields.IntegerField(),
                      'bar': fields.StringField()}
        obj = TestObj(self.context)
        obj.foo = 10
        err_message = ''
        try:
            obj['bar'] = 'value'
        except TypeError as e:
            err_message = str(e)
        finally:
            self.assertIn("'TestObj' object does not support item assignment",
                          err_message)


class TestObject(_LocalTest, _TestObject):
    pass


# The hashes are help developers to check if the change of objects need a
# version bump. It is md5 hash of object fields and remotable methods.
# The fingerprint values should only be changed if there is a version bump.
expected_object_fingerprints = {
    'Goal': '1.0-93881622db05e7b67a65ca885b4a022e',
    'Strategy': '1.1-73f164491bdd4c034f48083a51bdeb7b',
    'AuditTemplate': '1.1-b291973ffc5efa2c61b24fe34fdccc0b',
    'Audit': '1.7-19bc991c0b048263df021a36c8624f4d',
    'ActionPlan': '2.2-3331270cb3666c93408934826d03c08d',
    'Action': '2.0-1dd4959a7e7ac30c62ef170fe08dd935',
    'EfficacyIndicator': '1.0-655b71234a82bc7478aff964639c4bb0',
    'ScoringEngine': '1.0-4abbe833544000728e17bd9e83f97576',
    'Service': '1.0-4b35b99ada9677a882c9de2b30212f35',
    'MyObj': '1.5-23c516d1e842f365f694e688d34e47c3',
    'ActionDescription': '1.0-5761a3d16651046e7a0c357b57a6583e'
}


def get_watcher_objects():
    """Get Watcher versioned objects

    This returns a dict of versioned objects which are
    in the Watcher project namespace only. ie excludes
    objects from os-vif and other 3rd party modules
    :return: a dict mapping class names to lists of versioned objects
    """
    all_classes = base.WatcherObjectRegistry.obj_classes()
    watcher_classes = {}
    for name in all_classes:
        objclasses = all_classes[name]
        if (objclasses[0].OBJ_PROJECT_NAMESPACE !=
                base.WatcherObject.OBJ_PROJECT_NAMESPACE):
            continue
        watcher_classes[name] = objclasses
    return watcher_classes


class TestObjectVersions(test_base.TestCase):

    def test_object_version_check(self):
        classes = base.WatcherObjectRegistry.obj_classes()
        checker = object_fixture.ObjectVersionChecker(obj_classes=classes)
        # Compute the difference between actual fingerprints and
        # expect fingerprints. expect = actual = {} if there is no change.
        expect, actual = checker.test_hashes(expected_object_fingerprints)
        self.assertEqual(expect, actual,
                         "Some objects fields or remotable methods have been "
                         "modified. Please make sure the version of those "
                         "objects have been bumped and then update "
                         "expected_object_fingerprints with the new hashes. ")


class TestObjectSerializer(test_base.TestCase):

    def test_object_serialization(self):
        obj_ser = base.WatcherObjectSerializer()
        obj = MyObj(self.context)
        primitive = obj_ser.serialize_entity(self.context, obj)
        self.assertIn('watcher_object.name', primitive)
        obj2 = obj_ser.deserialize_entity(self.context, primitive)
        self.assertIsInstance(obj2, MyObj)
        self.assertEqual(self.context, obj2._context)

    def test_object_serialization_iterables(self):
        obj_ser = base.WatcherObjectSerializer()
        obj = MyObj(self.context)
        for iterable in (list, tuple, set):
            thing = iterable([obj])
            primitive = obj_ser.serialize_entity(self.context, thing)
            self.assertEqual(1, len(primitive))
            for item in primitive:
                self.assertFalse(isinstance(item, base.WatcherObject))
            thing2 = obj_ser.deserialize_entity(self.context, primitive)
            self.assertEqual(1, len(thing2))
            for item in thing2:
                self.assertIsInstance(item, MyObj)

    @mock.patch('watcher.objects.base.WatcherObject.indirection_api')
    def _test_deserialize_entity_newer(self, obj_version, backported_to,
                                       mock_indirection_api,
                                       my_version='1.6'):
        obj_ser = base.WatcherObjectSerializer()
        mock_indirection_api.object_backport_versions.return_value \
            = 'backported'

        @base.WatcherObjectRegistry.register
        class MyTestObj(MyObj):
            VERSION = my_version

        obj = MyTestObj(self.context)
        obj.VERSION = obj_version
        primitive = obj.obj_to_primitive()
        result = obj_ser.deserialize_entity(self.context, primitive)
        if backported_to is None:
            self.assertFalse(
                mock_indirection_api.object_backport_versions.called)
        else:
            self.assertEqual('backported', result)
            versions = object_base.obj_tree_get_versions('MyTestObj')
            mock_indirection_api.object_backport_versions.assert_called_with(
                self.context, primitive, versions)

    def test_deserialize_entity_newer_version_backports(self):
        "Test object with unsupported (newer) version"
        self._test_deserialize_entity_newer('1.25', '1.6')

    def test_deserialize_entity_same_revision_does_not_backport(self):
        "Test object with supported revision"
        self._test_deserialize_entity_newer('1.6', None)

    def test_deserialize_entity_newer_revision_does_not_backport_zero(self):
        "Test object with supported revision"
        self._test_deserialize_entity_newer('1.6.0', None)

    def test_deserialize_entity_newer_revision_does_not_backport(self):
        "Test object with supported (newer) revision"
        self._test_deserialize_entity_newer('1.6.1', None)

    def test_deserialize_entity_newer_version_passes_revision(self):
        "Test object with unsupported (newer) version and revision"
        self._test_deserialize_entity_newer('1.7', '1.6.1', my_version='1.6.1')


class TestRegistry(test_base.TestCase):

    @mock.patch('watcher.objects.base.objects')
    def test_hook_chooses_newer_properly(self, mock_objects):
        mock_objects.MyObj.VERSION = MyObj.VERSION
        reg = base.WatcherObjectRegistry()
        reg.registration_hook(MyObj, 0)

        class MyNewerObj(object):
            VERSION = '1.123'

            @classmethod
            def obj_name(cls):
                return 'MyObj'

        self.assertEqual(MyObj, mock_objects.MyObj)
        reg.registration_hook(MyNewerObj, 0)
        self.assertEqual(MyNewerObj, mock_objects.MyObj)

    @mock.patch('watcher.objects.base.objects')
    def test_hook_keeps_newer_properly(self, mock_objects):
        mock_objects.MyObj.VERSION = MyObj.VERSION
        reg = base.WatcherObjectRegistry()
        reg.registration_hook(MyObj, 0)

        class MyOlderObj(object):
            VERSION = '1.1'

            @classmethod
            def obj_name(cls):
                return 'MyObj'

        self.assertEqual(MyObj, mock_objects.MyObj)
        reg.registration_hook(MyOlderObj, 0)
        self.assertEqual(MyObj, mock_objects.MyObj)
