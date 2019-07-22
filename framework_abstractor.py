import os
import sys
import re

import tarsier_scrapper
import sepia_scrapper

HANDLERS_FILE_NAME_SUFFIX = ' Handlers Functions'
LAMBDA_FUNCTION_FROM = '{1}_function_for_{0}'
TYPES_DEF_FILE = "Defined events types"

NEW_TYPE_DEFAULT = "type_{0}"
USER_DEFINED = 'user_defined'

CPP_TAB = 4*' '
LUA_TAB = 4*' '

def W(Value):
    print("Here : {0}".format(Value))

class FrameworkAbstraction:
    def __init__(self, Data = None, LogFunction = None):
        self.Data = {'modules': [], 'name': '', 'events_types': [], 'files': {'Documentation':{'data': '~ Generated with Beaver ~', 'type': 'documentation'}}, 'user_defined_types': {}, 'links_types': {}, 'chameleon_tiles': {}, 'utilities': [], 'global_variables': []}
        self.NoneType = {'name': '?', 'fields':[], 'origin':'', 'value': None}
        self.ModulesIDs = []
        self.HasChameleon = False
        self.HasTariser = False
        if not Data is None:
            self._LoadData(Data)

        self.Modules = self.Data['modules']
        self.EventsTypes = self.Data['events_types']
        self.Files = self.Data['files'] # Abstracted Files, not actual ones
        self.LinksTypes = self.Data['links_types']
        self.ChameleonTiles = self.Data['chameleon_tiles']
        self.UserDefinedTypes = self.Data['user_defined_types']
        self.Utilities = self.Data['utilities']
        self.GlobalVariables = self.Data['global_variables']
        
        if LogFunction is None:
            self.LogFunction = sys.stdout.write
        else:
            self.LogFunction = LogFunction

        self.Writer = CodeWriterClass(LogFunction)

    def _LoadData(self, Data):
        self.Data = Data
        self.ModulesIDs = []
        for Module in self.Data['modules']:
            self.ModulesIDs += [Module['id']]
