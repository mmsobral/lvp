import sys,re,subprocess,select
from .evaluator import Evaluator
import time

class Result:

  Expr = re.compile('^[\t ]*(.*)$', re.M|re.S|re.I)
  #Expr = re.compile('^[\t ]*(.*)$', re.S|re.I)

  def __init__(self, data):
    m = self.Expr.search(data)
    if m:
      data = m.groups()[0]
      self.data = self.__normalize__(data.strip())
      self.expr = self.__get__(self.data)
    else:
      raise ValueError

  def __get__(self, data):
    return re.compile('^[\t\n ]*(%s)$' % data, re.M | re.S | re.I)
    #return re.compile('^[\t\n ]*(%s)' % data, re.S | re.I)

  def __repr__(self):
    return self.data.replace(r'\s+', ' ')

  def check(self, data):
    data = data.strip()
    m = self.expr.match(data)
    if m:
      data = data[m.end()+1:]
      return data
    return None

  def __normalize__(self, data):
    data = map(re.escape, data.split())
    data = r'\s+'.join(data)
    return data

class ExactResult(Result):

  #Expr = re.compile('^[\t ]*"(.*?)"[ \n\t]*$', re.S)
  Expr = re.compile('^[\t ]*"(.*?)"[ \n\t]*$', re.M|re.S)

  def __get__(self, data):
    return re.compile('^[\t\n ]*(%s)$' % re.escape(data), re.M | re.S)
    #return re.compile('^[\t\n ]*(%s)' % re.escape(data), re.S)

  def __normalize__(self, data):
    return re.escape(data)

  def __repr__(self):
    return '"%s"' % self.data

class IntResult(Result):

  Expr = re.compile('^[\t ]*(([-+0-9]+[ \n\t]*)+)$')

  def __get__(self, data):
    r = data.strip().split()
    r = ' '.join(r)
    return Result.__get__(self, r)

class FloatResult(IntResult):

  #Expr = re.compile('^[\t ]*(([-+0-9.]+[ \n\t]*)+)$')
  Expr = re.compile(r'^[ ]*([-+]?\d*[.]+\d+[ ]*)$')

class RegexResult(ExactResult):

  Expr = re.compile(r'^[\t ]*/(.*?)/\s*$', re.M|re.S)
  #Expr = re.compile(r'^[\t ]*/(.*?)/\s*$', re.S)

  def __get__(self, data):
    return re.compile('^[\t\n ]*(%s)$' % data, re.M | re.S)
    #return re.compile('^[\t\n ]*(%s)' % data, re.S)

  def __repr__(self):
    return '/%s/' % self.data

class Reader:
  '''Reader: le e bufferiza chars de um arquivo'''

  MaxLine = 10240

  def __init__(self, fd):
    self.fd = fd
    self.data = ''

  def read(self, timeout):
      r,w,e = select.select([self.fd],[],[], timeout)
      if not r: 
        raise Exception('timeout')
      r = self.fd.read1(self.MaxLine)
      if not r:
        raise Exception('descritor fechado')
      #print('Reader:', r)
      try:
        r = r.decode('ascii')
      except UnicodeDecodeError:
        r = r.decode('utf8')
      self.data += r
      return self.data

  def flush(self, n):
    self.data = self.data[n:]

