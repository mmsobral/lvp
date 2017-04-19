import os,stat
from pathlib import Path

class Selector:
 
  Ext = []
  Prog = ['g++','-std=c++11','-I.']

 
  def __init__(self, arqs=[]):
    if not arqs:
      self.arqs = self.__find__()
    else:
      self.arqs = arqs
    if not self.arqs: raise ValueError('')

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
  Prog = ['g++','-std=c++11','-I.', '-lm','-lutil', '-o', 'vpltest']

class PySelector(Selector):

  Ext = ['.py']
  Prog = []

  def get_command(self):
    f = open('vpltest','w')
    f.write('#!/bin/bash\n\npython3 %s\n' % ' '.join(self.arqs))
    f.close()
    os.chmod('vpltest', stat.S_IROTH|stat.S_IRGRP|stat.S_IRUSR|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)
    return ['/bin/true']


