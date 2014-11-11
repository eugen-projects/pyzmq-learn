import logging
import time
import threading
import zmq


logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(asctime)s: %(levelname)s: %(message)s")
log_worker = logging.getLogger(name="WORKER")
log_client = logging.getLogger(name="CLIENT")
log_common = logging.getLogger(name="Helper")

url_worker = "inproc://workers"
url_client = "tcp://*:5555"
url_server = "tcp://127.0.0.1:5555"


def client_send(client_id, context, endpoint):
    socket = context.socket(zmq.REQ)
    socket.connect(endpoint)
    msg = "Hello_%s" % client_id
    REPEAT = 2
    for i in range(REPEAT):
        socket.send(msg)
        log_client.info("%s sent %s", client_id, msg)
        log_client.info("%s received %s", client_id, socket.recv())
    socket.close()


def start_clients():
    context = zmq.Context.instance()
    # Launch some clients
    client_threads = []
    for i in range(3):
        thread = threading.Thread(target=client_send, args=(i, context, url_server,))
        thread.start()
        client_threads.append(thread)
    return client_threads


def worker_routine(worker_id, context, worker_url):
    """Worker routine"""
    # Socket to talk to dispatcher
    socket = context.socket(zmq.REP)

    socket.connect(worker_url)

    while True:
        try:
            string = socket.recv()
        except zmq.ContextTerminated:
            break

        log_worker.info("%d - Received request: [ %s ]", worker_id, string)

        # do some 'work'
        time.sleep(1)

        #send reply back to client
        socket.send(b"World-%d" % worker_id)


def start_server():
    """Server routine"""

    # Prepare our context and sockets
    context = zmq.Context.instance()

    # Socket to talk to clients
    clients = context.socket(zmq.ROUTER)
    clients.bind(url_client)

    # Socket to talk to workers
    workers = context.socket(zmq.DEALER)
    workers.bind(url_worker)

    # Launch pool of worker threads
    for i in range(2):
        thread = threading.Thread(target=worker_routine, args=(i, context, url_worker,))
        thread.start()
    try:
        zmq.device(zmq.QUEUE, clients, workers)
    except zmq.ContextTerminated:
        clients.close()
        workers.close()


def main():
    """
    Client receives the reply from the worker that got the request but further communication
    can be done with any other free worker.

    Sample output (3 clients, 2 workers):

    CLIENT: 2014-11-10 19:11:18,015: INFO: 0 sent Hello_0
    CLIENT: 2014-11-10 19:11:18,016: INFO: 1 sent Hello_1
    CLIENT: 2014-11-10 19:11:18,017: INFO: 2 sent Hello_2
    WORKER: 2014-11-10 19:11:18,129: INFO: 0 - Received request: [ Hello_2 ]
    WORKER: 2014-11-10 19:11:18,144: INFO: 1 - Received request: [ Hello_0 ]
    WORKER: 2014-11-10 19:11:19,133: INFO: 0 - Received request: [ Hello_1 ]
    CLIENT: 2014-11-10 19:11:19,134: INFO: 2 received World-0
    CLIENT: 2014-11-10 19:11:19,134: INFO: 2 sent Hello_2
    WORKER: 2014-11-10 19:11:19,145: INFO: 1 - Received request: [ Hello_2 ]
    CLIENT: 2014-11-10 19:11:19,146: INFO: 0 received World-1
    CLIENT: 2014-11-10 19:11:19,146: INFO: 0 sent Hello_0
    WORKER: 2014-11-10 19:11:20,135: INFO: 0 - Received request: [ Hello_0 ]
    CLIENT: 2014-11-10 19:11:20,136: INFO: 1 received World-0
    CLIENT: 2014-11-10 19:11:20,136: INFO: 1 sent Hello_1
    WORKER: 2014-11-10 19:11:20,148: INFO: 1 - Received request: [ Hello_1 ]
    CLIENT: 2014-11-10 19:11:20,148: INFO: 2 received World-1
    CLIENT: 2014-11-10 19:11:21,138: INFO: 0 received World-0
    CLIENT: 2014-11-10 19:11:21,151: INFO: 1 received World-1
    """
    client_threads = start_clients()
    proxy_thread = threading.Thread(target=start_server)
    proxy_thread.start()
    for client_thread in client_threads:
        client_thread.join()
    context = zmq.Context.instance()
    context.term()

if __name__ == "__main__":
    main()