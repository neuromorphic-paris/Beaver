import os
import sys
import re

import tarsier_scrapper
import sepia_scrapper

HANDLERS_FILE_NAME_SUFFIX = ' Handlers Functions'
LAMBDA_FUNCTION_FROM = '{1}_function_for_{0}'
TYPES_DEF_FILE = "Defined events types"
DEFAULT_EVENT_NAME = 'event'

NEW_TYPE_DEFAULT = "type_{0}"
USER_DEFINED = 'user_defined'
GLOBAL_VARIABLE_NAME = 'var_{0}'

GENERAL_FILENAME = 'Framework'
DEFAULT_NAME = 'Untitled'
INTRODUCTION_LINE = '// {0} - Generated with Beaver'

CPP_TAB = 4*' '
LUA_TAB = 4*' '

NoneEventType = {'name': '?', 'fields':[], 'origin':'', 'value': None}

def W(Value):
    print("Here : {0}".format(Value))

def NextLevelAsDict(Object):
    if type(Object) == dict:
        return {Key: NextLevelAsDict(Value) for Key, Value in Object.items()}
    elif type(Object) == list:
        return [NextLevelAsDict(Value) for Value in Object]
    elif SimiliDict in Object.__class__.__bases__:
        return NextLevelAsDict(Object.asDict())
    else:
        return Object

def NextLevelFromDict(Object):
    if type(Object) == dict:
        if '__class__' in Object.keys():
            return globals()[Object['__class__']]({Key: NextLevelFromDict(Value) for Key, Value in Object.items()})
        else:
            return {Key: NextLevelFromDict(Value) for Key, Value in Object.items()}
    elif type(Object) == list:
        return [NextLevelFromDict(Value) for Value in Object]
    elif Object.__class__ in [LambdaModuleClass, LambdaFunctionClass, ModuleClass, EventTypeClass]:
        return NextLevelFromDict(Object.asDict())
    else:
        return Object

