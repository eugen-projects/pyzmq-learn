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


def receive_message(participant):
    """
    Multipart message can only be received with recv_multipart().
    Otherwise only the first part if returned by recv().

    recv_multipart() can be used to get single-part message but it returns a list of one item instead of a the message body
    """
    msg = participant.recv_multipart()
    if isinstance(msg, list) and len(msg) == 1:
        return msg[0]
    else:
        return msg


def clean_up(context, *sockets):
    for sock in sockets:
        sock.close()
    context.destroy()


def main():
    context = zmq.Context.instance()
    server = create_server(context, 'tcp://*:5555')
    client = create_client(context, 'tcp://127.0.0.1:5555')

    msg = ['A', 'B', 'C']
    #msg = 'A'
    status = send_message(client, msg)
    log_client.info("Sent message: %s", msg)
    msg = receive_message(server)
    log_server.info("Received: %s", msg)

    clean_up(context, server, client)



if __name__ == "__main__":
    main()
