import json, yaml, jinja2
import requests
import os, re

class TopologyBlock(object):
    def __init__(self, block_id, block_class):
        self.id = block_id
        self.block_class = block_class
        #self.attribute = None
        self.template = None
        self.previous = None
        self.next = None
        self.device = None
        self.hardware = None
        self.__initialize()

    def __load_block_property(self):
        with open(self.template_path) as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if '{{' in line and '}}' in line:
                continue
            new_lines.append(line)
        return yaml.load('\n'.join(new_lines))
            
    def __initialize(self):
        #self.type = info['type']
        self.template_path = 'nodes/' + self.block_class.replace('.', '/') + '.yaml'
        # used for composer
        self.properties = self.__load_block_property()
        block_name = self.properties.keys()[0]
        self.properties = self.properties.values()[0]
        self.properties['name'] = block_name
        self.properties['id'] = self.id
        if self.id == 'video_ingestion_1':
            self.properties['Input']['name'] = 'VideoSource'
            self.properties['Output']['name'] = 'Videostream'
        if self.id == 'face_recognition_1':
            self.properties['Input']['name'] = 'Videostream'
            self.properties['Output']['name'] = 'Videostream'
        #print self.properties
        if 'Compatability' in self.properties:
            self.hardware = self.properties['Compatability']
        self.role = self.properties['role']

    def assignDevice(self, device):
        self.device = device

    def render_template(self):
        #print self.template_path
        path = os.path.dirname(self.template_path)
        fn = os.path.basename(self.template_path)
        loader = jinja2.FileSystemLoader(path)
        env = jinja2.Environment(loader=loader)
        template = env.get_template(fn)
     
        print '========='
        print self.device
        print '========='
        print self.properties
        print '========='
        print self.previous
        print '========='
        print self.next
        print '========='
        '''
        try:
            str_template = template.render(device=self.device, \
                                           interface=self.properties, \
                                           previous=self.previous, \
                                           next=self.next)
            self.template = yaml.load(str_template).values()[0]
        except Exception, e:
            print "Fail to render template %s" % self.template_path
            print e.message
            return False
        '''
        print "+++++++++++++++"
        print dir(self.previous)
        print "+++++++++++++++"
        str_template = template.render(device=self.device, \
                                       interface=self.properties, \
                                       previous=self.previous, \
                                       next=self.next)
        self.template = yaml.load(str_template).values()[0]
        print "========="
        print str_template
        print self.template
        print "========="
        matches = re.findall('current\.[\w\.]+', str_template)
        if matches is []:
            # No inner reference found
            return True
        # there is inner reference need replacing
        for m in matches:
            keys = m.split('.')[1:] # skip first 'current'
            value = self.template
            for key in keys:
                value = value[key]
            # only replace first match
            print '***********************'
            print "match %s" % m
            print value
            print '***********************'
            str_template = re.sub(m, '"{}"'.format(yaml.dump(value)), str_template, count = 1)
        print str_template
        self.template = yaml.load(str_template).values()[0]
        self.template['device'] = self.device
        print "-----------"
        print str_template
        print self.template
        print "------------"
        return True


devmgmt_ip = '10.192.208.133'
devmgmt_port = 5000

def get_deploy_point():
    url = 'http://{}:{}/vg9/endpoint/deployment'.format(devmgmt_ip, devmgmt_port)
    r = requests(url)
    if r.status_code != 200:
        return None
    else:
        return json.loads(r.content)['endpoint']

def deploy_service(data):
    url = get_deploy_point()
    if url is None:
        print "Fail to get deploy endpoint."
        return False
    payload = data
    headers = {'content-type': 'application/json'}
    r = requests.post(url, data=json.dumps(payload), headers=headers, \
                      cert=('server.pem','server-key.pem'), verify=False)


# service orchestrator template
so_template = {}
def so_add_service(name, cmd, params, image, repo, version, target):
    global so_template

    service = {}
    service["apiVersion"] = "v1"
    service["kind"] = "Pod"
    service["metadata"] = {"labels": {"name": name},
                           "name": name,
                           "namespace": "default"}
    containers = []
    envs = []
    print params
    if type(params) == type([]):
        for item in params:
            envs.append({'name':item['name'], 'value':json.dumps(item['value'])})
    #print envs
    containers.append({"args": [cmd],
                      "command": ["/bin/bash", "-c"],
                      "image": "{}/{}:{}".format(repo, image, version),
                      "env": envs,
                      "imagePullPolicy": "IfNotPresent",
                      "name": name,
                      "securityContext": {"privileged": True}})
    spec = {"containers" : containers, \
            "hostNetwork": True, \
            "imagePullSecrets": [{"name": "secretnxp"}], \
            "nodeSelector": {"kubernetes.io/hostname": target}, \
            "restartPolicy": "Always"}
    service["spec"] = spec
    so_template[name] = service
 
