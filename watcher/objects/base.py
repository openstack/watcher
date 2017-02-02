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

"""Watcher common internal object model"""

from oslo_utils import versionutils
from oslo_versionedobjects import base as ovo_base
from oslo_versionedobjects import fields as ovo_fields

from watcher import objects

remotable_classmethod = ovo_base.remotable_classmethod
remotable = ovo_base.remotable


def get_attrname(name):
    """Return the mangled name of the attribute's underlying storage."""
    # FIXME(danms): This is just until we use o.vo's class properties
    # and object base.
    return '_obj_' + name


class WatcherObjectRegistry(ovo_base.VersionedObjectRegistry):
    notification_classes = []

    def registration_hook(self, cls, index):
        # NOTE(danms): This is called when an object is registered,
        # and is responsible for maintaining watcher.objects.$OBJECT
        # as the highest-versioned implementation of a given object.
        version = versionutils.convert_version_to_tuple(cls.VERSION)
        if not hasattr(objects, cls.obj_name()):
            setattr(objects, cls.obj_name(), cls)
        else:
            cur_version = versionutils.convert_version_to_tuple(
                getattr(objects, cls.obj_name()).VERSION)
            if version >= cur_version:
                setattr(objects, cls.obj_name(), cls)

    @classmethod
    def register_notification(cls, notification_cls):
        """Register a class as notification.

        Use only to register concrete notification or payload classes,
        do not register base classes intended for inheritance only.
        """
        cls.register_if(False)(notification_cls)
        cls.notification_classes.append(notification_cls)
        return notification_cls

    @classmethod
    def register_notification_objects(cls):
        """Register previously decorated notification as normal ovos.

        This is not intended for production use but only for testing and
        document generation purposes.
        """
        for notification_cls in cls.notification_classes:
            cls.register(notification_cls)


class WatcherObject(ovo_base.VersionedObject):
    """Base class and object factory.

    This forms the base of all objects that can be remoted or instantiated
    via RPC. Simply defining a class that inherits from this base class
    will make it remotely instantiatable. Objects should implement the
    necessary "get" classmethod routines as well as "save" object methods
    as appropriate.
    """

    OBJ_SERIAL_NAMESPACE = 'watcher_object'
    OBJ_PROJECT_NAMESPACE = 'watcher'

    def as_dict(self):
        return {
            k: getattr(self, k) for k in self.fields
            if self.obj_attr_is_set(k)}


class WatcherObjectDictCompat(ovo_base.VersionedObjectDictCompat):
    pass


class WatcherComparableObject(ovo_base.ComparableVersionedObject):
    pass


class WatcherPersistentObject(object):
    """Mixin class for Persistent objects.

    This adds the fields that we use in common for all persistent objects.
    """
    fields = {
        'created_at': ovo_fields.DateTimeField(nullable=True),
        'updated_at': ovo_fields.DateTimeField(nullable=True),
        'deleted_at': ovo_fields.DateTimeField(nullable=True),
    }

    # Mapping between the object field name and a 2-tuple pair composed of
    # its object type (e.g. objects.RelatedObject) and the name of the
    # model field related ID (or UUID) foreign key field.
    # e.g.:
    #
    # fields = {
    #     # [...]
    #     'related_object_id': fields.IntegerField(),  # Foreign key
    #     'related_object': wfields.ObjectField('RelatedObject'),
    # }
    # {'related_object': (objects.RelatedObject, 'related_object_id')}
    object_fields = {}

    def obj_refresh(self, loaded_object):
        """Applies updates for objects that inherit from base.WatcherObject.

        Checks for updated attributes in an object. Updates are applied from
        the loaded object column by column in comparison with the current
        object.
        """
        fields = (field for field in self.fields
                  if field not in self.object_fields)
        for field in fields:
            if (self.obj_attr_is_set(field) and
                    self[field] != loaded_object[field]):
                self[field] = loaded_object[field]

    @staticmethod
    def _from_db_object(obj, db_object, eager=False):
        """Converts a database entity to a formal object.

        :param obj: An object of the class.
        :param db_object: A DB model of the object
        :param eager: Enable the loading of object fields (Default: False)
        :return: The object of the class with the database entity added

        """
        obj_class = type(obj)
        object_fields = obj_class.object_fields

        for field in obj.fields:
            if field not in object_fields:
                obj[field] = db_object[field]

        if eager:
            # Load object fields
            context = obj._context
            loadable_fields = (
                (obj_field, related_obj_cls, rel_id)
                for obj_field, (related_obj_cls, rel_id)
                in object_fields.items()
                if obj[rel_id]
            )
            for obj_field, related_obj_cls, rel_id in loadable_fields:
                if getattr(db_object, obj_field, None) and obj[rel_id]:
                    # The object field data was eagerly loaded alongside
                    # the main object data
                    obj[obj_field] = related_obj_cls._from_db_object(
                        related_obj_cls(context), db_object[obj_field])
                else:
                    # The object field data wasn't loaded yet
                    obj[obj_field] = related_obj_cls.get(context, obj[rel_id])

        obj.obj_reset_changes()
        return obj


class WatcherObjectSerializer(ovo_base.VersionedObjectSerializer):
    # Base class to use for object hydration
    OBJ_BASE_CLASS = WatcherObject
