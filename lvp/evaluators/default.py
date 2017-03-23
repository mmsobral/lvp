import sys,regex as re,subprocess,select
from .evaluator import Evaluator
import time
import traceback

class Result:

  Expr = re.compile('^[\t ]*(.*)$', re.M|re.S|re.I)
  #Expr = re.compile('^[\t ]*(.*)$', re.S|re.I)

  def __init__(self, data):
    m = self.Expr.search(data)
    self.errpos = 0
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
    #print('check: data=%s, m=%s, expr=%s'%(data, m, self.data))
    #print(self.expr)
    if m:
      data = data[m.end()+1:]
      return data
    else:
      self.__partial_match__(data)
    return None


  def __partial_match__(self, data):
    n = len(data)
    self.errpos = 0
    while n > 1:
      m = self.expr.match(data[:self.errpos], partial=True)
      n1 = n //2
      n2 = n - n1
      n = max(n1, n2)
      if not m: 
        self.errpos -= n1
      elif not m.partial: break
      else: self.errpos += n1
    self.errpos -= 1

  def __partial_match0__(self, data):
    while self.errpos < len(data):
      m = self.expr.match(data[:self.errpos+1], partial=True)
      if not m: break
      if not m.partial: break
      self.errpos += 1

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
    return re.compile('^[\t\n ]*(%s)' % data, re.M | re.S)
    #return re.compile('^[\t\n ]*(%s)' % data, re.S)

  def __repr__(self):
    return '/%s/' % self.data

  def __normalize__(self, data):
    #data = map(re.escape, data.split())
    data = r'\s+'.join(data.split())
    return data

class AnyRegexResult(ExactResult):

  Expr = re.compile(r'^[\t ]*\|(.*?)\|\s*$', re.M|re.S)
  #Expr = re.compile(r'^[\t ]*/(.*?)/\s*$', re.S)

  def __get__(self, data):
    return re.compile('^[\t\n ]*(%s)' % data, re.M | re.S)
    #return re.compile('^[\t\n ]*(%s)' % data, re.S)

  def __repr__(self):
    return '|%s|' % self.orig

  def __normalize__(self, data):
    #data = map(re.escape, data.split())
    self.orig = data
    # possibilita virgulas dentro dos dados, mas com escape
    # nesse caso, deve-se precede-las com \
    # aqui se substitui a sequencia \, por  chr(0)
    data = data.replace(r'\,', chr(0))
    data = r'\s+'.join(data.split())
    data = data.split(',')
    r = list(map(lambda x: '(?=(^|.*?\s+)%s)'%x, data[:-1]))
    r.append('(^|.*?\s+)%s' % data[-1])
    # revertem-se os chr(0) para simples ,
    res = ''
    for x in r:
      if chr(0) in x: res.append(x.replace(chr(0), ','))
      else: res += x 
    return res

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

  def __check_output__(self, data):
    outp = self.dial.output
    print('check_output:', type(outp))
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

  def run(self, outfd, infd):
    self.sent = ''
    self.rcvd = ''
    self.errpos = 0 
    if self.dial.output != None: self.expected = repr(self.dial.output)
    else: self.expected = ''
    #print('run_dialog: tx=%s, rx=%s, type=%s, timeout=%d' % (self.dial.input,self.expected, self.dial.output.__class__.__name__,self.timeout))
    #return False
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
          #print('...', rout, len(rout))
          tout -= (time.time()-t0)
        except Exception:
          # se ocorreu timeout ...
          # retorna verdadeiro se nada foi apresentado pelo programa
          # e output for None.
          self.rcvd = infd.data
          if infd.data == '': 
            ok = self.dial.output == None
            return ok
          elif rout == infd.data: 
            self.errpos = self.dial.output.errpos
            #print('errpos:', self.errpos)
            return False
          rout = infd.data
        if self.dial.output != None: 
          ok = self.__check_output__(rout)
          #print('... ok=%d'% ok)
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
          # Aqui deve-se identificar a posicao do erro,
          # em que a saida do programa diverge do esperado
          return False  
    return True


class Case:

  ResultList = [ExactResult, IntResult, FloatResult, RegexResult, AnyRegexResult, Result]
  MaxLine = 10240

  def __init__(self, name):
    self.name = name
    self.dialogs = []
    self.curr_dialog = 0
    self.reduction = 0
    self.info = ''

  def __hash__(self):
    return hash(self.name)

  def __eq__(self, o):
    if o != None: return self.name == o.name
    return False

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
        #print('exc:', e, outp, 'tipo=%s'%type(outp))
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
    self.errpos = -1 
    #print(self.dialogs)
    infd = Reader(proc.stdout)
    len_rcvd = 0
    while self.curr_dialog < len(self.dialogs):
      try:
        dial = Dialog(self.dialogs[self.curr_dialog], timeout)
        ok = dial.run(proc.stdin,infd)
        self.data_sent += dial.sent
        self.data_rcvd += dial.rcvd
        self.expected += dial.expected+'\n'
        if not ok:
          self.errpos = dial.errpos + len_rcvd
          #print('len=%d, errpos=%d, rcvd=%d: %d, %s' % (len(self.data_rcvd),dial.errpos, len_rcvd, self.errpos, self.data_rcvd[self.errpos-2:self.errpos+20]))
          break
        len_rcvd = len(self.data_rcvd)
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
      r.append(self.__loadcase__(c))
    return r

  def __loadcase__(self, c):
    caso = Case(c.name)
    caso.add_dialogs(c.dialogs)
    caso.requisite = c.requisite
    caso.parent = c.parent
    try:
      caso.set_reduction(c.grade_reduction)
    except:
      pass
    caso.set_info(c.info)
    return caso

  def __runcase__(self, caso, prog):
    result = {}
    #caso = self.__loadcase__(case)
    succ = caso.run([prog], self.timeout)
    result = {'success': succ, 'info': caso.info, 'input':caso.data_sent,
                           'output':caso.data_rcvd, 'expected': caso.expected}
    if not succ:
      result['text'] = caso.get_hint_data()
      result['reduction'] = caso.reduction
      result['errpos'] = caso.errpos
    return result

#####################################################
def init(test, **args):
  fac = DefaultEvaluator(test, **args)
  return fac

