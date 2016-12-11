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
    self.tlist = []
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
    if self.tlist: return self.tlist
    prog = prog + ['--help-tests']
    r = Evaluator.__run__(self, prog)
    r = r.split('\n')[2:]
    for test in r:
      test = test.split()
      if test[0] == self.name: self.tlist.append(test[1][4:])
    return self.tlist

  def __runcase__(self, case, prog):
    if type(prog) == type([]): pass
    else: prog = [prog]
    result = {}
    if not case.name in self.__list_tests__(prog): return result
    program = prog + [self.name, 'test%s' % test]
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
        result = {'success': False, 'reduction': case.grade_reduction, 'info':case.info}
        if t2-t1 >= test_timeout:
           result[text'] = 'Timeout !'
        else:
           result['text'] = 'Algum erro fatal: ' + r
          
    return result

  def __check_output__(self, data, case):
    r = ET.fromstring(data)
    result = {}
    for test in r:
      tname = test.attrib['name'][4:]
      if tname != case.name: continue
      result = {'success': True, 'text': '', 'info':case.info}
      if test.tag == 'testcase':
        for res in test:
          if res.tag == 'trace':
            result['text'] += '%s\n' % res.text
          elif res.tag == 'failure':
            result['reduction'] = case.grade_reduction
            result['success'] = False
            try:
              result['text'] += '%s\n' % case.hint
            except:
              pass
            err = res.text.replace('Test failed:', '')
            result[text'] += 'Erro => %s\n' % err
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