# TODO : Add NonDefaultLambdaFunctions IDs here
            if Module['module']['origin'] == 'tarsier':
                self.HasTariser = True
            elif Module['module']['origin'] == 'chameleon':
                self.HasChameleon = True

    def AddModule(self, Module, AskedModuleName = None):
        NewID = self.GetNewID()
        self.Modules += [{'module': Module, 
                            'id': NewID, 
                            'parameters': [param['default'] for param in Module['parameters']], 
                            'parent_ids': [], 
                            'name': Module['name'], 
                            'templates': [template['default'] for template in Module['templates']], 
                            'lambda_functions': {}, 
                            'ev_outputs': {handle_event: list(Fields) for handle_event, Fields in Module['ev_outputs'].items()}}]
        if not AskedModuleName is None:
            self.Modules[-1]['name'] = AskedModuleName
        self.FillLambdasLinks(NewID)
        return self.Modules[-1]

    def RemoveModule(self, Module):
        ModuleName = Module['name']
        AvailableToRemove = []
        for ParentID in Module['parent_ids']:
            ParentModule = self.GetModuleByID(ParentID)
            self.RemoveLink(ParentID, Module['id'])
        for nParameter in FindModuleHandlers(Module['module']):
            if Module['parameters'][nParameter] != '@' + LAMBDA_FUNCTION_FROM.format(Module['name'], Module['module']['parameters'][nParameter]['name']):
                self.RemoveLink(Module['id'], self.GetModuleByName(Module['parameters'][nParameter].split('@')[1])['id'])
            else:
                ChildrenLambdaFunction = self.GetModuleByName(Module['parameters'][nParameter].split('@')[1])
                if not ChildrenLambdaFunction is None:
                    self.RemoveModule(self.GetModuleByName(Module['parameters'][nParameter].split('@')[1]))
            HandlersFileName = Module['name'] + HANDLERS_FILE_NAME_SUFFIX
            if HandlersFileName in self.Files.keys():
                del self.Files[HandlersFileName]
        self.Modules.remove(Module)
        self.UpdateHandlersCodeFiles()
    
    def AddLink(self, ParentID, ChildrenID):
        if ChildrenID is None:
            self.FillLambdasLinks(ParentID)
            return None

        ParentModule = self.GetModuleByID(ParentID)
        ChildrenModule = self.GetModuleByID(ChildrenID)

        if ChildrenModule['module']['origin'] == 'chameleon':
            return self.AddChameleonLink(ParentID, ChildrenID)

        if not ChildrenModule['module']['has_operator']:
            self.LogFunction("Can't send events to {0}".format(ChildrenModule['name']))
            return None

        Added = False
        HandlersParamsIndexes = FindModuleHandlers(ParentModule['module'])
        EventToParamIndexes = FindModuleEventTo(ParentModule['module'])
        for nHandlerLocal in range(len(HandlersParamsIndexes)):
            self.LinksTypes[GetLinkTuple(ParentID, ChildrenID)] = ['', self.NoneType['name']]

            HandlerIndex = HandlersParamsIndexes[nHandlerLocal]
            HandlerName = ParentModule['module']['parameters'][HandlerIndex]['name']
            HandlerParamFuncName = LAMBDA_FUNCTION_FROM.format(ParentModule['name'], HandlerName)
            if ParentModule['parameters'][HandlerIndex] and (not (ParentModule['parameters'][HandlerIndex] == '@'+HandlerParamFuncName) or not ParentModule['lambda_functions'][HandlerParamFuncName]['default']):
                # (should always be the case now)        //       If the hangler is actually a module, so we cannot link to another       //    If the lambda function has been modified (chameleon module or user written code)
                continue

            ChildrenModule['parent_ids'] += [ParentID]
            self.LinksTypes[GetLinkTuple(ParentID, ChildrenID)] = ['', '?']

            if ParentModule['parameters'][HandlerIndex] == '@'+HandlerParamFuncName:
                del ParentModule['lambda_functions'][HandlerParamFuncName]

            if HandlerName in ParentModule['ev_outputs'].keys():
                OutputFields = ParentModule['ev_outputs'][HandlerName]
            else:
                OutputFields = []
            RequiredFieldsForNextModule = ChildrenModule['module']['ev_fields']
            RequiredFieldsCommentLine = CreateCommentsForRequieredFields(RequiredFieldsForNextModule)

            if EventToParamIndexes:
                EventToParamIndex = EventToParamIndexes[nHandlerLocal]
                EventToParamName = ParentModule['module']['parameters'][EventToParamIndex]['name']
                EventToParamFuncName = LAMBDA_FUNCTION_FROM.format(ParentModule['name'], EventToParamName)
                ParentModule['parameters'][EventToParamIndex] = '@' + EventToParamFuncName

                ParentModule['lambda_functions'][EventToParamFuncName] = LambdaFunctionClass(ID = None,
                                                                                        Name = EventToParamFuncName,
                                                                                        IntroductionLine = '/// lambda function for {0} :\n'.format(ParentModule['module']['parameters'][EventToParamIndex]['name']),
                                                                                        InputFields = OutputFields, 
                                                                                        RequiredFieldsCommentLine = RequiredFieldsCommentLine, 
                                                                                        GlobalContext = False, 
                                                                                        ReturnedObject = ' -> ? ')
                self.LinksTypes[GetLinkTuple(ParentID, ChildrenID)][0] = EventToParamName

            ParentModule['parameters'][HandlerIndex] = '@' + ChildrenModule['name']

            Added = True
            break

        self.FillLambdasLinks(ParentID)
        if not Added:
            self.LogFunction("Unable to link {0} to {1} : no Handler slot available".format(ParentModule['name'], ChildrenModule['name']))

    def AddChameleonLink(self, ParentID, ChildrenID):
        ParentModule = self.GetModuleByID(ParentID)
        ChildrenModule = self.GetModuleByID(ChildrenID)

        if not ChildrenModule['module']['has_operator']:
            self.LogFunction("Can't send events to {0}".format(ChildrenModule['name']))
            return None

        Added = False
        HandlersParamsIndexes = FindModuleHandlers(ParentModule['module'])
        EventToParamIndexes = FindModuleEventTo(ParentModule['module'])
        for nHandlerLocal in range(len(HandlersParamsIndexes)):
            HandlerIndex = HandlersParamsIndexes[nHandlerLocal]
            HandlerName = ParentModule['module']['parameters'][HandlerIndex]['name']
            HandlerParamFuncName = LAMBDA_FUNCTION_FROM.format(ParentModule['name'], HandlerName)
            if ParentModule['parameters'][HandlerIndex] and not (ParentModule['parameters'][HandlerIndex] == '@'+HandlerParamFuncName):
                # (should always be the case now)        //       If the hangler is actually a module, so we cannot add chameleon link
                continue

            LinkTuple = GetLinkTuple(ParentID, ChildrenID)
            if LinkTuple in self.LinksTypes.keys():
                self.LogFunction("{0} already sending events to {1} with this handler. More complex behaviours not implemented yet.".format(ParentModule['name'], ChildrenModule['name']))
                continue
            
            LambdaFunction = ParentModule['lambda_functions'][HandlerParamFuncName]
            LineID = LambdaFunction.AddAutoWrittenLine(ChildrenModule['name']+'->push();')
            self.LinksTypes[GetLinkTuple(LambdaFunction['id'], ChildrenID)] = [LineID, '?']
            if LambdaFunction not in self.Modules:
                self.Modules += [LambdaFunction]

            Added = True
            break
        if not Added:
            self.LogFunction("Unable to link {0} to {1} : no Handler slot available".format(ParentModule['name'], ChildrenModule['name']))

    def FillLambdasLinks(self, ModuleID, Force = False):
        Module = self.GetModuleByID(ModuleID)
        print("Filling lambdas for "+Module['name'])
        
        EventToParamIndexes = FindModuleEventTo(Module['module'])
        HandlersParamsIndexes = FindModuleHandlers(Module['module'])
        for nHandlerLocal in range(len(HandlersParamsIndexes)):
            HandlerIndex = HandlersParamsIndexes[nHandlerLocal]
            HandlerName = Module['module']['parameters'][HandlerIndex]['name']
            if Module['parameters'][HandlerIndex] and Module['parameters'][HandlerIndex].split('@')[-1] != LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName):
                continue
            if HandlerName in Module['ev_outputs'].keys():
                OutputFields = Module['ev_outputs'][HandlerName]
            else:
                OutputFields = []
            RequiredFieldsCommentLine = ''

            if EventToParamIndexes:
                EventToParamIndex = EventToParamIndexes[nHandlerLocal]
                EventToParamName = Module['module']['parameters'][EventToParamIndex]['name']
                EventToParamFuncName = LAMBDA_FUNCTION_FROM.format(Module['name'], EventToParamName)
                if EventToParamFuncName in Module['lambda_functions'].keys():
                    Default = Module['lambda_functions'][EventToParamFuncName]['default']
                    if not Default and not Force:
                        continue
                Module['lambda_functions'][EventToParamFuncName] = LambdaFunctionClass(ID = None, 
                                                                                    Name = EventToParamFuncName, 
                                                                                    IntroductionLine = '/// lambda function for {0} :\n'.format(EventToParamName),
                                                                                    InputFields = OutputFields,
                                                                                    RequiredFieldsCommentLine = RequiredFieldsCommentLine,
                                                                                    GlobalContext = False,
                                                                                    ReturnedObject = ' -> ? ')
                OutputFields = []

                Module['parameters'][EventToParamIndex] = '@' + EventToParamFuncName

            HandlerParamFuncName  = LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName)
            if HandlerParamFuncName in Module['lambda_functions'].keys():
                Default = Module['lambda_functions'][HandlerParamFuncName]['default']
                if not Default and not Force:
                    continue
            NewID = self.GetNewID()
            Module['lambda_functions'][HandlerParamFuncName] = LambdaFunctionClass(ID = NewID,
                                                                                Name = HandlerParamFuncName,
                                                                                IntroductionLine = '/// Redirection for {0} :\n'.format(HandlerName),
                                                                                InputFields = OutputFields,
                                                                                RequiredFieldsCommentLine = '',
                                                                                GlobalContext = True,
                                                                                ReturnedObject = '')
            Module['parameters'][HandlerIndex] = '@' + Module['lambda_functions'][HandlerParamFuncName]['name']
            self.LinksTypes[GetLinkTuple(ModuleID, NewID)] = [None, '']

    def RemoveLink(self, ParentID, ChildrenID):
        ParentModule = self.GetModuleByID(ParentID)
        ChildrenModule = self.GetModuleByID(ChildrenID)

        Removed = False
        HandlersParamsIndexes = FindModuleHandlers(ParentModule['module'])
        for nParam in HandlersParamsIndexes:
            if ParentModule['parameters'][nParam] and ParentModule['parameters'][nParam].split('@')[-1] == ChildrenModule['name']:
                ParentModule['parameters'][nParam] = ''
                Removed = True
                break
        if not Removed:
            self.LogFunction("Unable to find and remove link from {0} to {1}".format(ParentModule['name'], ChildrenModule['name']))
            return None
        ChildrenModule['parent_ids'].remove(ParentModule['id'])
        if self.LinksTypes[GetLinkTuple(ParentID, ChildrenID)][0]: # If the module needed an output lambda function
            self.RemoveLambdaFunction(self.LinksTypes[GetLinkTuple(ParentID, ChildrenID)][0])
            del self.LinksTypes[GetLinkTuple(ParentID, ChildrenID)]
            return None

        del self.LinksTypes[GetLinkTuple(ParentID, ChildrenID)]
        self.FillLambdasLinks(ParentID)
        self.UpdateHandlersCodeFiles()
        return None

    def ChangeModuleName(self, Module, AskedName):
        PreviousName = Module['name']
        Module['name'] = AskedName

        PreviousHandlersFileName = PreviousName + HANDLERS_FILE_NAME_SUFFIX
        NewHandlersFileName = Module['name'] + HANDLERS_FILE_NAME_SUFFIX
        self.Files[NewHandlersFileName] = self.Files[PreviousHandlersFileName]
        del self.Files[PreviousHandlersFileName]

        for ParentID in Module['parent_ids']:
            ParentModule = self.GetModuleByID(ParentID)
            for HandlerIndex in FindModuleHandlers(ParentModule['module']):
                Param = ParentModule['parameters'][HandlerIndex]
                if '@' in Param and Param.split('@')[1] == PreviousName:
                    ParentModule['parameters'][nParam] = '@' + AskedName

        for HandlerIndex in FindModuleHandlers(Module['module']):
            HandlerName = Module['module']['parameters'][HandlerIndex]['name']
            PreviousHandlerParamFuncName = LAMBDA_FUNCTION_FROM.format(PreviousName, HandlerName)
            if Module['parameters'][HandlerIndex] == '@' + PreviousHandlerParamFuncName:
                NewHandlerParamFuncName = LAMBDA_FUNCTION_FROM.format(AskedName, HandlerName)
                Module['parameters'][HandlerIndex] = '@' + NewHandlerParamFuncName
                Module['lambda_functions'][NewHandlerParamFuncName] = Module['lambda_functions'][PreviousHandlerParamFuncName]
                del Module['lambda_functions'][PreviousHandlerParamFuncName]
        self.UpdateHandlersCodeFiles()

    def SetType(self, Module, NewType, UpdatedIDsOnTrigger = []):
        W(Module['name']+" start")
        OriginalUpdatedIDsOnTrigger = list(UpdatedIDsOnTrigger)
        print(OriginalUpdatedIDsOnTrigger)
        if Module['id'] in UpdatedIDsOnTrigger: # To avoid permanent recursion
            return None
        self.LogFunction("Updating type of "+Module['name'])

        UpdatedIDsOnTrigger += [Module['id']]
        if Module['module']['origin'] == 'sepia' and 'observable' in  Module['module']['name']: # Here, type is actually the output type
            Found = False
            for TemplateField in Module['module']['templates']:
                if TemplateField['name'] == 'event_stream_type':
                    Module['templates'][TemplateField['template_number']] = NewType['name']
                    Found = True
                    break

            if not Found:
                self.LogFunction("Unable to change type for sepia module in SetType: no event_stream_type field found")
                return None

            HandlersParamsIndexes = FindModuleHandlers(Module['module'])
            HandlerIndex = HandlersParamsIndexes[0]
            HandlerName = Module['module']['parameters'][HandlerIndex]['name']

            if NewType['name'] == self.NoneType['name']:
                Module['ev_outputs'][HandlerName] = []
            else:
                Module['ev_outputs'][HandlerName] = [{'type': NewType['name'], 'name': 'event'}]
        
            HandlerParamFuncName  = LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName)

            if Module['parameters'][HandlerIndex] != '@' + HandlerParamFuncName: # Way to know that a link has been made for this handler
                ChildrenModule = self.GetModuleByName(Module['parameters'][HandlerIndex].split('@')[-1])
                self.LinksTypes[GetLinkTuple(Module['id'], ChildrenModule['id'])][1] = NewType['name']
                self.SetType(ChildrenModule, NewType, UpdatedIDsOnTrigger)
            else: # If no link, then lets tell the lambda function which type it gets
                Module['lambda_functions'][HandlerParamFuncName].input_fields = Module['ev_outputs'][HandlerName]

            self.FillLambdasLinks(Module['id'])
            # Those modules cannot have parents

        elif Module['module']['origin'] == 'sepia' and  Module['module']['name'] == 'make_split':
                self.LogFunction('Not implemented')
        else:
            Found = False
            W(Module['name']+" 1")
            for TemplateField in Module['module']['templates']:
                if TemplateField['name'] == 'Event':
                    Module['templates'][TemplateField['template_number']] = NewType['name']
                    Found = True
                    break

            if not Found:
                self.LogFunction("Unable to change type for module in SetType: no Event field found")
                self.UpdateHandlersCodeFiles()
                return None
            
            HandlersParamsIndexes = FindModuleHandlers(Module['module'])
            EventToParamIndexes = FindModuleEventTo(Module['module'])

            W(Module['name']+" 2")
            HasUpdatedRelative = False
            for nHandlerLocal in range(len(HandlersParamsIndexes)):
                HandlerIndex = HandlersParamsIndexes[nHandlerLocal]
                HandlersParamsIndexes = FindModuleHandlers(Module['module'])
                HandlerIndex = HandlersParamsIndexes[0]
                HandlerName = Module['module']['parameters'][HandlerIndex]['name']

                if NewType['name'] == self.NoneType['name']:
                    Module['ev_outputs'][HandlerName] = list(Module['module']['ev_outputs'][HandlerName])
                else:
                    for nField, Field in enumerate(Module['module']['ev_outputs'][HandlerName]):
                        if Field['type'] == 'Event':
                            Module['ev_outputs'][HandlerName][nField]['type'] = NewType['name']
        
                if EventToParamIndexes: # If there is a lambda function out of this module, then he had to deal with the descending change of type
                    EventToParamIndex = EventToParamIndexes[nHandlerLocal]
                    EventToParamName = Module['module']['parameters'][EventToParamIndex]['name']
                    EventToParamFuncName = LAMBDA_FUNCTION_FROM.format(Module['name'], EventToParamName)
                    if EventToParamFuncName in Module['lambda_functions'].keys():
                        Module['lambda_functions'][EventToParamFuncName].input_fields = Module['ev_outputs'][HandlerName]
                        continue
                HandlerParamFuncName  = LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName)

                if Module['parameters'][HandlerIndex] != '@' + HandlerParamFuncName: # Way to know that a link has been made for this handler
                    ChildrenModule = self.GetModuleByName(Module['parameters'][HandlerIndex].split('@')[-1])
                    HasUpdatedRelative = True
                    self.LinksTypes[GetLinkTuple(Module['id'], ChildrenModule['id'])][1] = NewType['name']
                    self.SetType(ChildrenModule, NewType, UpdatedIDsOnTrigger)

                else:
                    Module['lambda_functions'][HandlerParamFuncName].input_fields = Module['ev_outputs'][HandlerName]

            W(Module['name']+" 3")
            for ParentID in Module['parent_ids']:
                print("Going up to {0}".format(ParentID))
                self.LinksTypes[GetLinkTuple(Module['id'], ParentID)][1] = NewType['name']
                self.SetType(self.GetModuleByID(ParentID),  NewType, UpdatedIDsOnTrigger)
            self.FillLambdasLinks(Module['id'])
        if OriginalUpdatedIDsOnTrigger:
            return None
        self.UpdateHandlersCodeFiles()

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
            del self.Files[TYPES_DEF_FILE]
            return None
        
        self.Files[TYPES_DEF_FILE] = {'data': '', 'type': 'code'}

        for TypeName in sorted(self.UserDefinedTypes.keys()):
            self.Files[TYPES_DEF_FILE]['data'] += self.UserDefinedTypes[TypeName]['data']
            self.Files[TYPES_DEF_FILE]['data'] += '\n'

    def UpdateHandlersCodeFiles(self):
        for Module in self.Modules:
            if Module['module']['origin'] != 'chameleon' and Module['module']['origin'] != USER_DEFINED:
                self.GenerateCurrentHandlersFile(Module)

    def GenerateCurrentHandlersFile(self, Module):
        print("Generating handler code file for {0}".format(Module['name']))
        HandlersFileName = Module['name'] + HANDLERS_FILE_NAME_SUFFIX
        self.Files[HandlersFileName]['data'] = ''

        HandlersParamsIndexes = FindModuleHandlers(Module['module'])
        EventToParamIndexes = FindModuleEventTo(Module['module'])

        if EventToParamIndexes and len(EventToParamIndexes) != len(HandlersParamsIndexes):
            self.LogFunction("EventTo function found, but not the same number as HandleEvents. Unpredictable behavious expected")

        for nHandlerLocal in range(len(HandlersParamsIndexes)):
            HandlerIndex = HandlersParamsIndexes[nHandlerLocal]
            HandlerName = Module['module']['parameters'][HandlerIndex]['name']

            if EventToParamIndexes:
                EventToParamIndex = EventToParamIndexes[nHandlerLocal]
                EventToParamName = Module['module']['parameters'][EventToParamIndex]['name']
                EventToParamFuncName = LAMBDA_FUNCTION_FROM.format(Module['name'], EventToParamName)
                
                self.Files[HandlersFileName]['data'] += '// '+EventToParamFuncName+'\n'
                FuncName = LAMBDA_FUNCTION_FROM.format(Module['name'], EventToParamName)
                self.Files[HandlersFileName]['data'] += Module['lambda_functions'][FuncName]['data']
                self.Files[HandlersFileName]['data'] += '\n'

            self.Files[HandlersFileName]['data'] += '// '+HandlerName+'\n'

            FuncName = LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName)
            if FuncName in Module['lambda_functions'].keys():
                self.Files[HandlersFileName]['data'] += Module['lambda_functions'][FuncName]['data']
            else:
                self.Files[HandlersFileName]['data'] += Module['parameters'][HandlerIndex]+'\n\n'

            self.Files[HandlersFileName]['data'] += '\n'

    def RemoveLambdaFunction(self, FuncName):
        del self.Files[FuncName]

    def ModuleNameValidity(self, Module, NewName):
        if NewName == '':
            return False
        for ComparedModule in self.Modules:
            if ComparedModule['name'] == NewName and Module['id'] != ComparedModule['id']:
                return False
        return True

    def WellDefinedModule(self, Module):
        for nModule, ParameterAsked in enumerate(Module['module']['parameters']):
            if Module['parameters'][nModule] == '':
                return False
            CanBeChecked, WasChecked = CheckParameterValidity(ParameterAsked['type'], Module['parameters'][nModule])
            if CanBeChecked and not WasChecked:
                return False
        return True

    def GetFreeHandlersSlots(self, ModuleID):
        Module = self.GetModuleByID(ModuleID)
        HandlersParamsIndexes = FindModuleHandlers(Module['module'])
        FreeHandlersParamsIndexes = []
        for HandlerIndex in HandlersParamsIndexes:
            if self.IsFreeSlot(Module, HandlerIndex):
                FreeHandlersParamsIndexes += [HandlerIndex]
        return FreeHandlersParamsIndexes

    def IsFreeSlot(self, Module, HandlerIndex):
        HandlerName = Module['module']['parameters'][HandlerIndex]['name']
        HandlerParamFuncName  = LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName)
        if (Module['parameters'][HandlerIndex] == '@'+HandlerParamFuncName) and Module['lambda_functions'][HandlerParamFuncName]['default']:
            return True
        return False

    def GetModuleByID(self, ID):
        for Module in self.Modules:
            if Module['id'] == ID:
                return Module

    def GetModuleByName(self, Name):
        for Module in self.Modules:
            if Module['name'] == Name:
                return Module

    def GetNewID(self):
        if not self.ModulesIDs:
            NewID = 0
        else:
            NewID = max(self.ModulesIDs) + 1
        self.ModulesIDs += [NewID]
        return NewID

    def GetChildrenIDs(self, ParentID):
        IDs = []
        ParentModule = self.GetModuleByID(ParentID)
        HandlersParamsIndexes = FindModuleHandlers(ParentModule['module'])
        for nParam in HandlersParamsIndexes:
            if ParentModule['parameters'][nParam]:
                IDs += [self.GetModuleByName(ParentModule['parameters'][nParam].split('@')[-1])['id']]
        return IDs

    def GetParentAndChildFromLinkTuple(self, Tuple):
        if Tuple[1] in self.GetModuleByID(Tuple[0])['parent_ids']:
            return Tuple[1], Tuple[0]
        else:
            return Tuple[0], Tuple[1]

    def GenerateCode(self):
        self.Writer.WriteCode(self)

    def GenerateBuild(self):
        self.Writer.BuildDirectory(self.Data['name'], force = True)
        ChameleonModules = []
        for Module in self.Modules:
            if Module['module']['origin'] == 'chameleon':
                ChameleonModules += [Module]
        LuaFilename = self.Writer.CreateLUAFile(self.Data['name'], ChameleonModules)
        self.Files[LuaFilename] = {'data':LoadFile(LuaFilename), 'type': 'build'}
        return LuaFilename

