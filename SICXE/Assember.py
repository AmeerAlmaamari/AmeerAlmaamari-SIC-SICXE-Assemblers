import re
from symtable import SymbolTable
import instfile


class Entry:
    def __init__(self, string, token, attribute, block=0):
        self.string = string
        self.token = token
        self.att = attribute
        self.block = block


symtable = []
inst = 0
objectCode = True
startLoadingAddress = 0
programSize = 0
relocationList = []


def lookup(s):
    for i in range(0, len(symtable)):
        if s == symtable[i].string:
            return i
    return -1


def insert(string, token, attribute, block=0):
    symtable.append(Entry(string, token, attribute, block))
    return len(symtable) - 1


def init():
    for i in range(0, instfile.inst.__len__()):
        insert(instfile.inst[i], instfile.token[i], instfile.opcode[i])
    for i in range(0, instfile.directives.__len__()):
        insert(instfile.directives[i], instfile.dirtoken[i], instfile.dircode[i])


file = open('input.sic', 'r')
fileContent = []
bufferindex = 0
tokenval = 0
lineno = 1
pass1or2 = 1
locctr = [0, 0, 0] # -> to add a new block add 0
block = 0
lookahead = ''
startLine = True
baseValue = -1

Xbit4set = 0x800000
Bbit4set = 0x400000
Pbit4set = 0x200000
Ebit4set = 0x100000

Nbitset = 2
Ibitset = 1
objectCode = True

Xbit3set = 0x8000
Bbit3set = 0x4000
Pbit3set = 0x2000
Ebit3set = 0x1000


def is_hex(s):
    if s[0:2].upper() == '0X':
        try:
            int(s[2:], 16)
            return True
        except ValueError:
            return False
    else:
        return False


def lexan():
    global fileContent, tokenval, lineno, bufferindex, locctr, startLine

    while True:
        if len(fileContent) == bufferindex:
            return 'EOF'
        elif fileContent[bufferindex] == '\n':
            startLine = True
            bufferindex = bufferindex + 1
            lineno += 1
        else:
            break
    if fileContent[bufferindex].isdigit():
        tokenval = int(fileContent[bufferindex])  # all number are considered as decimals
        bufferindex = bufferindex + 1
        return ('NUM')
    elif is_hex(fileContent[bufferindex]):
        tokenval = int(fileContent[bufferindex][2:], 16)  # all number starting with 0x are considered as hex
        bufferindex = bufferindex + 1
        return ('NUM')
    elif fileContent[bufferindex] in ['+', '#', '@', ',','*']:
        c = fileContent[bufferindex]
        bufferindex = bufferindex + 1
        return (c)
    else:
        if (fileContent[bufferindex].upper() == 'C') and (fileContent[bufferindex + 1] == '\''):
            bytestring = ''
            bufferindex += 2
            while fileContent[bufferindex] != '\'':  # should we take into account the missing ' error?
                bytestring += fileContent[bufferindex]
                bufferindex += 1
                if fileContent[bufferindex] != '\'':
                    bytestring += ' '
            bufferindex += 1
            bytestringvalue = "".join("%02X" % ord(c) for c in bytestring)
            bytestring = '_' + bytestring
            p = lookup(bytestring)
            if p == -1:
                p = insert(bytestring, 'STRING', bytestringvalue)
            tokenval = p
        elif (fileContent[bufferindex] == '\''):
            bytestring = ''
            bufferindex += 1
            while fileContent[bufferindex] != '\'':
                bytestring += fileContent[bufferindex]
                bufferindex += 1
                if fileContent[bufferindex] != '\'':
                    bytestring += ' '
            bufferindex += 1
            bytestringvalue = "".join("%02X" % ord(c) for c in bytestring)
            bytestring = '_' + bytestring
            p = lookup(bytestring)
            if p == -1:
                p = insert(bytestring, 'STRING', bytestringvalue)
            tokenval = p
        elif (fileContent[bufferindex].upper() == 'X') and (fileContent[bufferindex + 1] == '\''):
            bufferindex += 2
            bytestring = fileContent[bufferindex]
            bufferindex += 2

            bytestringvalue = bytestring
            if len(bytestringvalue) % 2 == 1:
                bytestringvalue = '0' + bytestringvalue
            bytestring = '_' + bytestring
            p = lookup(bytestring)
            if p == -1:
                p = insert(bytestring, 'HEX', bytestringvalue)  # should we deal with literals?
            tokenval = p
        else:
            p = lookup(fileContent[bufferindex].upper())
            if p == -1:
                if startLine == True:
                    p = insert(fileContent[bufferindex].upper(), 'ID', locctr[block],
                               block)  # should we deal with case-sensitive?
                else:
                    p = insert(fileContent[bufferindex].upper(), 'ID', -1, -1)  # forward reference
            else:
                if (symtable[p].att == -1) and (startLine == True):
                    symtable[p].att = locctr[block]
                    symtable[p].block = block  # ADDED BY ME, TO FIX INCORRECT BLOCKS FOR FORWARD REFERENCE
            tokenval = p
            bufferindex = bufferindex + 1
        return (symtable[p].token)