class FrameworkAbstraction:
    def __init__(self, Data = None, LogFunction = None):
        self.ReferenceModulesDictionnary = {'name':{}, 'id':{}, 'list':[]}
        if not Data is None:
            self.Data = NextLevelFromDict(Data)
            for Module in self.Data['modules']:
                self.ReferenceModulesDictionnary['name'][Module.name] = Module
                self.ReferenceModulesDictionnary['id'][Module.id] = Module
        else:
            self.Data = {'modules': [], 'name': '', 'files': {GENERAL_FILENAME:{'data': INTRODUCTION_LINE.format(DEFAULT_NAME), 'type': 'code'}}, 'user_defined_types': {}, 'chameleon_tiles': {}, 'utilities': [], 'global_variables': []}

        self.ReferenceModulesDictionnary['list'] = self.Data['modules']
        self.Modules = self.Data['modules']
        self.ChameleonTiles = self.Data['chameleon_tiles']
        self.UserDefinedTypes = self.Data['user_defined_types']
        self.Utilities = self.Data['utilities']
        self.GlobalVariables = self.Data['global_variables']
        
        if LogFunction is None:
            self.LogFunction = sys.stdout.write
        else:
            self.LogFunction = LogFunction

        self.Writer = CodeWriterClass(LogFunction)

    def Files(self, Bare = False):
        if Bare:
            return self.Data['files']
        FilesShouldAppear = [GENERAL_FILENAME]
        if self.UserDefinedTypes:
            FilesShouldAppear += [TYPES_DEF_FILE]
            self.WriteTypesFile()
        for Module in self.Modules:
            if Module['origin'] == 'chameleon':
                continue
            FileName = Module.FileName()
            FilesShouldAppear += [FileName]
            
            self.Data['files'][FileName] = {'data': Module['data'], 'type': 'code'}
        for FileName in self.Data['files']:
            if FileName not in FilesShouldAppear:
                del self.Data['files'][FileName]
        return self.Data['files']

    def ToDict(self):
        return NextLevelAsDict(self.Data)

    def _LoadData(self, Data):
        self.Data = NextLevelFromDict(Data)

    def AddModule(self, Module, AskedModuleName):
        NewID = self.GetNewID()
        NewModule = ModuleClass(NewID, self.ReferenceModulesDictionnary, AskedModuleName, Module)

    def RemoveModule(self, Module, WithLinks = True):
        print("Removing {0}".format(Module.name))
        print([M.name for M in self.Modules])
        ModuleName = Module['name']

        if WithLinks:
            for ParentID in Module['parent_ids']:
                ParentModule = self.ReferenceModulesDictionnary['id'][ParentID]
                self.RemoveLink(ParentID, Module['id'])
            for nParameter in Module.FindModuleHandlers():
                ChildrenModule = self.ReferenceModulesDictionnary['name'][Module['parameters'][nParameter].split('@')[1]]
                self.RemoveLink(Module['id'], ChildrenModule['id'], RecreateLinks = False)
                if type(ChildrenModule) == LambdaModuleClass and ChildrenModule['default']:
                    self.RemoveModule(ChildrenModule, WithLinks = False)

        Module.HideFromTheWorld()
    
    def AddLink(self, ParentID, ChildrenID):
        ParentModule = self.ReferenceModulesDictionnary['id'][ParentID]
        ChildrenModule = self.ReferenceModulesDictionnary['id'][ChildrenID]

        if ChildrenModule['origin'] == 'chameleon':
            return self.AddChameleonLink(ParentID, ChildrenID)

        if not ChildrenModule.HasOperator():
            self.LogFunction("Can't send events to {0}".format(ChildrenModule['name']))
            return None

        Added = False
        HandlersParamsIndexes = ParentModule.FindModuleHandlers()
        EventToParamIndexes = ParentModule.FindModuleEventTo()
        for nHandlerLocal in range(len(HandlersParamsIndexes)):
            HandlerIndex = HandlersParamsIndexes[nHandlerLocal]
            HandlerName = ParentModule['module']['parameters'][HandlerIndex]['name']
            ExistingHandler = self.ReferenceModulesDictionnary['name'][LAMBDA_FUNCTION_FROM.format(ParentModule['name'], HandlerName)]
            if not type(ExistingHandler) == LambdaModuleClass or not ExistingHandler['default']:
                continue

            ChildrenModule['parent_ids'] += [ParentID]

            self.RemoveModule(ExistingHandler, WithLinks = False)

            ParentModule['parameters'][HandlerIndex] = '@' + ChildrenModule['name']

            Added = True
            break

        if not Added:
            self.LogFunction("Unable to link {0} to {1} : no Handler slot available".format(ParentModule['name'], ChildrenModule['name']))

    def AddChameleonLink(self, ParentID, ChildrenID):
        ParentModule = self.ReferenceModulesDictionnary['id'][ParentID]
        ChildrenModule = self.ReferenceModulesDictionnary['id'][ChildrenID]

        if not ChildrenModule.HasOperator():
            self.LogFunction("Can't send events to {0}".format(ChildrenModule['name']))
            return None

        Added = False
        HandlersParamsIndexes = ParentModule.FindModuleHandlers()
        EventToParamIndexes = ParentModule.FindModuleEventTo()
        for nHandlerLocal in range(len(HandlersParamsIndexes)):
            HandlerIndex = HandlersParamsIndexes[nHandlerLocal]
            HandlerName = ParentModule['module']['parameters'][HandlerIndex]['name']
            ExistingHandler = self.ReferenceModulesDictionnary['name'][LAMBDA_FUNCTION_FROM.format(ParentModule['name'], HandlerName)]
            if not type(ExistingHandler) == LambdaModuleClass:
                continue

            LineID = ExistingHandler.AddAutoWrittenLine(ChildrenModule['name']+'->push();')
            Added = True
            break
        if not Added:
            self.LogFunction("Unable to link {0} to {1} : no Handler slot available".format(ParentModule['name'], ChildrenModule['name']))

    def RemoveLink(self, ParentID, ChildrenID, RecreateLinks = True):
        ParentModule = self.ReferenceModulesDictionnary['id'][ParentID]
        ChildrenModule = self.ReferenceModulesDictionnary['id'][ChildrenID]

        Removed = False
        HandlersParamsIndexes = ParentModule.FindModuleHandlers()
        for nParam in HandlersParamsIndexes:
            if ParentModule['parameters'][nParam] and ParentModule['parameters'][nParam].split('@')[-1] == ChildrenModule['name']:
                ParentModule['parameters'][nParam] = ''
                Removed = True
                break
        if not Removed:
            self.LogFunction("Unable to find and remove link from {0} to {1}".format(ParentModule['name'], ChildrenModule['name']))
            return None
        ChildrenModule['parent_ids'].remove(ParentModule['id'])
        
        if RecreateLinks:
            ParentModule.FillLambdasLinks()
        return None

    def ChangeModuleName(self, Module, AskedName):
        if type(Module) == LambdaModuleClass:
            print("Warning : attempt to change lambda function module name. Dangerous behabiour possible, aborting.")
            return None
        PreviousName = Module['name']
        Module['name'] = AskedName

        for ParentID in Module['parent_ids']:
            ParentModule = self.ReferenceModulesDictionnary['id'][ParentID]
            for HandlerIndex in ParentModule.FindModuleHandlers():
                Param = ParentModule['parameters'][HandlerIndex]
                if '@' in Param and Param.split('@')[1] == PreviousName:
                    ParentModule['parameters'][nParam] = '@' + AskedName

        for HandlerIndex in Module.FindModuleHandlers():
            HandlerName = Module['module']['parameters'][HandlerIndex]['name']
            PreviousHandlerParamFuncName = LAMBDA_FUNCTION_FROM.format(PreviousName, HandlerName)
            if Module['parameters'][HandlerIndex] == '@' + PreviousHandlerParamFuncName:
                NewHandlerParamFuncName = LAMBDA_FUNCTION_FROM.format(AskedName, HandlerName)
                Module['parameters'][HandlerIndex] = '@' + NewHandlerParamFuncName
                HandlerModule = self.ReferenceModulesDictionnary['name'][PreviousHandlerParamFuncName]
                HandlerModule['name'] = NewHandlerParamFuncName

