# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import unittest
import mock
import configuration
import yaml
from string import Template
from copy import deepcopy


class BaseTest(unittest.TestCase):
    def setUp(self):
        def info(x):
            print x
        self.config = configuration.versa_config
        self.fake_ctx = mock.MagicMock()
        self.fake_ctx._context['storage']._storage_dir = '/tmp'
        self.fake_ctx.logger.info = info
        patcher_ctx1 = mock.patch('versa_plugin.ctx', self.fake_ctx)
        patcher_ctx2 = mock.patch('versa_plugin.operations.ctx', self.fake_ctx)
        patcher_ctx3 = mock.patch('versa_plugin.versaclient.ctx', self.fake_ctx)
        patcher_ctx1.start()
        patcher_ctx2.start()
        patcher_ctx3.start()
        self.prop = []

    def tearDown(self):
        mock.patch.stopall()

    def update_node_properties(self, template, fields):
        kwargs = {}
        nc = configuration.Node
        for field in fields.split():
            kwargs[field] = getattr(nc, field)
        node_config = Template(template).substitute(kwargs)
        self.fake_ctx.node.properties = {'versa_config': self.config}
        self.fake_ctx.node.properties.update(yaml.load(node_config))
        self.fake_ctx.instance.runtime_properties = {}

    def save_properties(self):
        self.prop.append(deepcopy(self.fake_ctx.node.properties))

    def restore_properties(self):
        self.fake_ctx.node.properties.clear()
        self.fake_ctx.node.properties.update(self.prop.pop())

    def set_runtime(self, fields):
        kwargs = {}
        nc = configuration.Node
        for field in fields.split():
            kwargs[field] = getattr(nc, field)
        self.fake_ctx.instance.runtime_properties.update(kwargs)