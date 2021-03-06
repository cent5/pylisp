""" Parse and evaluate.
"""

import operator
from collections import Callable
from collections import deque
from functools import reduce

SEPARATOR = " "
KW_ATOM = "atom?"
KW_QUOTE = "quote"
KW_DEFINE = "define"
KW_LAMBDA = "lambda"
KW_COND = "cond"


def tokenize(s):
    """
    We rely on " " to identify each token. For the open and close parentheses,
    simply surround each with a " ".
    """
    return deque(s.replace("(", " ( ").replace(")", " ) ").split())


def parse(tokens):
    token = tokens.popleft()
    if token == "(":
        sexp = List()
        while tokens[0] != ")":
            sexp.append(parse(tokens))
            if not tokens:
                raise SyntaxError("Missing )")
        assert tokens.popleft() == ")"
        return sexp
    elif token == ")":
        raise SyntaxError("Unexpected )")
    else:
        return Atom(token)


class Program:
    """
    Essentially a list of S-expressions.
    """
    def __init__(self, s='', env=None, repl_mode=False):
        self.stdout = []
        self.repl_mode = repl_mode
        self.env = Env()
        self.env.update({
            "+": lambda *args: sum(args),
            "-": lambda *args: args[0] - sum(args[1:]),
            "*": lambda *args: reduce(operator.mul, args),
            "/": lambda *args: args[0] / reduce(operator.mul, args[1:]),
            "<": operator.lt,
            ">": operator.gt,
            "eq?": operator.eq,  # is_
            "car": lambda x: x[0],
            "cdr": lambda x: List(x[1:]),
            "cons": lambda x, y: List([x] + y) if isinstance(y, List) else List([x] + [y]),
            "print": lambda x: self.stdout.append(str(x)),
        })
        if env:
            self.env.update(env)
        self.sexps = []
        if not self.repl_mode:
            if not s:
                raise SyntaxError("Empty program")
            tokens = tokenize(s)

            while tokens:
                self.sexps.append(parse(tokens))

    def __repr__(self):
        return "\n".join(map(repr, self.sexps))

    def __str__(self):
        return "\n".join(map(str, self.sexps))

    def eval(self):
        values = [sexp.eval(self.env) for sexp in self.sexps]
        str_output = str(values[-1]) if values[-1] is not None else ""
        print_statement_outputs = self.get_std_out()
        if print_statement_outputs:
            str_output = print_statement_outputs + "\n" + str_output
        return str_output

    def add_and_run_statement(self, s):
        tokens = tokenize(s)
        self.sexps.append(parse(tokens))
        output = self.sexps[-1].eval(self.env)
        print(self.get_std_out())
        return str(output)

    def get_std_out(self):
        if self.stdout:
            str_output = "\n".join(self.stdout)
            self.stdout = []
            return str_output
        return ""


class Atom:
    """Atomic S-expression"""
    def __init__(self, token):
        self.x = None
        try:
            self.x = int(token)
        except ValueError:
            try:
                self.x = float(token)
            except ValueError:
                self.x = token

    def __str__(self):
        return str(self.x)

    def __repr__(self):
        return f"(Atom {str(self.x)})"

    def eval(self, env=None):
        if env and isinstance(self.x, str):
            _env = env.find(self.x)
            if self.x in _env:
                return _env[self.x]
        return self.x


class List(list):
    """List S-expression"""
    def __str__(self):
        return f"'({' '.join(map(str, self))})"

    def __repr__(self):
        return f"(List {' '.join(map(repr, self))})"

    def eval(self, env):
        args = self[:-1]
        op = self[-1].eval(env)
        if op == KW_QUOTE:
            assert len(args) == 1
            return args[0]
        elif op == KW_ATOM:
            assert len(args) == 1
            return isinstance(args[0], Atom) or not isinstance(args[0].eval(env), list)
        elif op == KW_DEFINE:
            assert len(args) == 2
            env[args[0].eval(env)] = args[1].eval(env)
            return None
        elif op == KW_LAMBDA:
            assert len(args) == 2
            return Udf(args[0], args[1], env)
        elif op == KW_COND:
            for test_expression in args:
                if test_expression[0].eval(env):
                    return test_expression[1].eval(env)
            return None
        values = [item.eval(env) for item in self[:-1]]
        assert isinstance(op, Callable), f"Not callable: {type(op)}:{op}. {env}"
        return op(*values)


class Udf:
    """User-defined function. Generate a deeper-level Env when execute."""
    def __init__(self, arg_names, body, env):
        self.arg_names, self.body, self.env = arg_names, body, env

    def __call__(self, *args):
        return self.body.eval(
            Env([arg_name.eval(self.env)
                 for arg_name in self.arg_names], args, self.env))

class LetScope:
    def __init__(self):
        pass

class Env(dict):
    """Mapping from symbols to expressions."""
    def __init__(self, arg_names=(), args=(), outer=None):
        super().__init__()
        self.update(zip(arg_names, args))
        self.outer = outer

    def find(self, arg_name):
        return self if not self.outer or arg_name in self else self.outer.find(arg_name)