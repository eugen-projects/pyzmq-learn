import logging
import threading
import time
import zmq


logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(asctime)s: %(levelname)s: %(message)s")
log_pub = logging.getLogger(name="PUBLISHER")
log_sub = logging.getLogger(name="SUBSCRIBER")
log_common = logging.getLogger(name="Helper")


def create_sub(context, publisher_url, topic_name):
    subscriber = context.socket(zmq.SUB)
    subscriber.setsockopt(zmq.SUBSCRIBE, topic_name)
    subscriber.connect(publisher_url)

    while True:
        try:
            msg = subscriber.recv_multipart()
            log_sub.info("%s got: %s", threading.current_thread().name, msg)
        except zmq.ZMQError:  # closing the publisher socket causes the subscribers to throw an exception in recv()
            subscriber.close()
            break


def main():
    context = zmq.Context.instance()
    publisher = context.socket(zmq.PUB)
    publisher.bind("tcp://*:5555")
    msg = ['A', 'This message will be lost']
    publisher.send_multipart(msg)
    log_pub.info("Sent: %s", msg)

    time.sleep(0.5)

    N_SUBS = 2
    subscriber_threads = []

    for i in range(N_SUBS):
        th = threading.Thread(target=create_sub, args=(context, "tcp://127.0.0.1:5555", "A"), name="Sub-%d" % (i+1))
        subscriber_threads.append(th)
        th.start()

    time.sleep(0.5)  # let the subscribers connect first

    msg = ['B', 'This message is filtered out']
    publisher.send_multipart(msg)
    log_pub.info("Sent: %s", msg)
    msg = ['A', 'This message should be received by all subscribers']
    publisher.send_multipart(msg)
    log_pub.info("Sent: %s", msg)
    msg = 'A message that also should be received by all subscribers'
    publisher.send(msg)  # matches by prefix
    log_pub.info("Sent: %s", msg)

    time.sleep(2)  # wait for subscribers to receive

    publisher.close()
    log_pub.info("Closed publisher socket")
    context.term()
    log_common.info("Terminated the context")
    [th.join() for th in subscriber_threads]
    log_common.info("All sockets were closed")

if __name__ == "__main__":
    main()
