import time
import zmq


def cleanup(sockets, context):
    for socket in sockets:
        socket.close()
    context.destroy()


def rep_multiple_reqs():
    context = zmq.Context.instance()
    requesters = []
    server = context.socket(zmq.REP)
    server.set_hwm(2) # set to 1 and server discards messages
    nr_requesters = 3
    port = 5005
    endpoint = "tcp://127.0.0.1:%s" % port

    server.bind(endpoint)
    for i in range(0, nr_requesters):
        requester = context.socket(zmq.REQ)
        requester.connect(endpoint)
        requesters.append(requester)

    for i in range(len(requesters)):
        requester_id = i + port
        print 'requester %d sends: %d' % (requester_id, requester_id)
        requesters[i].send(str(requester_id))
        time.sleep(0.05)

    for i in range(len(requesters)):
        reply = server.recv(zmq.NOBLOCK)
        print "server got: %s" % reply
        print "server sends thanks"
        server.send("thanks: %s" % reply)
        time.sleep(0.05)

    for i in range(len(requesters)):
        requester_id = i + port
        try:
            reply = requesters[i].recv(zmq.NOBLOCK)
            print "requester %d got: %s" % (requester_id, reply)
        except zmq.Again as eagain:
            print "requester %d got %s" % (requester_id, eagain)
        except zmq.ZMQError as zmqe:
            print "requester %d invalid state" % (requester_id, zmqe)

    cleanup(requesters + [server], context)


def req_multiple_rep():
    context = zmq.Context.instance()
    servers = []
    requester = context.socket(zmq.REQ)
    #dealer.setsockopt(zmq.IDENTITY, b"smooth-dealer:")
    requester.set_hwm(1)
    ports = range(6005, 6008)
    for port in ports:
        endpoint = "tcp://127.0.0.1:%s" % port
        server = context.socket(zmq.REP)
        server.bind(endpoint)
        servers.append(server)
        requester.connect(endpoint)

    for port in ports:
        print 'requester sends: %s' % port
        requester.send(str(port))
        time.sleep(0.05)
        for i in range(len(servers)):
            server_id = i+ports[0]
            try:
                reply = servers[i].recv(zmq.NOBLOCK)
                print "server %d got: %s" % (server_id, reply)
                print "server %d sends thanks" % server_id
                servers[i].send("thanks %d" % server_id)
                time.sleep(0.05)
                reply = requester.recv()
                print "requester got: %s" % reply
            except zmq.Again as eagain:
                print "server at %d got %s" % (server_id, eagain)
            except zmq.ZMQError as zmqe:
                print "server at %d already received message" % server_id

    cleanup([requester] + servers, context)


def dealer_rep():
    context = zmq.Context.instance()
    servers = []
    dealer = context.socket(zmq.DEALER)
    #dealer.setsockopt(zmq.IDENTITY, b"smooth-dealer:")
    dealer.set_hwm(1) # note that it doesn't block
    ports = range(6005, 6008)
    for port in ports:
        endpoint = "tcp://127.0.0.1:%s" % port
        server = context.socket(zmq.REP)
        server.bind(endpoint)
        servers.append(server)
        dealer.connect(endpoint)

    for port in ports:
        for inc in range(0, 20, 10):
            print 'dealer sends: %s' % (port + inc,)
            dealer.send("", zmq.SNDMORE)
            dealer.send(str(port + inc))
        time.sleep(0.05)
        for i in range(len(servers)):
            server_id = i+ports[0]
            try:
                reply = servers[i].recv(zmq.NOBLOCK)
                print "%d: %s" % (server_id, reply)
            except zmq.Again as eagain:
                print "server at %d got %s" % (server_id, eagain)
            except zmq.ZMQError as zmqe:
                print "server at %d already received a message" % server_id

    cleanup(servers + [dealer], context)


def router_receive_from_multiple_dealers():
    # for some reason not all messages are delivered...
    context = zmq.Context.instance()
    dealers = []
    router = context.socket(zmq.ROUTER)
    dealer_ids = range(5005, 5008)
    router.bind("tcp://127.0.0.1:%d" % dealer_ids[0])
    for dealer_id in dealer_ids:
        dealer = context.socket(zmq.DEALER)
        dealer.setsockopt(zmq.IDENTITY, str(dealer_id))  # must be present to identify the router
        dealer.connect("tcp://127.0.0.1:%d" % dealer_ids[0])
        dealers.append(dealer)

    # each dealer sends one message
    msgs_sent = 0
    for dealer in dealers:
        for inc in range(0, 20, 10):
            dealer_id = int(dealer.getsockopt(zmq.IDENTITY))
            print 'dealer sends: %s' % ([str(dealer_id), str(dealer_id + inc)])
            dealer.send_multipart([dealer.getsockopt(zmq.IDENTITY), str(dealer_id + inc)])  # must send the receiver id first
            #print 'dealer sends: %s' % str(dealer_id + inc)
            #dealer.send(str(dealer_id + inc))  # must send the receiver id first
            msgs_sent += 1
        time.sleep(0.05)

    while True:
        try:
            reply = router.recv(zmq.NOBLOCK)
            print 'router received: %s' % reply
        except zmq.Again as eagain:
            break

    cleanup(dealers +[router], context)


def router_send_to_multiple_dealers():
    # for some reason not all messages are delivered...
    context = zmq.Context.instance()
    dealers = []
    router = context.socket(zmq.ROUTER)
    dealer_ids = range(5005, 5006)
    router.bind("tcp://127.0.0.1:%d" % dealer_ids[0])
    for dealer_id in dealer_ids:
        dealer = context.socket(zmq.DEALER)
        dealer.setsockopt(zmq.IDENTITY, str(dealer_id))  # must be present to identify the router
        dealer.connect("tcp://127.0.0.1:%d" % dealer_ids[0])
        dealers.append(dealer)

    # router sends 6 messages
    for dealer_id in dealer_ids:
        for inc in range(0, 30, 10):
            print 'router sends: %s' % (dealer_id + inc,)
            router.send_multipart([str(dealer_id), str(dealer_id + inc)])  # must send the receiver id first
        time.sleep(0.05)
        for dealer_id, dealer in zip(dealer_ids, dealers):
            try:
                reply = dealer.recv(zmq.NOBLOCK)  # the dealer only receives the payload
                print "dealer at %d got: %s" % (dealer_id, reply)
            except zmq.Again as eagain:
                print "error: dealer %d: %s" % (dealer_id, eagain)

    END_MSG = "%END%"
    # router sends final messages
    for dealer_id in dealer_ids:
        print 'router sends end message to %s' % (dealer_id,)
        router.send_multipart([str(dealer_id), END_MSG])

    # get remaining messages
    for dealer, dealer_id in zip(dealers, dealer_ids):
        while True:
            try:
                reply = dealer.recv(zmq.NOBLOCK)  # the dealer only receives the payload
                print "dealer at %d got: %s" % (dealer_id, reply)
                if reply == END_MSG:
                    break
            except zmq.Again as eagain:
                print "error: dealer %d: %s" % (dealer_id, eagain)

    cleanup(dealers + [router], context)


rep_multiple_reqs()
#req_multiple_rep()
#dealer_rep()
#router_receive_from_multiple_dealers()
#router_send_to_multiple_dealers()