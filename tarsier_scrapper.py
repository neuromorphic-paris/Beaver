import sys
import os

TARSIER_FOLDER = 'third_party/tarsier/'
TARSIER_SOURCE_FOLDER = 'third_party/tarsier/source/'
TARSIER_NAMESPACE_INDICATOR = 'namespace tarsier'

COMMENT_INDICATOR = '//'
MAKE_FUNCTION_INDICATOR = 'make_'

TEMPLATE_LINE_INDICATOR = 'template'
TEMPLATE_PARAM_TYPE = 'typename'
CLASS_INDICATOR = 'class '

VARIABLE_CHARS = 'abcdefghijklmnopqrstuvwxyz_'
EVENT_OPERATOR_INDICATOR = 'operator()'

def GetTarsierCode(Filename, Full = False):
    with open(TARSIER_SOURCE_FOLDER + Filename, 'r') as f:
        Lines = []
        FoundTarsierNamespace = False

        while True:
            Line = f.readline()
            if not Line:
                return Lines
            if TARSIER_NAMESPACE_INDICATOR in Line or Full:
                FoundTarsierNamespace = True
            if FoundTarsierNamespace:
                if Line[-1] == '\n':
                    Line = Line[:-1]
                Lines += [Line]

def Find_Make_Function(Filename, Lines):
    ExpectedFunction = Filename.split('.')[0]
    FoundMakeFunction = False
    for nLine, Line in enumerate(Lines):
        if not COMMENT_INDICATOR in Line and MAKE_FUNCTION_INDICATOR in Line:
            if Line.split(MAKE_FUNCTION_INDICATOR)[1][:len(ExpectedFunction)] == ExpectedFunction:
                FoundMakeFunction = True
                print "Found expected function make at line {0} ({1})".format(nLine + 1, ExpectedFunction)
                return nLine
            else:
                FoundMakeFunction = True
                RHS = Line.split(MAKE_FUNCTION_INDICATOR)[1]
                if '(' in RHS:
                    RHS = RHS.split('(')[0]
                print "Unexpected function make at line {0} : ".format(nLine + 1, RHS)
                return nLine
    if not FoundMakeFunction:
        print "Unable to find correct {0} function.".format(MAKE_FUNCTION_INDICATOR)
        return None

# We  assume here that only one tarsier class and module exist per file> Otherwise, use following lines as done with sepia
#def FindAssociatedClass(Filename, Lines):
#    ExpectedFunction = Filename.split('.')[0]
#    for nLine, Line in enumerate(Lines):
#        if CLASS_INDICATOR in Line and (not COMMENT_INDICATOR in Line or Line.index(COMMENT_INDICATOR) > Line.index(CLASS_INDICATOR)):
#            StudiedPart = Line.split(CLASS_INDICATOR)[0]
#            for nChar, Char in StudiedPart:
#                if Char not in VARIABLE_CHARS:
#                    if StudiedPart[:nChar] == ExpectedFunction:
#                        return nLine
#
#def ExtractClassLines(Lines, ClassStartLine):
#    nOpen = 0
#    nClose = 0
#    EndLine = ClassStartLine
#    while nOpen == 0 or nOpen > nClose:
#        Line = Lines[EndLine]
#        StudiedPart = Line.split(COMMENT_INDICATOR)[-1]
#        nOpen += StudiedPart.count('{')
#        nClose += StudiedPart.count('}')
#        EndLine += 1
#    return Lines[ClassStartLine:EndLine]

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

        if len(Outs) != 2:
            print "Unexpected parameters definition : "
            print Outs
            return []
        Parameters += [{'name': Outs[1], 'type': Outs[0], 'param_number': nParameter, 'default': ''}]
        nParameter += 1
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

        if len(Outs) != 2:
            print "Unexpected templates definition between lines {0} and {1}: ".format(StartLine+1, EndLine+1)
            print Outs
            return Templates
        Templates += [{'name': Outs[1], 'type' :Outs[0], 'template_number': nTemplate}]
        nTemplate += 1
    return Templates

def ExtractEventRequiredFields(Lines, FuncName):
    StartLine = None
    for nLine, Line in enumerate(Lines):
        if EVENT_OPERATOR_INDICATOR in Line and (not COMMENT_INDICATOR in Line or Line.index(COMMENT_INDICATOR) > Line.index(EVENT_OPERATOR_INDICATOR)):
            StartLine = nLine
            print "Found oprator at line {0}".format(StartLine)
            break
    if StartLine is None:
        print "Unable to find operator() for function {0}".format(FuncName)
        return []
    EndLine = StartLine
    StudiedPart = Line.split(EVENT_OPERATOR_INDICATOR)[1]
    while StudiedPart.count(')') == 0:
        EndLine += 1
        StudiedPart = StudiedPart + ' ' + Lines[EndLine].split(COMMENT_INDICATOR)[-1]
    UsefulPart = StudiedPart.split(')')[0].split('(')[1]
    TypeName = ''
    VarName = ''
    for Part in UsefulPart.split(' '):
        if Part:
            if not TypeName:
                TypeName = Part
            else:
                VarName = Part
                break
    if not VarName:
        print "Unable to parse event variable name in operator of function {0}".format(FuncName)
        return []
    StartLine = EndLine
    StudiedPart = Lines[StartLine].split('{')[-1]

    RequiredFields = []
    
    nOpen = 1
    nClose = 0
    EndLine = StartLine + 1
    while nOpen > nClose:
        Line = Lines[EndLine]
        StudiedPart = Line.split(COMMENT_INDICATOR)[-1]
        nOpen += StudiedPart.count('{')
        nClose += StudiedPart.count('}')
        EndLine += 1
        if VarName + '.' in StudiedPart:
            for AppearingField in StudiedPart.split(VarName + '.')[1:]:
                for nChar, Char in enumerate(AppearingField):
                    if Char not in VARIABLE_CHARS:
                        break
                FinalField = AppearingField[:nChar]
                if FinalField not in RequiredFields:
                    RequiredFields += [FinalField]
        if not Line:
            print "Unable to end properly the operator() function definition for {0}".format(FuncName)
            return RequiredFields
    return RequiredFields

def ScrapTarsierFolder():
    Filenames = os.listdir(TARSIER_SOURCE_FOLDER)
    Modules = {}
    for Filename in Filenames:
        ModuleName = Filename.split('.hpp')[0]
        if Filename[0] == '.':
            continue
        print ""
        print " -> " + Filename
        Lines = GetTarsierCode(Filename)
        if Lines:
            StartLine = Find_Make_Function(Filename, Lines)
            if not StartLine is None:
                Modules[ModuleName] = {}
                Modules[ModuleName]['parameters'] = ExtractArguments(Lines, StartLine)
                Modules[ModuleName]['templates'] = ExtractTemplates(Lines, StartLine)
                Modules[ModuleName]['origin'] = 'tarsier'
                Modules[ModuleName]['name'] = ModuleName
                Modules[ModuleName]['ev_fields'] = ExtractEventRequiredFields(Lines, ModuleName)
    return Modules

if __name__ == '__main__':
    args = sys.argv

    if len(args) > 1 and args[1][0] != '-':
        Filename = args[1]
        Lines = GetTarsierCode(Filename)
        if Lines:
            Find_Make_Function(Filename, Lines)
    else:
        Modules = ScrapTarsierFolder()
