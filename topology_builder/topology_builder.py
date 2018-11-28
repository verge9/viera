import yaml, json
import os, sys
import requests


topology = None
#def find_node_in_solution(name):
#    for category in 
def findNodeById(id, solution):
    node_type = ['devices', 'services']
    for t in node_type:
        if not t in solution.keys():
            continue
        for node in solution[t]:
            #print node['id']
            #print id
            if node['id'] == id:
                return node
    return None

def getPrevNodes(curNodeId, nodes):
    prev_nodes = []
    for node in nodes:
        if curNodeId in node['linkto']:
            prev_nodes.append(node)
    return prev_nodes

def getNextNodes(curNode, solution):
    nodes = []
    for linkto in curNode['linkto']:
        next_node = findNodeById(linkto, solution)
        nodes.append(next_node)
    return nodes

def addInputNode(in_node, to_node):
    url = "http://10.193.21.210:15000/addInput/%s" % to_node['name']
    #url = "http://10.193.21.210:15000/run_test"
    data = {}
    headers = {'content-type':'application/json'}
    data['input'] = {'id': in_node['id'], 'name':in_node['name']}
    data['dest_node'] = {'id': to_node['id'], 'name':to_node['name']}
    r = requests.post(url, data = json.dumps(data), headers=headers)

    return r

def load_module(classname, libs={}):
    if classname in libs:
        return libs[classname]
    path = 'nodes/' + os.path.dirname(classname.replace('.', '/'))
    fn = os.path.basename(classname.replace('.', '/'))
    if not path in sys.path:
        sys.path.append(path)
    # there is implication that class name is same as module name
    module = __import__(fn)
    new_class = getattr(module, fn)
    libs[classname] = new_class
    return new_class

def find_block(name):
    struct = get_global_topology()
    if not name in struct['blocks']:
        return None
    return struct['blocks'][name]

def find_and_init_block(name):
    block = find_block(name)
    if block == None:
        return None
    if 'status' in block and block['status'] == "init":
        return block
    if init_block(block):
        return block
    else:
        print "Fail to init block %s." % name
        return None

# service orchestrator template
so_template = {} 
def so_add_service(name, cmd, param, image, repo, version, target):
    global so_template

    service = {}
    service["apiVersion"] = "v1"
    service["kind"] = "Pod"
    service["metadata"] = {"labels": {"name": name},
                           "name": name,
                           "namespace": "default"}
    containers = []
    containers.append({"args": [cmd],
                      "command": ["/bin/bash", "-c"],
                      "image": "{}/{}:{}".format(repo, image, version),
                      "env": [{"name": "SERVICE_PARAMETERS", \
                               "value": json.dumps(param)}],
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


devmgmt_ip = '10.192.208.133' 
devmgmt_port = 5000

def devmgmt_query(url, require):
    devices = json.loads(requests.get(url, data = require).content)
    return devices['items']

def query_devices(type, require):
    url = 'http://{}:{}/vg9/lowend/{}'.format(devmgmt_ip, devmgmt_port, type)
    return devmgmt_query(url, require)

def query_boards(require):
    url = 'http://{}:{}/vg9/devices'.format(devmgmt_ip, devmgmt_port)
    return devmgmt_query(url, require)

def reserve_boards(device):
    return True

def init_service(block):
    depend_blocks = {}
    for prop in ['Source', 'Target']:
        if not prop in block['Properties']:
            continue
        dep = block['Properties'][prop]['Name']
        dep_block = find_and_init_block(dep)
        if dep_block == None:
            print "Fail to init dependency."
            return False
        depend_blocks[prop] = dep_block

    block_class = load_module(block['Class'])
    service = block_class.create_block(block['id'])
    hw_require = service.get_hw_requirement()
    while True:
        devices = query_boards(hw_require)
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
    block['Properties']['device'] = target
    block['status'] = 'init'

    deploy_info = service.get_deploy_info(block['Properties'], depend_blocks)
    if deploy_info == None:
        print "Fail to get deploy informatoin for service id %s" % block['id']
    so_add_service(deploy_info['name'], deploy_info['cmd'], \
                   deploy_info['param'], deploy_info['image'], \
                   deploy_info['repo'], deploy_info['version'], \
                   target['name'])
    
    with open('output.json', 'w') as f:
        json.dump(so_template, f, indent=4)
    
    return True

def init_device(block):
    device_class = load_module(block['Class'])
    device = device_class.create_device(block['id'])
    dev = query_devices(block['name'], require={'count':1})[0]
    block["Properties"] = dev['attr']
    #device.set_properties(dev['attr'])
    
    access, value = getattr(device, device.accessPoint)(block["Properties"])
    block['Properties'][access] = value 
    block['status'] = 'init'

    return True

def init_block(block):
    if block['Type'] == 'service':
        return init_service(block)
    elif block['Type'] == 'device':
        return init_device(block)

def get_deploy_endpoint():
    url = 'http://10.192.208.133:5000/vg9/endpoint/deployment'
    r = requests.get(url)
    return r.content['endpoint']

def deploy_service(block):
    # skip block that has been deployed
    if 'status' in block and block['status'] == "deployed":
        continue
    for prop in ['Source', 'Target']:
        if not prop in block['Properties']:
            continue
        dep = block['Properties'][prop]['Name']
        ret = deploy_service(dep)
        if ret == False:
            return False

    try:
        url = get_deploy_endpoint()
        requests.post(url, cert=('server.pem', 'server-key.pem'), verify=False)
    except:
        print "Fail to deploy %s." % block['name']
        return False
    # Deploy succeeds
    block['status'] = 'deployed'
    return True

def deploy_rollback():
    pass

def set_global_topology(topo):
    global topology
    topology = topo

def get_global_topology():
    global topology
    if topology == None:
        print "The topology hasn't been intilized."
    return topology

if __name__ == '__main__':
    sys.path.append('nodes/common')
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
        block = solution_node['blocks'][blockid]
        if 'status' in block and block['status'] == "init":
            continue
        ret = init_block(block)
        if not ret:
            print "Fail to initialize block %s." % blockid
    # All blocks have been initialized, deploy service
    for blockid in solution_node['blocks']:
        block = solution_node['blocks'][blockid]
        if block['Type'] == "service":
            # Only service needs deploying
            continue
        ret = deploy_service(block)
        if ret == False:
            break
    if ret == False:
        deploy_rollback()
        # call rollback function
    

