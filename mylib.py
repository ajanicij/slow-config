import random
import time

def init():
    print 'mylib.init'
    random.seed()

def readConfig():
    print 'mylib.readConfig...'
    t = random.randint(0, 30)
    print '   sleep(', t, ')'
    time.sleep(t)
    print 'mylib.readConfig done'

def calc(x):
    print 'mylib.calc(', x, ')'
    return x + 1

def uninit():
    print 'mylib.uninit'