def error(s):
    global lineno
    print('line ' + str(lineno) + ': ' + s)




def checkAddressRange(PCrAddress):
    global lineno, baseValue, locctr
    BaseAddres = baseValue - locctr[block]
    if 2047 >= PCrAddress and PCrAddress >= -2048:
        return 'PC'
    elif baseValue < 0:
        error('Base not initialized')
    elif 4096 >= BaseAddres and BaseAddres >= 0:
        return 'BASE'
    else:
        error('Relative addressing out of range in line:', lineno)
        return None




def match(token):
    global lookahead
    if lookahead == token:
        lookahead = lexan()
    else:
        error('Syntax error')



def index(isExtended=False):
    global inst
    if lookahead == ',':
        match(',')

        if pass1or2 == 2:
            if isExtended:
                inst += Xbit4set
            else:
                inst += Xbit3set
        prevRegIndex = tokenval
        match('REG')
        if (symtable[prevRegIndex].string != 'X') and (pass1or2 == 2):
            error('Index register should be X')


def rest3(prevStmtment):
    global inst
    if startLine == False:
        inst += symtable[tokenval].att
        match('ID')
        index()
    else:
        if symtable[prevStmtment].string != 'RSUB':
            error('Statement EROOR')


def rest4():
    global lookahead, pass1or2, inst
    if lookahead == ",":
        match(',')
        if pass1or2 == 2:
            inst += symtable[tokenval].att
        match('REG')


def rest6(isExtended, ATorHASH):
    global lookahead, pass1or2, inst, baseValue

    if lookahead == 'ID':
        if pass1or2 == 2:
            if isExtended==False:
             PcAddres = symtable[tokenval].att - locctr[block]
             BaseAddres =   locctr[block]-baseValue
             PorB = checkAddressRange(PcAddres)
            inst+=symtable[tokenval].att
            if isExtended==False:
               if PorB == 'PC':
                inst += PcAddres
                inst += Pbit3set
               elif PorB == 'BASE':
                inst += BaseAddres
                inst += Bbit3set
            if ATorHASH == '#':
                if isExtended:
                    inst += Ibitset << 24
                    inst += Ebit4set
                else:
                    inst += Ibitset << 16
            elif ATorHASH == '@':
                if isExtended:
                    inst += Nbitset << 24
                    inst += Ebit4set
        match('ID')
    elif lookahead == 'NUM':
        if pass1or2 == 2:
            if ATorHASH == '#':
                inst += tokenval
                if isExtended:
                    inst += Ibitset << 24
                    inst += Ebit4set
                else:
                    inst += Ibitset << 16
            elif ATorHASH == '@':
                if isExtended:
                    inst += tokenval
                    inst += Nbitset << 24
                    inst += Ebit4set
                else:
                    PcAddres = symtable[tokenval].att - locctr[block]
                    BaseAddres =   symtable[tokenval].att -baseValue
                    PorB = checkAddressRange(PcAddres)
                    if PorB == 'BASE':
                        inst += BaseAddres
                        inst += Bbit3set
                    elif PorB == 'PC':
                        inst += PcAddres & 0xFFF
                        inst += Pbit3set

                    inst += Nbitset << 16
        match('NUM')


