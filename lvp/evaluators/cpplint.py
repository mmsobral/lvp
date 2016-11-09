import subprocess,re
from .evaluator import Evaluator

class CpplintEvaluator(Evaluator):

  # reconhece uma linha de erro do cpplint
  Expr = re.compile(r'([-_a-zA-Z0-9+./]+):([0-9]+):\s+(.*?)\s+\[(.*?)\]\s+\[([0-9])\]')
  Suffixes = ['.cc', '.C', '.cpp', '.h']

  def __init__(self, test, **args):
    Evaluator.__init__(self, **args)
    self.cases = test.cases
    try:
      self.files = test.files
    except:
      self.files = self.__find_files__(self.Suffixes)

  def __run__(self,prog):
    prog = [prog, '--filter=-legal']
    has_default = False
    for c in self.cases:
      if c.name == 'default':
        has_default = True
        break
    if not has_default:
      for c in self.cases:
        prog.append('--filter=+%s' % c.name)
    prog += self.files
    r = Evaluator.__run__(self, prog, True)
    return self.__check_output__(r)

  def __get_tests__(self, data):
    tests = {}
    for test in self.Expr.findall(data):
      arq, line, desc, test, score = test
      score = int(score)
      try:
        tests[test]['data'].append((arq,line,score))
      except KeyError:
        tests[test] = {'desc': desc}
        tests[test]['data'] = [(arq,line,score)]
    return tests

  def __get_threshold__(self):
    try:
      limiar = int(case.output)
    except:
      limiar = 1
    return limiar

  def __check_output__(self, data):
    result = {}
    for c in self.cases:
      result[c.name] = {'success': True, 'text': '', 'reduction': 0}
    tests = self.__get_tests__(data)
    for test,val in tests.items():
      case = self.__get_case__(test)
      if not case: continue
      limiar = self.__get_threshold__()
      arqs = filter(lambda x: x[-1] >= limiar, val['data'])
      arqs = list(arqs)
      if len(arqs) > 0:
        arqs = map(lambda x: '%s:%s' % (x[0], x[1]), arqs)
        arqs = list(arqs)
        text = ', '.join(arqs)
        text = '\t** %s: %s: files=%s' % (test, val['desc'], text)
        result[case.name]['success'] = False
        if result[case.name]['text']:
          result[case.name]['text'] += '%s\n' % text
        else:
          result[case.name]['text'] = '\n%s\n' % text
        result[case.name]['reduction'] += case.grade_reduction*len(arqs)
    return result

  def compile(self):
    pass

  def evaluate(self):
    return self.run('cpplint')

          
#####################################################
def init(test, **args):
  fac = CpplintEvaluator(test, **args)
  return fac

