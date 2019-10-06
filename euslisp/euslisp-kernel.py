from ipykernel.kernelbase import Kernel
from pexpect import replwrap, EOF
from subprocess import check_output

import re
import signal

crlf_pat = re.compile(r'[\r\n]+')

class myREPLWrapper(replwrap.REPLWrapper):
    def _expect_prompt(self, timeout=-1, async=False):
        return self.child.expect(self.prompt, #self.continuation_prompt],
                                       timeout=timeout)

def flatten_s_exp(s_exps):
    inspect_str = ' ' + re.sub(r'\n', ' ', s_exps) # make input command one-line
    paren_count = [0, 0] #current and previous (to prevent from counting \n s)
    idcs = [0] #where the list ends
    if not '(' in s_exps:
        return s_exps

    for i in range(1, len(inspect_str)):
        if inspect_str[i] is "(":
            paren_count[0] += 1
        if inspect_str[i] is ")":
            paren_count[0] -= 1

        if paren_count[0] == 0 and paren_count[1] != 0:
            idcs.append(i)

        paren_count[1] = paren_count[0]

    strs = ""

    if paren_count[0] != 0 :
        raise ValueError("Check the parentheses.")

    for i in range(1,len(idcs)):
        strs += inspect_str[1:][idcs[i-1]:idcs[i]] + "\n"

    return strs[:-1]


class EuslispKernel(Kernel):
    implementation = 'euslisp_kernel'
    implementation_version = '0.0.1'

    language_info = {'name': 'euslisp',
                     'codemirror_mode': 'common-lisp',
                     'mimetype': 'text/plain',
                     'file_extension': '.l'}

    _language_version = '9.26'


    @property
    def language_version(self):
        if self._language_version is None:
            self._language_version = check_output(['sml', '']).decode('utf-8')
        return self._language_version

    @property
    def banner(self):
        return u'Simple EusLisp Kernel (%s)' % self.language_version

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self._start_euslisp()

    def _start_euslisp(self):
        sig = signal.signal(signal.SIGINT, signal.SIG_DFL)
        try:
            self.euslispwrapper = myREPLWrapper("irteusgl", '[0-9]*\.(E[0-9]*-|B[0-9]*-|)irteusgl\$\ ', None)
        finally:
            signal.signal(signal.SIGINT, sig)

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        code = crlf_pat.sub(' ', code.strip())
        if not code:
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        interrupted = False
        try:
            output = self.euslispwrapper.run_command(flatten_s_exp(code), timeout=None)
        except KeyboardInterrupt:
            self.euslispwrapper.child.sendintr()
            interrupted = True
            self.euslispwrapper._expect_prompt()
            output = self.euslispwrapper.child.before
        except EOF:
            output = self.euslispwrapper.child.before + 'Restarting irteusgl'
            self._start_euslisp()

        if not silent:
            # Send standard output
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)

        if interrupted:
            return {'status': 'abort', 'execution_count': self.execution_count}

        return {'status': 'ok', 'execution_count': self.execution_count,
                'payload': [], 'user_expressions': {}}

# ===== MAIN =====
if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=EuslispKernel)