def rest5(prevStmtment, isExtended=False):
    global lookahead, pass1or2, inst, startLine

    if lookahead == 'ID':
        if startLine == False:
            if pass1or2 == 2:
                if isExtended:
                    inst += symtable[tokenval].att
                    inst += Nbitset << 24
                    inst += Ibitset << 24
                    inst += Ebit4set
                else:
                    PcAddres = symtable[tokenval].att - locctr[block]
                    BaseAddres = symtable[tokenval].att -baseValue
                    PorB = checkAddressRange(PcAddres)

                    if PorB == 'PC':
                        inst += PcAddres & 0xFFF
                        inst += Pbit3set
                    elif PorB == 'BASE':
                        inst += BaseAddres
                        inst += Bbit3set
                    inst += Nbitset << 16
                    inst += Ibitset << 16

            match('ID')
            index(isExtended)
        else:
            if symtable[prevStmtment].string != 'RSUB':
                error('Statement EROR')
    elif lookahead == 'NUM':
        if isExtended:
            inst += tokenval
            inst += Nbitset << 24
            inst += Ebit4set
        else:
            PcAddres = tokenval - locctr[block]
            BaseAddres =  locctr[block]-baseValue
            PorB = checkAddressRange(PcAddres)
            if PorB == 'PC':
                inst += PcAddres
                inst += Pbit3set
            elif PorB == 'BASE':
                inst += BaseAddres
                inst += Bbit3set
            inst += Nbitset << 16
        match('NUM')
    elif lookahead == '#':
        match('#')
        rest6(isExtended, '#')
    elif lookahead == '@':
        match('@')
        rest6(isExtended, '@')


def rest20(nbrreg):
    global inst

    shiftstep = 12

    for i in range(nbrreg + 1):
        match(",")

        inst += symtable[tokenval].att << shiftstep

        shiftstep -= 4

        match("REG")

def rest21(operands):
    global inst
    if operands == 2:
        match(',')
        if pass1or2 == 2:
            inst += (symtable[tokenval].att << 8)
        match('REG')

    elif operands == 3:
        match(',')
        if pass1or2 == 2:
            inst += (symtable[tokenval].att << 8)
        match('REG')
        match(',')
        if pass1or2 == 2:
            inst += (symtable[tokenval].att << 4)
        match('REG')

    elif operands == 4:
        match(',')
        if pass1or2 == 2:
            inst += (symtable[tokenval].att << 8)
        match('REG')
        match(',')
        if pass1or2 == 2:
            inst += (symtable[tokenval].att << 4)
        match('REG')
        match(',')
        if pass1or2 == 2:
            inst += (symtable[tokenval].att)
        match('REG')

def stmt():
    global locctr, startLine, inst

    startLine = False
    prevStmtment = tokenval

    # FORMATS
    if lookahead == 'f1':
        if pass1or2 == 2:
            inst = symtable[tokenval].att
        locctr[block] += 1
        match('f1')

        if pass1or2 == 2:
                print('T {:06X} {:02X} {:02X}'.format(locctr[block] - 1, 1, inst))

    elif lookahead == 'f2':
        if pass1or2 == 2:
            inst = symtable[tokenval].att << 8
        locctr[block] += 2
        match('f2')
        # startLine = True
        if pass1or2 == 2:
            inst += symtable[tokenval].att << 4
        match('REG')
        rest4()
        

        if pass1or2 == 2:
                print('T {:06X} {:02X} {:04X}'.format(locctr[block] - 2, 2, inst))

    elif lookahead == 'f3':
        if pass1or2 == 2:
            inst = symtable[tokenval].att << 16
        locctr[block] += 3
        match('f3')
        rest5(prevStmtment)
        if pass1or2 == 2:
                print('T {:06X} {:02X} {:06X}'.format(locctr[block] - 3, 3, inst))

    elif lookahead == 'f5':
        if pass1or2 == 2:
            inst = symtable[tokenval].att <<16
        match('f5')
        locctr[block] += 3
        nbrreg = tokenval
        if pass1or2 == 2:
            inst += tokenval <<16
        match("NUM")

        rest20(nbrreg)
        if pass1or2 == 2:
            print("T {:06X} {:02X} {:06X}".format(locctr[block] - 3, 3, inst))

    elif lookahead == '+':
        match('+')
        if pass1or2 == 2:
            inst = symtable[tokenval].att << 24
        if locctr[block] + 1 not in relocationList:
            relocationList.append(locctr[block] + 1)
        locctr[block] += 4
        match('f3')

        rest5(prevStmtment, True)
        if pass1or2 == 2:
                print('T {:06X} {:02X} {:08X}'.format(locctr[block] - 4, 4, inst))
    
    elif lookahead == '*':
        locctr[block] += 3
        match('*')
        if pass1or2 == 2:
            inst = symtable[tokenval].att << 16
        match('f2')
        if pass1or2 == 2:
            inst += tokenval << 16
        numberOfReg = tokenval
        match('NUM')
        match(',')
        if pass1or2 == 2:
            inst += (symtable[tokenval].att << 12)
        match('REG')
        rest21(numberOfReg)
        if pass1or2 == 2:
            if (not objectCode):
                print('{:06X}'.format(inst))
            else:
                print('T {:06X} {:02X} {:06X}'.format(locctr[block] - 3, 3, inst))



