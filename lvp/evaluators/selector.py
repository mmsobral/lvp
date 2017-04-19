import os,stat
from pathlib import Path

class Selector:
 
  Ext = []
  Prog = ['g++','-std=c++11','-I.']

 
  def __init__(self, arqs=[]):
    if not arqs:
      self.arqs = self.__find__()
    elif self.__check__(arqs):
      self.arqs = arqs
    else:
      self.arqs = None
    if not self.arqs: raise ValueError('')

  def __check__(self, arqs):
    'at least one file has one of this selector extensions'
    for arq in arqs:
      for ext in self.Ext:
        if arq.endswith(ext): return True
    return False
      
  def __find__(self):
    files = []
    p = Path('.')
    q = []
    q.append(p)
    
    while q:
      p = q.pop()
      for x in p.iterdir():
        if x.is_dir(): q.insert(0, x)
        elif x.is_file():
          if x.suffix in self.Ext or str(x) in self.Ext:
            files.append(x.as_posix())
    return files

  def get_command(self):
    prog = self.Prog + self.arqs
    return prog

class CppSelector(Selector):

  Ext = ['.cpp','.cc','.CC','.C']
  Prog = ['g++','-std=c++11','-I.', '-lm','-lutil', '-o', 'vpl_test']

class PySelector(Selector):

  Ext = ['.py']
  Prog = []
  Default = 'main.py'

  def __init__(self, arqs=[]):
    Selector.__init__(self, arqs)
    if len(self.arqs) > 1:
      if self.Default not in self.arqs: raise Exception('main.py not found')
      self.arqs = [self.Default]
      
  def get_command(self):
    f = open('vpl_test','w')
    f.write('#!/bin/bash\n\npython3 %s\n' % ' '.join(self.arqs))
    f.close()
    os.chmod('vpl_test', stat.S_IROTH|stat.S_IRGRP|stat.S_IRUSR|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)
    return ['/bin/true']


class SelectorFactory:

  Classes = [CppSelector, PySelector]

  def __init__(self):
    pass

  def get_selector(self, arqs=[]):
    for c in self.Classes:
      try:
        obj = c(arqs)
        return obj
      except ValueError as e:
        pass
      except Exception as e:
        raise e
    raise ValueError('')

