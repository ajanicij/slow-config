slow-config
-----------

Here's a semi-realistic problem I set out to solve using ZeroMQ. Somebody
thought that a certain type of distributed computing problem would not be
easy to solve using conventional methods of interprocess communications.
I thought that this would be a good showcase of how much easier ZeroMQ
makes distributed computing. That got me wondering how I would solve it
using ZeroMQ, and here it is. I am sure 5 years from now my solution would
be very different and hopefully more elegant, but this reflects my level
now. So here goes...

We are licensing library mylib from company C. mylib has the following
functionality:

 - init() - initialize
 - readConfig() - read and process configuration
 - int calc(int x) - take input value x, process it somehow based on
                     the configuration, and return result
 - uninit() - uninitialize

Functions init, calc and uninit are fast, but readConfig can take up to
30 seconds.

We are writing a program prog that uses mylib. prog has a user interface,
can run the whole day. We know that the configuration for mylib can be
updated at any time, so we need to periodically call readConfig. mylib
is written in such a way that init, readConfig and calc have to be run
in the same thread, or else mylib will crash and bring down the process
it is running in.

Since prog is user-facing, it cannot wait for readConfig because to the
user that would feel like the program has hung; we would rather accept
that calling calc can fail because it is done while readConfig is
processing a new configuration file.

How do we do this? Obviously, mylib has to be run in a separate thread
or even separate process from prog, because we don't want to keep prog
waiting while readConfig is running. So this is a problem of
implementing communication between the process in which prog is running
and the process in which mylib is called.

We have a task to design this communication in Python (C would work too,
but Python programs can be modified more quickly, so we can make more
experiments). The resulting code will be one Python module that is
used by prog and one Python program that will use mylib and run in a
separate process.

To make things more concrete, we will make a proxy module mylib_proxy.py
that exports functions init, uninit and calc (but not readConfig).
Function calc can fail, if mylib is in readConfig.

The solution turns out to be simpler than I expected. ZeroMQ makes it
easy to communicate between processes. I use pyzmq library.

First, these files make up the solution:
 - mylib.py - The library that we start with. Two most interesting functions
              are readConfig(), that can take up to 30 seconds, and calc(x),
              that does a 'calculation' and returns x+1.
 - mylib_proxy.py - Proxy library that is to be used from program prog on the
                    client side. It imports zmq module and exports three
                    functions: init() initializes the ZeroMQ context,
                    creates DEALER socket, connects it and sends 'INIT'
                    command; calc(x) sends a 'CALC' message and returns the
                    response; and uninit() sends 'UNINIT' message.
 - mylib_run.py - Program that 'drives' the execution of mylib functions. It
                  receives commands through a DEALER socket.
 - service.py - Program that sits between prog and mylib_run.py.

Of these, service.py is the most interesting for solving our problem. How does
it work?

Let's first analyze how calling function calc works. Open three shell windows.
In window 1, run python REPL and import mylib_proxy. In window 2, run
python service.py. In window 3, run python mylib_run.py.

1. In window 1, type mylib_proxy.init(). It sends 'INIT' message to service.py
   running in window 2.
2. service.py forwards message to mylib_run.py in window 3.
3. mylib_run.py receives 'INIT' and calls mylib.init().
4. In window 1, type mylib_proxy.calc(5). It sends message ['CALC', '5'] to
   service.py (in other words, it sends a multipart message with the first
   part being the string 'CALC' and the second part the string '5').
5. service.py forwards the message to mylib_proxy.py.
6. mylib_proxy.py receives message ['CALC', '5'], calls mylib.calc(5), gets
   results 6, and sends message ['CALC-RESULT', '6'] to service.py.
7. service.py forwards the message to window 1.
8. In window 1, function mylib_proxy.calc() running in Python REPL receives
   the message ['CALC_RESULT', '6'] and writes in to the console.

This is the successful case, when we call calc() and mylib_run.py is not
executin mylib.readConfig() at the same moment. Now let's see what happens
when mylib.readConfig() gets called and while it is being executed we want
to call calc(x).

1. In window 3, mylib_proxy.py, after 10 seconds of inactivity timeout occurs
   and mylib_proxy.py sends message 'TIMEOUT' to service.py. After that,
   mylib_proxy.py does nothing else and simply goes back to polling the
   socket.
2. In window 2, service.py receives message 'TIMEOUT'. It sets variable
   waiting to True and sends message 'READCONFIG' back to mylib_proxy.py,
   telling it to call readConfig().
3. mylib_proxy.py receives message 'READCONFIG'. It calls mylib.readConfig(),
   which will run for a random time between 0 and 30 seconds.
4. While mylib.readConfig() is being run, in window 1 execute
   mylib_proxy.calc(5).
5. service.py receives message ['CALC', '5'] just like before, but now
   variable waiting has the value True. service.py immediately sends message
   'CALC-FAIL' back to mylib_proxy.py.
6. mylib_proxy.py receives message 'CALC-FAIL', writes it to console and
   returns.
7. When the sleep() in mylib.readConfig() is over, mylib_proxy.py sends
   message 'READCONFIG-DONE' to service.py.
8. service.py receives 'READCONFIG-DONE' and sets waiting to False.

So, the whole smarts is in service.py. It keeps the state in the global
variable waiting. When this variable is True, it rejects messages 'CALC' from
the mylib_proxy.py side and responds with 'CALC-FAIL'. When this variable is
False, it forward messages 'CALC' to mylib_run.py.

Another essential part of this design is that mylib_run.py doesn't call
readConfig() on its own, but only sends message 'TIMEOUT' to service.py, which
in turn sets waiting to True and sends message 'READCONFIG' back to
mylib_run.py.

Notice that we are using socket type PAIR for all sockets. That is because
mylib_proxy.py and service.py form a pair on port 6000 and service.py and
mylib_run.py form a pair on port 6002. Other types of sockets would also
work (e.g. DEALER-DEALER), but PAIR guarantees the semantics we want.