def rest2():
    global locctr, symtable
    if lookahead == 'STRING':
        size = int(len(symtable[tokenval].att) / 2)
        locctr[block] += size
        if pass1or2 == 2:
            if objectCode:
                print('T {:06X} {:02X}'.format(locctr[block] - size, size) + ' ' + symtable[tokenval].att)
            else:
                print(symtable[tokenval].att)
        match('STRING')

    elif lookahead == 'HEX':
        size = int(len(symtable[tokenval].att) / 2)
        locctr[block] += size
        if pass1or2 == 2:
            if objectCode:
                print('T {:06X} {:02X}'.format(locctr[block] - size, size) + ' ' + symtable[tokenval].att)
            else:
                print(symtable[tokenval].att)
        match('HEX')
    else:
        error("EROOR")


def data():
    global locctr
    if lookahead == 'WORD':
        match('WORD')
        locctr[block] += 3
        if pass1or2 == 2:
            if objectCode:
                print('T {:06X} {:02X} {:06X}'.format(locctr[block] - 3, 3, tokenval))
            else:
                print('0x{:06X}'.format(tokenval))
        match('NUM')

    elif lookahead == 'RESW':
        match('RESW')
        locctr[block] += tokenval * 3

        if (pass1or2 == 2) and not objectCode:
            for i in range(tokenval):
                print("000000")
        match('NUM')
    elif lookahead == 'RESB':
        match('RESB')
        locctr[block] += tokenval
        if (pass1or2 == 2) and not objectCode:
            for i in range(tokenval):
                print("00")
        match('NUM')
    elif lookahead == 'BYTE':
        match('BYTE')
        rest2()
    else:
        error("ERROR")


def header():
    global locctr, symtable, startLoadingAddress, programSize
    tok = tokenval

    match('ID')
    match('START')
    startLoadingAddress = locctr[block] = tokenval
    symtable[tok].att = tokenval
    match('NUM')

    if pass1or2 == 2:
        if objectCode:
            print('H ' + symtable[tok].string + ' {:06X} {:06X}'.format(startLoadingAddress, programSize))

def rest7():
    global block
    if lookahead == 'CDATA':
        block = 1
        match('CDATA')
    elif lookahead == 'CBLCK':
        block = 2
        match('CBLCK')
    else:
        block = 0


def rest1():
    if lookahead in ['WORD', 'RESW', 'RESB', 'BYTE']:
        data()
        body()
    elif lookahead in ['f1', 'f2', 'f3', '+','f5','*']:
        stmt()
        body()


def body():
    global baseValue, startLine
    if lookahead == 'ID':
        match('ID')
        rest1()
    elif lookahead in ['f1', 'f2', 'f3', '+','f5','*']:
        stmt()
        body()
    elif lookahead == "BASE":
        startLine = False
        match('BASE')
        if pass1or2 == 2:
            baseValue = symtable[tokenval].att
        match('ID')
        body()
    elif lookahead == 'USE':
        match('USE')
        rest7()
        body()
    elif lookahead != 'END':
        error('Syntax Error')


def tail():
    global programSize, startLine
    programSize = locctr[block] - startLoadingAddress
    match('END')
    startLine = False
    previousTokenIndex = tokenval
    match('ID')

    if (pass1or2 == 2) and objectCode:
        for i in relocationList:
            print('M {0:06X} 5'.format(i))
        print('E {:06X}'.format(symtable[previousTokenIndex].att))

    if pass1or2 == 1:
        sizeDefault = locctr[0]
        sizeCDATA = locctr[1]
        sizeCBLCK = locctr[2]

        for symbol in symtable:
            if symbol.token == 'ID' and symbol.block == 1:
                symbol.att += sizeDefault
            elif symbol.token == 'ID' and symbol.block == 2:
                symbol.att += sizeDefault + sizeCDATA
            


def parse():
    global lookahead
    lookahead = lexan()
    header()
    body()
    tail()


def main():
    global file, fileContent, locctr, pass1or2, bufferindex, lineno
    init()
    w = file.read()
    fileContent = re.split("([\W])", w)
    i = 0
    while True:
        while (fileContent[i] == ' ') or (fileContent[i] == '') or (fileContent[i] == '\t'):
            del fileContent[i]
            if len(fileContent) == i:
                break
        i += 1
        if len(fileContent) <= i:
            break
    if fileContent[len(fileContent) - 1] != '\n':  # to be sure that the content ends with new line
        fileContent.append('\n')
    for pass1or2 in range(1, 3):
        parse()
        bufferindex = 0
        locctr = [0, 0, 0]
        lineno = 1

    file.close()


main()

