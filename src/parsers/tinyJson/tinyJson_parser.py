from parsers.common import *

type Json = str | int | dict[str, Json]

def ruleJson(toks: TokenStream) -> Json:
    return alternatives("json", toks, [ruleObject, ruleString, ruleInt])

def ruleObject(toks: TokenStream) -> dict[str, Json]:
    toks.ensureNext("LBRACE")
    obj = ruleEntryList(toks)
    toks.ensureNext("RBRACE")
    return obj

def ruleEntryList(toks: TokenStream) -> dict[str, Json]:
    if toks.lookahead().type != "STRING":
        return {}
    return ruleEntryListNotEmpty(toks)

def ruleEntryListNotEmpty(toks: TokenStream) -> dict[str, Json]:
    key, value = ruleEntry(toks)
    entries = {key: value}
    # If there's a comma, parse further entries
    while toks.lookahead().type == "COMMA":
        toks.next()  
        k, v = ruleEntry(toks)
        entries[k] = v
    return entries

def ruleEntry(toks: TokenStream) -> tuple[str, Json]:
    # entry: STRING COLON json
    key = ruleString(toks)
    toks.ensureNext("COLON")
    value = ruleJson(toks)
    return key, value

def ruleString(toks: TokenStream) -> str:
    token = toks.ensureNext("STRING")
    return token.value[1:-1]

def ruleInt(toks: TokenStream) -> int:
    token = toks.ensureNext("INT")
    return int(token.value)

def parse(code: str) -> Json:
    parser = mkLexer("./src/parsers/tinyJson/tinyJson_grammar.lark")
    tokens = list(parser.lex(code))
    log.info(f'Tokens: {tokens}')
    toks = TokenStream(tokens)
    res = ruleJson(toks)
    toks.ensureEof(code)
    return res
