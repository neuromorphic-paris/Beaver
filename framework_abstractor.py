import os
import sys
import re

import tarsier_scrapper
import sepia_scrapper

class FrameworkAbstraction:
    def __init__(self, Data = None, LogFunction = None):
        self.Data = {'modules': [], 'name': '', 'events_types': [], 'files': {'Documentation':{'data': '~ Generated with Beaver ~', 'type': 'documentation'}}, 'user_defined': [], 'links_types': {}, 'chameleon_tiles': {}}
        self.ModulesIDs = []
        self.HasChameleon = False
        self.HasTariser = False
        if not Data is None:
            self._LoadData(Data)

        self.Modules = self.Data['modules']
        self.EventsTypes = self.Data['events_types']
        self.Files = self.Data['files'] # Abstracted Files, not actual ones
        self.UserWrittenCode = self.Data['user_defined']
        self.LinksTypes = self.Data['links_types']
        self.ChameleonTiles = self.Data['chameleon_tiles']
        
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
            if Module['module']['origin'] == 'tarsier':
                self.HasTariser = True
            elif Module['module']['origin'] == 'chameleon':
                self.HasChameleon = True

    def AddModule(self, Module, AskedModuleName = None):
        if not self.ModulesIDs:
            NewID = 0
        else:
            NewID = max(self.ModulesIDs) + 1
        self.Modules += [{'module': Module, 'id': NewID, 'parameters': [param['default'] for param in Module['parameters']], 'parent_ids': [], 'name': Module['name'], 'templates': [template['default'] for template in Module['templates']]}]
        if not AskedModuleName is None:
            self.Modules[-1]['name'] = AskedModuleName
        self.ModulesIDs += [NewID]
        return self.Modules[-1]

    def AddLink(self, ParentID, ChildrenID):
        ParentModule = self.GetModuleByID(ParentID)
        ChildrenModule = self.GetModuleByID(ChildrenID)

        Added = False
        HandlersParamsIndexes = FindModuleHandlers(ParentModule['module'])
        for nParam in HandlersParamsIndexes:
            if not ParentModule['parameters'][nParam]:
                ParentModule['parameters'][nParam] = '@' + ChildrenModule['name']
                Added = True
                break
        if not Added:
            self.LogFunction("Unable to link {0} to {1} : no Handler slot available".format(ParentModule['name'], ChildrenModule['name']))
            return False
        ChildrenModule['parent_ids'] += [ParentID]
        self.LinksTypes[GetLinkTuple(ParentID, ChildrenID)] = None
        return True

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
            return False
        ChildrenModule['parent_ids'].remove(ParentModule['id'])
        del self.LinksTypes[GetLinkTuple(ParentID, ChildrenID)]
        return True

    def GenerateCode(self):
        self.Writer.WriteCode(self.Data)

    def GenerateBuild(self):
        self.Writer.BuildDirectory(self.Data['name'], force = True)
        ChameleonModules = []
        for Module in self.Modules:
            if Module['module']['origin'] == 'chameleon':
                ChameleonModules += [Module]
        LuaFilename = self.Writer.CreateLUAFile(self.Data['name'], ChameleonModules)
        self.Files[LuaFilename] = {'data':LoadFile(LuaFilename), 'type': 'build'}
        return LuaFilename

    def WellDefinedModule(self, Module):
        for nModule, ParameterAsked in enumerate(Module['module']['parameters']):
            if Module['parameters'][nModule] == '':
                return False
            CanBeChecked, WasChecked = CheckParameterValidity(ParameterAsked['type'], Module['parameters'][nModule])
            if CanBeChecked and not WasChecked:
                return False
        return True

    def GetModuleByID(self, ID):
        for Module in self.Modules:
            if Module['id'] == ID:
                return Module

    def GetModuleByName(self, Name):
        for Module in self.Modules:
            if Module['name'] == Name:
                return Module

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

def GetLinkTuple(M1ID, M2ID):
    return (min(M1ID, M2ID), max(M1ID, M2ID))

def FindModuleHandlers(Module):
    Indexes = []
    for nParam, Param in enumerate(Module['parameters']):
        if re.compile('Handle[a-zA-Z]*').match(Param['type']):
            if 'exception' not in Param['type'].lower():
                Indexes += [nParam]
    return Indexes

def CountEventsHandlers(Module):
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

class CodeWriterClass:
    def __init__(self, LogFunction = None):
        self.PROJECTS_DIRECTORY = "Projects/"
        self.SOURCE_DIRECTORY = 'source/'
        self.THIRD_PARTY_DIRECTORY = 'third_party/'

        self.BUILD_TARGET = "build/"

        self.LUA_TAB = " "*4

        self.SYSTEM_CONFIGS = {}
        self.SYSTEM_CONFIGS['release'] = {'targetdir': self.BUILD_TARGET + 'release', 'defines': ['NDEBUG'], 'flags': ['OptimizeSpeed']}
        self.SYSTEM_CONFIGS['debug'] = {'targetdir': self.BUILD_TARGET + 'debug', 'defines': ['DEBUG'], 'flags': ['Symbols']}
        self.SYSTEM_CONFIGS['linux'] = {'links': ['pthread'], 'buildoptions': ['-std=c++11'], 'linkoptions': ['-std=c++11']}
        self.SYSTEM_CONFIGS['macosx'] = {'buildoptions': ['-std=c++11'], 'linkoptions': ['-std=c++11']}
        self.SYSTEM_CONFIGS['windows'] = {'files': ['.clang-format']}

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
    
    def _AddIncludeModule(self, File, ModuleOrigin, ModuleFile):
        File.write("#include \"../" + self.THIRD_PARTY_DIRECTORY + ModuleOrigin + "source/" + ModuleFile + "\"\n")

    def WriteCode(self, Framework):
        ProjectName = Framework['name']
        ProjectDir = self._GetProjectDir(ProjectName)
        with open(ProjectDir + self.SOURCE_DIRECTORY + ProjectName + '.cpp', 'w') as CppFile:
            _AddIncludeModule(CppFile, 'sepia/', 'sepia.hpp')

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
