import json, os 
from nxpservice import *

class videoingestion(nxpservice):
    def __init__(self, id):
        self.id = id

        with open("%s.json" % __file__.split('.')[0]) as f:
            node = json.load(f)
        self.properties = node["properties"]

    def get_hw_requirement(self):
        return self.properties['require']

    @staticmethod
    def create_block(id):
        obj = videoingestion(id)
        nxpservice.objects[id] = obj
        return obj

    def get_deploy_info(self, block, depends):
        name = '{}-{}'.format(self.__class__.__name__, self.id)
        cmd = self.properties['cmd']
        image = self.properties['image']
        repo = self.properties['repo']
        version = self.properties['version']
        param = self.__class__.get_service_param(block, depends)
        return {'name': name, 'cmd': cmd, 'param': param, 'image': image, \
                'repo': repo, 'version': version}

    @staticmethod
    def get_service_param(block, depends):
        src_type = block['Source']['Type']
        if src_type == "nxp.camera.ip_camera":
            src_prop = depends['Source']['Properties']
        else:
            print "Unsupported source type."
            return None

        dst_type = block['Target']['Type']
        dst_prop = {}
        if dst_type == "apache.kafka":
            topic_ref = block['Target']['Topic'].split('.')[-1]
            topic_prop = depends['Target']['Properties']['Topics'][topic_ref]
            topic = topic_prop['Name']
            partid = topic_prop['Partition']
            dst_prop['ip'] = depends['Target']['Properties']['device']['local_ip']
            dst_prop['port'] = depends['Target']['Properties']['port']
            dst_prop['topic'] = topic
            dst_prop['partition'] = partid
        else:
            print "Unsupported source type."
            return None

        return {src_type: src_prop, dst_type: dst_prop}
