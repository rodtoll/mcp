import sys, time, mcp
from daemon import Daemon
import traceback

class MyDaemon(Daemon):
	def run(self):
            while True:
                try:
                    mcp.daemon_main(self)
                except:
                    sys.stderr.write( traceback.format_exc()+"\n")
                    sys.stderr.write( "Crashed, waiting and then restarting\n")
                    time.sleep(60)

if __name__ == "__main__":
	daemon = MyDaemon('/home/root/mcp/mcp.pid')
	if len(sys.argv) == 2:
		if 'start' == sys.argv[1]:
			daemon.start()
		elif 'stop' == sys.argv[1]:
			daemon.stop()
		elif 'restart' == sys.argv[1]:
			daemon.restart()
		else:
			print "Unknown command"
			sys.exit(2)
		sys.exit(0)
	else:
		print "usage: %s start|stop|restart" % sys.argv[0]
		sys.exit(2)

