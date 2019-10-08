from ipykernel.kernelbase import Kernel
from pexpect import replwrap, EOF
from subprocess import check_output
import re
import signal

crlf_pat = re.compile(r'[\r\n]+')

### get euslisp version ###
def getVersion():
    import pexpect
    import re

    p = pexpect.spawn("irteusgl")

    while True:
        try:
            p.expect('[0-9]*\.(E[0-9]*-|B[0-9]*-|)irteusgl\$\ ')
            p.sendline("(lisp-implementation-version)")
            p.expect('[0-9]*\.(E[0-9]*-|B[0-9]*-|)irteusgl\$\ ')
            inspect_str = p.before.decode(encoding="UTF-8")
            p.sendline("(exit)")
        except pexpect.EOF:
            break

    match = re.search(r'((?i)euslisp)\ [0-9]*(\.|)[0-9]*', inspect_str).group()
    return match[8:] # 8 = length of "euslisp "

### define wrapper ###
class myREPLWrapper(replwrap.REPLWrapper):
    def _expect_prompt(self, timeout=-1, async=False):
        return self.child.expect(self.prompt, timeout=timeout)

    def run_command(self, command, response_sender, timeout=-1, async=False):
        # Split up multiline commands and feed them in bit-by-bit
        cmdlines = command.splitlines()
        # splitlines ignores trailing newlines - add it back in manually
        if command.endswith('\n'):
            cmdlines.append('')
        if not cmdlines:
            raise ValueError("No command was given")
        # response_sender("command: {}".format(command))
        # response_sender("cmdlines: {}".format(cmdlines))

        prompt_res = 0
        # self.child.sendline(cmdlines[0])
        for line in cmdlines:
            # self._expect_prompt(timeout=timeout)
            self.child.sendline(line)
            while True:
                # read each line
                prompt_res = self.child.expect([self.prompt, '\n'], timeout=None)
                # show each line on the notebook
                response_sender(u'' + self.child.before)
                if prompt_res == 1:
                    if self.child.before != '':
                        response_sender('\n')
                else: # if find "irteusgl$", go to next command
                    break
        return 0

### make input command one-line ###
def flatten_s_exp(s_exps):
    inspect_str = ' ' + re.sub(r'\n', ' ', s_exps)
    paren_count = [0, 0] #current and previous (to prevent counting continuous \n)
    idcs = [0] #where the list ends
    if not '(' in s_exps:
        return s_exps # e.g., 'exit' -> '(exit)'

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

# def bk_count(s):
#     bras = [i for i in range(len(s)) if s[i] == '(']
#     kets = [i for i in range(len(s)) if s[i] == ')']
#     return len(bras) - len(kets)
#
# def flatten_s_exp(s_exps):
#     s_lines = s_exps.splitlines()
#     strs = ""
#     cntr = 0
#     for s in s_lines:
#         strs += s + ' '
#         cntr += bk_count(s)
#         if cntr == 0:
#             strs += '\n'
#     if cntr != 0:
#         raise ValueError("Check the parentheses.")
#     return strs[:-1]

### Kernel Main ###
class EuslispKernel(Kernel):
    implementation = 'euslisp_kernel'
    implementation_version = '0.0.1'

    language_info = {'name': 'euslisp',
                     'codemirror_mode': 'commonlisp',
                     'mimetype': 'text/plain',
                     'file_extension': '.l'}

    _language_version = None


    @property
    def language_version(self):
        if self._language_version is None:
            self._language_version = getVersion()
        return self._language_version

    @property
    def banner(self):
        return u'Eusropa ― EusLisp Kernel for Jupyter (%s)' % self.language_version

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self._start_euslisp()

    def _start_euslisp(self):
        sig = signal.signal(signal.SIGINT, signal.SIG_DFL)
        try:
            self.euslispwrapper = myREPLWrapper("irteusgl", '[0-9]*\.(E[0-9]*-|B[0-9]*-|)irteusgl\$\ ', None)
        finally:
            signal.signal(signal.SIGINT, sig)

    def response_sender(self, output):
        stream_content = {'name': 'stdout', 'text': output}
        self.send_response(self.iopub_socket, 'stream', stream_content)

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        # code = crlf_pat.sub(' ', code.strip())
        if not code:
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        interrupted = False
        output = ''

        # self.response_sender("code: {}".format(code))
        try:
            self.euslispwrapper.run_command(flatten_s_exp(code), self.response_sender, timeout=None)
        except KeyboardInterrupt:
            self.euslispwrapper.child.sendintr()
            interrupted = True
            self.euslispwrapper._expect_prompt()
            output = self.euslispwrapper.child.before
        except EOF:
            output = self.euslispwrapper.child.before + 'Restarting irteusgl'
            self._start_euslisp()
        except ValueError as e:
            interrupted = True
            output = '\033[1m\033[91m' + 'ValueError:'
            for arg in e.args:
                output += '\n' + arg
            output += '\033[0m\033[0m'

        if not silent:
            # Send standard output
            # stream_content = {'name': 'stdout', 'text': output}
            # self.send_response(self.iopub_socket, 'stream', stream_content)
            self.response_sender(output)

        if interrupted:
            return {'status': 'abort', 'execution_count': self.execution_count}

        return {'status': 'ok', 'execution_count': self.execution_count,
                'payload': [], 'user_expressions': {}}

# ===== MAIN =====
if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=EuslispKernel)
