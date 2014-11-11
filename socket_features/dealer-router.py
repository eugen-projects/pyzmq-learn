import logging
import zmq


logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(asctime)s: %(levelname)s: %(message)s")
log_server = logging.getLogger(name="DEALER")
log_client = logging.getLogger(name="ROUTER")
log_common = logging.getLogger(name="Helper")


def main():
    pass

if __name__ == "__main__":
    main()