def GetLinkTuple(M1ID, M2ID):
    return (min(M1ID, M2ID), max(M1ID, M2ID))

def FindModuleHandlers(Module):
    if Module['origin'] == USER_DEFINED:
        return []
    Indexes = []
    for nParam, Param in enumerate(Module['parameters']):
        if re.compile('Handle[a-zA-Z]*').match(Param['type']):
            if 'exception' not in Param['type'].lower():
                Indexes += [nParam]
    return Indexes

def FindModuleEventTo(Module):
    if Module['origin'] == USER_DEFINED:
        return []
    Indexes = []
    for nParam, Param in enumerate(Module['parameters']):
        if re.compile(tarsier_scrapper.EVENT_TO_REGEX).match(Param['type']):
            Indexes += [nParam]
    return Indexes

def CountEventsHandlers(Module):
    if Module['origin'] == USER_DEFINED:
        return 0
    nOutputs = 0
    for Template in Module['templates']:
        if Template['type'] == 'typename' and re.compile('Handle[a-zA-Z]*').match(Template['name']):
            if 'exception' not in Template['name'].lower():
                nOutputs += 1
    return nOutputs

def LoadFile(Filename):
    with open(Filename, 'r') as f:
        Lines = f.readlines()
    return ''.join(Lines)

class SimiliDict:
    def __init__(self):
        None
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

