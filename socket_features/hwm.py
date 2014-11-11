import logging
import signal
import threading
import zmq


logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(asctime)s: %(levelname)s: %(message)s")
log_sender = logging.getLogger(name="SENDER")
log_receiver = logging.getLogger(name="RECEIVER")
log_common = logging.getLogger(name="Helper")


def test_blocking_on_reaching_sndhwm(context, sock_type):
    """
    Works as expected but note that there is no peer bound to that address so the messages stay in the input queue
    """
    log_common.info("Testing blocking on reaching send HWM")
    context = zmq.Context()
    socket = context.socket(sock_type)
    socket.setsockopt(zmq.SNDHWM, 5)
    log_sender.info("Set sndhwm to %d", socket.sndhwm)
    socket.connect('tcp://127.0.0.1:5555')

    out_msgs_queued = 0

    while True:
        try:
            socket.send("block")
            out_msgs_queued += 1
            log_sender.info("Queued %d messages so far", out_msgs_queued)
        except zmq.ZMQError:
            log_common.info("Terminating the loop on exception", exc_info=True)
            socket.close()
            break


def saturate_receiver_threads(context, sock_type, endpoint, total_msgs):
    def start_sender(context, sock_type, endpoint, msg):
        sender = context.socket(sock_type)
        sender.connect(endpoint)
        try:
            sender.send(str(msg))
            log_sender.info("Sent: %s", msg)
            msg = sender.recv()  # this blocks in a C call and the signal is never delivered to the main thread
            log_sender.info("Recv: %s", msg)
        except zmq.ZMQError:
            pass
        finally:
            sender.close()

    threads = []
    for i in range(total_msgs):
        th = threading.Thread(target=start_sender, args=(context, sock_type, endpoint, i+1))
        th.setDaemon(True)
        th.start()
        threads.append(th)
    return threads


def saturate_receiver_no_threads(context, sock_type, endpoint, total_msgs):
    senders = []
    for i in range(total_msgs):
        sender = context.socket(sock_type)
        sender.connect(endpoint)
        msg = str(i+1)
        sender.send(msg)
        log_sender.info("Sent: %s", msg)
        senders.append(sender)
    poller = zmq.Poller()
    for sock in senders:
        poller.register(sock, zmq.POLLIN)

    while True:
        try:
            poller.poll(timeout=1)
        except zmq.Again:
            log_common.info("Timeout passed")
        except zmq.ZMQError as e:
            log_common.info("Got error %d - %s", e.errno, e.strerror)
            for sock in senders:
                poller.unregister(sock)
                sock.close()
            break


def test_blocking_on_reaching_rcvhwm(context, sock_type_receiver, sock_type_sender):
    """
    RCVHWM doesn't work.

    Perhaps the messages are actually sent and the input queue for the sender is emptied and the messages are queued
    in output of the receiver. But then why it doesn't block after RCVHVM_LIMIT messages ???
    """
    log_common.info("Testing blocking on reaching rcvhwm HWM")
    socket = context.socket(sock_type_receiver)
    RCVHVM_LIMIT = 5
    socket.setsockopt(zmq.RCVHWM, RCVHVM_LIMIT)
    log_receiver.info("Set rcvhwm to %d", socket.rcvhwm)
    endpoint_receiver = "tcp://127.0.0.1:5555"
    socket.bind(endpoint_receiver)
    saturate_receiver_no_threads(context, sock_type_sender, endpoint_receiver, RCVHVM_LIMIT*2 + 3)


def main():
    def signal_handler(signum, frame):
        log_common.info("Interrupting test app...")
        context.destroy(linger=1)  # without 'linger' blocks indefinitely

    signal.signal(signal.SIGINT, signal_handler)
    #context = zmq.Context()
    #test_blocking_on_reaching_sndhwm(context, zmq.DEALER)
    context = zmq.Context()
    test_blocking_on_reaching_rcvhwm(context, zmq.REP, zmq.REQ)

if __name__ == "__main__":
    main()
