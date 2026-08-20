# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Topology dataclasses for functional tests.

Typed objects replacing raw dicts for defining compute cluster
topologies in functional tests.  Each dataclass has sensible defaults
matching the emulator defaults, so tests only need to specify the
fields that matter for their scenario.

Objects can be constructed manually or via helper functions for bulk
generation.  The emulators accept dataclass instances directly via
the ``normalize()`` helper which converts them to dicts.
"""

import dataclasses
import uuid

from dataclasses import dataclass
from dataclasses import field


DEFAULT_PROJECT_ID = 'aaaaaaaa-1111-2222-3333-444444444444'


@dataclass
class ComputeNode:
    """A compute node in the emulated cluster."""

    hostname: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    vcpus: int = 16
    memory: int = 32768
    disk: int = 500
    state: str = 'up'
    status: str = 'enabled'
    disabled_reason: str = None
    availability_zone: str = 'nova'
    vcpu_ratio: float = 1.0
    memory_ratio: float = 1.0
    disk_ratio: float = 1.0
    vcpu_reserved: int = 0
    memory_mb_reserved: int = 0
    disk_gb_reserved: int = 0
    cpu: float = 0.0
    ram: float = 0.0


@dataclass
class Instance:
    """An instance (VM) in the emulated cluster."""

    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ''
    host: str = ''
    vcpus: int = 4
    memory: int = 4096
    disk: int = 20
    state: str = 'active'
    project_id: str = 'test-project'
    locked: bool = False
    metadata: dict = field(default_factory=dict)
    hypervisor_hostname: str = None
    ephemeral: int = 0
    swap: int = 0
    created: str = '2025-01-01T00:00:00Z'
    bfv: bool = False
    availability_zone: str = 'nova'
    volumes_attached: list = field(default_factory=list)
    cpu: float = 0.0
    ram: float = 0.0


@dataclass
class Aggregate:
    """A host aggregate grouping compute nodes."""

    id: int
    name: str
    hosts: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ComputeTopology:
    """A complete compute cluster topology for functional tests.

    Supports builder-pattern chaining::

        topo = (
            ComputeTopology()
            .add_computes(count=2)
            .add_instances(computes=['compute-1'], count=2, vcpus=2)
            .add_instances(computes=['compute-2'], count=1, vcpus=2)
        )
    """

    compute_nodes: list = field(default_factory=list)
    instances: list = field(default_factory=list)
    aggregates: list = field(default_factory=list)

    def add_computes(self, count, hostname_prefix='compute', **kwargs):
        """Append *count* compute nodes with generated hostnames/UUIDs.

        Returns ``self`` for chaining.
        """
        start = _next_index(self.compute_nodes, hostname_prefix, 'hostname')
        for i in range(count):
            idx = start + i
            global_idx = len(self.compute_nodes) + 1
            hostname = '%s-%d' % (hostname_prefix, idx)
            self.compute_nodes.append(
                ComputeNode(
                    hostname=hostname, uuid=_node_uuid(global_idx), **kwargs
                )
            )
        return self

    def add_instances(self, computes, count, name_prefix='vm', **kwargs):
        """Append *count* instances per compute node.

        Returns ``self`` for chaining.
        """
        if computes == 'all':
            computes = [n.hostname for n in self.compute_nodes]
        kwargs.setdefault('project_id', DEFAULT_PROJECT_ID)
        start = _next_index(self.instances, name_prefix, 'name')
        vm_index = start
        for hostname in computes:
            for _ in range(count):
                global_idx = len(self.instances) + 1
                self.instances.append(
                    Instance(
                        uuid=_instance_uuid(global_idx),
                        name='%s-%d' % (name_prefix, vm_index),
                        host=hostname,
                        **kwargs,
                    )
                )
                vm_index += 1
        return self

    def update_compute(self, hostname, **kwargs):
        """Update fields on the ComputeNode with the given *hostname*.

        Returns ``self`` for chaining.
        """
        for node in self.compute_nodes:
            if node.hostname == hostname:
                for k, v in kwargs.items():
                    setattr(node, k, v)
                return self
        raise ValueError('No compute node with hostname %r' % hostname)

    def update_instance(self, name, **kwargs):
        """Update fields on the Instance with the given *name*.

        Returns ``self`` for chaining.
        """
        for inst in self.instances:
            if inst.name == name:
                for k, v in kwargs.items():
                    setattr(inst, k, v)
                return self
        raise ValueError('No instance with name %r' % name)


def _asdict_strip_none(obj):
    """Convert a dataclass to a dict, dropping keys with None values.

    Emulators use ``dict.get(key, default)`` to apply defaults for
    optional fields.  ``dataclasses.asdict()`` includes every field —
    even those set to ``None`` — which defeats the ``.get()`` fallback
    (the key is present, so the default is never used).
    """
    return {k: v for k, v in dataclasses.asdict(obj).items() if v is not None}


def normalize(items):
    """Convert a list of dataclasses to a list of dicts.

    Plain dicts are passed through unchanged, so emulators can accept
    either format.  None-valued fields are stripped so that emulator
    ``.get(key, default)`` patterns apply the correct defaults.
    """
    if not items:
        return items
    return [
        _asdict_strip_none(x) if dataclasses.is_dataclass(x) else x
        for x in items
    ]


def _node_uuid(index):
    """Deterministic UUID for compute node at 1-based *index*."""
    return 'aaaa%04d-0000-0000-0000-%012d' % (index, index)


def _instance_uuid(index):
    """Deterministic UUID for instance at 1-based *index*."""
    return 'bbbb%04d-0000-0000-0000-%012d' % (index, index)


def _next_index(items, prefix, name_attr):
    """Return the next 1-based index for *prefix*-N names."""
    max_index = 0
    tag = prefix + '-'
    for item in items:
        name = getattr(item, name_attr)
        if name.startswith(tag):
            try:
                max_index = max(max_index, int(name[len(tag) :]))
            except ValueError:
                pass
    return max_index + 1
