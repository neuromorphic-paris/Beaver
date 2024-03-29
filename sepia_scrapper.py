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
SEPIA_TYPES_DEFINITION_LINE = "struct event<type::{0}>"
TEMPLATE_SCRAPED_FUNCTIONS = ['make_split', 'join_observable', 'make_observable']

EVENT_TO_INDICATOR = 'EventTo'

def GetSepiaCode(Full = False):
    with open(SEPIA_SOURCE_FOLDER + 'sepia.hpp', 'r') as f:
        Lines = []
        FoundSepiaNamespace = False

        while True:
            Line = f.readline()
            if not Line:
                return Lines
            if SEPIA_NAMESPACE_INDICATOR in Line or Full:
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
            Name = 'sepia::'+RawType.strip()+'_event'
            Types[Name] = {'value': RawDefault, 'origin': 'sepia', 'fields': [], 'name': Name}
            Definition = SEPIA_TYPES_DEFINITION_LINE.format(RawType.strip())
            StudiedPart = ''
            for nLine, Line in enumerate(Lines):
                if Definition in Line and (COMMENT_INDICATOR not in Line or Line.index(COMMENT_INDICATOR) > Line.index(Definition)):
                    print("Found definition of type {0} at line {1}".format(RawType.strip(), nLine))
                    StudiedPart = StudiedPart + Line.split(COMMENT_INDICATOR)[0] + '\n'
                    continue
                if StudiedPart:
                    StudiedPart = StudiedPart + '\n' + Line
                    if '}' in Line:
                        break
            if not StudiedPart:
                continue
            StudiedPart = ('{'.join(StudiedPart.split('{')[1:]))
            StudiedPart = ('}'.join(StudiedPart.split('}')[:-1]))
            TypeLines = StudiedPart.split('\n')
            for Line in TypeLines:
                UsefulPart = Line.split(COMMENT_INDICATOR)[0].strip()
                if not UsefulPart:
                    continue
                if not ';' in UsefulPart:
                    continue
                UsefulPart = UsefulPart.split(';')[0]
                Field = {'name':None, 'type':None}
                for RawData in UsefulPart.split(' '):
                    if not RawData.strip():
                        continue
                    if Field['type'] is None:
                        Field['type'] = RawData.strip()
                    elif Field['name'] is None:
                        Field['name'] = RawData.strip()
                        Types[Name]['fields'] += [Field]
                        break

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
            Parameters += [{'name': Outs[1], 'type': Outs[0], 'param_number': nParameter, 'default': ''}]
            nParameter += 1
        elif len(Outs) != 2 and Outs.count("=") == 1:
            RawParameter, DefaultParameter = RawParameter.split('=')
            RawOuts = RawParameter.strip().split(' ')
            Outs = [RawOut for RawOut in RawOuts if RawOut]
            if len(Outs) == 2:
                Parameters += [{'name': Outs[1], 'type': Outs[0], 'param_number': nParameter, 'default' : DefaultParameter.strip()}]
                nParameter += 1
            else:
                print("Unexpected parameters definition : ")
                print(Outs)
                print("Used part :")
                print(UsefulPart)
                print("")
                return []
        else:
            print("Unexpected parameters definition : ")
            print(Outs)
            print("Used part :")
            print(UsefulPart)
            print("")
            return []
        if Parameters[-1]['name'] == 'handle_exception':
            Parameters[-1]['default'] = "[](std::exception_ptr) {}"
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
            Templates += [{'name': Outs[1], 'type' :Outs[0], 'template_number': nTemplate, 'default' :''}]
            nTemplate += 1
        elif len(Outs) != 2 and Outs.count("=") == 1:
            RawParameter, DefaultParameter = RawParameter.split('=')
            RawOuts = RawParameter.strip().split(' ')
            Outs = [RawOut for RawOut in RawOuts if RawOut]
            if len(Outs) == 2:
                Templates += [{'name': Outs[1], 'type': Outs[0], 'template_number': nTemplate, 'default' : DefaultParameter.strip()}]
                nTemplate += 1
            else:
                print("Unexpected templates definition between lines {0} and {1}: ".format(StartLine+1, EndLine+1))
                print(Outs)
                return Templates
        else:
            print("Unexpected templates definition between lines {0} and {1}: ".format(StartLine+1, EndLine+1))
            print(Outs)
            return Templates
    return Templates

def AddUtilities():
    Utilities = {}
    Utilities['read_header'] = {}
    Utilities['read_header']['name'] = 'read_header'
    Utilities['read_header']['origin'] = 'sepia'
    Utilities['read_header']['parameters'] = [{'name': 'event_stream', 'type': 'std::istream&', 'param_number':0, 'default':''}]
    Utilities['read_header']['outputs'] = [{'type' : 'header', 'name': 'header'}]
    return Utilities

def ScrapSepiaFile():
    Lines = GetSepiaCode()
    Modules = {}
    Utilities = {}
    for funcName in TEMPLATE_SCRAPED_FUNCTIONS:
        StartLine = FindTemplateFunctions(Lines, funcName)
        Modules[funcName] = {}
        Modules[funcName]['parameters'] = ExtractArguments(Lines, StartLine)
        Modules[funcName]['templates'] = ExtractTemplates(Lines, StartLine)
        for Template in Modules[funcName]['templates']:
            if Template['type'] == 'type': # That is actually sepia::type, also scrapped here.
                Template['type'] = 'sepia::type'
            for Parameter in Modules[funcName]['parameters']:
                if Template['name'] == Parameter['type'].strip('&'):
                    if Template['default']:
                        Template['default'] = '#Deduced' + ' (' + Template['default'] + ')'
                    else:
                        Template['default'] = '#Deduced'
        Modules[funcName]['origin'] = 'sepia'
        Modules[funcName]['name'] = funcName
        Modules[funcName]['ev_fields'] = []
        Modules[funcName]['has_operator'] = (funcName == 'make_split') # Hardcoded here, cause impossible anyway to get which template is created
        Modules[funcName]['ev_outputs'] = {}
        Modules[funcName]['has_event_to'] = False

    Utilities = AddUtilities()

    Types = GetSepiaTypes(Lines)

    return Modules, Types, Utilities

if __name__ == '__main__':
    args = sys.argv

    if len(args) > 1 and args[1][0] != '-':
        Filename = args[1]
        Lines = Is_Tarsier_Module(Filename)
        if Lines:
            Find_Make_Function(Filename, Lines)
    else:
        SepiaModules, SepiaTypes, SepiaUtilities = ScrapSepiaFile()