#    def SetType(self, Module, NewType, UpdatedIDsOnTrigger = []): # Deprecated
#        OriginalUpdatedIDsOnTrigger = list(UpdatedIDsOnTrigger)
#        print(OriginalUpdatedIDsOnTrigger)
#        if Module['id'] in UpdatedIDsOnTrigger: # To avoid permanent recursion
#            return None
#        self.LogFunction("Updating type of "+Module['name'])
#
#        UpdatedIDsOnTrigger += [Module['id']]
#        if Module['origin'] == 'sepia' and 'observable' in Module['module']['name']: # Here, type is actually the output type
#            Found = False
#            for TemplateField in Module['module']['templates']:
#                if TemplateField['name'] == 'event_stream_type':
#                    Module['templates'][TemplateField['template_number']] = NewType['name']
#                    Found = True
#                    break
#
#            if not Found:
#                self.LogFunction("Unable to change type for sepia module in SetType: no event_stream_type field found")
#                return None
#            Module.returned_event_type = NewType
#
#            HandlersParamsIndexes = Module.FindModuleHandlers()
#            HandlerIndex = HandlersParamsIndexes[0]
#            HandlerName = Module['module']['parameters'][HandlerIndex]['name']
#
#            if NewType['name'] == NoneEventType['name']:
#                Module['ev_outputs'][HandlerName] = []
#            else:
#                Module['ev_outputs'][HandlerName] = [{'type': NewType['name'], 'name': 'event'}]
#        
#            HandlerParamFuncName  = LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName)
#
#            ChildrenModule = self.ReferenceModulesDictionnary['name'][Module['parameters'][HandlerIndex].split('@')[-1]]
#            self.SetType(ChildrenModule, NewType, UpdatedIDsOnTrigger)
#            #else: # If no link, then lets tell the lambda function which type it gets
#            #    Module['lambda_functions'][HandlerParamFuncName].input_fields = Module['ev_outputs'][HandlerName]
#
#            Module.FillLambdasLinks()
#            # Those modules cannot have parents
#
#        elif Module['origin'] == 'sepia' and  Module['module']['name'] == 'make_split':
#                self.LogFunction('Not implemented')
#        elif type(Module) == ModuleClass:
#            Found = False
#            for TemplateField in Module['module']['templates']:
#                if TemplateField['name'] == 'Event':
#                    Module['templates'][TemplateField['template_number']] = NewType['name']
#                    Found = True
#                    break
#
#            if not Found:
#                self.LogFunction("Unable to change type for module in SetType: no Event field found")
#                return None
#
#            Module.received_event_type = NewType
#            
#            HandlersParamsIndexes = Module.FindModuleHandlers()
#            EventToParamIndexes = Module.FindModuleEventTo()
#
#            HasUpdatedRelative = False
#            for nHandlerLocal in range(len(HandlersParamsIndexes)):
#                HandlerIndex = HandlersParamsIndexes[nHandlerLocal]
#                HandlersParamsIndexes = Module.FindModuleHandlers()
#                HandlerIndex = HandlersParamsIndexes[0]
#                HandlerName = Module['module']['parameters'][HandlerIndex]['name']
#
#                if NewType['name'] == NoneEventType['name']:
#                    Module['ev_outputs'][HandlerName] = list(Module['module']['ev_outputs'][HandlerName])
#                else:
#                    for nField, Field in enumerate(Module['module']['ev_outputs'][HandlerName]):
#                        if Field['type'] == 'Event':
#                            Module['ev_outputs'][HandlerName][nField]['type'] = NewType['name']
#        
#                if EventToParamIndexes: # If there is a lambda function out of this module, then he had to deal with the descending change of type
#                    EventToParamIndex = EventToParamIndexes[nHandlerLocal]
#                    EventToParamName = Module['module']['parameters'][EventToParamIndex]['name']
#                    EventToParamFuncName = LAMBDA_FUNCTION_FROM.format(Module['name'], EventToParamName)
#                    if EventToParamFuncName in Module['event_to_lambda_functions'].keys():
#                        Module['event_to_lambda_functions'][EventToParamFuncName].input_fields = Module['ev_outputs'][HandlerName]
#                        continue
#                HandlerParamFuncName  = LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName)
#
#                self.SetType(ChildrenModule, NewType, UpdatedIDsOnTrigger)
#
#            for ParentID in Module['parent_ids']:
#                print("Going up to {0}".format(ParentID))
#                self.SetType(self.ReferenceModulesDictionnary['id'][ParentID],  NewType, UpdatedIDsOnTrigger)
#            Module.FillLambdasLinks()
#        elif type(Module) == LambdaModuleClass:
#            Module.received_event_type = NewType
#        else:
#            print("Bug #15486")

    def AddNewType(self):
        N = 0
        while NEW_TYPE_DEFAULT.format(N) in self.UserDefinedTypes.keys():
            N += 1
        NewTypeName = NEW_TYPE_DEFAULT.format(N)
        self.UserDefinedTypes[NewTypeName] = EventTypeClass(NewTypeName)

        self.WriteTypesFile()

    def RemoveType(self, TypeName):
