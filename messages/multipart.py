import logging
import zmq


logging.basicConfig(level=logging.INFO, format="%(name)s: %(asctime)s: %(levelname)s: %(message)s")
log_server = logging.getLogger(name="SERVER")
log_client = logging.getLogger(name="CLIENT")


def create_server(context, address):
    server = context.socket(zmq.REP)
    server.bind(address)
    return server


def create_client(context, address):
    client = context.socket(zmq.REQ)
    client.connect(address)
    return client


def send_message(participant, message):
    if isinstance(message, list):
        participant.send_multipart(message)  # internally the list is iterated as in the code commented below
        #for part in message[:-1]:
        #    participant.send_multipart(part, flags=zmq.SNDMORE)  # send() works too
        #participant.send_multipart(message[-1])
    else:
        return participant.send(message)


def receive_message(participant, is_multipart=False):
    """
    Multipart message can only be received with recv_multipart().
    Otherwise only the first part if returned by recv().
    """
    if not is_multipart:
        return participant.recv()
    else:
        return participant.recv_multipart()  # copy=False returns the Frame rather than part payload


def clean_up(context, *sockets):
    for sock in sockets:
        sock.close()
    context.destroy()


def main():
    context = zmq.Context.instance()
    server = create_server(context, 'tcp://*:5555')
    client = create_client(context, 'tcp://127.0.0.1:5555')

    msg = ['A', 'B', 'C']
    status = send_message(client, msg)
    log_client.info("Sent message: %s", msg)
    msg = receive_message(server, is_multipart=True)
    log_server.info("Received: %s", msg)

    clean_up(context, server, client)



if __name__ == "__main__":
    main()
