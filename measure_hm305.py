#!/usr/bin/python3

import logging
import sys

from serial import SerialException

from hm305 import CRCError, CSVWriter
from hm305.hm305 import HM305

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('--port', type=str, help='serial port', required=True)
    parser.add_argument('--voltage', type=float, help='set voltage')
    parser.add_argument('--current', type=float, help='set current')
    parser.add_argument('--csv', type=str, help='path to csv')
    parser.add_argument('--debug', action='store_true', help='enable verbose logging')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        hm = HM305(args.port)
    except SerialException:
        logging.fatal(f"Port {args.port} could not open!")
        sys.exit(1)

    if args.voltage is not None:
        logging.info(f"Setting voltage: {args.voltage}")
        hm.v = args.voltage
    if args.current is not None:
        logging.info(f"Setting current: {args.current}")
        hm.i = args.current

    csv_logger = CSVWriter(args.csv, delimiter=";")

    is_running = True
    while is_running:
        try:
            logging.info(f"voltage: {hm.v} V | current: {hm.i} A | power: {hm.w} W")
            csv_logger.write(hm.v, hm.i, hm.w)
        except SerialException as ex:
            logging.warning(f"Could not read measurements. {ex}")
        except KeyboardInterrupt:
            is_running = False
            logging.debug("cancel by user keyboard")
        except CRCError as ex:
            logging.warning(f"CRCError: {ex}")
        except Exception as ex:
            logging.error(f"unknown issue: {ex}")

    logging.debug("Shutdown")
