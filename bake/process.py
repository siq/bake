import os
import shlex
import subprocess
from threading import Thread
from time import time

class ProcessFailure(Exception):
    pass

class Process(object):
    def __init__(self, cmdline, environ=None, shell=False):
        self.process = None
        self.returncode = None
        self.shell = shell
        self.stderr = None
        self.stdout = None

        self.environ = dict(os.environ)
        if environ:
            self.environ.update(environ)

        self.cmdline = self._parse_cmdline(cmdline)

    def __call__(self, data=None, timeout=None, stream=None):
        def _thread():
            self.process = subprocess.Popen(
                self.cmdline,
                bufsize=0,
                env=self.environ,
                shell=self.shell,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            self.stdout, self.stderr = self.process.communicate(data)

        thread = Thread(target=_thread)
        thread.start()

        if stream:
            delta = time()
            while thread.isAlive():
                thread.join(1)
                stream.write('.')
                stream.flush()
                if timeout and (time() - delta) > timeout:
                    break

            stream.write('\n')
            stream.flush()
        else:
            thread.join(timeout)

        if thread.isAlive():
            self.process.terminate()
            thread.join()

        self.returncode = self.process.returncode
        return self.returncode

    def run(self, runtime, data=None, timeout=None):
        stream = None
        if runtime.verbose:
            stream = runtime.stream

        runtime.info('shell: %s' % ' '.join(self.cmdline))
        returncode = self(data, timeout, stream)

        if runtime.verbose:
            lines = []
            if self.stdout:
                lines.extend(self.stdout.strip().split('\n'))
            if self.stderr:
                lines.extend(self.stderr.strip().split('\n'))
            lines = '\n'.join('  %s' % line for line in lines)
            runtime.info(lines, True)

        if returncode != 0:
            raise ProcessFailure(returncode, self)

    def _parse_cmdline(self, cmdline):
        if isinstance(cmdline, basestring) and not self.shell:
            cmdline = shlex.split(cmdline)
        return cmdline
