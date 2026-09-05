"""Recursive-descent parser for the documented PyGeoLab expression grammar."""

from __future__ import annotations

from pygeolab.math_engine.ast_nodes import Binary, Call, Expr, Number, Unary, Variable
from pygeolab.math_engine.tokenizer import Token, TokenKind, tokenize


class ParseError(ValueError):
    """Raised when an expression does not conform to the safe grammar."""


class Parser:
    """Parse tokens without executing Python or accepting arbitrary syntax."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.tokens = tokenize(source)
        self.index = 0

    def parse(self) -> Expr:
        """Parse one complete expression and reject trailing input."""
        if self.current.kind is TokenKind.EOF:
            raise ParseError("L'expression est vide")
        expression = self._expression()
        if self.current.kind is not TokenKind.EOF:
            raise self._error("Élément inattendu")
        return expression

    @property
    def current(self) -> Token:
        """Return the token currently being consumed."""
        return self.tokens[self.index]

    def _advance(self) -> Token:
        token = self.current
        self.index += 1
        return token

    def _accept(self, kind: TokenKind) -> Token | None:
        if self.current.kind is kind:
            return self._advance()
        return None

    def _expect(self, kind: TokenKind, message: str) -> Token:
        token = self._accept(kind)
        if token is None:
            raise self._error(message)
        return token

    def _error(self, message: str) -> ParseError:
        return ParseError(f"{message} à la position {self.current.position}")

    def _expression(self) -> Expr:
        node = self._term()
        while self.current.kind in {TokenKind.PLUS, TokenKind.MINUS}:
            op = self._advance().text
            node = Binary(op, node, self._term())
        return node

    def _term(self) -> Expr:
        node = self._unary()
        while self.current.kind in {TokenKind.STAR, TokenKind.SLASH}:
            op = self._advance().text
            node = Binary(op, node, self._unary())
        return node

    def _unary(self) -> Expr:
        if self.current.kind in {TokenKind.PLUS, TokenKind.MINUS}:
            op = self._advance().text
            return Unary(op, self._unary())
        return self._power()

    def _power(self) -> Expr:
        node = self._primary()
        if self._accept(TokenKind.CARET):
            node = Binary("^", node, self._unary())
        return node

    def _primary(self) -> Expr:
        if self.current.kind is TokenKind.NUMBER:
            return Number(float(self._advance().text))
        if self.current.kind is TokenKind.IDENTIFIER:
            name = self._advance().text
            if self._accept(TokenKind.LPAREN):
                arguments: list[Expr] = []
                if self.current.kind is not TokenKind.RPAREN:
                    arguments.append(self._expression())
                    while self._accept(TokenKind.COMMA):
                        arguments.append(self._expression())
                self._expect(TokenKind.RPAREN, "Parenthèse fermante attendue")
                return Call(name, tuple(arguments))
            return Variable(name)
        if self._accept(TokenKind.LPAREN):
            node = self._expression()
            self._expect(TokenKind.RPAREN, "Parenthèse fermante attendue")
            return node
        raise self._error("Nombre, variable ou parenthèse attendue")


def parse(source: str) -> Expr:
    """Parse source into an immutable internal AST."""
    return Parser(source).parse()
