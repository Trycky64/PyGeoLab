"""Tokenize the small, safe mathematical expression language used by PyGeoLab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    """Kinds recognized by the expression tokenizer."""

    NUMBER = auto()
    IDENTIFIER = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    CARET = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    """One lexical token with source position for useful error messages."""

    kind: TokenKind
    text: str
    position: int


_SINGLE = {
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "*": TokenKind.STAR,
    "/": TokenKind.SLASH,
    "^": TokenKind.CARET,
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
    ",": TokenKind.COMMA,
}


def tokenize(source: str) -> tuple[Token, ...]:
    """Convert source text to tokens, rejecting every unsupported character."""
    tokens: list[Token] = []
    index = 0
    while index < len(source):
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if char in _SINGLE:
            tokens.append(Token(_SINGLE[char], char, index))
            index += 1
            continue
        if char.isdigit() or char == ".":
            start = index
            seen_dot = char == "."
            index += 1
            while index < len(source):
                current = source[index]
                if current.isdigit():
                    index += 1
                elif current == "." and not seen_dot:
                    seen_dot = True
                    index += 1
                else:
                    break
            if index < len(source) and source[index] in "eE":
                exponent = index
                index += 1
                if index < len(source) and source[index] in "+-":
                    index += 1
                digits = index
                while index < len(source) and source[index].isdigit():
                    index += 1
                if digits == index:
                    raise ValueError(f"Exposant invalide à la position {exponent}")
            text = source[start:index]
            try:
                float(text)
            except ValueError as exc:
                raise ValueError(f"Nombre invalide à la position {start}") from exc
            tokens.append(Token(TokenKind.NUMBER, text, start))
            continue
        if char.isalpha() or char == "_":
            start = index
            index += 1
            while index < len(source) and (source[index].isalnum() or source[index] == "_"):
                index += 1
            tokens.append(Token(TokenKind.IDENTIFIER, source[start:index], start))
            continue
        raise ValueError(f"Caractère interdit {char!r} à la position {index}")
    tokens.append(Token(TokenKind.EOF, "", len(source)))
    return tuple(tokens)
