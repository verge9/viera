import json

class nxpservice(object):
    objects = {}

    def __init__(self):
        pass

    @staticmethod
    def initialize(block, param):
        raise Exception("Subclass hasn't implemented initialize funtion")

    @staticmethod
    def getImageInfo(template):
        #print globals()
        # Assuming using json file with same name
        with open(template) as f:
            node = json.load(f)
        info = {}
        info['image'] = node['properties']['image']
        info['repo'] = node['properties']['repo']
        info['version'] = node['properties']['version']
        return info

