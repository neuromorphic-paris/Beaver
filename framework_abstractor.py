import os
import sys

import tarsier_scrapper
import sepia_scrapper

class FrameworkAbstraction:
    def __init__(self, Data = None, LogFunction = None):
        self.Data = {'modules': [], 'name': '', 'events_types': [], 'files': {'Documentation':'        ~ Generated with Beaver ~'}, 'user_defined': []}
        self.ModulesIDs = []
        self.HasChameleon = False
        self.HasTariser = False
        if not Data is None:
            self._LoadData(Data)

        self.Modules = self.Data['modules']
        self.EventsTypes = self.Data['events_types']
        self.Files = self.Data['files'] # Abstracted Files, not actual ones
        self.UserWrittenCode = self.Data['user_defined']
        
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

    def AddModule(self, Module):
        if not self.ModulesIDs:
            NewID = 0
        else:
            NewID = max(self.ModulesIDs) + 1
        self.Modules += [{'module': Module, 'id': NewID, 'parameters': []}]
        self.ModulesIDs += [NewID]

    def GenerateCode(self):
        self.Writer.WriteCode(self.Data)

    def GenerateBuild(self):
        self.Writer.BuildDirectory(self.Data['name'], force = True)
        ChameleonModules = []
        for Module in self.Modules:
            if Module['module']['origin'] == 'chameleon':
                ChameleonModules += [Module]
        LuaFilename = self.Writer.CreateLUAFile(self.Data['name'], ChameleonModules)
        self.Files[LuaFilename] = LoadFile(LuaFilename)
        return LuaFilename

    def WellDefinedModule(self, Module):
        if len(Module['parameters']) == len(Module['module']['parameters']):
            return True
        else:
            return False

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
                ans = raw_input("Found already existing project folder with name '{0}'. Erase ? (y/N) ".format(ProjectName))
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
    
            for ConfigName, Config in self.SYSTEM_CONFIGS.items():
                LuaFile.write(2*self.LUA_TAB + "configuration '{0}'\n".format(ConfigName))
                for Key, Value in Config.items():
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
