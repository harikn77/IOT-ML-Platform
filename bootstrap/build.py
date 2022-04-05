import docker
import json
import logging
from jinja2 import Template

def render_template(template_file, output_file, workers):
    with open(template_file) as f:
        template = Template(f.read())
    with open(output_file, 'w') as f:
        f.write(template.render(servers=workers))

logging.basicConfig(level=logging.INFO)

logging.info('Reading config files')
services = json.loads(open('services.json').read())
servers = json.loads(open('servers.json').read())

def build(host,path,image_tag,container_name):
    logging.info('Connecing to ' + host)
    client = docker.DockerClient(base_url=host)
    logging.info('Connected to Docker')
    logging.info('Building ' + image_tag)
    client.images.build(path=path, tag=image_tag)
    logging.info('Built image: ' + image_tag)
    try:
        container = client.containers.get(container_name)
        logging.info('Container exists, stopping')
        container.stop()
        logging.info('Removing container: ' + container_name)
        container.remove()
    except:
        logging.info('Container does not exist')
    logging.info('Creating container: ' + container_name)
    try:
        if container_name == 'deployer':
            client.containers.run(image_tag,name=container_name, detach=True, network='host', volumes={'/var/run/docker.sock': {'bind': '/var/run/docker.sock', 'mode': 'rw'}})
        elif container_name == "monitor_ha":
            client.containers.run(image_tag,name=container_name, detach=True, network='host', volumes={'/home/vm1/.ssh': {'bind': '/root/.ssh', 'mode': 'rw'}})
        else:
            client.containers.run(image_tag,name=container_name, detach=True, network='host')
    except Exception as e:
        logging.info('Error: ' + str(e))
    logging.info('Started ' + container_name)


def haproxy_config():
    workers = []
    for worker in servers['workers']:
        temp = {}
        temp['name'] = worker['user']
        temp['ip'] = worker['ip']
        workers.append(temp)
    render_template('haproxy.j2', 'haproxy.cfg', workers=workers)

def generate_service_config():
    logging.info('Generating service config')
    master_ip = servers['master']['ip']
    workers = []
    for worker in servers['workers']:
        temp = {}
        temp['name'] = worker['user']
        temp['ip'] = worker['ip']
        workers.append(temp)
    service_config = {
        "kafka_ip": master_ip,
        "kafka_port": "9092",
        "mongo_server": servers['mongo_server'],
        "sensor_api": "http://" + master_ip + ":7000/",
        "deployer_master": "http://" + master_ip + ":9999/",
        "platform_manager": "http://" + master_ip + ":5000/",
        "scheduler": "http://" + master_ip + ":8210/",
        "workers": workers
    }
    logging.info('Writing service config')
    for service in services['services']:
        path = '../' + service['name'] + '/' + service['name'] + '/config.json'
        with open(path, 'w') as outfile:
            json.dump(service_config, outfile)
        logging.info('Wrote service config to ' + path)
    
def start_service():
    generate_service_config()
    logging.info('Starting service')
    for service in services['services']:
        image_name = f'{service["name"]}:{service["version"]}'
        logging.info('building image ' + image_name)
        host = 'ssh://' + servers['master']['user'] + '@' + servers['master']['ip']
        # host = 'unix://var/run/docker.sock'
        if service['name'] == 'deployer':
            for worker in servers['workers']:
                host = 'ssh://' + worker['user'] + '@' + worker['ip'] 
                data = json.load(open('../deployer/deployer/config.json'))
                data['host_ip'] = worker['ip']
                data['host_name'] = worker['user']
                with open('../deployer/deployer/config.json', 'w') as outfile:
                    json.dump(data, outfile)
                logging.info('Updating config.json')
                build(host,service['path'],image_name,service['name'])
        elif service['name'] == 'system_monitor':
            for worker in servers['workers']:
                host = 'ssh://' + worker['user'] + '@' + worker['ip'] 
                build(host,service['path'],image_name,service['name'])
        else:
            build(host,service['path'],image_name,service['name'])
    logging.info('Platform has been deployed' + servers['master']['ip'] + ':2500')