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
    'MAX_POINT_BACKLOG':      os.getenv('MAX_POINT_BACKLOG',                              '1000'),
    'HEALTHCHECK_PORT':       os.getenv('HEALTHCHECK_PORT',                               '8085')
}

try:
    int(env['INTERVAL'])
    int(env['HEALTHCHECK_PORT'])
    int(env['MAX_POINT_BACKLOG'])

    if int(env['MAX_POINT_BACKLOG']) < 1:
        raise ValueError('MAX_POINT_BACKLOG must be greater than 0')
except ValueError as e:
    log.error(e)
    sys.exit(1)