#TODO remove references to this type in modules
        del self.UserDefinedTypes[TypeName]

    def WriteTypesFile(self):
        if not self.UserDefinedTypes:
            return None
        
        self.Data['files'][TYPES_DEF_FILE] = {'data': '', 'type': 'code'}

        for TypeName in sorted(self.UserDefinedTypes.keys()):
            self.Data['files'][TYPES_DEF_FILE]['data'] += self.UserDefinedTypes[TypeName]['data']
            self.Data['files'][TYPES_DEF_FILE]['data'] += '\n'

    def AddGlobalVariable(self, Type = ''):
        Names = []
        for Variable in self.GlobalVariables:
            Names += [Variable['name']]
        N = 0
        Name = GLOBAL_VARIABLE_NAME.format(N)
        while Name in Names:
            N += 1
            Name = GLOBAL_VARIABLE_NAME.format(N)
        self.GlobalVariables += [{'name': Name, 'type': Type, 'value': ''}]

    def UpdateVariablesFile(self):
        print('here')
        Data = INTRODUCTION_LINE.format(self.Data['name']) + '\n\n'
        for Variable in self.GlobalVariables:
            if not Variable['type']:
                Data += 'auto'
            else:
                Data += Variable['type']
            Data += ' ' + Variable['name']
            if Variable['value']:
                Data += ' = ' + Variable['value']
            Data += ';\n'
        self.Data['files'][GENERAL_FILENAME]['data'] = Data

    def ModuleNameValidity(self, Module, NewName):
        if NewName == '':
            return False
        for ComparedModule in self.Modules:
            if ComparedModule['name'] == NewName and Module['id'] != ComparedModule['id']:
                return False
        return True

    def WellDefinedModule(self, Module):
        if type(Module) == LambdaModuleClass:
            return self.WellDefinedLambdaFunction(Module)
        for nModule, ParameterAsked in enumerate(Module['module']['parameters']):
            if Module['parameters'][nModule] == '':
                return False
            CanBeChecked, WasChecked = CheckParameterValidity(ParameterAsked['type'], Module['parameters'][nModule])
            if CanBeChecked and not WasChecked:
                return False
        return True

    def WellDefinedLambdaFunction(self, Module):#TODO
        return True

    def GetFreeHandlersSlots(self, ModuleID):
        Module = self.ReferenceModulesDictionnary['id'][ModuleID]
        HandlersParamsIndexes = Module.FindModuleHandlers()
        FreeHandlersParamsIndexes = []
        for HandlerIndex in HandlersParamsIndexes:
            if self.IsFreeSlot(Module, HandlerIndex):
                FreeHandlersParamsIndexes += [HandlerIndex]
        return FreeHandlersParamsIndexes

    def IsFreeSlot(self, Module, HandlerIndex):
        HandlerName = Module['module']['parameters'][HandlerIndex]['name']
        HandlerParamFuncName  = LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName)
        if (Module['parameters'][HandlerIndex] == '@'+HandlerParamFuncName) and self.ReferenceModulesDictionnary['name'][HandlerParamFuncName]['default']:
            return True
        return False

    def GetNewID(self):
        if not self.Modules:
            return 0
        return max(self.ReferenceModulesDictionnary['id'].keys()) + 1

    def GetChildrenIDs(self, ParentID):
        IDs = []
        ParentModule = self.ReferenceModulesDictionnary['id'][ParentID]
        HandlersParamsIndexes = ParentModule.FindModuleHandlers()
        for nParam in HandlersParamsIndexes:
            if ParentModule['parameters'][nParam]:
                IDs += [self.ReferenceModulesDictionnary['name'][ParentModule['parameters'][nParam].split('@')[-1]]['id']]
        return IDs

    def GenerateCode(self):
        self.Writer.WriteCode(self)

    def GenerateBuild(self):
        self.Writer.BuildDirectory(self.Data['name'], force = True)
        ChameleonModules = []
        for Module in self.Modules:
            if Module['module']['origin'] == 'chameleon':
                ChameleonModules += [Module]
        LuaFilename = self.Writer.CreateLUAFile(self.Data['name'], ChameleonModules)
        self.Data['files'][LuaFilename] = {'data':LoadFile(LuaFilename), 'type': 'build'}
        return LuaFilename

    def GetParentAndChildFromLinkStr(self, Str):
        ID1, ID2 = (int(ID) for ID in Str.split('&'))
        if ID2 in self.ReferenceModulesDictionnary['id'][ID1].parent_ids:
            return ID1, ID2
        else:
            return ID2, ID1
        
def GetLinkStr(M1ID, M2ID):
    return '{0}&{1}'.format(min(M1ID, M2ID), max(M1ID, M2ID))
    
def LoadFile(Filename):
    with open(Filename, 'r') as f:
        Lines = f.readlines()
    return ''.join(Lines)

class SimiliDict:
    def __init__(self, IniDict):
        self.__dict__ = IniDict
    def __getitem__(self, key):
        if key == 'data':
            self.Write()
        return self.__dict__[key]
    def __setitem__(self, key, value):
        self.__dict__[key] = value
    def keys(self):
        return self.__dict__.keys()
    def values(self):
        return self.__dict__.values()
    def items(self):
        return self.__dict__.items()
    def asDict(self):
        D = dict(self.__dict__)
        D['__class__'] = str(self.__class__.__name__)
        return D
    def Write(self):
        pass

class EventTypeClass(SimiliDict):
    def __init__(self, Name, Value = None, Fields = [], Origin = USER_DEFINED):
        if type(Name) == dict:
            super().__init__(Name)
            return None
        self.name = Name
        self.value = Value
        self.fields = Fields
        self.origin = Origin
        self.EVENT_TYPE_INTRO = '// #arl_{0}\n'
        self.ReferencedByModuleIDs = []

    def Write(self):
        self.data = self.EVENT_TYPE_INTRO.format(self.name)
        self.data += 'struct {0}'.format(self.name) + ' {\n'
        for field in self.fields:
            if field['type'].strip() or field['name'].strip():
                self.data += CPP_TAB + field['type'] + ' ' + field['name'] + ';\n'
        self.data += '}\n'

class HandlerClass(SimiliDict):
    def __init__(self, ID, RMD, Name = None):
        self._RMD = RMD # RMD stands for Reference Module Dictionnary. Modules need references to the rest of the framework especially for writing out data
        if type(ID) == dict:
            super().__init__(ID)
            self.Publicise()
            return None
        self.id = ID
        self.name = Name
        self.parent_ids = []
        self.data = ''
        self.origin = None
        self.returned_event_type = None
        self.received_event_type = dict(NoneEventType)
        self.Publicise()

    def HasOperator(self):
        if type(self) == LambdaModuleClass:
            return True
        else:
            return self.module['has_operator']

    def __setitem__(self, key, value):
        if key == 'name' and self.__dict__[name] in self._RMD['name'].keys():
            PreviousName = self.__dict__[name]
            NewName = value
            del self._RMD['name'][PreviousName]
            self._RMD['name'][NewName] = self
        self.__dict__[key] = value
            
    def Publicise(self):
        if not self._RMD is None:
            print("Publicating "+self.name)
            self._RMD['id'][self.id] = self
            self._RMD['name'][self.name] = self
            self._RMD['list'] += [self]

    def HideFromTheWorld(self):
        if not self._RMD is None:
            print("Hiding "+self.name)
            del self._RMD['id'][self.id]
            del self._RMD['name'][self.name]
            self._RMD['list'].remove(self)

    def FillLambdasLinks(self):
        pass
    def FileName(self):
        return self.name + ' default filename. Unimplemented stuff in here'

    def SetInputType(self, InputType):
        for key, value in InputType.items():
            self.received_event_type[key] = value # This allows to keep links between modules

