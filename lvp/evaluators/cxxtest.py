import subprocess,re
from .evaluator import Evaluator
import xml.etree.ElementTree as ET
import time

class CxxEvaluator(Evaluator):

  Expr = re.compile(r'grade reduction *= *([0-9]{1,3} *%?)')
  Err = re.compile(r'Error: (.*)', re.S | re.M)
  Suffixes = ['.cc', '.C', '.cpp']
  TestExpr = r'class\s+%s\s*:\s*public\s+CxxTest::TestSuite'

  def __init__(self, test, **args):
    Evaluator.__init__(self, **args)
    self.cases = test.cases
    self.name = test.name
    self.timeout = test.timeout
    self.__find_test__(test.name)
    try:
      self.files = test.files
    except:
      self.files = self.__find_files__(self.Suffixes)

  def __find_test__(self, name):
    arqs = self.__find_files__(['.h'])
    expr = re.compile(self.TestExpr % name)
    for arq in arqs:
      data = open(arq).read()
      if expr.search(data):
        self.test = arq
        return
    raise ValueError('test file for test suite %s not found' % name)

  def __list_tests__(self, prog):
    prog = prog + ['--help-tests']
    r = Evaluator.__run__(self, prog)
    r = r.split('\n')[2:]
    res = []
    for test in r:
      test = test.split()
      if test[0] == self.name: res.append(test)
    return res
    
  def __run__(self,prog):
    #if type(prog) == type([]): prog.append('-v')
    #else: prog = [prog, '-v']
    if type(prog) == type([]): pass
    else: prog = [prog]
    result = {}
    for test in self.__list_tests__(prog):
      cname = test[1][4:]
      case = self.__get_case__(cname)
      if not case:
        continue
      program = prog + test
      global_timeout = self.timeout
      if case.timeout > 0 and case.timeout < self.timeout:
        self.timeout = case.timeout
      test_timeout = self.timeout
      #print('timeout:', self.timeout, global_timeout)
      t1 = time.time()
      r = Evaluator.__run__(self, program)
      self.timeout = global_timeout
      try:
        if r:
          result.update(self.__check_output__(r, case))
        else:
          raise Exception()
      except Exception as e:
          t2 = time.time()
          tname = '%s' % test[1]
          result[tname] = {'success': False, 'reduction': case.grade_reduction, 'info':case.info}
          if t2-t1 >= test_timeout:
             result[tname]['text'] = 'Timeout !'
          else:
             result[tname]['text'] = 'Algum erro fatal: ' + r
          
    return result

  def __check_output__(self, data, case):
    r = ET.fromstring(data)
    result = {}
    for test in r:
      tname = test.attrib['name'][4:]
      result[tname] = {'success': True, 'text': '', 'info':case.info}
      if test.tag == 'testcase':
        for res in test:
          if res.tag == 'trace':
            result[tname]['text'] += '%s\n' % res.text
          elif res.tag == 'failure':
            result[tname]['reduction'] = case.grade_reduction
            #m = self.Expr.search(res.text)
            #if m:
            #  reduc = m.groups()[0]
            #  reduc = reduc.strip()
            #  if reduc[-1] == '%':
            #    reduc = float('.%s' % reduc[:-1])
            #  else:
            #    reduc = int(reduc)
            result[tname]['success'] = False
            try:
              result[tname]['text'] += '%s\n' % case.hint
            except:
              pass
            #m = self.Err.search(res.text)
            #if m:
            #  result[tname]['text'] += '%s\n' % m.groups()[0]
            #else:
            err = res.text.replace('Test failed:', '')
            result[tname]['text'] += 'Erro => %s\n' % err
    return result

  def compile(self):
    cmd = ['cxxtestgen','--runner=XmlPrinter', '-o', 'runner.cpp', self.test]
    self.__exec__(cmd)
    #subprocess.call(cmd)
    #print(self.files)
    cmd = ['g++','-o','vpl_test','-I.','-std=c++11','runner.cpp','-lm','-lutil'] + self.files
    self.__exec__(cmd)
    #subprocess.call(cmd)
          
#####################################################
def init(test, **args):
  fac = CxxEvaluator(test, **args)
  return fac

