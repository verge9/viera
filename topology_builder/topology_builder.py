import json, yaml, jinja2
import requests
import os, re, sys, time


def trim_prototype(node, key=None):
    if type(node) != type({}) or node == {}:
        return

    if key is None:
        for k in node:
            trim_prototype(node, k)
    else:
        if type(node[key]) is not type({}):
            return
        if 'value' in node[key]:
            node[key] = node[key]['value']
            return
        trim_prototype(node[key])

class TopologyBlock(object):
    def __init__(self, block_id, block_interface):
        self.id = block_id
        self.block_class = block_interface['class']
        #self.attribute = None
        self.template = None
        self.previous = None
        self.successor = None
        self.device = None
        self.hardware = None
        self.properties = block_interface
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
        self.template_path = 'nodes/' + self.block_class.replace('.', '/') + '.yaml'
        # used for composer
        block_name = self.block_class.split('.')[-1]
        self.properties['name'] = block_name
        self.properties['id'] = self.id
        if 'Compatability' in self.properties:
            self.hardware = self.properties['Compatability']
        self.role = self.properties['role']

    def assignDevice(self, device):
        self.device = device
        #if self.id == 'kafka-1':
        #    self.device['local_ip'] = '10.193.20.94'

    def render_template(self):
        path = os.path.dirname(self.template_path)
        fn = os.path.basename(self.template_path)
        loader = jinja2.FileSystemLoader(path)
        env = jinja2.Environment(loader=loader)
        template = env.get_template(fn)
     
        str_template = template.render(device=self.device, \
                                       interface=self.properties, \
                                       previous=self.previous, \
                                       successor=self.successor)
        self.template = yaml.load(str_template).values()[0]
        trim_prototype(self.template)
        str_template = yaml.dump(self.template)

        matches = re.findall('current\.[\w\.]+', str_template)
        #print matches
        # No inner reference found
        if matches == []:
            # assign device at last
            self.template['device'] = self.device
            return True
        # there is inner reference need replacing
        for m in matches:
            keys = m.split('.')[1:] # skip beginning 'current'
            value = self.template
            for key in keys:
                value = value[key]
            # only replace first match
            #str_template = re.sub(m, '"{}"'.format(yaml.dump(value)), str_template, count = 1)
            str_template = re.sub(m, '{}'.format(json.dumps(value)), str_template, count = 1)
        self.template = yaml.load(str_template)
        self.template['device'] = self.device
        return True


devmgmt_ip = '10.192.208.133'
devmgmt_port = 5000

def get_deploy_point():
    url = 'http://{}:{}/vg9/endpoint/deployment'.format(devmgmt_ip, devmgmt_port)
    r = requests.get(url)
    if r.status_code != 200:
        return None
    else:
        return json.loads(r.content)['endpoint']

