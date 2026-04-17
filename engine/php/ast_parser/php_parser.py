"""
PHP AST Parser
Parses PHP source into a structured AST for rule-based analysis.
Uses regex-based tokenization with structural awareness for PHP constructs.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from ..models.migration_models import ASTNode


# ---------------------------------------------------------------------------
# Token definitions
# ---------------------------------------------------------------------------

TOKEN_PATTERNS = [
    ("PHP_OPEN",       r"<\?php|<\?="),
    ("PHP_CLOSE",      r"\?>"),
    ("COMMENT_BLOCK",  r"/\*[\s\S]*?\*/"),
    ("COMMENT_LINE",   r"//[^\n]*|#[^\n]*"),
    ("HEREDOC",        r"<<<['\"]?(\w+)['\"]?\n[\s\S]*?\n\1;"),
    ("NOWDOC",         r"<<<'(\w+)'\n[\s\S]*?\n\1;"),
    ("STRING_DQ",      r'"(?:[^"\\]|\\.)*"'),
    ("STRING_SQ",      r"'(?:[^'\\]|\\.)*'"),
    ("FLOAT",          r"\b\d+\.\d+([eE][+-]?\d+)?\b"),
    ("INT_HEX",        r"\b0x[0-9a-fA-F]+\b"),
    ("INT_BIN",        r"\b0b[01]+\b"),
    ("INT_OCT",        r"\b0[0-7]+\b"),
    ("INT",            r"\b\d+\b"),
    ("VARIABLE",       r"\$[a-zA-Z_]\w*"),
    ("KEYWORD",        r"\b(?:abstract|and|array|as|break|callable|case|catch|"
                       r"class|clone|const|continue|declare|default|die|do|echo|"
                       r"else|elseif|empty|enddeclare|endfor|endforeach|endif|"
                       r"endswitch|endwhile|eval|exit|extends|final|finally|fn|"
                       r"for|foreach|function|global|goto|if|implements|include|"
                       r"include_once|instanceof|insteadof|interface|isset|list|"
                       r"match|namespace|new|or|print|private|protected|public|"
                       r"readonly|require|require_once|return|static|switch|throw|"
                       r"trait|try|unset|use|var|while|xor|yield|yield from|"
                       r"enum|never|mixed|true|false|null|TRUE|FALSE|NULL)\b"),
    ("TYPE_HINT",      r"\b(?:int|float|string|bool|array|object|callable|"
                       r"iterable|void|never|mixed|self|parent|static)\b"),
    ("FUNCTION_CALL",  r"\b([a-zA-Z_]\w*)\s*(?=\()"),
    ("IDENTIFIER",     r"[a-zA-Z_]\w*"),
    ("ARROW",          r"=>|->|::"),
    ("NULL_COALESCE",  r"\?\?=?"),
    ("SPREAD",         r"\.\.\."),
    ("OPERATOR",       r"[+\-*/%&|^~<>!=?:]+"),
    ("LBRACE",         r"\{"),
    ("RBRACE",         r"\}"),
    ("LPAREN",         r"\("),
    ("RPAREN",         r"\)"),
    ("LBRACKET",       r"\["),
    ("RBRACKET",       r"\]"),
    ("SEMICOLON",      r";"),
    ("COMMA",          r","),
    ("ATTRIBUTE",      r"#\["),
    ("WHITESPACE",     r"[ \t]+"),
    ("NEWLINE",        r"\n"),
    ("UNKNOWN",        r"."),
]

_MASTER_RE = re.compile(
    "|".join(f"(?P<{name}>{pat})" for name, pat in TOKEN_PATTERNS),
    re.MULTILINE,
)


@dataclass
class Token:
    type: str
    value: str
    line: int
    col: int


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def tokenize(source: str) -> list[Token]:
    """Tokenize raw PHP source into a flat token list."""
    tokens: list[Token] = []
    line = 1
    line_start = 0

    for m in _MASTER_RE.finditer(source):
        tok_type = m.lastgroup
        tok_value = m.group()
        col = m.start() - line_start

        tokens.append(Token(type=tok_type, value=tok_value, line=line, col=col))

        newlines = tok_value.count("\n")
        if newlines:
            line += newlines
            line_start = m.start() + tok_value.rfind("\n") + 1

    return tokens


# ---------------------------------------------------------------------------
# AST Builder
# ---------------------------------------------------------------------------

class PHPASTParser:
    """
    Recursive-descent style AST builder over token stream.
    Produces a lightweight AST focused on migration-relevant constructs.
    """

    def __init__(self, source: str):
        self.source = source
        self.tokens: list[Token] = [
            t for t in tokenize(source)
            if t.type not in ("WHITESPACE",)
        ]
        self.pos = 0

    # ------------------------------------------------------------------ helpers

    def peek(self, offset: int = 0) -> Optional[Token]:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def consume(self) -> Optional[Token]:
        tok = self.peek()
        if tok:
            self.pos += 1
        return tok

    def expect(self, tok_type: str) -> Optional[Token]:
        tok = self.peek()
        if tok and tok.type == tok_type:
            return self.consume()
        return None

    def match_value(self, *values: str) -> Optional[Token]:
        tok = self.peek()
        if tok and tok.value in values:
            return self.consume()
        return None

    # ------------------------------------------------------------------ entry

    def parse(self) -> ASTNode:
        root = ASTNode(
            node_type="program",
            start_line=1,
            end_line=self._last_line(),
            start_col=0,
            end_col=0,
            raw_value="",
        )
        while self.peek():
            node = self._parse_statement()
            if node:
                root.children.append(node)
        return root

    def _last_line(self) -> int:
        return self.source.count("\n") + 1

    # ------------------------------------------------------------------ statements

    def _parse_statement(self) -> Optional[ASTNode]:
        tok = self.peek()
        if not tok:
            return None

        # Skip PHP open/close tags
        if tok.type in ("PHP_OPEN", "PHP_CLOSE", "NEWLINE", "SEMICOLON"):
            self.consume()
            return None

        # Skip comments but capture them as nodes for doc block analysis
        if tok.type in ("COMMENT_LINE", "COMMENT_BLOCK"):
            return self._parse_comment()

        if tok.type == "KEYWORD":
            return self._parse_keyword_statement(tok)

        if tok.type == "VARIABLE":
            return self._parse_expression_statement()

        if tok.type == "FUNCTION_CALL":
            return self._parse_expression_statement()

        # Fallthrough – consume single token
        self.consume()
        return None

    def _parse_comment(self) -> ASTNode:
        tok = self.consume()
        return ASTNode(
            node_type="comment",
            start_line=tok.line,
            end_line=tok.line,
            start_col=tok.col,
            end_col=tok.col + len(tok.value),
            raw_value=tok.value,
        )

    def _parse_keyword_statement(self, tok: Token) -> Optional[ASTNode]:
        kw = tok.value.lower()

        dispatch = {
            "function":  self._parse_function,
            "class":     self._parse_class,
            "interface": self._parse_class,
            "trait":     self._parse_class,
            "enum":      self._parse_class,
            "namespace": self._parse_namespace,
            "use":       self._parse_use,
            "echo":      self._parse_echo,
            "return":    self._parse_return,
            "if":        self._parse_if,
            "foreach":   self._parse_foreach,
            "for":       self._parse_for,
            "while":     self._parse_while,
            "try":       self._parse_try,
            "throw":     self._parse_throw,
            "match":     self._parse_match,
            "require":   self._parse_include,
            "require_once": self._parse_include,
            "include":   self._parse_include,
            "include_once": self._parse_include,
        }

        handler = dispatch.get(kw)
        if handler:
            return handler()

        # Modifiers like public/private/protected/abstract/final/readonly
        if kw in ("public", "private", "protected", "abstract", "final",
                  "readonly", "static"):
            return self._parse_modified_declaration()

        self.consume()
        return None

    # ------------------------------------------------------------------ constructs

    def _parse_function(self) -> ASTNode:
        start = self.consume()  # 'function'
        is_ref = False

        amp = self.peek()
        if amp and amp.value == "&":
            is_ref = True
            self.consume()

        name_tok = self.peek()
        name = ""
        if name_tok and name_tok.type in ("IDENTIFIER", "FUNCTION_CALL"):
            name = name_tok.value
            self.consume()

        params = self._parse_parameter_list()
        return_type = self._parse_return_type()
        body = self._parse_block()

        end_line = body.end_line if body else (start.line)

        node = ASTNode(
            node_type="function_declaration",
            start_line=start.line,
            end_line=end_line,
            start_col=start.col,
            end_col=0,
            raw_value=self.source.split("\n")[start.line - 1],
            children=[p for p in params] + ([body] if body else []),
            metadata={
                "name": name,
                "is_ref": is_ref,
                "return_type": return_type,
                "param_count": len(params),
            },
        )
        return node

    def _parse_parameter_list(self) -> list[ASTNode]:
        params = []
        if not self.expect("LPAREN"):
            return params

        depth = 1
        param_tokens: list[Token] = []

        while self.peek() and depth > 0:
            tok = self.consume()
            if tok.type == "LPAREN":
                depth += 1
                param_tokens.append(tok)
            elif tok.type == "RPAREN":
                depth -= 1
                if depth == 0:
                    break
                param_tokens.append(tok)
            else:
                param_tokens.append(tok)

        # Parse individual parameters from collected tokens
        current: list[Token] = []
        for tok in param_tokens:
            if tok.type == "COMMA" and len(current) > 0:
                param = self._build_param_node(current)
                if param:
                    params.append(param)
                current = []
            else:
                current.append(tok)
        if current:
            param = self._build_param_node(current)
            if param:
                params.append(param)

        return params

    def _build_param_node(self, tokens: list[Token]) -> Optional[ASTNode]:
        if not tokens:
            return None

        type_hint = None
        name = None
        default = None
        is_ref = False
        is_spread = False
        has_default = False
        modifiers = []

        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t.type == "KEYWORD" and t.value in (
                "public", "private", "protected", "readonly"
            ):
                modifiers.append(t.value)
            elif t.type in ("TYPE_HINT", "IDENTIFIER") and name is None:
                # Could be type hint
                if i + 1 < len(tokens) and tokens[i + 1].type == "VARIABLE":
                    type_hint = t.value
                elif t.type == "VARIABLE":
                    name = t.value
            elif t.type == "VARIABLE":
                name = t.value
            elif t.value == "&":
                is_ref = True
            elif t.type == "SPREAD":
                is_spread = True
            elif t.value == "=" and i + 1 < len(tokens):
                has_default = True
                default = tokens[i + 1].value
                i += 1
            i += 1

        if not name:
            return None

        start_tok = tokens[0]
        end_tok = tokens[-1]
        return ASTNode(
            node_type="parameter",
            start_line=start_tok.line,
            end_line=end_tok.line,
            start_col=start_tok.col,
            end_col=end_tok.col + len(end_tok.value),
            raw_value=" ".join(t.value for t in tokens),
            metadata={
                "name": name,
                "type_hint": type_hint,
                "is_ref": is_ref,
                "is_spread": is_spread,
                "has_default": has_default,
                "default": default,
                "modifiers": modifiers,
            },
        )

    def _parse_return_type(self) -> Optional[str]:
        tok = self.peek()
        if tok and tok.value == ":":
            self.consume()
            type_parts = []
            # Handle union types (int|string), nullable (?int)
            while self.peek() and self.peek().value not in ("{", ";"):
                t = self.consume()
                type_parts.append(t.value)
            return "".join(type_parts).strip()
        return None

    def _parse_block(self) -> Optional[ASTNode]:
        tok = self.peek()
        if not tok or tok.type != "LBRACE":
            return None

        start = self.consume()
        depth = 1
        children = []

        while self.peek() and depth > 0:
            t = self.peek()
            if t.type == "LBRACE":
                depth += 1
                self.consume()
            elif t.type == "RBRACE":
                depth -= 1
                end_tok = self.consume()
                if depth == 0:
                    return ASTNode(
                        node_type="block",
                        start_line=start.line,
                        end_line=end_tok.line,
                        start_col=start.col,
                        end_col=end_tok.col,
                        raw_value="",
                        children=children,
                    )
            else:
                stmt = self._parse_statement()
                if stmt:
                    children.append(stmt)

        return ASTNode(
            node_type="block",
            start_line=start.line,
            end_line=start.line,
            start_col=start.col,
            end_col=0,
            raw_value="",
            children=children,
        )

    def _parse_class(self) -> ASTNode:
        start = self.consume()  # class/interface/trait/enum
        class_type = start.value

        name_tok = self.consume()
        name = name_tok.value if name_tok else ""

        # Collect extends/implements
        extends = []
        implements = []
        while self.peek() and self.peek().type not in ("LBRACE",):
            t = self.consume()
            if t.value == "extends":
                n = self.consume()
                if n:
                    extends.append(n.value)
            elif t.value == "implements":
                while self.peek() and self.peek().type not in ("LBRACE",):
                    n = self.consume()
                    if n.type not in ("COMMA",):
                        implements.append(n.value)

        body = self._parse_block()
        end_line = body.end_line if body else start.line

        return ASTNode(
            node_type="class_declaration",
            start_line=start.line,
            end_line=end_line,
            start_col=start.col,
            end_col=0,
            raw_value=self.source.split("\n")[start.line - 1],
            children=[body] if body else [],
            metadata={
                "name": name,
                "class_type": class_type,
                "extends": extends,
                "implements": implements,
            },
        )

    def _parse_namespace(self) -> ASTNode:
        start = self.consume()
        parts = []
        while self.peek() and self.peek().type not in ("SEMICOLON", "LBRACE", "NEWLINE"):
            tok = self.consume()
            parts.append(tok.value)
        self._skip_until_semi()
        return ASTNode(
            node_type="namespace",
            start_line=start.line,
            end_line=start.line,
            start_col=start.col,
            end_col=0,
            raw_value=" ".join(parts),
            metadata={"namespace": "".join(parts)},
        )

    def _parse_use(self) -> ASTNode:
        start = self.consume()
        parts = []
        alias = None
        while self.peek() and self.peek().type not in ("SEMICOLON",):
            tok = self.consume()
            if tok.value == "as":
                a = self.consume()
                if a:
                    alias = a.value
            else:
                parts.append(tok.value)
        self._skip_until_semi()
        return ASTNode(
            node_type="use_statement",
            start_line=start.line,
            end_line=start.line,
            start_col=start.col,
            end_col=0,
            raw_value=" ".join(parts),
            metadata={"import": "".join(parts), "alias": alias},
        )

    def _parse_echo(self) -> ASTNode:
        start = self.consume()
        expr_tokens = self._collect_until_semi()
        return ASTNode(
            node_type="echo_statement",
            start_line=start.line,
            end_line=start.line,
            start_col=start.col,
            end_col=0,
            raw_value=" ".join(t.value for t in expr_tokens),
        )

    def _parse_return(self) -> ASTNode:
        start = self.consume()
        expr_tokens = self._collect_until_semi()
        return ASTNode(
            node_type="return_statement",
            start_line=start.line,
            end_line=start.line,
            start_col=start.col,
            end_col=0,
            raw_value=" ".join(t.value for t in expr_tokens),
        )

    def _parse_if(self) -> ASTNode:
        start = self.consume()
        condition = self._parse_paren_expr()
        body = self._parse_block()
        children = [body] if body else []

        # else if / else
        while self.peek() and self.peek().value in ("else", "elseif"):
            kw = self.consume()
            if kw.value == "elseif" or (
                self.peek() and self.peek().value == "if"
            ):
                if self.peek() and self.peek().value == "if":
                    self.consume()
                cond = self._parse_paren_expr()
                blk = self._parse_block()
                children.append(ASTNode(
                    node_type="elseif_clause",
                    start_line=kw.line,
                    end_line=blk.end_line if blk else kw.line,
                    start_col=kw.col,
                    end_col=0,
                    raw_value="",
                    children=[blk] if blk else [],
                    metadata={"condition": condition},
                ))
            else:
                blk = self._parse_block()
                children.append(ASTNode(
                    node_type="else_clause",
                    start_line=kw.line,
                    end_line=blk.end_line if blk else kw.line,
                    start_col=kw.col,
                    end_col=0,
                    raw_value="",
                    children=[blk] if blk else [],
                ))
                break

        end_line = children[-1].end_line if children else start.line
        return ASTNode(
            node_type="if_statement",
            start_line=start.line,
            end_line=end_line,
            start_col=start.col,
            end_col=0,
            raw_value="",
            children=children,
            metadata={"condition": condition},
        )

    def _parse_foreach(self) -> ASTNode:
        start = self.consume()
        expr = self._parse_paren_expr()
        body = self._parse_block()
        return ASTNode(
            node_type="foreach_statement",
            start_line=start.line,
            end_line=body.end_line if body else start.line,
            start_col=start.col,
            end_col=0,
            raw_value=expr,
            children=[body] if body else [],
        )

    def _parse_for(self) -> ASTNode:
        start = self.consume()
        expr = self._parse_paren_expr()
        body = self._parse_block()
        return ASTNode(
            node_type="for_statement",
            start_line=start.line,
            end_line=body.end_line if body else start.line,
            start_col=start.col,
            end_col=0,
            raw_value=expr,
            children=[body] if body else [],
        )

    def _parse_while(self) -> ASTNode:
        start = self.consume()
        expr = self._parse_paren_expr()
        body = self._parse_block()
        return ASTNode(
            node_type="while_statement",
            start_line=start.line,
            end_line=body.end_line if body else start.line,
            start_col=start.col,
            end_col=0,
            raw_value=expr,
            children=[body] if body else [],
        )

    def _parse_try(self) -> ASTNode:
        start = self.consume()
        body = self._parse_block()
        children = [body] if body else []

        while self.peek() and self.peek().value in ("catch", "finally"):
            kw = self.consume()
            if kw.value == "catch":
                exc_type = self._parse_paren_expr()
                blk = self._parse_block()
                children.append(ASTNode(
                    node_type="catch_clause",
                    start_line=kw.line,
                    end_line=blk.end_line if blk else kw.line,
                    start_col=kw.col,
                    end_col=0,
                    raw_value=exc_type,
                    children=[blk] if blk else [],
                ))
            else:  # finally
                blk = self._parse_block()
                children.append(ASTNode(
                    node_type="finally_clause",
                    start_line=kw.line,
                    end_line=blk.end_line if blk else kw.line,
                    start_col=kw.col,
                    end_col=0,
                    raw_value="",
                    children=[blk] if blk else [],
                ))

        return ASTNode(
            node_type="try_statement",
            start_line=start.line,
            end_line=children[-1].end_line if children else start.line,
            start_col=start.col,
            end_col=0,
            raw_value="",
            children=children,
        )

    def _parse_throw(self) -> ASTNode:
        start = self.consume()
        expr_tokens = self._collect_until_semi()
        return ASTNode(
            node_type="throw_statement",
            start_line=start.line,
            end_line=start.line,
            start_col=start.col,
            end_col=0,
            raw_value=" ".join(t.value for t in expr_tokens),
        )

    def _parse_match(self) -> ASTNode:
        start = self.consume()
        expr = self._parse_paren_expr()
        body = self._parse_block()
        return ASTNode(
            node_type="match_expression",
            start_line=start.line,
            end_line=body.end_line if body else start.line,
            start_col=start.col,
            end_col=0,
            raw_value=expr,
            children=[body] if body else [],
        )

    def _parse_include(self) -> ASTNode:
        start = self.consume()
        expr_tokens = self._collect_until_semi()
        return ASTNode(
            node_type="include_statement",
            start_line=start.line,
            end_line=start.line,
            start_col=start.col,
            end_col=0,
            raw_value=" ".join(t.value for t in expr_tokens),
            metadata={"include_type": start.value},
        )

    def _parse_modified_declaration(self) -> Optional[ASTNode]:
        """Handle public/private/protected/abstract/final/readonly function/property."""
        modifiers = []
        while self.peek() and self.peek().type == "KEYWORD" and self.peek().value in (
            "public", "private", "protected", "abstract", "final", "readonly", "static"
        ):
            modifiers.append(self.consume().value)

        tok = self.peek()
        if not tok:
            return None

        if tok.value == "function":
            node = self._parse_function()
            if node:
                node.metadata["modifiers"] = modifiers
            return node
        elif tok.type == "IDENTIFIER" or tok.type == "TYPE_HINT" or tok.type == "VARIABLE":
            # Property declaration
            start_line = self.tokens[self.pos - len(modifiers)].line if modifiers else tok.line
            expr_tokens = self._collect_until_semi()
            return ASTNode(
                node_type="property_declaration",
                start_line=start_line,
                end_line=start_line,
                start_col=0,
                end_col=0,
                raw_value=" ".join(t.value for t in expr_tokens),
                metadata={"modifiers": modifiers},
            )
        else:
            self.consume()
            return None

    def _parse_expression_statement(self) -> ASTNode:
        start = self.peek()
        expr_tokens = self._collect_until_semi()
        return ASTNode(
            node_type="expression_statement",
            start_line=start.line if start else 0,
            end_line=start.line if start else 0,
            start_col=start.col if start else 0,
            end_col=0,
            raw_value=" ".join(t.value for t in expr_tokens),
        )

    # ------------------------------------------------------------------ helpers

    def _parse_paren_expr(self) -> str:
        """Collect tokens inside parentheses and return as string."""
        if not self.expect("LPAREN"):
            return ""
        depth = 1
        parts = []
        while self.peek() and depth > 0:
            tok = self.consume()
            if tok.type == "LPAREN":
                depth += 1
                parts.append(tok.value)
            elif tok.type == "RPAREN":
                depth -= 1
                if depth > 0:
                    parts.append(tok.value)
            else:
                parts.append(tok.value)
        return " ".join(parts)

    def _collect_until_semi(self) -> list[Token]:
        tokens = []
        depth = 0
        while self.peek():
            tok = self.peek()
            if tok.type in ("LBRACE", "LPAREN", "LBRACKET"):
                depth += 1
            elif tok.type in ("RBRACE", "RPAREN", "RBRACKET"):
                if depth == 0:
                    break
                depth -= 1
            elif tok.type == "SEMICOLON" and depth == 0:
                self.consume()
                break
            tokens.append(self.consume())
        return tokens

    def _skip_until_semi(self):
        while self.peek() and self.peek().type != "SEMICOLON":
            self.consume()
        if self.peek() and self.peek().type == "SEMICOLON":
            self.consume()
