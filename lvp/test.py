class File:

  def __init__(self, name):
    self.name = name

  def __repr__(self):
    try:
      x = open(self.name).read()
      #print('File: %d bytes\n' % len(x))
      return x
    except:
      raise ValueError('%s not found!' % self.name)

  def __str__(self):
    return repr(self)

class Base:

  Attrs = ['name','attrs', 'Kind']
  Kind = 'base'

  def __init__(self, name, attrs={}):
    object.__setattr__(self,'name',name)
    object.__setattr__(self,'attrs',{})
    if attrs: self.attrs.update(attrs)

  def __repr__(self):
    #return 'Case "%s": %s' % (self.name, self.attrs)
    r = '%s %s {\n' % (self.Kind, self.name)
    for k,val in self.attrs.items():
      r += '%s=%s\n' % (k, val)
    r += '}\n'
    return r

  def __getattr__(self, k):
    try:
      return self.attrs[k]
    except:
      try:
        return self.__dict__[k]
      except:
        raise AttributeError(k)

  def __attrs__(self):
    return self.Attrs + list(self.attrs.keys())

  def __setattr__(self, k, v):
    if not k in self.__attrs__(): raise AttributeError('%s: invalid attribute' % k)
    try:
      self.attrs[k]
      self.attrs[k] = v
    except KeyError:
      object.__setattr__(self,k, v)

class Dialog(Base):

  Kind = 'dialog'

  def __init__(self, attrs={}):
    Base.__init__(self, '', {'input':None, 'output':None, 'hint':'', 'timeout':0})    
    self.attrs.update(attrs)
    self.attrs['timeout'] = int(self.attrs['timeout'])
    if self.attrs['output']: 
      self.attrs['output'] = str(self.attrs['output'])

  def __setattr__(self, k, v):
    if k == 'timeout': v = int(v)
    #if k == 'output': v = str(v)
    Base.__setattr__(self, k, v)

class Case(Base):

  Kind = 'case'

  def __init__(self, name, attrs={}):
    Base.__init__(self, name, {'info':'', 'timeout': 30, 'hint': ''})    
    self.attrs.update(attrs)
    self.__check_dialogs__()

  def __check_dialogs__(self):
    d = {}
    for k,val in self.attrs.items():
      if k in ['input','output']:
        d[k] = val
    if d:
      for k,val in d.items():
        del self.attrs[k]
      d['timeout'] = self.attrs['timeout']      
      try:
        self.attrs['dialogs'].append(Dialog(d))
      except KeyError:
        self.attrs['dialogs'] = [Dialog(d)]

  def __getattr__(self, k):
    if k == 'timeout':
      if 'dialogs' in self.attrs:
        t = 0
        for dial in self.dialogs:
          t += dial.timeout
      else:
        t = self.attrs['timeout'] 
      return t
    #elif k == 'hint':
    #  t = ''
    #  for dial in self.dialogs:
    #    t += dial.hint
    #  return t
    try:
      return self.attrs[k]
    except:
      try:
        return self.__dict__[k]
      except:
        raise AttributeError(k)

class BasicTest(Base):

  Timeout=30
  Kind = 'test'

  def __init__(self, name, attrs={}):
    Base.__init__(self, name, {'weight':1, 'timeout':0})
    self.attrs.update(attrs)
    
  def __repr__(self):
#    return 'TestSuite "%s": %s' % (self.name, self.attrs)
    return 'TestSuite "%s" (%s): %s' % (self.name, self.type, self.attrs)


