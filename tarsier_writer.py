import os

PROJECTS_DIRECTORY = "Projects/"
SOURCE_DIRECTORY = 'source/'
THIRD_PARTY_DIRECTORY = 'third_party/'

BUILD_TARGET = "build/"

LUA_TAB = " "*4

SYSTEM_CONFIGS = {}
SYSTEM_CONFIGS['release'] = {'targetdir': BUILD_TARGET + 'release', 'defines': ['NDEBUG'], 'flags': ['OptimizeSpeed']}
SYSTEM_CONFIGS['debug'] = {'targetdir': BUILD_TARGET + 'debug', 'defines': ['DEBUG'], 'flags': ['Symbols']}
SYSTEM_CONFIGS['linux'] = {'links': ['pthread'], 'buildoptions': ['-std=c++11'], 'linkoptions': ['-std=c++11']}
SYSTEM_CONFIGS['macosx'] = {'buildoptions': ['-std=c++11'], 'linkoptions': ['-std=c++11']}
SYSTEM_CONFIGS['windows'] = {'files': ['.clang-format']}

def _GetProjectDir(ProjectName):
    if ProjectName[-1] == '/':
        ProjectName = ProjectName[:-1]
    ProjectDir = PROJECTS_DIRECTORY + ProjectName + '/'
    return ProjectDir

def _AddInclude(File, ModuleOrigin, ModuleFile):
    File.write("#include \"../" + THIRD_PARTY_DIRECTORY + ModuleOrigin + "source/" + ModuleFile + "\"\n")

def BuildDirectory(ProjectName):
    ProjectDir = _GetProjectDir(ProjectName)
    if ProjectName in os.listdir(PROJECTS_DIRECTORY):
        ans = raw_input("Found already existing project folder with name '{0}'. Erase ? (y/N) ".format(ProjectName))
        if not ans.lower() == 'y':
            return False
        os.system('rm -rf '+ ProjectDir)
    os.mkdir(ProjectDir)
    os.mkdir(ProjectDir + SOURCE_DIRECTORY)
    os.mkdir(ProjectDir + THIRD_PARTY_DIRECTORY)

    os.system('cp -r tarsier/ {0}'.format(ProjectDir + 'third_party/'))
    os.system('cp -r sepia/ {0}'.format(ProjectDir + 'third_party/'))

def CreateLUAFile(ProjectName, ChameleonModules = []):
    ProjectDir = _GetProjectDir(ProjectName)
    configurations = ['release', 'debug']
    with open(ProjectDir + 'premake4.lua', 'w') as LuaFile:
        if ChameleonModules:
            LuaFile.write("local qt = require '{0}chameleon/qt'\n".format(THIRD_PARTY_DIRECTORY))
            LuaFile.write("\n")
        LuaFile.write("solution '{0}'\n".format(ProjectName))
        LuaFile.write(LUA_TAB + "configurations {'" + "', '".join(configurations) + "'}\n")
        LuaFile.write(LUA_TAB + "location '{0}'\n".format(BUILD_TARGET[:-1]))
        LuaFile.write(LUA_TAB + "project '{0}'\n".format(ProjectName))

        LuaFile.write(2*LUA_TAB + "kind 'ConsoleApp'\n")
        LuaFile.write(2*LUA_TAB + "language 'C++'\n")
        LuaFile.write(2*LUA_TAB + "location '{0}'\n".format(BUILD_TARGET[:-1]))
        Files = ['*.cpp', '*.hpp']
        if ChameleonModules:
            Files += ['*.qml']
        LuaFile.write(2*LUA_TAB + "files {'" + ("', '".format(SOURCE_DIRECTORY)).join([SOURCE_DIRECTORY + File for File in Files]) + "'}\n")
        if ChameleonModules:
            LuaFile.write(2*LUA_TAB + "files(qt.moc({\n")

            ModulesStr = ",\n".join([3*LUA_TAB + "{0}chameleon/source/{1}.hpp".format(THIRD_PARTY_DIRECTORY, Module) for Module in ChameleonModules]) + "},\n"
            LuaFile.write(ModulesStr)
            LuaFile.write(3*LUA_TAB + "'build/moc'))\n")
            for AddedField in ["includedirs(qt.includedirs())", "libdirs(qt.libdirs())", "links(qt.links())", "buildoptions(qt.buildoptions())", "linkoptions(qt.linkoptions())"]:
                LuaFile.write(3*LUA_TAB + AddedField + "\n")
        LuaFile.write(2*LUA_TAB + "defines {'SEPIA_COMPILER_WORKING_DIRECTORY="' .. project().location .. '"'}\n")

        for ConfigName, Config in SYSTEM_CONFIGS.items():
            LuaFile.write(2*LUA_TAB + "configuration '{0}'\n".format(ConfigName))
            for Key, Value in Config.items():
                if type(Value) == list:
                    LuaFile.write(3*LUA_TAB + Key + " {'" + "', '".join(Value) + "'}\n")
                else:
                    LuaFile.write(3*LUA_TAB + Key + " '{0}'\n".format(Value))
    print "Generated Lua file"

def WriteCode(ProjectName, Framework):
    ProjectDir = _GetProjectDir(ProjectName)
    with open(ProjectDir + SOURCE_DIRECTORY + ProjectName + '.cpp', 'w') as CppFile:
        _AddInclude(CppFile, 'sepia/', 'sepia.hpp')

testName = 'test'
BuildDirectory(testName)
CreateLUAFile(testName)
WriteCode(testName, {})
