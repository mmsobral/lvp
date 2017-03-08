#!/usr/bin/python3

import sys
from lvp.parser import VplParser
from lvp.evaluators.evaluator import Evaluator
#import lvp.evaluators
import importlib
import traceback
import json

CASES = 'evaluate.cases'
Timeout = 30

class Aggregator(Evaluator):

  def __init__(self, tests, **args):
    Evaluator.__init__(self, **args)
    self.tests = tests
    self.grade = 0
    self.result = {}

  def __load_module__(self, name):
    try:
      module = importlib.import_module('lvp.evaluators.%s' % name)
    except ImportError:
      module = importlib.import_module(name)
    return module

  def __run_test__(self, test):
      module = self.__load_module__(test.type)
      test.generate()
      #runner = module.init(test, timeout=Timeout)
      runner = module.init(test)
      runner.compile()
      runner.evaluate()
      return runner

  def __sum_weights__(self, suites):
    s = 0
    for test in suites:
      if test.weight < 0: raise ValueError('weight must be >= 0')
      s += test.weight
    return s

  def compile(self):
    pass

  def run(self):
    pass

  def evaluate(self):
    p = VplParser(self.tests)
    suites = p.parse()
    lev = []
    total = self.__sum_weights__(suites)
    if total <= 0: raise ValueError('weird ... sum of weights <= 0 !')
    self.grade = 0
    self.result = {}
    for test in suites:
      res = self.__run_test__(test)
      if not res: raise ValueError('test %s cannot be applied !' % test.type)
      self.grade += test.weight*res.grade()/total
      self.result[test.name] = res
    return self.grade

  def error_report(self, e):
    r = '<|--\n- Erro: %s\n\n' % str(e) 
    r += '\n--|>\n'
    return r

  def report(self):
    result = {}
    for test,res in self.result.items():
      result[test] = {'grade': res.grade()}
      result[test]['cases'] = res.get_result()
    result = json.dumps(result)
    result = '<|--\n%s\n--|>\nGrade :=>> %.2f\n' % (result, self.grade)
    return result
    for test,res in self.result.items():
      r += '<|--\n- Start of test: %s\n\n' % test
      r += res.report()
      r += '\n- End of test %s\n--|>\n' % test
    r += 'Grade :=>> %.2f\n' % self.grade
    r += ''
    return r
        
###################################################################
if __name__ == '__main__':
  try:
    casos = sys.argv[1]
  except:
    casos = CASES
  try:
    obj = Aggregator(casos)
  except Exception as e:
    print('Falha ao ler configuracao: %s' % repr(e))
    print('Grade :=>> 0.00')
    sys.exit(0)
  try:
    obj.evaluate()
  except Exception as e:
    print(obj.error_report(e))
    #print(traceback.format_exc())
    print('Grade :=>> 0.00')
    sys.exit(0)
  try:
    print(obj.report())
  except Exception as e:
    print('Falha ao emitir relatorio: %s' % repr(e))
    print('Grade :=>> 0.00')