class LambdaFunctionClass(SimiliDict):
    def __init__(self, Name = None, IntroductionLine = '', InputFields = [], RequiredFieldsCommentLine = '', ReturnedEventType = None):
        self.origin = USER_DEFINED
        self.default = True
        self.auto_written_lines = {}
        self.data = ''
        self.name = Name

        self.input_fields = InputFields
        self.intro_comment_line = '/// Lambda function {0}\n'.format(self.name)
        self.req_fields_comment_line = RequiredFieldsCommentLine
        self.global_context = False
        self.returned_event_type = ReturnedEventType

        self.AUTO_WRITTEN_LINE_COMMENT = ' // #arl{0}'

    def FileName(self):
        return self.name

    def Write(self):
        self.data = self.intro_comment_line
        self.data += self.req_fields_comment_line
        self.data += '['
        if self.global_context:
            self.data += '&'
        self.data += ']('
        if self.input_fields:
            self.data += '\n'
            for Field in self.input_fields:
                CorrectName = True
                for Char in Field['name'].strip():
                    if Char not in tarsier_scrapper.VARIABLE_CHARS:
                        CorrectName = False
                        break
                if CorrectName:
                    TryName = Field['name'].strip().strip('_')
                else:
                    TryName = '?'
                self.data += CPP_TAB + Field['type']+' '+TryName+', // from variable ' + Field['name'] + '\n'
        elif not self.returned_event_type is None:
            self.data += self.returned_event_type['type']+' '+DEFAULT_EVENT_NAME
        self.data += ') '
        if not self.returned_event_type is None:
            self.data += self.returned_event_type['name'] + ' '
        self.data += '{\n'
        for auto_line_key in sorted(self.auto_written_lines.keys()):
            auto_line = self.auto_written_lines[auto_line_key] + self.AUTO_WRITTEN_LINE_COMMENT.format(auto_line_key)
            self.data += CPP_TAB + auto_line + '\n'
        self.data += '}'

    def AddAutoWrittenLine(self, Line):
        if self.auto_written_lines.keys():
            LineID = max(self.auto_written_lines.keys())
        else:
            LineID = 0
        self.auto_written_lines[LineID] = Line
        self.default = False
        return LineID

class LambdaModuleClass(LambdaFunctionClass, HandlerClass):
    def __init__(self, ID, RMD, Name, ReceivedEventType, IntroductionLine = '',  RequiredFieldsCommentLine = '', ReturnedEventType = None):
        LambdaFunctionClass.__init__(self, Name, IntroductionLine)
        HandlerClass.__init__(self, ID, RMD, Name)
        self.received_event_type = ReceivedEventType
        self.global_context = True
        self.input_fields = [{'type': self.received_event_type['name'], 'name': self.received_event_type['name'].split(':')[-1]}]

    def FileName(self):
        return LambdaFunctionClass.FileName(self)

    def SetInputType(self, InputType):
        HandlerClass.SetInputType(self, InputType)
        self.input_fields = [{'type': self.received_event_type['name'], 'name': self.received_event_type['name'].split(':')[-1]}]

    def FindModuleHandlers(self):
        return []
    def FindModuleEventTo(self):
        return []
    def CountEventsHandlers(self):
        return 0

