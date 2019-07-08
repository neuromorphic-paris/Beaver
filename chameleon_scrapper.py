import sys
import os
import re

CHAMELEON_FOLDER = 'third_party/chameleon/'
CHAMELEON_SOURCE_FOLDER = 'third_party/chameleon/source/'
CHAMELEON_NAMESPACE_INDICATOR = 'namespace chameleon'

COMMENT_INDICATOR = '//'
CLASS_INDICATOR = 'class '
RENDERER_INDICATOR = '_renderer'

VARIABLE_CHARS = 'abcdefghijklmnopqrstuvwxyz_'
PUSHEVENT_INDICATOR = 'push('

def GetChameleonClassCode(Filename, Full = False):
    with open(CHAMELEON_SOURCE_FOLDER + Filename, 'r') as f:
        Lines = {'class':[], 'renderer':[]}
        FoundChameleonNamespace = False
        FoundClass = ''
        ExpectedFunction = Filename.split('.')[0]

        while True:
            Line = f.readline()
            if not Line:
                return Lines
            if CHAMELEON_NAMESPACE_INDICATOR in Line or Full:
                FoundChameleonNamespace = True
            if CLASS_INDICATOR in Line and (not COMMENT_INDICATOR in Line or Line.index(COMMENT_INDICATOR) > Line.index(CLASS_INDICATOR)):
                StudiedPart = Line.split(CLASS_INDICATOR)[1].strip()
                for nChar, Char in enumerate(StudiedPart):
                    if Char.lower() not in VARIABLE_CHARS:
                        break
                ClassName = StudiedPart[:nChar]
                if ClassName == ExpectedFunction:
                    FoundClass = 'class'
                elif ClassName == ExpectedFunction + RENDERER_INDICATOR:
                    FoundClass = 'renderer'
            if (FoundChameleonNamespace and FoundClass) or Full:
                if Line[-1] == '\n':
                    Line = Line[:-1]
                Lines[FoundClass] += [Line]

def FindPushAndExtractRequiredFields(Lines, FuncName):
    Lines = Lines['renderer']
    StartLine = None
    for nLine, Line in enumerate(Lines):
        if PUSHEVENT_INDICATOR in Line and (not COMMENT_INDICATOR in Line or Line.index(COMMENT_INDICATOR) > Line.index(PUSHEVENT_INDICATOR)):
            StartLine = nLine
            OpeLine = StartLine
            print("Found push operator at line {0}".format(OpeLine))
            break
    if StartLine is None:
        print("Unable to find push operator for function {0}".format(FuncName))
        return [], None
    EndLine = StartLine
    StudiedPart = Line.split(PUSHEVENT_INDICATOR)[1]
    while StudiedPart.count(')') == 0:
        EndLine += 1
        StudiedPart = StudiedPart + ' ' + Lines[EndLine].split(COMMENT_INDICATOR)[0]
    UsefulPart = StudiedPart.split(')')[0]
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
        print("Unable to parse event variable name in push operator of function {0}".format(FuncName))
        return [], OpeLine
    StartLine = EndLine
    StudiedPart = Lines[StartLine].split('{')[-1]

    RequiredFields = []
    
    nOpen = 1
    nClose = 0
    EndLine = StartLine + 1
    while nOpen > nClose:
        Line = Lines[EndLine]
        StudiedPart = Line.split(COMMENT_INDICATOR)[0]
        nOpen += StudiedPart.count('{')
        nClose += StudiedPart.count('}')
        EndLine += 1
        if VarName + '.' in StudiedPart:
            for AppearingField in StudiedPart.split(VarName + '.')[1:]:
                for nChar, Char in enumerate(AppearingField):
                    if Char not in VARIABLE_CHARS:
                        break
                FinalField = AppearingField[:nChar]
                if FinalField[0] == '_':
                    FinalField = FinalField[1:]
                if FinalField not in RequiredFields:
                    
                    RequiredFields += [FinalField]
        if not Line:
            print("Unable to end properly push operator definition for {0}".format(FuncName))
            return RequiredFields, OpeLine
    return RequiredFields, OpeLine

def ScrapChameleonFolder():
    Filenames = os.listdir(CHAMELEON_SOURCE_FOLDER)
    Modules = {}
    for Filename in Filenames:
        ModuleName = Filename.split('.hpp')[0]
        if Filename[0] == '.':
            continue
        print("")
        print(" -> " + Filename)
        Lines = GetChameleonClassCode(Filename)
        if not Lines['renderer']:
            print("No renderer class here")
        if Lines['renderer']:
            Modules[ModuleName] = {}
            Modules[ModuleName]['parameters'] = []
            Modules[ModuleName]['templates'] = []
            Modules[ModuleName]['origin'] = 'chameleon'
            Modules[ModuleName]['name'] = ModuleName
            EVFields, PushLineInRenderer = FindPushAndExtractRequiredFields(Lines, ModuleName)
            Modules[ModuleName]['ev_fields'] = EVFields
            Modules[ModuleName]['has_operator'] = True
            Modules[ModuleName]['has_event_to'] = False
            Modules[ModuleName]['ev_outputs'] = {}
    return Modules

if __name__ == '__main__':
    args = sys.argv

    Modules = ScrapChameleonFolder()
