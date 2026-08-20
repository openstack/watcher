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

"""Base class for in-process API emulators.

Provides shared infrastructure for API emulators used in functional
tests: Pecan app creation, topology loading from XML/JSON files,
state reset, and standalone server helpers.

Subclasses must implement:

  - ``_init_stores()`` — create the empty dicts that hold emulator state
  - ``_make_root_controller()`` — return a Pecan root controller
  - ``load_topology(topology)`` — populate stores from a topology object

The default ``load_from_xml()`` and ``load_from_json()`` build a
``ComputeTopology``.  Emulators with a different topology model
(e.g. Cinder / StorageTopology) should override these methods.
"""

import argparse
import dataclasses

from xml.etree import ElementTree

import fixtures
import pecan

from oslo_serialization import jsonutils
from werkzeug import serving

from watcher.tests.functional import topology as topo_mod


def _parse_xml_element(element, cls, **extra):
    """Build a dataclass instance from XML element attributes.

    Field names and types are discovered dynamically from *cls*.
    Only simple scalar types (int, float, str, bool) are extracted;
    complex types (dict, list) cannot be represented as XML
    attributes and are left to the dataclass defaults.
    """
    kwargs = dict(extra)
    for f in dataclasses.fields(cls):
        if f.name in kwargs:
            continue
        if f.name not in element.attrib:
            continue
        raw = element.attrib[f.name]
        if f.type is bool:
            kwargs[f.name] = raw == 'True'
        elif f.type is int:
            kwargs[f.name] = int(raw)
        elif f.type is float:
            kwargs[f.name] = float(raw)
        elif f.type is str:
            kwargs[f.name] = raw
    return cls(**kwargs)


def _from_dict(cls, d):
    """Construct a dataclass from a dict, ignoring unknown keys."""
    known = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in d.items() if k in known})


class BaseAPIEmulator(fixtures.Fixture):
    """Base class for in-process API emulators."""

    def __init__(self):
        super().__init__()
        self._init_stores()
        root = self._make_root_controller()
        self.app = pecan.make_app(root, guess_content_type_from_ext=False)

    def _init_stores(self):
        raise NotImplementedError

    def _make_root_controller(self):
        raise NotImplementedError

    def reset(self):
        """Clear all public dict attributes (data stores)."""
        for attr in list(vars(self)):
            val = getattr(self, attr)
            if isinstance(val, dict) and not attr.startswith('_'):
                val.clear()

    def load_topology(self, topology=None):
        raise NotImplementedError

    # Model loading (auto-detect format)

    def load_model(self, model_path):
        """Load topology from a file, auto-detecting XML or JSON format.

        Tries JSON first, then XML.  Raises ValueError if neither
        parser succeeds.
        """
        try:
            self.load_from_json(model_path)
            return
        except (ValueError, UnicodeDecodeError):
            pass
        try:
            self.load_from_xml(model_path)
            return
        except ElementTree.ParseError:
            pass
        raise ValueError('Unable to parse %s as JSON or XML' % model_path)

    # XML loading (default implementation for compute topology)

    def load_from_xml(self, xml_path):
        """Load topology from a watcher scenario XML model file.

        Field names are discovered dynamically from the ``ComputeNode``
        and ``Instance`` dataclasses.  Only ``hostname`` (for nodes) and
        ``name``/``host`` (for instances) are mandatory; everything else
        uses the dataclass defaults when absent from the XML.
        """
        tree = ElementTree.parse(xml_path)
        root = tree.getroot()

        compute_nodes = []
        instances = []

        for node in root.iter('ComputeNode'):
            compute_nodes.append(
                _parse_xml_element(node, topo_mod.ComputeNode)
            )
            hostname = node.attrib['hostname']
            for inst in node.findall('Instance'):
                instances.append(
                    _parse_xml_element(inst, topo_mod.Instance, host=hostname)
                )

        self.load_topology(
            topo_mod.ComputeTopology(
                compute_nodes=compute_nodes, instances=instances
            )
        )

    # JSON loading (default implementation for compute topology)

    def load_from_json(self, json_path):
        """Load topology from a JSON file.

        Only fields defined on ``ComputeNode``, ``Instance``, and
        ``Aggregate`` are used; unknown keys are silently ignored.
        Missing fields use the dataclass defaults.
        """
        with open(json_path, 'rb') as f:
            data = jsonutils.load(f)
        self.load_topology(
            topo_mod.ComputeTopology(
                compute_nodes=[
                    _from_dict(topo_mod.ComputeNode, d)
                    for d in data.get('compute_nodes', [])
                ],
                instances=[
                    _from_dict(topo_mod.Instance, d)
                    for d in data.get('instances', [])
                ],
                aggregates=[
                    _from_dict(topo_mod.Aggregate, d)
                    for d in data.get('aggregates', [])
                ],
            )
        )


def create_app(emulator_class, model_path=None, topology=None):
    """Factory: create an emulator, optionally loading topology."""
    emulator = emulator_class()
    if model_path:
        emulator.load_model(model_path)
    elif topology:
        emulator.load_topology(topology)
    return emulator


def run_standalone(emulator_class, description, default_port):
    """Run an emulator as a standalone dev server."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '--model',
        default=None,
        help='Path to model file (XML or JSON, auto-detected by extension)',
    )
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=default_port)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument(
        '--cert', default=None, help='Path to TLS certificate (.crt)'
    )
    parser.add_argument(
        '--key', default=None, help='Path to TLS private key (.key)'
    )
    args = parser.parse_args()

    ssl_ctx = None
    if args.cert and args.key:
        ssl_ctx = (args.cert, args.key)
    elif args.cert or args.key:
        parser.error('--cert and --key must both be provided for HTTPS')

    emulator = create_app(emulator_class, model_path=args.model)
    serving.run_simple(
        args.host,
        args.port,
        emulator.app,
        use_debugger=args.debug,
        use_reloader=args.debug,
        ssl_context=ssl_ctx,
    )
