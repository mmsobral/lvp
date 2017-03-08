import sys
from .ply import yacc,lex
#import ply.yacc as yacc
#import ply.lex as lex
import traceback
import types
import subprocess
from .test import Dialog,Case,BasicTest,File

class SemanticError(Exception):

  def __init__(self, lineno, value, line=''):
    self.value = value
    self.n = lineno
    self.line = line

  def __str__(self):
      return 'Semantic error: %s' % self.value

class ParseError (Exception):

  def __init__(self, lineno, column, value, line=''):
    self.column = column
    self.value = value
    self.line = line
    self.n = lineno

  def __str__(self):
    if self.column < 0:
      return 'Parse error: %s' % self.value
    else:
      return 'Parse error at %d,%d: %s' % (self.n, self.column, self.value)

class Test(BasicTest):

  def generate(self):
    try:
      prog = self.attrs['generator']
      proc = subprocess.Popen(prog, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      try:
        r, data = proc.communicate('', self.Timeout)
      except subprocess.TimeoutExpired:
        return False
      proc.stdin.close()
      proc.stdout.close()
      try:
        r = r.decode('ascii')
      except UnicodeDecodeError:
        r = r.decode('utf8')
      r = r.strip()
      del self.attrs['generator']
      fname = self.__save__(r)
      p = VplParser(fname)
      suites = p.parse()
      self.cases = suites[0].cases
    except Exception as e:
      pass

  def __save__(self, r):
    fname = '.tmp.%s' % self.name
    f = open(fname, 'w')
    f.write('test %s {\n' % self.name)
    for k,val in self.attrs.items():
      if k == 'cases':
        for case in val:
          f.write('%s' % case)
      else:
        f.write('%s=%s\n' % (k, val))
    f.write('%s\n}' % r)
    f.close()
    return fname

class VplParser:

  start = 'statement'
  t_ignore = ' \t'
  precedence = ()
  literals = ''

  #t_COLON  = r':'
  t_EQUALS  = r'='
  t_LBRACE  = r'\{'
  t_RBRACE  = r'\}'
  t_VIRG    = r','
  #t_FLOATNUMBER = r'[0-9]*\.[0-9]+'
  t_LPAR = r'\('
  t_RPAR = r'\)'
  #t_ASPAS = r'"'
  t_DIV = '/'
  t_PERC = r'%'
  #t_NODE = r'[a-zA-Z_.0-9][-a-zA-Z_. 0-9]*'

  reserved = {'test': 'TEST', 'case': 'CASE', 'grade_reduction':'GRADERED', 	      'files':'FILES', 'weight':'WEIGHT', 'input':'INPUT','output':'OUTPUT',
	      'hint':'HINT', 'generator':'GENERATOR', 'type':'TYPE',
              'dialog':'DIALOG','build':'BUILD', 'timeout':'TIMEOUT',
              'info':'INFO', 'parent':'PARENT','requisite':'REQUISITE'}

  tokens = (
    'LBRACE', 'RBRACE','EQUALS','NUMBER', 'VIRG',
    'LPAR','RPAR','PERC','STRING','REGEX','FLOATNUMBER',
    'COMMENT','ID','PATHNAME', 'DIV', 'OUTPUTFILE', 'SPECIAL')


  def __init__(self, conf):
    self.tokens += tuple(self.reserved.values())
    self.lineno = 1
    self.line = ''
    self.conf = conf
    self.__built = False

  def build(self, **args):
    self.lex = lex.lex(module=self, **args)
    self.yacc = yacc.yacc(module=self)
    self.__built = True

  def get_reserved(self, token):
    it = self.reserved.iteritems()
    while True:
      try:
        key,val = it.next()
        if val == token: return key
      except StopIteration:
        return None

  def t_COMMENT(self, t):
    r'\//.*'
    pass

  def t_newline(self, t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")
    
  def t_error(self, t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

  def parse(self):
    if not self.__built: self.build()
    self.lex.lineno = 0
    f=open(self.conf)
    r = []
    buffer = f.read()
    try:
      r = self.yacc.parse(buffer, lexer=self.lex)
      #print self.lex.lineno
    except SyntaxError:
      pass
    f.close()
    if not r:
      raise SyntaxError('nada reconhecido ...')
    return r

  def p_error(self,p):
    if not p:
      raise ParseError(self.lineno, 0, "Unknown or incomplete declaration", self.line)
    raise ParseError(self.lex.lineno, p.lexpos, p.value, self.line)

  def tokenize(self, x=''):
    try:
      x = x.read()
    except:
      x = open(self.conf).read()
    print(x)
    lexer = lex.lex(module=self)
    lexer.input(x)
    #print self.tokens, tokens, t_ID
    r = []
    while True:
      tok = lexer.token()
      if not tok: break
      r.append(tok)
    return r

  def t_REGEX(self, t):
    r'/.*/\s+'
    t.type = self.reserved.get(t.value,'REGEX')    # Check for reserved words
    return t

  def t_OUTPUTFILE(self, t):
    r'<"[-_a-z A-Z.+0-9]+"'
    t.value = t.value[2:-1]
    return t

  def t_PATHNAME(self, t):
    r'''/?([-_a-z A-Z.+0-9]+/)+[-_a-z A-Z.+0-9]+
        | "/?([-_a-z A-Z.+0-9]+/)+[-_a-z A-Z.+0-9]+"'''
    return t

  def t_STRING(self, t):
    r'".*"'
    t.type = self.reserved.get(t.value,'STRING')    # Check for reserved words
    t.value = t.value[1:-1]
    return t

  def t_FLOATNUMBER(self, t):
    r'[-+]?\d*[.]\d+'
    return t

  def t_NUMBER(self, t):
    r'[-+]?\d+'
    return t

  def t_ID(self, t):
    r'[-a-zA-Z_.:]([-a-zA-Z_0-9.:]+-)?[a-zA-Z_0-9.:]*'
    #r'[a-zA-Z_][-a-zA-Z_0-9]*'
    t.type = self.reserved.get(t.value,'ID')    # Check for reserved words
    return t


  def t_SPECIAL(self, t):
     r'[-+/^!%]'
     return t

  def p_statement_comment(self, p):
    '''statement : COMMENT
             | '''
    p[0] = None
    return p[0]

  def p_statement_tests(self, p):
    'statement : tests'
    p[0] = p[1]
    return p[0]

  def p_tests_decl1(self, p):
    'tests : test tests'
    p[0] = [p[1]] + p[2]

  def p_tests_decl2(self, p):
    'tests : test'
    p[0] = [p[1]]

  def p_test_decl1(self, p):
      r'test : TEST ID LBRACE testattrs RBRACE'
      p[0] = Test(p[2], p[4])

  def p_test_decl2(self, p):
      r'testattrs : tattr testattrs'
      p[0] = p[2]
      if isinstance(p[1], Case):
        try:
          p[0]['cases'].append(p[1])
        except:
          p[0]['cases'] = [p[1]]
      else:
        p[0].update(p[1])

  def p_test_decl3(self, p):
      r'testattrs : tattr'
      if isinstance(p[1], Case):
        p[0] = {'cases': [p[1]]}
      else:
        p[0] = p[1]

  def p_test_decl4(self, p):
      r'tattr : CASE caseid LBRACE case RBRACE'
      p[0] = Case(p[2], p[4])

  def p_tattr_decl1(self, p):
      r'tattr : WEIGHT EQUALS NUMBER'
      p[0] = {p[1]:int(p[3])}

  def p_tattr_decl2(self, p):
      r'tattr : TYPE EQUALS ID'
      p[0] = {p[1]:p[3]}

  def p_tattr_decl3(self, p):
      r'tattr : FILES EQUALS pathlist'
      p[0] = {p[1]:p[3]}

  #def p_tattr_decl3b(self, p):
  #    r'tattr : FILES EQUALS idlist'
  #    p[0] = {p[1]:p[3]}

  def p_tattr_decl4(self, p):
      r'tattr : GENERATOR EQUALS PATHNAME'
      p[0] = {p[1]:p[3]}

  def p_tattr_decl5(self, p):
      r'tattr : BUILD EQUALS PATHNAME'
      p[0] = {p[1]:p[3]}

  def p_tattr_decl6(self, p):
      r'tattr : TIMEOUT EQUALS NUMBER'
      p[0] = {p[1]:int(p[3])}

  def p_case_decl1(self, p):
      r'case : attr case'
      #p[2].update(p[1])
      #p[0] = p[2]
      for k,val in p[1].items():
        try:
          p[2][k] = val + '\n' + p[2][k]
        except: 
          p[2][k] = val
      p[0] = p[2]

  def p_case_decl2(self, p):
      r'case : attr'
      p[0] = p[1]

  def p_case_decl3(self, p):
      r'case : dialog case'
      try:
        p[2]['dialogs'].insert(0, p[1])
      except:
        p[2]['dialogs'] = [p[1]]
      p[0] = p[2]

  def p_case_decl4(self, p):
      r'case : dialog'
      p[0] = {'dialogs': [p[1]]}

  def p_caseid_decl1(self, p):
      r'caseid : casetok caseid' 
      p[0] = p[1] + ' ' + p[2]

  def p_caseid_decl2(self, p):
      r'caseid : casetok' 
      p[0] = p[1]

  def p_casetok_decl1(self, p):
      r'''casetok : ID
                  | NUMBER'''
      p[0] = p[1]

  def p_attr_decl1(self, p):
      r'attr : commonattr'
      p[0] = {p[1][0]: p[1][1]}

  def p_attr_decl2(self, p):
      r'''attr : GRADERED EQUALS NUMBER'''
      n = int(p[3])
      p[0] = {p[1]: n}

  def p_attr_decl3(self, p):
      r'''attr : GRADERED EQUALS NUMBER PERC'''
      n = int(p[3])*.01
      p[0] = {p[1]: n}

  def p_attr_decl4(self, p):
      r'''attr : PARENT EQUALS caseid'''
      p[0] = {p[1]: p[3]}

  def p_attr_decl5(self, p):
      r'''attr : REQUISITE EQUALS caselist'''
      p[0] = {p[1]: p[3]}

  def p_caselist_decl1(self, p):
      r'''caselist : caseid VIRG caselist'''
      p[0] = [p[1]] + p[3]

  def p_caselist_decl2(self, p):
      r'''caselist : caseid'''
      p[0] = [p[1]]

  def p_dialog_decl1(self, p):
      'dialog : DIALOG LBRACE commonlist RBRACE'
      p[0] = Dialog(p[3])

  def p_commonlist_decl1(self, p):
      'commonlist : commonattr commonlist'
      try:
        p[2][p[1][0]] = p[1][1] + '\n' +  p[2][p[1][0]]
      except:
        p[2][p[1][0]] = p[1][1]
      p[0] = p[2]

  def p_commonlist_decl2(self, p):
      'commonlist : commonattr'
      p[0] = {p[1][0]: p[1][1]}

  def p_commonattr_decl1(self, p):
      'commonattr : OUTPUT EQUALS OUTPUTFILE'
      p[0] = (p[1], open(p[3]).read())

  def p_commonattr_decl2(self, p):
      'commonattr : OUTPUT EQUALS multi'
      p[0] = (p[1], p[3])

  def p_commonattr_decl3(self, p):
      '''commonattr : common EQUALS multi'''
      p[0] = (p[1], p[3])

  def p_commonattr_decl4(self, p):
      '''commonattr : common EQUALS'''
      p[0] = (p[1], '')

  def p_commonattr_decl5(self, p):
      '''commonattr : TIMEOUT EQUALS NUMBER'''
      p[0] = (p[1], int(p[3]))

  def p_common_decl1(self, p):
      '''common : INPUT
                | HINT
                | INFO'''
      p[0] = p[1]

  def p_pathlist_decl1(self, p):
    'pathlist : PATHNAME  pathlist'
    p[0] = [p[1]]
    p[0] += p[2]

  #def p_idlist_decl1(self, p):
  #  'idlist : ID VIRG idlist'
  #  p[0] = [p[1]]
  #  p[0] += p[3]

  #def p_idlist_decl2(self, p):
  #  'idlist : ID'
  #  p[0] = [p[1]]

  def p_pathlist_decl2(self, p):
    '''pathlist : PATHNAME VIRG pathlist
                | ID VIRG pathlist'''
    p[0] = [p[1]]
    p[0] += p[3]

  def p_pathlist_decl3(self, p):
    '''pathlist : PATHNAME
                | ID'''
    p[0] = [p[1]]

  def p_multi_decl1(self, p):
    r'multi : multiid multi' 
    p[0] = p[1] + ' ' + p[2]
    #p[0] = p[0].strip()

  def p_multi_decl2(self, p):
    r'multi : multiid' 
    p[0] = p[1]
    #p[0] = p[0].strip()

  def p_multiid_decl1(self, p):
    r'''multiid : ID
              | FLOATNUMBER
              | NUMBER
              | EQUALS
              | VIRG
              | LPAR
              | RPAR
              | DIV
              | PERC
              | PATHNAME
              | STRING
              | REGEX
	      | SPECIAL''' 
              #|	WORD
    p[0] = p[1]

