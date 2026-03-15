import logging
import os
import sys

from typing import Dict


log = logging.getLogger(__name__)

env: Dict[str, str]  = {
    'DEBUG':                  os.getenv('DEBUG',                                              ''),
    'INFLUXDB_HOST':          os.getenv('INFLUXDB_HOST',                         'influxdb:8086'),
    'INFLUXDB_TOKEN':         os.getenv('INFLUXDB_TOKEN',                                     ''),
    'INFLUXDB_ORG':           os.getenv('INFLUXDB_ORG',                            'orchidarium'),
    'INFLUXDB_DATABASE':      os.getenv('INFLUXDB_DATABASE',                       'orchidarium'),
    'INTERVAL':               os.getenv('INTERVAL',                                         '60'),
    # 'HEALTHCHECK_CACHE_TTL':  os.getenv('HEALTHCHECK_CACHE_TTL',                             '5'),
    'HEALTHCHECK_CACHE_PATH': os.getenv('HEALTHCHECK_CACHE_PATH', '/opt/orchidarium/healthcheck'),
    'HEALTHCHECK_PORT':       os.getenv('HEALTHCHECK_PORT',                               '8085')
}

try:
    int(env['INTERVAL'])
    # int(env['HEALTHCHECK_CACHE_TTL'])
    int(env['HEALTHCHECK_PORT'])
except ValueError as e:
    log.error(e)
    sys.exit(1)