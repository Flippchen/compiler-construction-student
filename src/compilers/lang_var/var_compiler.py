from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *


def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    result: list[WasmInstr] = []
    for s in stmts:
        result.extend(compileStmt(s))
    return result

def compileStmt(s: stmt) -> list[WasmInstr]:
    match s:
        case StmtExp(e):
            instrs = compileExp(e)
            return instrs
        case Assign(x, e):
            instrs = compileExp(e)
            instrs.append(WasmInstrVarLocal('set', identToWasmId(x)))
            return instrs

def compileExp(e: exp) -> list[WasmInstr]:
    match e:
        case IntConst(value):
            return [WasmInstrConst('i64', value)]
        case Call(id, args):
            match (id.name, args):
                case ('input_int', []):
                    return [WasmInstrCall(WasmId('$input_i64'))]
                case ('print', [e]):
                    return compileExp(e) + [WasmInstrCall(WasmId('$print_i64'))]
                case _:
                    raise CompileError.typeError(f'Invalid function call of {id.name} with {len(args)} arguments')
        case UnOp(USub(), sub):
            return compileExp(sub) + [WasmInstrConst('i64', -1), WasmInstrNumBinOp('i64', 'mul')]
        case BinOp(left, op, right):
            instrs = compileExp(left) + compileExp(right)
            match op:
                case Add(): instrs.append(WasmInstrNumBinOp('i64', 'add'))
                case Sub(): instrs.append(WasmInstrNumBinOp('i64', 'sub'))
                case Mul(): instrs.append(WasmInstrNumBinOp('i64', 'mul'))
            return instrs
        case Name(name):
            return [WasmInstrVarLocal('get', identToWasmId(name))]

def identToWasmId(x: ident) -> WasmId:
    return WasmId(f'${x.name}')



def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule: 
    """
    Compiles the given module.
    """
    vars = var_tychecker.tycheckModule(m) 
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x), 'i64') for x in vars]
    return WasmModule(
        imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals=[],
        data=[],
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, locals, instrs)]
        )