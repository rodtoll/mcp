import time
import mcp
import logging
import os
import sys
import traceback

from daemon import runner

class App():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/home/root/mcp/mcp.stdout.log'
        self.stderr_path = '/home/root/mcp/mcp.stderr.log'
        self.pidfile_path =  '/home/root/mcp/mcp.pid'
        self.logfile_path = '/home/root/mcp/mcp.log'
        self.pidfile_timeout = 5

    def log_message(self,msg):
        self.logger.error(msg)

    def init_logger(self):
        self.logger = logging.getLogger("DaemonLog")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.handler = logging.FileHandler(self.logfile_path)
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)

    def run(self):
        self.init_logger()
        self.logger.error("Start")
        try:
            mcp.daemon_main(self.logger)
        except:
            tb = traceback.format_exc()
            self.logger.error("FAILED!!!!! "+tb)
        self.logger.error("Done")

app = App()
daemon_runner = runner.DaemonRunner(app)
daemon_runner.do_action()
