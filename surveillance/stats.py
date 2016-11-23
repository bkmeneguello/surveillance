import os

import statsd

client = statsd.StatsClient(prefix='surveillance',
                            host=os.environ.get('STATSD_HOST', 'localhost'),
                            port=int(os.environ.get('STATSD_PORT', 8125)),
                            maxudpsize=int(os.environ.get('STATSD_MAX_UDP_SIZE', 512)),
                            ipv6=bool(os.environ.get('STATSD_IPV6', False)))

incr = client.incr
decr = client.decr
timer = client.timer
timing = client.timing
gauge = client.gauge
set = client.set