class ModuleClass(HandlerClass):
    def __init__(self, ID, RMD, Name = None, BaseModule = None):
        super().__init__(ID, RMD, Name)
        self.origin = BaseModule['origin']
        self.module = BaseModule
        self.parameters = [param['default'] for param in BaseModule['parameters']]
        self.templates = [template['default'] for template in BaseModule['templates']]
        self.ev_outputs = {handle_event: list(Fields) for handle_event, Fields in BaseModule['ev_outputs'].items()}
        self.event_to_lambda_functions = {}
        if self.origin == 'chameleon':
            self.returned_event_type = None
        else:
            if self.FindModuleEventTo():
                self.returned_event_type = {self.module['parameters'][HandlerIndex]['name']: dict(NoneEventType) for HandlerIndex in self.FindModuleHandlers()}
            else:
                self.returned_event_type = {self.module['parameters'][HandlerIndex]['name']: self.received_event_type for HandlerIndex in self.FindModuleHandlers()}

        self.FillLambdasLinks()

    def FileName(self):
        return self.name + HANDLERS_FILE_NAME_SUFFIX

    def FillLambdasLinks(self):
        print("Filling lambdas for "+self.name)
        
        EventToParamIndexes = self.FindModuleEventTo()
        HandlersParamsIndexes = self.FindModuleHandlers()
        for nHandlerLocal in range(len(HandlersParamsIndexes)):
            HandlerIndex = HandlersParamsIndexes[nHandlerLocal]
            HandlerName = self.module['parameters'][HandlerIndex]['name']
            if self.parameters[HandlerIndex] and self.parameters[HandlerIndex].split('@')[-1] != LAMBDA_FUNCTION_FROM.format(self.name, HandlerName):
                continue
            RequiredFieldsCommentLine = ''

            if EventToParamIndexes:
                EventToParamIndex = EventToParamIndexes[nHandlerLocal]
                EventToParamName = self.module['parameters'][EventToParamIndex]['name']
                EventToParamFuncName = LAMBDA_FUNCTION_FROM.format(self.name, EventToParamName)
                if EventToParamFuncName in self.event_to_lambda_functions.keys():
                    Default = self.event_to_lambda_functions[EventToParamFuncName]['default']
                    if not Default:
                        continue
                self.event_to_lambda_functions[EventToParamFuncName] = LambdaFunctionClass(Name = EventToParamFuncName, 
                                                                                    InputFields = self.ev_outputs[HandlerName],
                                                                                    RequiredFieldsCommentLine = RequiredFieldsCommentLine,
                                                                                    ReturnedEventType = self.returned_event_type[HandlerName])
                self.parameters[EventToParamIndex] = '@' + EventToParamFuncName

            HandlerParamFuncName  = LAMBDA_FUNCTION_FROM.format(self.name, HandlerName)
            if HandlerParamFuncName in self._RMD['name'].keys():
                SimilarModule = self._RMD['name'][HandlerParamFuncName]
                if not SimilarModule['default']:
                    continue
                NewDefaultModuleID = SimilarModule['id']
                self._RMD['list'].remove(SimilarModule)
            else:
                NewDefaultModuleID = max(self._RMD['id'].keys()) + 1
            NewDefaultModule = LambdaModuleClass(ID = NewDefaultModuleID,
                                            RMD = self._RMD,
                                            Name = HandlerParamFuncName,
                                            ReceivedEventType = self.returned_event_type[HandlerName],
                                            RequiredFieldsCommentLine = '',
                                            ReturnedEventType = None)
            
            NewDefaultModule.parent_ids += [self.id]
            self.parameters[HandlerIndex] = '@' + HandlerParamFuncName

    def SetEventTemplate(self, InputType, TemplateIndex = None):
        HandlerClass.SetInputType(self, InputType)
        if not TemplateIndex is None:
            self.templates[TemplateIndex] = InputType['name']
        else:
            for TemplateField in self.module['templates']:
                if TemplateField['name'] == 'Event':
                    self.templates[TemplateField['template_number']] = InputType['name']
                    break
        if self.origin == 'sepia' and 'observable' in self.module['name']:
            self.SetOutputType(InputType, HandlerIndexList = None)

        EventToParamIndexes = self.FindModuleEventTo()
        if EventToParamIndexes:
            HandlersParamsIndexes = self.FindModuleHandlers()
            for nHandlerLocal, HandlerIndex in enumerate(HandlersParamsIndexes):
                HandlerName = self.module['parameters'][HandlerIndex]['name']
                EventToParamIndex = EventToParamIndexes[nHandlerLocal]
                EventToParamName = self.module['parameters'][EventToParamIndex]['name']
                EventToParamFuncName = LAMBDA_FUNCTION_FROM.format(self.name, EventToParamName)

                EventToParamFunc = self.event_to_lambda_functions[EventToParamFuncName]
                for n_field, field in enumerate(self.module['ev_outputs'][HandlerName]):
                    if field['type'] == 'Event':
                        EventToParamFunc.input_fields[n_field]['type'] = InputType['name']
                        EventToParamFunc.input_fields[n_field]['name'] = InputType['name'].split(':')[-1]
                        break

    def SetInputType(self, InputType):
        self.SetEventTemplate(InputType)

    def SetOutputType(self, OutputType, HandlerIndexList):
        if HandlerIndexList is None: # If we want to change all output - probably the only one existing
            HandlerIndexList = self.FindModuleHandlers()
        for HandlerIndex in HandlerIndexList:
            self.returned_event_type[self.module['parameters'][HandlerIndex]['name']] = OutputType
            self._RMD['name'][self.parameters[HandlerIndex].split('@')[-1]].SetInputType(OutputType)


    def Write(self):
        print("Generating handler code file for {0}".format(self.name))
        self.data = ''
        HandlersParamsIndexes = self.FindModuleHandlers()
        EventToParamIndexes = self.FindModuleEventTo()

        if EventToParamIndexes and len(EventToParamIndexes) != len(HandlersParamsIndexes):
            self.LogFunction("EventTo function found, but not the same number as HandleEvents. Unpredictable behaviour expected")

        for nHandlerLocal in range(len(HandlersParamsIndexes)):
            HandlerIndex = HandlersParamsIndexes[nHandlerLocal]
            HandlerName = self.module['parameters'][HandlerIndex]['name']

            if EventToParamIndexes:
                EventToParamIndex = EventToParamIndexes[nHandlerLocal]
                EventToParamName = self.module['parameters'][EventToParamIndex]['name']
                EventToParamFuncName = LAMBDA_FUNCTION_FROM.format(self.name, EventToParamName)
                
                self.data += '// '+EventToParamName+'\n'
                EventToParamFunc = self.event_to_lambda_functions[EventToParamFuncName]
                self.data += EventToParamFunc['data']
                self.data += '\n\n'

            self.data += '// '+HandlerName+'\n'
            HandlerValue = self.parameters[HandlerIndex].split('@')[-1]
            HandlerFunc = self._RMD['name'][HandlerValue]
            if type(HandlerFunc) == LambdaModuleClass:
                self.data += HandlerFunc['data']
            else:
                self.data += self.parameters[HandlerIndex]+'\n\n'

            self.data += '\n\n'

    def FindModuleHandlers(self):
        Indexes = []
        for nParam, Param in enumerate(self.module['parameters']):
            if re.compile('Handle[a-zA-Z]*').match(Param['type']):
                if 'exception' not in Param['type'].lower():
                    Indexes += [nParam]
        return Indexes
    def FindModuleEventTo(self):
        Indexes = []
        for nParam, Param in enumerate(self.module['parameters']):
            if re.compile(tarsier_scrapper.EVENT_TO_REGEX).match(Param['type']):
                Indexes += [nParam]
        return Indexes
    def CountEventsHandlers(self):
        nOutputs = 0
        for Template in self.module['templates']:
            if Template['type'] == 'typename' and re.compile('Handle[a-zA-Z]*').match(Template['name']):
                if 'exception' not in Template['name'].lower():
                    nOutputs += 1
        return nOutputs