class Dialog:

  MaxLine = 10240

  def __init__(self, dial, timeout):
    self.dial = dial        
    if dial.timeout > 0 and dial.timeout < timeout: 
      self.timeout = dial.timeout
    else:
      self.timeout = timeout

  def __readsome__(self, fd, timeout):
    r,w,e = select.select([fd],[],[], timeout)
    if not r: return ''
    # talvez aqui por fd nonblock e ler uma linha
    # ou em check_output bufferizar o conteÃdo em excesso
    # ou fazer strip a cada etapa de verificaÃÃ£o de check_outpu
    r = fd.read1(self.MaxLine)
    try:
      r = r.decode('ascii')
    except UnicodeDecodeError:
      r = r.decode('utf8')
    return r

  def __check_output__(self, data):
    outp = self.dial.output
    if outp:
      resto = outp.check(data)
    else:
      resto = ''
    #print('check_output:', resto)
    #print('check:', data, type(outp))
    if resto == None: return False
    #print('check:', data, len(data))
    #return resto.strip() == ''
    n = len(data) - len(resto)
    return n

  def run1(self, proc):
    self.sent = ''
    self.rcvd = ''
    if self.dial.output != None: self.expected = repr(self.dial.output)
    else: self.expected = ''
    #print('run_dialog: tx=%s, rx=%s' % (self.dial.input,self.dial.output))
    if self.dial.input != None:
      inp = self.dial.input+'\n'
      self.sent += inp
      proc.stdin.write(inp.encode('ascii'))
      proc.stdin.flush()
    # se output for None, entao programa em avaliacao nada deve apresentar na saida
    # define um timeout pequeno para conferir se o programa apresenta algo na saida
    if self.dial.output == None:
      tout = 2
    else:
      tout = self.timeout
    r = ''
    ok = False
    while True:
        t0 = time.time()
        rout = self.__readsome__(proc.stdout, tout)
        #print('...', rout, len(rout))
        tout -= (time.time()-t0)
        # se ocorreu timeout ...
        if not rout: 
          # retorna verdadeiro se nada foi apresentado pelo programa
          # e output for None.
          return r == '' and self.dial.output == None
        r += rout
        self.rcvd += r
        ok = self.__check_output__(r)
        if ok: return True
        elif tout <= 0: 
          # se ocorreu timeout:
          # retorna verdadeiro se nada foi apresentado pelo programa
          # e output for None.
          return r == '' and self.dial.output == None

  def run(self, outfd, infd):
    self.sent = ''
    self.rcvd = ''
    if self.dial.output != None: self.expected = repr(self.dial.output)
    else: self.expected = ''
    print('run_dialog: tx=%s, rx=%s, timeout=%d' % (self.dial.input,self.expected, self.timeout))
    if self.dial.input != None:
      inp = self.dial.input+'\n'
      self.sent += inp
      outfd.write(inp.encode('ascii'))
      outfd.flush()
    # se output for None, entao programa em avaliacao nada deve apresentar na saida
    # define um timeout pequeno para conferir se o programa apresenta algo na saida
    if self.dial.output == None:
      tout = 2
    else:
      tout = self.timeout
    r = ''
    rout = ''
    ok = False
    while True:
        try:
          t0 = time.time()
          rout = infd.read(tout)
          print('...', rout, len(rout))
          tout -= (time.time()-t0)
        except Exception:
          # se ocorreu timeout ...
          # retorna verdadeiro se nada foi apresentado pelo programa
          # e output for None.
          self.rcvd = infd.data
          if infd.data == '': return self.dial.output == None
          elif rout == infd.data: return False
          rout = infd.data
        if self.dial.output != None: 
          ok = self.__check_output__(rout)
          print('... ok=%d', ok)
          if ok > 0:
            self.rcvd = rout[:ok]
            infd.flush(ok) 
            return True
          elif tout <= 0: 
            self.rcvd = rout
            # se ocorreu timeout:
            # retorna verdadeiro se nada foi apresentado pelo programa
            # e output for None.
            return False
        else:
          self.rcvd = rout
          return False  
    return True

  def run0(self, proc):
    self.sent = ''
    self.rcvd = ''
    self.expected = repr(self.dial.output)
    if self.dial.input != None:
      #print('run_dialog: tx=%s' % self.dial.input)
      inp = self.dial.input+'\n'
      self.sent += inp
      proc.stdin.write(inp.encode('ascii'))
      proc.stdin.flush()
    if self.dial.output != None:
      #data = self.__check_output__('0.00')
      #print('run_dialog: rx=', data, self.dial.output)
      r = ''
      tout = self.timeout
      ok = False
      while True:
        t0 = time.time()
        rout = self.__readsome__(proc.stdout, tout)
        tout -= (time.time()-t0)
        if not rout: 
          #print('...',ok,r, '-->',self.dial.output)
          return False
        r += rout
        self.rcvd += r
        ok = self.__check_output__(r)
        #print('===',ok,r, '-->',self.dial.output)
        if ok: return True
        elif tout <= 0: return False
    return True
    

