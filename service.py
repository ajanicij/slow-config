import zmq

def index(str, n):
    try:
        return str[n]
    except:
        return ''

ctx = zmq.Context()

client = ctx.socket(zmq.PAIR)
print 'Created client socket'
client.bind('tcp://*:6000')

worker = ctx.socket(zmq.PAIR)
print 'Created worker socket'
worker.bind('tcp://*:6002')

waiting = False

poller = zmq.Poller()
poller.register(client)
poller.register(worker)
while True:
    events = poller.poll()
    for t in events:
        (socket, event) = t
        if socket == client:
            if event & zmq.POLLIN != 0:
                msg = client.recv_multipart()
                cmd = index(msg, 0)
                arg = index(msg, 1)
                rest = msg[1:]
                print 'From client received message %s' % repr(msg)
                if cmd == 'CALC':
                    if waiting:
                        print 'Waiting for mylib to finish readConfig'
                        client.send('CALC-FAIL')
                    else:
                        num = index(msg, 2)
                        worker.send_multipart([cmd, arg])
        if socket == worker:
            if event & zmq.POLLIN != 0:
                msg = worker.recv_multipart()
                cmd = index(msg, 0)
                arg = index(msg, 1)
                rest = msg[1:]
                print 'From worker received message %s' % repr(msg)
                if cmd == 'TIMEOUT':
                    waiting = True
                    worker.send('READCONFIG')
                elif cmd == 'CALC-RESULT':
                    client.send_multipart([cmd, arg])
                elif cmd == 'READCONFIG-DONE':
                    waiting = False
                        

# end of file