class CodeWriterClass:
    def __init__(self, LogFunction = None):
        self.PROJECTS_DIRECTORY = "Projects/"
        self.SOURCE_DIRECTORY = 'source/'
        self.THIRD_PARTY_DIRECTORY = 'third_party/'

        self.BUILD_TARGET = "build/"

        self.LUA_TAB = LUA_TAB

        self.SYSTEM_CONFIGS = {}
        self.SYSTEM_CONFIGS['release'] = {'targetdir': self.BUILD_TARGET + 'release', 'defines': ['NDEBUG'], 'flags': ['OptimizeSpeed']}
        self.SYSTEM_CONFIGS['debug'] = {'targetdir': self.BUILD_TARGET + 'debug', 'defines': ['DEBUG'], 'flags': ['Symbols']}
        self.SYSTEM_CONFIGS['linux'] = {'links': ['pthread'], 'buildoptions': ['-std=c++11'], 'linkoptions': ['-std=c++11']}
        self.SYSTEM_CONFIGS['macosx'] = {'buildoptions': ['-std=c++11'], 'linkoptions': ['-std=c++11']}
        self.SYSTEM_CONFIGS['windows'] = {'files': ['.clang-format']}

        self.CPP_TAB = CPP_TAB
        self.HPP_EXTENSION = '.hpp'

        if LogFunction is None:
            self.LogFunction = sys.stdout.write
        else:
            self.LogFunction = LogFunction

    def _GetProjectDir(self, ProjectName):
        if ProjectName[-1] == '/':
            ProjectName = ProjectName[:-1]
        ProjectDir = self.PROJECTS_DIRECTORY + ProjectName + '/'
        return ProjectDir
    
    def BuildDirectory(self, ProjectName, force = False):
        ProjectDir = self._GetProjectDir(ProjectName)
        if ProjectName in os.listdir(self.PROJECTS_DIRECTORY):
            if not force:
                ans = input("Found already existing project folder with name '{0}'. Erase ? (y/N) ".format(ProjectName))
                if not ans.lower() == 'y':
                    return False
            os.system('rm -rf '+ ProjectDir)
        os.mkdir(ProjectDir)
        os.mkdir(ProjectDir + self.SOURCE_DIRECTORY)
        os.mkdir(ProjectDir + self.THIRD_PARTY_DIRECTORY)
    
        os.system('cp -r ' + tarsier_scrapper.TARSIER_FOLDER + ' {0}'.format(ProjectDir + 'third_party/'))
        os.system('cp -r ' + sepia_scrapper.SEPIA_FOLDER + ' {0}'.format(ProjectDir + 'third_party/'))
        
        self.LogFunction("Built project directory.")
    
    def CreateLUAFile(self, ProjectName, ChameleonModules = []):
        ProjectDir = self._GetProjectDir(ProjectName)
        configurations = ['release', 'debug']
        with open(ProjectDir + 'premake4.lua', 'w') as LuaFile:
            if ChameleonModules:
                LuaFile.write("local qt = require '{0}chameleon/qt'\n".format(self.THIRD_PARTY_DIRECTORY))
                LuaFile.write("\n")
            LuaFile.write("solution '{0}'\n".format(ProjectName))
            LuaFile.write(self.LUA_TAB + "configurations {'" + "', '".join(configurations) + "'}\n")
            LuaFile.write(self.LUA_TAB + "location '{0}'\n".format(self.BUILD_TARGET[:-1]))
            LuaFile.write(self.LUA_TAB + "project '{0}'\n".format(ProjectName))
    
            LuaFile.write(2*self.LUA_TAB + "kind 'ConsoleApp'\n")
            LuaFile.write(2*self.LUA_TAB + "language 'C++'\n")
            LuaFile.write(2*self.LUA_TAB + "location '{0}'\n".format(self.BUILD_TARGET[:-1]))
            Files = ['*.cpp', '*.hpp']
            if ChameleonModules:
                Files += ['*.qml']
            LuaFile.write(2*self.LUA_TAB + "files {'" + ("', '".format(self.SOURCE_DIRECTORY)).join([self.SOURCE_DIRECTORY + File for File in Files]) + "'}\n")
            if ChameleonModules:
                LuaFile.write(2*self.LUA_TAB + "files(qt.moc({\n")
    
                ModulesStr = ",\n".join([3*self.LUA_TAB + "{0}chameleon/source/{1}.hpp".format(self.THIRD_PARTY_DIRECTORY, Module) for Module in ChameleonModules]) + "},\n"
                LuaFile.write(ModulesStr)
                LuaFile.write(3*self.LUA_TAB + "'build/moc'))\n")
                for AddedField in ["includedirs(qt.includedirs())", "libdirs(qt.libdirs())", "links(qt.links())", "buildoptions(qt.buildoptions())", "linkoptions(qt.linkoptions())"]:
                    LuaFile.write(3*self.LUA_TAB + AddedField + "\n")
            LuaFile.write(2*self.LUA_TAB + "defines {'SEPIA_COMPILER_WORKING_DIRECTORY="' .. project().location .. '"'}\n")
    
            for ConfigName, Config in list(self.SYSTEM_CONFIGS.items()):
                LuaFile.write(2*self.LUA_TAB + "configuration '{0}'\n".format(ConfigName))
                for Key, Value in list(Config.items()):
                    if type(Value) == list:
                        LuaFile.write(3*self.LUA_TAB + Key + " {'" + "', '".join(Value) + "'}\n")
                    else:
                        LuaFile.write(3*self.LUA_TAB + Key + " '{0}'\n".format(Value))
        self.LogFunction("Generated Lua file")
        return ProjectDir + 'premake4.lua'
    
    def _Write(self, string):
        string = string.strip('\n')
        for Line in string.split('\n'):
            self.CppFile.write(self.NTabs * self.CPP_TAB + Line + '\n')
    def _AddRawData(self, Data):
        self._Write(Data)

    def WriteCode(self, Framework):
        ProjectName = Framework.Data['name']
        ProjectDir = self._GetProjectDir(ProjectName)
        self.NTabs = 0
        self.IncludeLines = []
        self.WrittenModulesIDs = []
        with open(ProjectDir + self.SOURCE_DIRECTORY + ProjectName + '.cpp', 'w') as self.CppFile:
            self._AddIncludeModule('sepia/', 'sepia.hpp')
            for Module in Framework.Modules:
                if Module['module']['origin'] == 'tarsier':
                    self._AddIncludeModule('tarsier/', Module['module']['name']+self.HPP_EXTENSION)

            if True or Framework.ChameleonTiles:
                self._AddQtHeaders()
            
            self._JumpLines(2)
            for Type in Framework.UserDefinedTypes.values():
                if True or Type.ReferencedByModuleIDs: # TODO : set to true to make sure writing is ok
                    self._AddRawData(Type['data'])
            if Framework.UserDefinedTypes:
                self._JumpLines(2)

            self._StartMain()

            for Module in Framework.Modules:
                if type(Module) == ModuleClass:
                    for LambdaFunctionName, LambdaFunction in Module['event_to_lambda_functions'].items():
                        self._AddLambdaFunction(LambdaFunctionName, LambdaFunction['data'])
                        self._JumpLines(1)
            for LambdaModule in Framework.Modules:
                if type(LambdaModule) == LambdaModuleClass:
                    if Module['id'] in LambdaModule['parent_ids']:
                        self._WriteModule(LambdaModule)

            while len(self.WrittenModulesIDs) != len(Framework.Modules):
                for Module in Framework.Modules:
                    if Module['id'] in self.WrittenModulesIDs:
                        continue
                    AllChildrenWritten = True
                    for HandlerIndex in Module.FindModuleHandlers():
                        HandlerName = Module['module']['parameters'][HandlerIndex]['name']
                        HandlerParamFuncName = LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName)
                        if (not (Module['parameters'][HandlerIndex] == '@'+HandlerParamFuncName)):
                            ChildrenName = Module['parameters'][HandlerIndex].split('@')[-1]
                            ChildrenID = Framework.ReferencedByModuleIDs['name'][ChildrenName]['id']
                            if ChildrenID not in self.WrittenModulesIDs:
                                AllChildrenWritten = False
                                break
                    if AllChildrenWritten:
                        self._WriteModule(Module)

            self._CloseMain()
    def _AddIncludeModule(self, ModuleOrigin, ModuleFile):
        Line = "#include \"../" + self.THIRD_PARTY_DIRECTORY + ModuleOrigin + "source/" + ModuleFile + "\"\n"
        if Line not in self.IncludeLines:
            self._Write("#include \"../" + self.THIRD_PARTY_DIRECTORY + ModuleOrigin + "source/" + ModuleFile + "\"\n")
            self.IncludeLines += [Line]

    def _AddQtHeaders(self):
         self._Write("#include <QtGui/QGuiApplication>\n")
         self._Write("#include <QtQml/QQmlApplicationEngine>\n")
         self._Write("#include <QtQml/QQmlContext>\n")

    def _JumpLines(self, N):
        for i in range(N):
            self.CppFile.write("\n")

    def _StartMain(self):
        self._Write("int main(int argc, char* argv[]) {\n")
        self.NTabs += 1
    def _CloseMain(self):
        self.NTabs -= 1
        self._Write("}\n")

    def _WriteModule(self, Module):
        self.WrittenModulesIDs += [Module['id']]
        if Module['module']['origin'] != USER_DEFINED:
            CppModuleName = Module['module']['origin'] + "::" + Module['module']['name']
        else:
            None
        DefLine = "auto {0} = {1}".format(Module['name'], CppModuleName)
        WrittenTemplates = [Template for Template in Module['templates'] if '#Deduced' not in Template]
        print(WrittenTemplates)
        if WrittenTemplates:
            DefLine += '<'
            DefLine += ', '.join(WrittenTemplates)
            DefLine += '>'
        DefLine += '('
        self._Write(DefLine)
        self.NTabs += 1

        ParametersLines = ''
        for Parameter in Module['parameters']:
            if not Parameter:
                ParametersLines += ', // Argument missing\n'
                continue
            if Parameter[0] != '@':
                ParametersLines += Parameter
            else:
                ParametersLines += 'std::move({0})'.format(Parameter.split('@')[-1])
            ParametersLines += ',\n'
        ParametersLines = ParametersLines[:-2]
        ParametersLines += ');'
        self._Write(ParametersLines)
        self.NTabs -= 1


    def _AddLambdaFunction(self, Name, Data):
        self._Write("auto {0} = ".format(Name)+Data.strip('\n')+';')

