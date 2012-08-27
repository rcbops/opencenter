# vim: tabstop=4 shiftwidth=4 softtabstop=4
import json
import os
import random
import roush
import string
import unittest
import tempfile
from test_roush import RoushTestCase
from setup import RoushTest
import webapp


def _randomStr(size):
    return "".join(random.choice(string.ascii_lowercase) for x in range(size))


class ClusterTestCase(RoushTest):

    @classmethod
    def setup(cls):
         # Create a cluster
        cls.cluster_name = _randomStr(10)
        cls.cluster_desc = _randomStr(30)
        cluster_data = {"name": cls.cluster_name, 
                            "description": cls.cluster_desc}
        tmp = cls.app.post('/clusters/', data=json.dumps(cluster_data), 
                            content_type='application/json')
        assert tmp.status_code == 201,\
            "Unable to create cluster %s" % cluster_name
        cls.cluster_json = json.loads(tmp.data)
        cls.cluster_id = cls.cluster_json['cluster']['id']

    @classmethod
    def cleanup(cls):
        # Delete our test cluster
        tmp = cls.app.delete('/clusters/%s' % cls.cluster_id)
        assert tmp.status_code == 200, "Status code %s is not 200" % (
            tmp.status_code)
        data = json.loads(tmp.data)
        assert data['status'] == tmp.status_code,\
            "Status %s returned in data does not match response code %s" % (
                data['status'], tmp.status_code)
        assert data['message'] == 'Cluster deleted',\
            "Message %s is not Cluster deleted" % (data['message'])

    def test_create_cluster(self):
        #cluster is created in setup.  We should verify it is created
        #as expected.
        response = self.app.get("/clusters/%s" % (self.cluster_id))
        cluster = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.cluster_id, cluster['id'])
        self.assertEqual(self.cluster_name, cluster['name'])
        self.assertEqual(self.cluster_desc, cluster['description'])
        
    def test_update_cluster(self):
        # update cluster attributes
        new_desc = "updated description"
        new_cluster = {"description": new_desc}
        resp = self.app.put('/clusters/%s' % self.cluster_id, 
                            data=json.dumps(new_cluster), 
                            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        tmp_data = json.loads(resp.data)
        self.assertEqual(tmp_data['description'], new_desc)


        
                             
if __name__ == '__main__':
    unittest.main()
