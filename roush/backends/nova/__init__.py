#!/usr/bin/env python

import roush


class NovaBackend(roush.backends.Backend):
    def __init__(self):
        super(NovaBackend, self).__init__(__file__)

    def additional_constraints(self, api, node_id, action, ns):
        if action == 'add_backend':
            return ['"chef-client" in facts.backends']

        return []

    def add_backend(self, api, node_id, **kwargs):
        self.logger.debug('adding nova backend')

        roush.webapp.ast.apply_expression(
            node_id, 'facts.backends := union(facts.backends, "nova")', api)

        return True

    def _make_subcontainer(self, api, name, parent_id, facts, backends):
        subcontainer = api._model_create('nodes', {'name': name})
        if subcontainer is None:
            return None

        facts.update({'parent_id': parent_id,
                      'backends': backends})

        for k, v in facts.items():
            api._model_create('facts', {'key': k,
                                        'value': v,
                                        'node_id': subcontainer['id']})

        return subcontainer

    def create_cluster(self, api, node_id, **kwargs):
        if not 'cluster_name' in kwargs:
            return False

        cluster_facts = ["nova_public_if",
                         "keystone_admin_pw",
                         "nova_dmz_cidr",
                         "nova_vm_fixed_range",
                         "nova_vm_fixed_if",
                         "nova_vm_bridge",
                         "osops_mgmt",
                         "osops_nova",
                         "osops_public"]

        environment_hash = {}
        for k, v in kwargs.items():
            if k in cluster_facts:
                environment_hash[k] = v

        # have the attribute map, let's make it an apply the
        # facts.
        cluster = self._make_subcontainer(
            api, kwargs['cluster_name'], node_id, environment_hash,
            ['node', 'container', 'nova'])

        if cluster is None:
            return False

        infra = self._make_subcontainer(
            api, 'Infrasructure', cluster['id'],
            {}, ['node', 'container', 'nova'])

        if infra is None:
            return False

        comp = self._make_subcontainer(
            api, 'Compute', cluster['id'],
            {}, ['node', 'container', 'nova'])

        if comp is None:
            return False

        az = 'nova'
        if 'nova_az' in kwargs:
            az = kwargs['nova_az']

        self._make_subcontainer(
            api, 'AZ %s' % az, comp['id'], {'nova_az': az},
            ['node', 'container', 'nova'])

        return True
