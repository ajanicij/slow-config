import zmq
import mylib

def index(str, n):
    try:
        return str[n]
    except:
        return ''

ctx = zmq.Context()

dealer = ctx.socket(zmq.PAIR)
print 'Created worker socket'
dealer.connect('tcp://localhost:6002')

poller = zmq.Poller()
poller.register(dealer, zmq.POLLIN)

while True:
    events = poller.poll(timeout=10000)
    print 'After poll: events=', repr(events)
    print '  len(events) is', len(events)
    if len(events) == 0:
        # timeout
        print 'Timeout'
        dealer.send('TIMEOUT')
    else:
        for t in events:
            (socket, event) = t
            print 'socket=', repr(socket)
            print 'event=', repr(event)
            if (socket == dealer) and (zmq.POLLIN != 0):
                    msg = dealer.recv_multipart()
                    cmd = index(msg, 0)
                    arg = index(msg, 1)
                    rest = msg[2:]
                    print 'From broker received message %s' % repr(msg)
                    if cmd == 'CALC':
                        n = int(arg)
                        res = mylib.calc(n)
                        dealer.send_multipart(['CALC-RESULT', repr(res)])
                    elif cmd == 'UNINIT':
                        print 'Received UNINIT'
                        mylib.uninit()
                    elif cmd == 'INIT':
                        print 'Received INIT'
                        mylib.init()
                    elif cmd == 'READCONFIG':
                        print 'Received READCONFIG'
                        mylib.readConfig()
                        dealer.send('READCONFIG-DONE')

# end of file
