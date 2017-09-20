import sys
import time
from datetime import datetime
from string import Template

import dns.resolver
import docker
import logging

FORMAT = '%(asctime)s %(levelname)s: %(message)s'
logging.basicConfig(filename='chinadnswatch.log', level=logging.INFO, format=FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('filelogger')

testHosts = ['www.google.com',
             'www.6park.com',
             'www.youtube.com',
             'www.github.com',
             'www.rarbg.to']

client = docker.from_env()


def main(*args):
    while True:
        check_dns_status()
        time.sleep(20)


def check_dns_status():
    try:
        container_list = client.containers.list(all=True)
        illegal_container_list = list(
            filter(lambda container: container.name != 'chinadns' and
                                     list(filter(lambda key: '53' in key,
                                                 container_list[0].attrs['NetworkSettings'][
                                                     'Ports'].keys())), container_list))
        for container in illegal_container_list:
            container.remove(force=True)

        chinadns_container_list = list(filter(lambda container: container.name == 'chinadns', container_list))
        if_restart_container = False
        if len(chinadns_container_list) > 0:
            chinadns_container = chinadns_container_list[0]
            if chinadns_container.status == 'running':
                for host in testHosts:
                    ifResolve = resolve(host)
                    if not ifResolve:
                        if_restart_container = True
                        break
                    else:
                        logger.info('%s is resolved', host)
                if if_restart_container:
                    s = Template('Restart Chinadns at $time')
                    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    s.substitute(time=time_str)
                    chinadns_container.restart(timeout=30)
                    logger.warning('Restart Chinadns.')
            else:
                chinadns_container.remove(force=True)
                run_chinadns()
        else:
            run_chinadns()
    except BaseException as error:
        logger.error('An exception occurred: {}'.format(error))


def run_chinadns():
    client.containers.run('daocloud.io/hooyao/docker-chinadns:latest', ports={'53/udp': 53},
                          name='chinadns',
                          entrypoint='chinadns',
                          command='-s 114.114.114.114,8.8.8.8,8.8.4.4',
                          detach=True)
    logger.info('Run chinadns.')


def resolve(addr):
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['127.0.0.1']
        answer = resolver.query(addr)
        return len(answer) > 0
    except:
        return 0


if __name__ == '__main__':
    main(*sys.argv[1:])
