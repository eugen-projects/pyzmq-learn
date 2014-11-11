import logging
import random
import zmq


logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(asctime)s: %(levelname)s: %(message)s")
log_server = logging.getLogger(name="SERVER")
log_client = logging.getLogger(name="CLIENT")
log_common = logging.getLogger(name="Helper")


def send_acks_simple(server, clients):
    resp_order = []
    for _ in range(len(clients)):
        # must reply to first requester before can get the next request
        msg = server.recv()
        log_server.info("Got: %s", msg)
        server.send('ack')
        id = int(msg.split("_")[1])
        resp_order.append(id)
        log_client.info("Client %d got: %s", id, clients[id].recv())
        clients[id].close()
    return resp_order


def send_acks_poller(server, clients):
    poller = zmq.Poller()
    for client_sock in clients.values():
        poller.register(client_sock, zmq.POLLIN)

    resp_order = []
    for _ in range(len(clients)):
        # must reply to first requester before can get the next request
        msg = server.recv()
        log_server.info("Got: %s", msg)
        server.send('ack')
        id = int(msg.split("_")[1])
        resp_order.append(id)
        while True:
            try:
                sockets_ready = dict(poller.poll(timeout=None))
                for sock in sockets_ready:  # should be always at most one
                    msg = sock.recv()
                    log_client.info("Client got: %s", msg)
                    poller.unregister(sock)
                break
            except zmq.Again:
                log_common.debug("None available")
        clients[id].close()
    return resp_order

def main():
    """
    Check how binding a socket to multiple addresses works.

    Note for REQ-REP pattern it is inflexible: before receiving from another client we have to reply to previous one.
    The output shows that checking for sockets in the server is in connection order. However if it would be parallel
    the recv() will return as soon as any of the endpoints() has an incoming message. So if first connected client
    didn't send anything but the third did, the server will receive the response from the third client.

    Helper: 2014-11-10 12:56:40,601: INFO: experiment 1
    Helper: 2014-11-10 12:56:40,601: INFO: Connection order: 	4->2->1->0->3
    Helper: 2014-11-10 12:56:40,601: INFO: Sending order: 		2->3->1->0->4
    Helper: 2014-11-10 12:56:40,601: INFO: Reply order: 		4<-2<-1<-0<-3

    Helper: 2014-11-10 12:56:40,603: INFO: experiment 2
    Helper: 2014-11-10 12:56:40,603: INFO: Connection order: 	2->0->4->1->3
    Helper: 2014-11-10 12:56:40,603: INFO: Sending order: 		1->0->2->3->4
    Helper: 2014-11-10 12:56:40,603: INFO: Reply order: 		2<-0<-4<-1<-3

    Helper: 2014-11-10 12:56:40,607: INFO: experiment 3
    Helper: 2014-11-10 12:56:40,607: INFO: Connection order: 	1->2->3->4->0
    Helper: 2014-11-10 12:56:40,607: INFO: Sending order: 		1->0->4->2->3
    Helper: 2014-11-10 12:56:40,607: INFO: Reply order: 		1<-2<-3<-4<-0


    """
    context = zmq.Context.instance()
    INIT_PORT = 5555
    N_CLIENTS = 5
    addresses = ['tcp://127.0.0.1:%d' % port for port in range(INIT_PORT, INIT_PORT + N_CLIENTS)]

    server = context.socket(zmq.REP)
    for address in addresses:
        server.bind(address)

    for experiment_nr in range(3):
        clients = {}
        l = range(N_CLIENTS)
        random.shuffle(l)
        connection_order = "->".join(str(id) for id in l)
        for id in l:
            client = context.socket(zmq.REQ)
            client.connect(addresses[id])
            clients[id] = client
        l = range(N_CLIENTS)
        random.shuffle(l)
        send_order = "->".join(str(id) for id in l)
        for rid in l:
            clients[rid].send('C_%d' % rid)
            log_client.info("Client %d sent message", rid)

        log_common.info("experiment %d", experiment_nr + 1)
        log_common.info('Connection order: \t%s', connection_order)
        log_common.info('Sending order: \t\t%s', send_order)
        resp_order = send_acks_simple(server, clients)
        #resp_order = send_acks_poller(server, clients)
        log_common.info('Reply order: \t\t%s', "<-".join(str(i) for i in resp_order))

    server.close()
    context.destroy()



if __name__ == "__main__":
    main()
