# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica LTD
#
# Authors: Alexander Chadin <a.chadin@servionica.ru>
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

from oslo_serialization import jsonutils

from apscheduler.jobstores.base import ConflictingIdError
from apscheduler.jobstores import sqlalchemy
from apscheduler.util import datetime_to_utc_timestamp
from apscheduler.util import maybe_ref
from apscheduler.util import utc_timestamp_to_datetime

from watcher.common import context
from watcher.common import service
from watcher import objects

try:
    import cPickle as pickle
except ImportError:  # pragma: nocover
    import pickle

from sqlalchemy import Table, MetaData, select, and_, null
from sqlalchemy.exc import IntegrityError


class WatcherJobStore(sqlalchemy.SQLAlchemyJobStore):
    """Stores jobs in a database table using SQLAlchemy.

    The table will be created if it doesn't exist in the database.
    Plugin alias: ``sqlalchemy``
    :param str url: connection string
    :param engine: an SQLAlchemy Engine to use instead of creating a new
    one based on ``url``
    :param str tablename: name of the table to store jobs in
    :param metadata: a :class:`~sqlalchemy.MetaData` instance to use instead of
    creating a new one
    :param int pickle_protocol: pickle protocol level to use
    (for serialization), defaults to the highest available
    :param dict tag: tag description
    """

    def __init__(self, url=None, engine=None, tablename='apscheduler_jobs',
                 metadata=None, pickle_protocol=pickle.HIGHEST_PROTOCOL,
                 tag=None):
        super(WatcherJobStore, self).__init__(url, engine, tablename,
                                              metadata, pickle_protocol)
        metadata = maybe_ref(metadata) or MetaData()
        self.jobs_t = Table(tablename, metadata, autoload_with=engine)
        service_ident = service.ServiceHeartbeat.get_service_name()
        self.tag = tag or {'host': service_ident[0], 'name': service_ident[1]}
        self.service_id = objects.Service.list(context=context.make_context(),
                                               filters=self.tag)[0].id

    def start(self, scheduler, alias):
        # There should be called 'start' method of parent of SQLAlchemyJobStore
        super(self.__class__.__bases__[0], self).start(scheduler, alias)

    def add_job(self, job):
        insert = self.jobs_t.insert().values(**{
            'id': job.id,
            'next_run_time': datetime_to_utc_timestamp(job.next_run_time),
            'job_state': pickle.dumps(job.__getstate__(),
                                      self.pickle_protocol),
            'service_id': self.service_id,
            'tag': jsonutils.dumps(self.tag)
        })
        try:
            with self.engine.begin() as conn:
                conn.execute(insert)
        except IntegrityError:
            raise ConflictingIdError(job.id)

    def get_all_jobs(self):
        jobs = self._get_jobs(self.jobs_t.c.tag == jsonutils.dumps(self.tag))
        self._fix_paused_jobs_sorting(jobs)
        return jobs

    def get_next_run_time(self):
        selectable = select(self.jobs_t.c.next_run_time).\
            where(self.jobs_t.c.next_run_time != null()).\
            order_by(self.jobs_t.c.next_run_time).limit(1)
        with self.engine.begin() as connection:
            # NOTE(danms): The apscheduler implementation of this gets a
            # decimal.Decimal back from scalar() which causes
            # utc_timestamp_to_datetime() to choke since it is expecting a
            # python float. Assume this is SQLAlchemy 2.0 stuff, so just
            # coerce to a float here.
            next_run_time = connection.execute(selectable).scalar()
            return utc_timestamp_to_datetime(float(next_run_time)
                                             if next_run_time is not None
                                             else None)

    def _get_jobs(self, *conditions):
        jobs = []
        conditions += (self.jobs_t.c.service_id == self.service_id,)
        selectable = select(
            self.jobs_t.c.id, self.jobs_t.c.job_state, self.jobs_t.c.tag
        ).order_by(self.jobs_t.c.next_run_time).where(and_(*conditions))
        failed_job_ids = set()
        with self.engine.begin() as conn:
            for row in conn.execute(selectable):
                try:
                    jobs.append(self._reconstitute_job(row.job_state))
                except Exception:
                    self._logger.exception(
                        'Unable to restore job "%s" -- removing it', row.id)
                    failed_job_ids.add(row.id)

        # Remove all the jobs we failed to restore
        if failed_job_ids:
            delete = self.jobs_t.delete().where(
                self.jobs_t.c.id.in_(failed_job_ids))
            self.engine.execute(delete)

        return jobs
