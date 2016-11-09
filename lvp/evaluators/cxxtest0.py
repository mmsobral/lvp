import subprocess,re
from .evaluator import Evaluator
import xml.etree.ElementTree as ET

class CxxEvaluator(Evaluator):

  Expr = re.compile(r'grade reduction *= *([0-9]{1,3} *%?)')
  Err = re.compile(r'Error: (.*)', re.S | re.M)
  Suffixes = ['.cc', '.C', '.cpp']
  TestExpr = r'class\s+%s\s*:\s*public\s+CxxTest::TestSuite'

  def __init__(self, test, **args):
    Evaluator.__init__(self, **args)
    self.cases = test.cases
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
    
  def __run__(self,prog):
    if type(prog) == type([]): prog.append('-v')
    else: prog = [prog, '-v']
    r = Evaluator.__run__(self, prog)
    if r == None:
      return None
    return self.__check_output__(r)

  def __check_output__(self, data):
    r = ET.fromstring(data)
    result = {}
    for test in r:
      cname = test.attrib['name'] 
      cname = cname[4:] # corta o sufixo "test"
      case = self.__get_case__(cname)
      if not case:
        continue
      tname = '%s::%s' % (test.attrib['classname'],test.attrib['name'])
      result[tname] = {'success': True, 'text': ''}
      if test.tag == 'testcase':
        for res in test:
          if res.tag == 'trace':
            result[tname]['text'] += '%s\n' % res.text
          elif res.tag == 'failure':
            result[tname]['reduction'] = case.grade_reduction
            m = self.Expr.search(res.text)
            if m:
              reduc = m.groups()[0]
              reduc = reduc.strip()
              if reduc[-1] == '%':
                reduc = float('.%s' % reduc[:-1])
              else:
                reduc = int(reduc)
            result[tname]['success'] = False
            try:
              result[tname]['text'] += '%s\n' % case.hint
            except:
              pass
            m = self.Err.search(res.text)
            if m:
              result[tname]['text'] += '%s\n' % m.groups()[0]
            else:
              result[tname]['text'] += '%s\n' % res.text              
    return result

  def compile(self):
    cmd = ['cxxtestgen','--runner=XmlPrinter', '-o', 'runner.cpp', self.test]
    self.__exec__(cmd)
    #subprocess.call(cmd)
    cmd = ['g++','-o','vpl_test','-I.','-std=c++11','runner.cpp','-lm','-lutil'] + self.files
    self.__exec__(cmd)
    #subprocess.call(cmd)
          
#####################################################
def init(test, **args):
  fac = CxxEvaluator(test, **args)
  return fac

