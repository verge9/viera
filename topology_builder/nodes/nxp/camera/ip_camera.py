import json

class ip_camera(object):
    objects = {}

    def __init__(self, id):
        self.id = id

        with open("%s.json" % __file__.split('.')[0]) as f:
            node = json.load(f)
        self.properties = node["properties"]
        if 'accesspoint' not in self.properties or \
           self.properties['accesspoint'] == "":
            print "Missing access point in device."
        if not hasattr(self, self.properties['accesspoint']):
            print "Can't find accesspoint %s." % self.properties['accesspoint']
        self.accessPoint = self.properties['accesspoint']

    '''
    def set_properties(self, properties):
        require = self.properties['require']
        for item in require:
            if item not in properties:
                raise Exception("Missing property %s in device." % item) 
            require[item] = properties[item]
        return
    '''

    def getURL(self, properties):
        require = self.properties['require']
        for item in require:
            if item not in properties:
                raise Exception("Missing property %s in device." % item) 
        '''
            require[item] = properties[item]
        url = require['protocol'] + '://' + require['user'] + ':' + require['pw'] + \
              '@' + "10.192.208.10" + require['appendix']
              #block['password'] + '@' + block['ip'] + block['appendix']
        '''
        url = properties['protocol'] + '://' + properties['user'] + ':' + \
              properties['pw'] + '@' + properties['ip'] + properties['appendix']
        return ['url', url]

    @staticmethod
    def create_device(id):
        obj = ip_camera(id)
        ip_camera.objects[id] = obj
        return obj