def deploy_service(blockid):
    global topology
    global so_template
    global ca_cert
    global ca_key

    blockinfo = topology['blocks'][blockid]
    if blockinfo['role'] != "service" or blockinfo['status'] == 'deployed':
        return True
    # Deploy dependencies 
    for dep in ['Source', 'Target']:
        if dep in blockinfo:
            ret = deploy_service(blockinfo[dep])
            if ret == False:
                return False
 
    print "Deploying %s..." % blockid
    ca_cert = 'server.pem'
    ca_key = 'server-key.pem'

    url = get_deploy_point()
    if url is None:
        print "Fail to get deploy endpoint."
        return False
    payload = so_template[blockid]
    headers = {'content-type': 'application/json'}

    r = requests.post(url, data=json.dumps(payload), headers=headers, \
                      cert=(ca_cert, ca_key), verify=False)
    if r.status_code not in [200, 201]:
        print "Fail to send deployment request."
        #print r.content
        return False
    print "Waiting for app %s running..." % blockid
    time.sleep(10)
    limit = 300
    i = 0
    while i < limit:
        r = requests.get(url + '/' + blockid, headers=headers, \
                         cert=(ca_cert, ca_key), verify=False)
        if r.status_code not in [200, 201]:
            print "Fail to send query for app status."
        app_query = json.loads(r.content)
        if app_query['code'] != 0:
            print "app status error."
            print app_query['message']
            return False
        status = app_query['items'][0]['status']['phase']
        if status == 'Running':
            break
        print "The app {} is {}.".format(blockid, status)
        time.sleep(1)
    print "The app %s has been runnning." % blockid
    blockinfo['status'] = 'deployed'
    
    return True

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
    if type(params) == type([]):
        for item in params:
            value = item['value']
            if type(value) == type({}):
                # for dict type, need to convert to json string(embraced by "")
                value = json.dumps(item['value'])
            envs.append({'name':item['name'], 'value':value})
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
    '''
    if 'deviceid' in require:
        devices = json.loads(requests.get(url, data = require).content)
    else:
        devices = json.loads(requests.get(url, data = require).content)
    '''
    devices = json.loads(requests.get(url, data = require).content)
    if 'code' not in devices or devices['code'] != 0:
        return None
    if 'deviceid' in require:
        print "matching device %s" % require['deviceid']
        for dev in devices['items']:
            # get required board
            if 'name' in dev and dev['name'] == require['deviceid']:
                return [dev]
        # No intent device found
        return None
    return devices['items']

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
            block.successor = dep_block['instance'].template

    while True:
        if 'deviceid' in blockinfo and blockinfo['deviceid'] != "":
            devices = query_boards(require={'deviceid':blockinfo['deviceid']})
        else:
            devices = query_boards(block.hardware)
        # No device
        if devices == None or devices == []:
            break
        target = devices[0]
        # Fail to reserve device, need updating
        if not reserve_boards(target['name']):
            continue
        # Succeed to reserve device
        break
    if devices == None or devices == []:
        print "No available device for service."
        return False
    block.assignDevice(target)
    blockinfo['status'] = 'init'

    if block.id == 'kafka_1':
        block.properties['topics'] = blockinfo['topics']

    if block.render_template():
        docker_info = block.template['dockerapp-compose']
        so_add_service(block.id, docker_info['command'], docker_info['environment'], \
                       docker_info['image'], docker_info['repo'], \
                       docker_info['version'], target['name'])
    
    return True

def init_device(block, blockinfo):
    print "init device id %s" % block.id
    if 'deviceid' in blockinfo and blockinfo['deviceid'] != "":
        dev = query_devices(block.properties['name'], require={'deviceid':blockinfo['deviceid']})
    else:
        dev = query_devices(block.properties['name'], require={'count':1})
    if dev is None or dev == []:
        print "Can not find device of %s." % block.id
        return False
    # Use first one
    dev = dev[0]
    block.assignDevice(dev)
    ret = block.render_template()
    if block.render_template():
        blockinfo['status'] = 'init'
        return True
    else:
        return False

def init_block(block_id, blockinfo):
    block = TopologyBlock(block_id, blockinfo)
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
    if len(sys.argv) == 1:
        bp = "blueprint.yaml"
    elif len(sys.argv) == 2:
        bp = sys.argv[1]
    else:
        print "Deployment manager usage:"
        print "%s <blueprint template>" % sys.argv[0]
        exit(100)
    if not os.path.isfile(bp):
        print "Can NOT find blueprint template %s." % bp
        exit(101)

    f = open(bp, "r")
    bp_yaml = yaml.load(f)
    f.close()
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

    with open('output.json', 'w') as f:
        json.dump(so_template, f, indent=4)

    for blockid in solution_node['blocks']:
        ret = deploy_service(blockid)
        if ret == False:
            print "Fail to deploy %s, stop deployment and rollback." % blockid
            exit(104)

    #with open('output.yaml', 'w') as f:
    #    yaml.dump(bp_yaml, f)

