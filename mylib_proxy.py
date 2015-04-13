import zmq

ctx = None
dealer = None

def init():
    global dealer
    print 'mylib_proxy.init'
    ctx = zmq.Context()
    dealer = ctx.socket(zmq.PAIR)
    dealer.connect('tcp://localhost:6000')
    dealer.send('INIT')

def calc(x):
    global dealer
    print 'mylib_proxy.calc(', x, ')'
    dealer.send_multipart(['CALC', str(x)])
    response = dealer.recv_multipart()
    return response

def uninit():
    global dealer
    print 'mylib_proxy.uninit'
    dealer.send('UNINIT')

# end of file