class Case:

  ResultList = [ExactResult, IntResult, FloatResult, RegexResult, Result]
  MaxLine = 10240

  def __init__(self, name):
    self.name = name
    self.dialogs = []
    self.curr_dialog = 0
    self.reduction = 0
    self.info = ''
    self.parent = None

  def __eq__(self, o):
    if o != None: return self.name == o.name
    return False

  def set_parent(self, par):
    self.parent = par

  def set_reduction(self, reduc):
    if type(reduc) == type(int):
      if reduc > 100 or reduc < 0: return
    elif type(reduc) == type(float):
      if reduc > 1 or reduc < 0: return
    self.reduction = reduc

  def set_info(self, info):
    self.info = info

  def __get_input__(self, inp):
    return inp

  def __get_output__(self, outp):
    res = None
    if not outp: return outp
    #  return RegexResult(r'\s*$')
    for class_result in self.ResultList:
      try:
        res = class_result(outp)
        break
      except Exception as e:
        pass
    if not res:
      raise ValueError("invalid output: %s" % outp)
    return res

  def add_dialogs(self, l):
    for d in l:
      d.output = self.__get_output__(d.output)
      d.input = self.__get_input__(d.input)
    self.dialogs = l[:]

  def __get_data__(self, data, attr):
    l = map(lambda x: '%s=%s' % (attr, x), data)
    return '\n'.join(l)

  def get_hint_data(self):
    return self.dialogs[self.curr_dialog].hint

  def get_input_data(self):
    return self.dialogs[self.curr_dialog].input

  def get_output_data(self):
    return self.dialogs[self.curr_dialog].output

  def get_hint(self):
    return self.__get_data__(self.dialogs[self.curr_dialog].hint, 'hint')

  def get_input(self):
    return self.__get_data__(self.dialogs[self.curr_dialog].input, 'input')

  def get_output(self):
    return self.__get_data__(map(repr, self.dialogs[self.curr_dialog].output), 'output')

  def get_reduction(self):
    r = ''
    if self.reduction > 0:
      if type(self.reduction) == type(1.0):
        r = 'grade reduction=%d%%\n' % (int(100*self.reduction))
      else:
        r = 'grade reduction=%d\n' % self.reduction
    return r

  def __repr__(self):
    r = 'case=%s\n' % self.name
    r += self.get_input()
    r += self.get_output()
    r += self.get_hint()
    r += self.get_reduction()
    return r

  def run(self, prog, timeout):
    proc = subprocess.Popen(prog, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    self.curr_dialog = 0
    ok = True
    self.data_sent = ''
    self.data_rcvd = ''
    self.expected = ''
    #print(self.dialogs)
    infd = Reader(proc.stdout)
    while self.curr_dialog < len(self.dialogs):
      try:
        dial = Dialog(self.dialogs[self.curr_dialog], timeout)
        ok = dial.run(proc.stdin,infd)
        self.data_sent += dial.sent
        self.data_rcvd += dial.rcvd
        self.expected += dial.expected
        if not ok:
          break
      except BrokenPipeError:
        print('oopss')
        return False
      self.curr_dialog += 1
    try:
      proc.stdin.close()
      proc.stderr.close()
      proc.stdout.close()
      proc.kill()
    except:
      pass
    return ok

class DefaultEvaluator(Evaluator):

  def __init__(self, test, **args):
    Evaluator.__init__(self, **args)
    self.test = test
    if test.timeout: self.timeout = test.timeout
    self.cases = self.__load__(test.cases)
    self.status = False

  def compile(self):
    self.status = False
    try:
      build = self.test.build
      prog = ['make','-f',build]
    except AttributeError:
      try:
        arqs = self.test.files
      except AttributeError:
        arqs = self.__find_files__(['.cpp','.cc','.C'])
      #print(arqs)
      prog = ['g++', '-std=c++11', '-o', 'vpl_test', '-I.']
      prog += arqs
      prog.append('-lm')
      prog.append('-lutil')
    #status = subprocess.call(prog)
    status = self.__exec__(prog)
    self.status = (status == 0)
    if not self.status:
      raise Exception('compilation failed')
    return self.status


  def __load__(self, cases):
    r = []
    for c in cases:
      caso = Case(c.name)
      caso.add_dialogs(c.dialogs)
      try:
        caso.set_reduction(c.grade_reduction)
      except:
        pass
      caso.set_info(c.info)
      caso.set_parent(c.parent)
      r.append(caso)
    return r

  def __getcases__(self, parent=None):
    return filter(lambda caso: caso.parent == parent, self.cases)

  def __run__(self, prog):
    result = {}
    #subres = {}
    parents = [None]
    while parents:
      lpar = []
      for parent in parents:
        #print("parent:", parent)
        for caso in self.__getcases__(parent):
          #print("--caso:%s, parent=%s:" % (caso.name, caso.parent))
          succ = caso.run([prog], self.timeout)
          result[caso.name] = {'success': succ, 'info': caso.info, 'input':caso.data_sent,
                           'output':caso.data_rcvd, 'expected': caso.expected}
          if not succ:
            lpar.append(caso)
            #subres[caso.name] = caso.reduction
            result[caso.name]['text'] = caso.get_hint_data()
            result[caso.name]['reduction'] = caso.reduction
          #elif caso.parent: subres[caso.parent.name] -= caso.reduction
      parents = lpar
    #for name in subres:
    #  result[name]['reduction'] = min(subres[name], 0)
    return result

  def __run0__(self, prog):
    result = {}
    for caso in self.cases:
      succ = caso.run([prog], self.timeout)
      result[caso.name] = {'success': succ, 'info': caso.info, 'input':caso.data_sent,
                           'output':caso.data_rcvd, 'expected': caso.expected}
      if not succ:
        result[caso.name]['text'] = caso.get_hint_data()
        result[caso.name]['reduction'] = caso.reduction
    return result
#####################################################
def init(test, **args):
  fac = DefaultEvaluator(test, **args)
  return fac

