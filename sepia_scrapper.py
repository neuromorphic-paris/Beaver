import sys
import os

SEPIA_FOLDER = 'third_party/sepia/'
SEPIA_SOURCE_FOLDER = SEPIA_FOLDER + 'source/'
SEPIA_NAMESPACE_INDICATOR = 'namespace sepia'

COMMENT_INDICATOR = '//'

FUNCTION_DEF_INDICATOR = 'inline'
TEMPLATE_LINE_INDICATOR = 'template'
TEMPLATE_PARAM_TYPE = 'typename'

SEPIA_TYPES_INDICATOR = "enum class type"
TEMPLATE_SCRAPED_FUNCTIONS = ['make_split', 'join_observable', 'make_observable']

def GetSepiaCode():
    with open(SEPIA_SOURCE_FOLDER + 'sepia.hpp', 'r') as f:
        Lines = []
        FoundSepiaNamespace = False

        while True:
            Line = f.readline()
            if not Line:
                return Lines
            if SEPIA_NAMESPACE_INDICATOR in Line:
                FoundSepiaNamespace = True
            if FoundSepiaNamespace:
                if Line[-1] == '\n':
                    Line = Line[:-1]
                Lines += [Line]

def AddWriteFunction():
    None # TODO

def GetSepiaTypes(Lines):
    StudiedPart = ''
    Types = {}
    for nLine, Line in enumerate(Lines):
        if SEPIA_TYPES_INDICATOR in Line:
            StudiedPart = StudiedPart + Line
        elif StudiedPart:
            StudiedPart = StudiedPart + Line
            if '}' in Line:
                break
    UsefulPart = (StudiedPart.split('{')[1].split('}')[0]).strip()
    for RawType in UsefulPart.split(','):
        if '=' in RawType:
            RawType, RawDefault = RawType.split('=')
            RawDefault = RawDefault.strip()
        else:
            RawDefault = None
        if RawType.strip():
            Types[RawType.strip()] = {'value': RawDefault, 'origin': 'sepia'}
    return Types

def FindTemplateFunctions(Lines, funcName):
    for nLine, Line in enumerate(Lines):
        if funcName in Line and (COMMENT_INDICATOR not in Line or Line.index(COMMENT_INDICATOR) > Line.index(funcName)):
            if FUNCTION_DEF_INDICATOR in Line:
                return nLine

def ExtractArguments(Lines, StartLine):
    Parameters = []
    
    StudiedPart = Lines[StartLine]
    EndLine = StartLine
    while StudiedPart.count(')') == 0:
        EndLine += 1
        StudiedPart = StudiedPart + ' ' + Lines[EndLine]
    UsefulPart = StudiedPart.split(')')[0].split('(')[1]
    nParameter = 0
    for RawParameter in UsefulPart.split(','):
        RawOuts = RawParameter.strip().split(' ')
        Outs = [RawOut for RawOut in RawOuts if RawOut]

        if len(Outs) == 2:
            Parameters += [{'name': Outs[1], 'type': Outs[0], 'param_number': nParameter}]
            nParameter += 1
        elif len(Outs) != 2 and Outs.count("=") == 1:
            RawParameter, DefaultParameter = RawParameter.split('=')
            RawOuts = RawParameter.strip().split(' ')
            Outs = [RawOut for RawOut in RawOuts if RawOut]
            if len(Outs) == 2:
                Parameters += [{'name': Outs[1], 'type': Outs[0], 'param_number': nParameter, 'default' : DefaultParameter.strip()}]
                nParameter += 1
            else:
                print "Unexpected parameters definition : "
                print Outs
                print "Used part :"
                print UsefulPart
                print ""
                return []
        else:
            print "Unexpected parameters definition : "
            print Outs
            print "Used part :"
            print UsefulPart
            print ""
            return []
    return Parameters

def ExtractTemplates(Lines, FuncStartLine):
    Templates = []

    StartLine = FuncStartLine-1

    while not TEMPLATE_LINE_INDICATOR in Lines[StartLine]:
        StartLine -= 1
    EndLine = StartLine
    StudiedPart = Lines[StartLine]
    while ">" not in StudiedPart:
        EndLine += 1
        StudiedPart = StudiedPart + Lines[EndLine]
    if StudiedPart.count('>') > 1:
        StudiedPart = StudiedPart.split('>')[0]

    UsefulPart = StudiedPart.split('>')[0].split('<')[1]
    nTemplate = 0
    for RawParameter in UsefulPart.split(','):
        RawOuts = RawParameter.strip().split(' ')
        Outs = [RawOut for RawOut in RawOuts if RawOut]

        if len(Outs) == 2:
            Templates += [{'name': Outs[1], 'type' :Outs[0], 'template_number': nTemplate}]
            nTemplate += 1
        elif len(Outs) != 2 and Outs.count("=") == 1:
            RawParameter, DefaultParameter = RawParameter.split('=')
            RawOuts = RawParameter.strip().split(' ')
            Outs = [RawOut for RawOut in RawOuts if RawOut]
            if len(Outs) == 2:
                Templates += [{'name': Outs[1], 'type': Outs[0], 'template_number': nTemplate, 'default' : DefaultParameter.strip()}]
                nTemplate += 1
            else:
                print "Unexpected templates definition between lines {0} and {1}: ".format(StartLine+1, EndLine+1)
                print Outs
                return Templates
        else:
            print "Unexpected templates definition between lines {0} and {1}: ".format(StartLine+1, EndLine+1)
            print Outs
            return Templates
    return Templates

def ScrapSepiaFile():
    Lines = GetSepiaCode()
    Modules = {}
    for funcName in TEMPLATE_SCRAPED_FUNCTIONS:
        StartLine = FindTemplateFunctions(Lines, funcName)
        Modules[funcName] = {}
        Modules[funcName]['parameters'] = ExtractArguments(Lines, StartLine)
        Modules[funcName]['templates'] = ExtractTemplates(Lines, StartLine)
        Modules[funcName]['origin'] = 'sepia'
        Modules[funcName]['name'] = funcName
    Types = GetSepiaTypes(Lines)
    return Modules, Types

if __name__ == '__main__':
    args = sys.argv

    if len(args) > 1 and args[1][0] != '-':
        Filename = args[1]
        Lines = Is_Tarsier_Module(Filename)
        if Lines:
            Find_Make_Function(Filename, Lines)
    else:
        SepiaModules, SepiaTypes = ScrapSepiaFile()