def CreateCommentsForRequieredFields(Fields):
    if Fields:
        return '/// Children module expects {0} with at least fields : '.format(Fields[0]) + ', '.join(Fields[1:]) + '\n\n'
    else:
        return '/// Children module does not require any specific field'

def _Check_Type_Int(Value):
    if '<<' in Value:
        Value = _ByteshiftToInt(Value)
        if Value is None:
            return False
    try:
        a = int(Value)
    except:
        return False
    if int(Value) != float(Value):
        return False
    return True

def _Check_Type_Float(Value):
    if '<<' in Value:
        return False
    try:
        a = float(Value)
    except:
        return False
    return True

CHECKED_TYPES = {_Check_Type_Int: ['int', 'uint\d*_t', 'std::size_t'], _Check_Type_Float:['double', 'float']}

def CheckParameterValidity(TypeGiven, Entry): # Return (bool, bool), for (Found parameter and can check it, Given value matches requirements)
    if not Entry:
        return True, False
    for PythonType, PossibleValues in list(CHECKED_TYPES.items()):
        for PossibleValue in PossibleValues:
            if re.compile(PossibleValue).match(TypeGiven):
                if PythonType(Entry):
                    return True, True
                else:
                    return True, False
    return False, False

def _ByteshiftToInt(Value):
    try:
        return int(Value.split('<<')[0].strip()) << int(Value.split('<<')[1].strip())
    except:
        return None
