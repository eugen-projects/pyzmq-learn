import logging
import zmq

logging.basicConfig(level=logging.INFO, format="%(name)s: %(asctime)s: %(levelname)s: %(message)s")
log_server = logging.getLogger(name="SERVER")
log_client = logging.getLogger(name="CLIENT")

print("Current libzmq version is %s" % zmq.zmq_version())  # ZMQ version (4.0.5)
print("Current  pyzmq version is %s" % zmq.__version__)  # python package version (14.4.1)


def simple():
    context = zmq.Context.instance()

    #(+)  python  54948 ezaicanu    3u  0000    0,9        0    7451 anon_inode

    server = context.socket(zmq.REP)

    #(+) python  54948 ezaicanu    4u  0000    0,9        0    7451 anon_inode
    #(+) python  54948 ezaicanu    5u  0000    0,9        0    7451 anon_inode
    #(+) python  54948 ezaicanu    6u  0000    0,9        0    7451 anon_inode
    #(+) python  54948 ezaicanu    7u  0000    0,9        0    7451 anon_inode
    #(+) python  54948 ezaicanu    8u  0000    0,9        0    7451 anon_inode

    #(+) 3    Thread 0x7fd9a9a81700 (LWP 57633) "python" 0x00007fd9ad0faa93 in epoll_wait () from /lib/x86_64-linux-gnu/libc.so.6
    #(+) 2    Thread 0x7fd9a9280700 (LWP 57634) "python" 0x00007fd9ad0faa93 in epoll_wait () from /lib/x86_64-linux-gnu/libc.so.6


    r = server.bind("tcp://*:5555")

    #(+) python  54948 ezaicanu    9u  IPv4 592051      0t0     TCP *:5555 (LISTEN)

    log_server.debug("bind returned: %s", r)

    client = context.socket(zmq.REQ)

    #(+) python  54948 ezaicanu   10u  0000    0,9        0    7451 anon_inode

    r = client.connect("tcp://localhost:5555")

    #(+) python  54948 ezaicanu   11u  IPv4 615800      0t0     TCP localhost:58087->localhost:5555 (ESTABLISHED)
    #(+) python  54948 ezaicanu   12u  IPv4 615801      0t0     TCP localhost:5555->localhost:58087 (ESTABLISHED)

    log_client.debug("connect returned: %s", r)

    for i in range(2):  # ensure it is repeatable
        client_message = "World%d" % i
        r = client.send(client_message)
        log_client.debug("send returned: %s", r)
        log_client.info("sent: '%s'", client_message)
        r = server.recv()
        log_server.debug("recv returned : %s", r)
        log_server.info("Received '%s'", r)
        server_message = "ack%d" % i
        r = server.send(server_message)
        log_server.debug("send returned: %s", r)
        log_server.info("sent: '%s'", server_message)
        r = client.recv()
        log_client.debug("recv returned: %s", r)
        log_client.info("Received '%s'", r)

    server.close()

    #(-) python  54948 ezaicanu    8u  0000    0,9        0    7451 anon_inode
    #(-) python  54948 ezaicanu    9u  IPv4 592051      0t0     TCP *:5555 (LISTEN)
    #(-) python  54948 ezaicanu   11u  IPv4 615800      0t0     TCP localhost:58087->localhost:5555 (ESTABLISHED)
    #(-) python  54948 ezaicanu   12u  IPv4 615801      0t0     TCP localhost:5555->localhost:58087 (ESTABLISHED)

    client.close()

    #(-) python  54948 ezaicanu   10u  0000    0,9        0    7451 anon_inode

    # automatically closes the sockets setting first a small LINGER option.
    context.destroy()  # kills file handles (only 0,1,2 stay) even if sockets where not closed and a message was sent


    #(-) python  54948 ezaicanu    3u  0000    0,9        0    7451 anon_inode
    #(-) python  54948 ezaicanu    4u  0000    0,9        0    7451 anon_inode
    #(-) python  54948 ezaicanu    5u  0000    0,9        0    7451 anon_inode
    #(-) python  54948 ezaicanu    6u  0000    0,9        0    7451 anon_inode
    #(-) python  54948 ezaicanu    7u  0000    0,9        0    7451 anon_inode

    #(-) [Thread 0x7fd9a9a81700 (LWP 57633) exited]
    #(-) [Thread 0x7fd9a9280700 (LWP 57634) exited]

if __name__ == "__main__":
    simple()