def devmgmt_query(url, require):
    if 'deviceid' in require:
        devices = json.loads(requests.get(url, data = require).content)
    else:
        devices = json.loads(requests.get(url, data = require).content)
    if 'code' in devices and devices['code'] == 0:
        return devices['items']
    return None

def query_devices(type, require):
    url = 'http://{}:{}/vg9/lowend/{}'.format(devmgmt_ip, devmgmt_port, type)
    return devmgmt_query(url, require)

def query_boards(require):
    url = 'http://{}:{}/vg9/devices'.format(devmgmt_ip, devmgmt_port)
    return devmgmt_query(url, require)

def reserve_boards(device):
    return True

def load_template_by_class(class_name):
    fn = class_name.replace('.', '/') + '.yaml'

def find_block(block_id):
    topology = get_global_topology()
    if not block_id in topology['blocks']:
        return None
    return topology['blocks'][block_id]

def find_and_init_block(block_id):
    blockinfo = find_block(block_id)
    if blockinfo == None:
        return None
    if 'status' in blockinfo and blockinfo['status'] == "init":
        return blockinfo
    block = init_block(block_id, blockinfo)
    if block is None:
        print "Fail to init block %s." % block_id
        return None
    else:
        blockinfo['instance'] = block
    return blockinfo

def init_service(block, blockinfo):
    print "init service id %s" % block.id
    depend_blocks = {}
    for prop in ['Source', 'Target']:
        if not prop in blockinfo:
            continue
        dep_block_id = blockinfo[prop]
        dep_block = find_and_init_block(dep_block_id)
        if dep_block == None:
            print "Fail to init dependency."
            return False
        depend_blocks[prop] = dep_block
        if prop == 'Source':
            block.previous = dep_block['instance'].template
        if prop == 'Target':
            block.next = dep_block['instance'].template

    while True:
        if 'deviceid' in blockinfo and blockinfo['deviceid'] != "":
            devices = query_boards(require={'deviceid':blockinfo['deviceid']})
        else:
            devices = query_boards(block.hardware)
        # No device
        if devices == None:
            break
        target = devices[0]
        # Fail to reserve device, need updating
        if not reserve_boards(target['name']):
            continue
        # Succeed to reserve device
        break
    if devices == None:
        print "No available device for service."
        return False
    block.assignDevice(target)
    blockinfo['status'] = 'init'

    if block.id == 'kafka_1':
        block.properties['topics'] = blockinfo['Topics']

    if block.render_template():
        #print block.template
        docker_info = block.template['dockerapp-compose']
        so_add_service(block.id, docker_info['command'], docker_info['environment'], \
                       docker_info['image'], docker_info['repo'], \
                       docker_info['version'], target['name'])
    
    with open('output.json', 'w') as f:
        json.dump(so_template, f, indent=4)
    
    return True

def init_device(block, blockinfo):
    print "init device id %s" % block.id
    if 'deviceid' in blockinfo and blockinfo['deviceid'] != "":
        dev = query_devices(block.properties['name'], require={'deviceid':blockinfo['deviceid']})[0]
    else:
        dev = query_devices(block.properties['name'], require={'count':1})[0]
    block.assignDevice(dev)
    ret = block.render_template()
    if block.render_template():
        blockinfo['status'] = 'init'
        return True
    else:
        return False
    #device.set_properties(dev['attr'])


def init_block(block_id, blockinfo):
    block = TopologyBlock(block_id, blockinfo['class'])
    if block.role == 'service':
        ret = init_service(block, blockinfo)
    elif block.role == 'device':
        ret = init_device(block, blockinfo)
    return block if ret == True else None

def set_global_topology(topo):
    global topology
    topology = topo

def get_global_topology():
    global topology
    if topology == None:
        print "The topology hasn't been intilized."
    return topology

if __name__ == '__main__':
    f = open("blueprint.yaml", "r")
    bp_yaml = yaml.load(f)
    f.close()
    #print bp_yaml
    if not 'Solution' in bp_yaml:
        print "Missing Solution in topology. Quit..."
        exit(200)
    solution_node = bp_yaml['Solution']
    set_global_topology(solution_node)

    if not 'blocks' in solution_node:
        print "Missing blocks in topology. Quit..."
        exit(201)

    for blockid in solution_node['blocks']:
        # The block has been initialized
        block_info = solution_node['blocks'][blockid]
        if 'status' in block_info and block_info['status'] == "init":
            continue
        block = init_block(blockid, block_info)
        if block is None:
            print "Fail to initialize block %s." % blockid
            break
        block_info['instance'] = block

    with open('output.yaml', 'w') as f:
        yaml.dump(bp_yaml, f)