class EventTypeClass(SimiliDict):
    def __init__(self, Name, Value = None, Fields = [], Origin = USER_DEFINED):
        self.name = Name
        self.value = Value
        self.fields = Fields
        self.origin = Origin
        self.data = ''
        self.EVENT_TYPE_INTRO = '// #arl_{0}\n'
        self.ReferencedByModuleIDs = []

    def Write(self):
        self.data = self.EVENT_TYPE_INTRO.format(self.name)
        self.data += 'struct {0}'.format(self.name) + ' {\n'
        for field in self.fields:
            if field['type'].strip() or field['name'].strip():
                self.data += CPP_TAB + field['type'] + ' ' + field['name'] + ';\n'
        self.data += '}\n'

class LambdaFunctionClass(SimiliDict):
    def __init__(self, ID, Name, IntroductionLine = '', InputFields = [], RequiredFieldsCommentLine = '', GlobalContext = False, ReturnedObject = ''):
        self.id = ID
        self.name = Name
        self.default = True
        self.data = ''
        self.auto_written_lines = {}

        self.input_fields = InputFields
        self.intro_comment_line = IntroductionLine
        self.req_fields_comment_line = RequiredFieldsCommentLine
        self.global_context = GlobalContext
        self.returned_object = ReturnedObject

        # Module compatibility
        self.module = {'origin' : USER_DEFINED,
                        'parameters':[],
                        'templates':[],
                        'has_event_to':False,
                        'ev_outputs':[],
                        'has_operator':False,
                        'ev_fields':[]}
        
        self.AUTO_WRITTEN_LINE_COMMENT = ' // #arl{0}'

    def Write(self):
        self.data = self.intro_comment_line
        self.data += self.req_fields_comment_line
        self.data += '['
        if self.global_context:
            self.data += '&'
        self.data += ']('
        if not self.input_fields:
            None
        else:
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
        self.data += ')' + self.returned_object + '{\n'
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
                for LambdaFunctionName, LambdaFunction in Module['lambda_functions'].items():
                    self._AddLambdaFunction(LambdaFunctionName, LambdaFunction['data'])
                    self._JumpLines(1)

            while len(self.WrittenModulesIDs) != len(Framework.Modules):
                for Module in Framework.Modules:
                    if Module['id'] in self.WrittenModulesIDs:
                        continue
                    AllChildrenWritten = True
                    for HandlerIndex in FindModuleHandlers(Module['module']):
                        HandlerName = Module['module']['parameters'][HandlerIndex]['name']
                        HandlerParamFuncName = LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName)
                        if (not (Module['parameters'][HandlerIndex] == '@'+HandlerParamFuncName)):
                            ChildrenName = Module['parameters'][HandlerIndex].split('@')[-1]
                            ChildrenID = Framework.GetModuleByName(ChildrenName)['id']
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
