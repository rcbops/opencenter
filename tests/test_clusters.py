# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import os
import random
import roush
import string
import unittest
import tempfile
from test_roush import RoushTestCase
import webapp


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class ClusterCRUDTestCase(RoushTestCase):

    def test_cluster_crud(self):
        tmp_name = _randomStr(10)
        tmp_description = "lorem ipsum"

        # create a new cluster
        cluster = {"name": tmp_name, "description": tmp_description}
        resp = self.app.post('/clusters/', data=json.dumps(cluster), content_type='application/json')
        # pprint(resp)
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)

        # make sure the cluster was created
        resp = self.app.get('/clusters/%s' % data['cluster']['id'])
        tmp = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(tmp['id'], data['cluster']['id'])
        self.assertEqual(tmp['name'], tmp_name)
        self.assertEqual(tmp['description'], tmp_description)

        # update cluster attributes
        new_desc = "updated description"
        new_cluster = {"description": new_desc}
        resp = self.app.put('/clusters/%s' % data['cluster']['id'], data=json.dumps(new_cluster), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        tmp_data = json.loads(resp.data)
        self.assertEqual(tmp_data['description'], new_desc)

        # clean up the cluster
        resp = self.app.delete('/clusters/%s' % data['cluster']['id'])
        self.assertEqual(resp.status_code, 200)
        tmp = json.loads(resp.data)
        self.assertEqual(tmp['status'], 200)
        self.assertEqual(tmp['message'], 'Cluster deleted')


# class ClusterTestCase(unittest.TestCase):

#     @classmethod
#     def setUpClass(self):
#         # This has to be set to expose tracebacks
#         foo = webapp.Thing(configfile='local.conf', debug = True)
#         self.app = foo.test_client()
#         # roush.app.testing = True
#         # self.app = roush.app.test_client()
#         # Create a cluster
#         self.cluster_name = _randomStr(10)
#         self.cluster_desc = _randomStr(30)
#         self.cluster_data = {"name": self.cluster_name, "description": self.cluster_desc}
#         tmp = self.app.post('/clusters/', data=json.dumps(self.cluster_data), content_type='application/json')
#         self.cluster_json = json.loads(tmp.data)
#         self.cluster_id = self.cluster_json['cluster']['id']

#     @classmethod
#     def tearDownClass(self):
#         tmp = self.app.delete('/cluster/%s' % self.cluster_id)

#     def test_blah(self):
#         pass

if __name__ == '__main__':
    unittest.main()
