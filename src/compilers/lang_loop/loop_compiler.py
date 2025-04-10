from lang_loop.loop_ast import *
from common.wasm import *
import lang_loop.loop_tychecker as tychecker
from common.compilerSupport import *
import common.utils as utils
from typing import List

def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    result: list[WasmInstr] = []
    for s in stmts:
        result.extend(compileStmt(s))
    return result

def compileStmt(s: stmt) -> list[WasmInstr]:
    match s:
        case StmtExp(e):
            return compileExp(e)
        case Assign(i, e):
            # Stack: [expr] -> [set_var] (e.g. x = exp;2 + 5)
            return compileExp(e) + [WasmInstrVarLocal('set', WasmId('$' + i.name))]
        case IfStmt(cond, thn, els):
            # Stack: [cond] -> [then|else]
            return compileExp(cond) + [WasmInstrIf(None, compileStmts(thn), compileStmts(els))]
        case WhileStmt(cond, bod):
            # Stack: [cond] -> [loop_body] -> [cond] -> [branch]
            return compileExp(cond) + [WasmInstrIf(None, [WasmInstrLoop(WasmId('$whileLoop'), compileStmts(bod) + compileExp(cond) + [WasmInstrBranch(WasmId('$whileLoop'), True)])], [])]
        
def compileExp(expr: exp) -> list[WasmInstr]:
    match expr:
        case IntConst(value):
            # Stack: [] -> [i64_const]
            return [WasmInstrConst('i64', value)]
        case BoolConst(value, _):
            # Stack: [] -> [i32_const]
            return [WasmInstrConst('i32', int(value))] # Returns 1 if True, 0 if False
        case Name(name):
            # Stack: [] -> [local.gett]
            return [WasmInstrVarLocal('get', WasmId('$' + name.name))]
        case Call(id, args, t):
            # Stack: [arg1, arg2, ...] -> [call_result]
            p = '$' + id.name
            f = ''
            t_check = t
            if len(args) > 0:
                t_check = args[0].ty

            match tyOfExp(t_check):
                case Int():
                    f = 'i64'
                case Bool():
                    f = 'bool'
            match id.name:
                case 'print':
                    p = '$print_' + f
                case 'input_int':
                    p = '$input_' + f 
                case _:
                    raise Exception("Unknown function")
            return utils.flatten([compileExp(e) for e in args]) + [WasmInstrCall(WasmId(p))]
        # Unary operations -> left expr on stack, than do mathematic op on them
        case UnOp(op, arg):
            match op:
                case USub():
                    # Stack: [] -> [0, arg] -> [0-arg]
                    return [WasmInstrConst('i64', 0)] + compileExp(arg) + [WasmInstrNumBinOp('i64', 'sub')]
                case Not():
                    # Stack: [] -> [0, arg] -> [arg==0]
                    # Negate by checking if equals False since that is defined as only 0
                    return [WasmInstrConst('i32', 0)] + compileExp(arg) + [WasmInstrIntRelOp('i32', 'eq')]
        # Binary operations -> left and right expr on stack, than do mathematic op on them
        case BinOp(left, op, right):
            match op:
                case Add():
                     # Stack: [left, right] -> [left+right]
                    return compileExp(left) + compileExp(right) + [WasmInstrNumBinOp('i64', 'add')] 
                case Sub():
                    # Stack: [left, right] -> [left-right]
                    return compileExp(left) + compileExp(right) + [WasmInstrNumBinOp('i64', 'sub')] 
                case Mul():
                    # Stack: [left, right] -> [left*right]
                    return compileExp(left) + compileExp(right) + [WasmInstrNumBinOp('i64', 'mul')] 
                case And():
                    # Stack: [left] -> [if left then right else 0]
                    return compileExp(left) + [WasmInstrIf("i32", compileExp(right), [WasmInstrConst('i32', 0)])]
                case Or(): 
                    # Stack: [left] -> [if left then 1 else right]
                    return compileExp(left) + [WasmInstrIf("i32", [WasmInstrConst('i32', 1)], compileExp(right))]
                case Less():
                    # Stack: [left, right] -> [left<right]
                    return compileExp(left) + compileExp(right) + [WasmInstrIntRelOp('i64', 'lt_s')] 
                case LessEq():
                    # Stack: [left, right] -> [left<=right]
                    return compileExp(left) + compileExp(right) + [WasmInstrIntRelOp('i64', 'le_s')]
                case Greater():
                    # Stack: [left, right] -> [left>right]
                    return compileExp(left) + compileExp(right) + [WasmInstrIntRelOp('i64', 'gt_s')]
                case GreaterEq():
                    # Stack: [left, right] -> [left>=right]
                    return compileExp(left) + compileExp(right) + [WasmInstrIntRelOp('i64', 'ge_s')]
                case Eq():
                    # Stack: [left, right] -> [left==right]
                    match tyOfExp(left.ty):
                        # Same pattern, only different type
                        case Int():
                            return compileExp(left) + compileExp(right) + [WasmInstrIntRelOp('i64', 'eq')]
                        case Bool():
                            return compileExp(left) + compileExp(right) + [WasmInstrIntRelOp('i32', 'eq')]
                case NotEq():
                    # Stack: [left, right] -> [left!=right]
                    match tyOfExp(left.ty):
                        # Same pattern, only different type
                        case Int():
                            return compileExp(left) + compileExp(right) + [WasmInstrIntRelOp('i64', 'ne')]
                        case Bool():
                            return compileExp(left) + compileExp(right) + [WasmInstrIntRelOp('i32', 'ne')]
        


def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    vars = list(tychecker.tycheckModule(m).items())
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals:List[tuple[WasmId, WasmValtype]] = [(WasmId('$'+x[0].name), mapTyToWasmValType(x[1].ty)) for x in vars]
    wasm_imports = wasmImports(cfg.maxMemSize)
    wasm_exports = [WasmExport('main', WasmExportFunc(idMain))]
    funcs =[WasmFunc(idMain, [], None, locals, instrs)]

    return WasmModule(
        wasm_imports,
        wasm_exports,
        globals=[],
        data=[],
        funcTable=WasmFuncTable([idMain]), # idMain is optional, not used here
        funcs=funcs
        ) 

def mapTyToWasmValType(t: ty)->WasmValtype:
    match t:
        case Int():
            return 'i64'
        case Bool():
            return 'i32'

def boolToInt32(b: bool) -> int:
    return 1 if b else 0
  

def tyOfExp(e: Optional[resultTy]) -> ty: 
    match e:
        case NotVoid():
            return e.ty
        case Void() | None :
            return Int()