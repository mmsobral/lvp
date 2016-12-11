import subprocess
from pathlib import Path
import json

class Evaluator:

  def __init__(self, **args):
    self.gmin = self.__getarg__(args, 'gmin', 0)
    self.gmax = self.__getarg__(args, 'gmax', 100)
    self.timeout = self.__getarg__(args, 'timeout', 30)
    self.cases = []
    self.result = {}

  def __getarg__(self, args, k, defval):
    try:
      return args[k]
    except:
      return defval

  def __find_files__(self, suffixes):
    files = []
    p = Path('.')
    q = []
    q.append(p)
    while q:
      p = q.pop()
      for x in p.iterdir():
        if x.is_dir(): q.insert(0, x)
        elif x.is_file():
          if x.suffix in suffixes or str(x) in suffixes:
            files.append(x.as_posix())
    return files
    
  def grade(self, result=None):
    if not result: result = self.result
    nres = len(result)
    if nres == 0: return 0
    def_reduction = float(self.gmax) / nres
    total = self.gmax
    for name,status in result.items():
      #print(name, status, total)
      if not status['success']:
        r = status['reduction']
        if r == 0:
          total -= def_reduction
        elif type(r) == type(1):
          total -= r
        else:
          total -= self.gmax*r
    return max(0, total)

  def __get_case__(self, test):
    case = None
    default = None
    for c in self.cases:
      if c.name == test or test.find('%s/' % c.name) == 0:
        case = c
        break
      if c.name == 'default': default = c
    if not case:
      case = default
    return case

  def __exec__(self, prog):
    p = subprocess.Popen(prog, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
      out,err = p.communicate('',10)
    except subprocess.TimeoutException:
      p.kill()
      print('<|--\n- timeout\n--|>')
      return 1
    if err:
      err = err.decode('utf-8')
      print('<|--\n%s\n--|>' % err)
      return 1
    return 0

  def __run__(self,prog,get_stderr=False):
    proc = subprocess.Popen(prog, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
      r, data = proc.communicate('', self.timeout)
    except subprocess.TimeoutExpired:
      return ''
    proc.stdin.close()
    proc.stdout.close()
    try:
      r = r.decode('ascii')
    except UnicodeDecodeError:
      r = r.decode('utf8')
    if get_stderr:
      data = data.decode('ascii')
      r += data
    r = r.strip()
    return r

  def __check_key__(self, key, attr):
    try:
      ok = self.result[key][attr]
    except:
      self.result[key][attr]=''

  def __getcases__(self, caseset, parent=None):
    'get set of cases that have parent given by parameter parent'
    #print(caseset)
    return set(filter(lambda caso: caso.parent == parent, caseset))

  def __getcases_req__(self, req=set()):
    'get set of cases that have requsite given by parameter req'
    r = set(filter(lambda caso: set(caso.requisite).issubset(req) and caso.name not in req and caso.parent == None, self.cases))
    return r

  def __runcase__(self, caso, prog):
    'execute a specific case: this method must be overwritten by derived classes'
    print('--caso:', caso)
    result = {'success': True, 'info': caso.info, 'reduction': 0}
    return result

  def __runcases__(self, prog):
    'Execute all cases of this test, taking care of case requisites and case parents'
    result = {}
    # get all cases with no requisites
    lcases = self.__getcases_req__()
    casesok = set()
    # while there are cases to execute
    while lcases:
      # initiate list of parents
      parents = [None]
      # while there are parents that failed to execute
      while parents:
        lpar = []
        for parent in parents:
          #print("parent:", parent)
          # for each case that depends on failure of a parent
          for caso in self.__getcases__(lcases, parent):
            # run this specific case
            res = self.__runcase__(caso, prog)
            result[caso.name]=res
            # if case failed, add it to parent list, otherwise
            # extend case list with cases that has this case as requisite
            if not res['success']: lpar.append(caso.name)
            else:
              casesok.add(caso.name)
              lcases = lcases.union(self.__getcases_req__(casesok))
            # remove case from case list, since it was already executed
            #print(lcases,'\n',cases)
            lcases.remove(caso)
        parents = lpar
    failed = filter(lambda x: x.name not in casesok and x.name not in result, self.cases)
    for c in failed:
      if not c.parent:
       result[c.name] = {'success':False, 'reduction':c.grade_reduction, 'info':c.info, 'text': 'not executed because some of its requisites failed: '+','.join(c.requisite)}
    return result

  def run(self,prog='./vpl_test'):
    'run this evaluator'
    self.result = self.__runcases__(prog)
    for case in self.result:
      self.__check_key__(case, 'input')
      self.__check_key__(case, 'output')
      self.__check_key__(case, 'expected')
      self.__check_key__(case, 'text')
      self.__check_key__(case, 'info')
    return self.result

  def compile(self):
    subprocess.call('./vpl_run.sh')    

  def evaluate(self):
    return self.run()

  def get_result(self):
    return self.result

  def report(self):
    res= json.dumps(self.result)
    return res
    r = ''
    for caso,status in self.result.items():
      info = status['info']
      if info: info = '(%s)' % info
      if status['success']:
        r += '*** %s %s\n' % (caso, info)
    if r: 
      r = '- Succeeded tests\n' + r
    rf = ''
    for caso,status in self.result.items():
      info = status['info']
      if info: info = '(%s)' % info
      if not status['success']:
        rf += '*** %s %s: %s\n\n' % (caso, info,status['text'])
    if rf:
      r += '- Failed tests\n' + rf 
    r += '\n- Partial Grade: %.2f\n' % self.grade()
    return r

#######################################################################
def init(test, **args):
  return None

