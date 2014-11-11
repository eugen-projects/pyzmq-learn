import logging
import threading
import time
import zmq


logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(asctime)s: %(levelname)s: %(message)s")
log_pub = logging.getLogger(name="PUBLISHER")
log_sub = logging.getLogger(name="SUBSCRIBER")
log_common = logging.getLogger(name="Helper")


def create_sub(context, publisher_url, topic_name, publisher_sync_url, total_msgs):
    subscriber = context.socket(zmq.SUB)
    subscriber.setsockopt(zmq.SUBSCRIBE, topic_name)
    subscriber.connect(publisher_url)
    sub_id = threading.current_thread().name

    publisher_notify = context.socket(zmq.REQ)
    publisher_notify.connect(publisher_sync_url)
    publisher_notify.send(sub_id)
    publisher_notify.recv()

    received_msgs = 0

    while True:
        try:
            msg = subscriber.recv_multipart()
            log_sub.info("%s got: %s", sub_id, msg)
            received_msgs += 1
            if received_msgs >= total_msgs:
                subscriber.close()
                publisher_notify.send(sub_id)
                publisher_notify.recv()
                publisher_notify.close()
                break
        except zmq.ZMQError:  # closing the publisher socket causes the subscribers to throw an exception in recv()
            subscriber.close()
            break


def sync_with_subs(sync_sock, n_subs):
    for i in range(n_subs):
        sync_msg = sync_sock.recv()
        log_pub.info("Recv sync: %s", sync_msg)
        sync_sock.send("ack")


def main():
    context = zmq.Context.instance()
    publisher = context.socket(zmq.PUB)
    publisher.bind("tcp://*:5555")
    publisher_sync = context.socket(zmq.REP)
    publisher_sync.bind("tcp://*:5556")
    msg = ['A', 'This message will be lost']
    publisher.send_multipart(msg)
    log_pub.info("Sent: %s", msg)

    time.sleep(0.5)

    N_SUBS = 2
    subscriber_threads = []

    for i in range(N_SUBS):
        th = threading.Thread(target=create_sub, args=(context, "tcp://127.0.0.1:5555", "A", "tcp://127.0.0.1:5556", 2), name="Sub-%d" % (i+1))
        subscriber_threads.append(th)
        th.start()

    sync_with_subs(publisher_sync, N_SUBS)

    msg = ['B', 'This message is filtered out']
    publisher.send_multipart(msg)
    log_pub.info("Sent: %s", msg)
    msg = ['A', 'This message should be received by all subscribers']
    publisher.send_multipart(msg)
    log_pub.info("Sent: %s", msg)
    msg = 'A message that also should be received by all subscribers'
    publisher.send(msg)  # matches by prefix
    log_pub.info("Sent: %s", msg)

    sync_with_subs(publisher_sync, N_SUBS)

    publisher.close()
    publisher_sync.close()
    log_pub.info("Closed publisher sockets")
    context.term()
    log_common.info("Terminated the context")
    [th.join() for th in subscriber_threads]
    log_common.info("All sockets were closed")

if __name__ == "__main__":
    main()
