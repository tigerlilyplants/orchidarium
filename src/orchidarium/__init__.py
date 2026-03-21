import logging
import os
import sys
import json

from typing import Dict


log = logging.getLogger(__name__)

env: Dict[str, str]  = {
    'DEBUG':                  os.getenv('DEBUG',                                              ''),
    'INFLUXDB_HOST':          os.getenv('INFLUXDB_HOST',                         'influxdb:8086'),
    'INFLUXDB_TOKEN':         os.getenv('INFLUXDB_TOKEN',                                     ''),
    'INFLUXDB_ORG':           os.getenv('INFLUXDB_ORG',                            'orchidarium'),
    'INFLUXDB_DATABASE':      os.getenv('INFLUXDB_DATABASE',                       'orchidarium'),
    'INTERVAL':               os.getenv('INTERVAL',                                         '10'),
    'HEALTHCHECK_PORT':       os.getenv('HEALTHCHECK_PORT',                               '8085')
}

# Log the configuration
log.debug(
    json.dumps(
        {
            k: env[k] for k in env
            if k != 'INFLUXDB_TOKEN'
        }
    )
)

try:
    int(env['INTERVAL'])
    int(env['HEALTHCHECK_PORT'])
except ValueError as e:
    log.error(e)
    sys.exit(1)