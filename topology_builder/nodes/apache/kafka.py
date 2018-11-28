import json, os 
from nxpservice import *

class kafka(nxpservice):
    def __init__(self, id):
        self.id = id

        with open("%s.json" % __file__.split('.')[0]) as f:
            node = json.load(f)
        self.properties = node["properties"]

    def get_hw_requirement(self):
        return self.properties['require']

    def get_deploy_info(self, block, depends):
        name = '{}-{}'.format(self.__class__.__name__, self.id)
        cmd = self.properties['cmd']
        image = self.properties['image']
        repo = self.properties['repo']
        version = self.properties['version']
        param = ""
        return {'name': name, 'cmd': cmd, 'param': param, 'image': image, \
                'repo': repo, 'version': version}

    @staticmethod
    def create_block(id):
        obj = kafka(id)
        kafka.objects[id] = obj
        return obj

