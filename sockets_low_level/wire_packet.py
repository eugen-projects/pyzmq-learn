import logging
import socket
import struct
import threading
import time
import zmq


logging.basicConfig(level=logging.INFO, format="%(name)s: %(asctime)s: %(levelname)s: %(message)s")
log_receiver = logging.getLogger(name="RECEIVER")
log_sender = logging.getLogger(name="SENDER")


def _get_signature(sock):
    msg = sock.recv(10)
    assert len(msg) == 10
    log_receiver.info("Got signature: %s", msg.encode('hex'))
    return msg


def _get_revision(sock):
    msg = sock.recv(1)
    assert len(msg) == 1
    log_receiver.info("Got revision: %s", msg.encode('hex'))
    return msg


def _get_sock_type(sock):
    sock_type = {
        0: "PAIR",
        1: "PUB",
        2: "SUB",
        3: "REQ",
        4: "REP",
        5: "DEALER",
        6: "ROUTER",
        7: "PULL",
        8: "PUSH"
    }
    msg = sock.recv(1)
    assert len(msg) == 1
    log_receiver.info("Got socket type: %s", sock_type[ord(msg)])


def _get_identity(sock):
    msg = sock.recv(2)
    assert len(msg) == 2
    id_len = int(msg[1].encode('hex'), 16)
    if id_len > 0:
        prefix = msg
        msg = sock.recv(id_len)
        assert len(msg) == id_len
        log_receiver.info("Got identity: %s", (prefix + msg).encode('hex'))
        return msg
    log_receiver.info("Got identity: %s", msg.encode('hex'))


def _get_message(sock):
    msgs = []
    has_more_frames = True
    while has_more_frames:
        flag_byte = sock.recv(1)
        assert len(flag_byte) == 1
        flag = struct.unpack('!b', flag_byte)[0]
        has_more_frames = flag & 0x01
        len_field = 8 if flag & 0x02 else 1
        msg_len_bytes = sock.recv(len_field)
        assert len(msg_len_bytes) == len_field
        if len_field == 8:
            msg_len = struct.unpack("!Q", msg_len_bytes)[0]
        else:
            msg_len = struct.unpack("!B", msg_len_bytes)[0]
        payload = ""
        if msg_len:
            payload = sock.recv(msg_len)
            assert len(payload) == msg_len
            msgs.append(payload)
        msg = flag_byte+msg_len_bytes+payload
        log_receiver.info("Got message: %s (%s)", payload, msg.encode('hex'))
    return msgs[0] if len(msgs) == 1 else msgs


def _send_signature(sock):
    signature = 'ff00000000000000017f'
    revision = '01'
    socket_type = zmq.REP
    identity = '0005457567656e'
    msg = struct.pack("!10ssB%ds" % len(identity.decode('hex')), signature.decode('hex'), revision.decode('hex'), socket_type,
                      identity.decode('hex'))
    sock.sendall(msg)
    log_receiver.info("Sent: %s", msg.encode('hex'))


def _send_message(sock, msg, receiver_sock_type):
    if receiver_sock_type in [zmq.REQ]:  # some socket types do not understand identities but require an empty frame
        preamble = '0100'.decode('hex')
        sock.sendall(preamble)
        log_receiver.info("Sent: %s", preamble.encode('hex'))
    if len(msg) <= 255:
        msg = ("00%02x" % len(msg)).decode("hex") + msg
        sock.sendall(msg)
    else:
        msg = struct.pack("!cQs", 0, len(msg), msg)
        sock.sendall(msg)
    log_receiver.info("Sent: %s", msg.encode('hex'))


def receive_in_loop(ip, port, receiver_sock_type):
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((ip, port))
    sock.listen(5)

    try:
        client_sock, addr = sock.accept()
        log_receiver.info("---GREETING STAGE---")

        sender_sig = _get_signature(client_sock)

        _send_signature(client_sock)

        _get_revision(client_sock)

        _get_sock_type(client_sock)

        sender_id = _get_identity(client_sock)

        if receiver_sock_type != zmq.ROUTER:
            msg = _get_message(client_sock)
            _send_message(client_sock, "ack", receiver_sock_type)
        else:
            _send_message(client_sock, "hello", receiver_sock_type)
            msg = _get_message(client_sock)
        client_sock.close()
    except Exception:
        log_receiver.warn("exception", exc_info=True)
    finally:
        sock.close()


def test_REQ(context, endpoint):
    sender_sock_type = zmq.REQ
    receiver_thread = threading.Thread(target=receive_in_loop, args=('127.0.0.1', 5555, zmq.REQ))
    receiver_thread.start()
    sender = context.socket(sender_sock_type)
    sender.connect(endpoint)
    sender.send("test")
    log_sender.info("Sent message")
    msg = sender.recv()
    log_sender.info("Got reply: %s", msg)
    return receiver_thread


def test_DEALER(context, endpoint):
    sender_sock_type = zmq.DEALER
    receiver_thread = threading.Thread(target=receive_in_loop, args=('127.0.0.1', 5555, zmq.DEALER))
    receiver_thread.start()
    sender = context.socket(sender_sock_type)
    sender.setsockopt(zmq.IDENTITY, 'abc')
    sender.connect(endpoint)
    sender.send("test")
    log_sender.info("Sent message")
    msg = sender.recv()
    log_sender.info("Got reply: %s", msg)
    return receiver_thread


def test_ROUTER(context, endpoint):
    sender_sock_type = zmq.ROUTER
    receiver_thread = threading.Thread(target=receive_in_loop, args=('127.0.0.1', 5555, zmq.ROUTER))
    receiver_thread.start()
    sender = context.socket(sender_sock_type)
    sender.setsockopt(zmq.ROUTER_MANDATORY, 1)  # instead of silently dropping unroutable messages, throw an exception
    sender.connect(endpoint)
    msg = sender.recv_multipart()
    log_sender.info("Got reply: %s", msg)
    sender.send_multipart([msg[0], "test"])  # without address the message is dropped
    log_sender.info("Sent message")
    time.sleep(0.5)
    return receiver_thread


def main():
    context = zmq.Context()
    endpoint = "tcp://127.0.0.1:5555"

    receiver_thread = test_REQ(context, endpoint)
    receiver_thread.join()
    receiver_thread = test_DEALER(context, endpoint)
    receiver_thread.join()
    receiver_thread = test_ROUTER(context, endpoint)
    receiver_thread.join()

    context.destroy(linger=1)


if __name__ == "__main__":
    main()
