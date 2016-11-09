import argparse
import logging
import pathlib

import yaml


def main():
    parser = argparse.ArgumentParser(description='Capture and record from various input sources.')
    parser.add_argument('-c', '--config', default='/etc/surveillance.conf', help='configuration file path')
    parser.add_argument('-l', '--log', default='/var/log/surveillance.log', help='log file path')
    args = parser.parse_args()

    logging.basicConfig(filename=args.log,  level=logging.INFO)

    config = {}
    with pathlib.Path(args.config) as conf_path:
        if conf_path.exists():
            with conf_path.open() as conf_file:
                config = yaml.load(conf_file)

    for service in config.get('services', []):
        service.start()


if __name__ == "__main__":
    main()
