import numpy as np

import matplotlib
import matplotlib.pyplot as pyl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

import tkinter as Tk
from tkinter import ttk
from tkinter import scrolledtext as ScrolledText
from tkinter import messagebox as MessageBox
from tkinter import filedialog as FileDialog
from tkinter import font as tkFont

import os
import json
import inspect
from functools import partial
matplotlib.use("TkAgg")

import tarsier_scrapper
import sepia_scrapper
import chameleon_scrapper
import framework_abstractor

PROJECTS_DIR = 'Projects/'

TARSIER_UNSUPPORTED_MODULES = []
TARSIER_UNSUPPORTED_MODULES += ['hash'] # handle_event is in destructor, as it forces compiler to run the code

SEPIA_UNSUPPORTED_MODULES = []

CHAMELEON_UNSUPPORTED_MODULES = []

UNSUPPORTED_MODULES = TARSIER_UNSUPPORTED_MODULES + SEPIA_UNSUPPORTED_MODULES + CHAMELEON_UNSUPPORTED_MODULES

def about_command():
    label = MessageBox.showinfo("About", "Tarsier code geneerator\nWork In Progress, be kind\nPlease visit https://github.com/neuromorphic-paris/")

        
class GUI:
    def __init__(self):
        self.Framework = framework_abstractor.FrameworkAbstraction(LogFunction = self.Log)
        self.FrameworkFileName = ''

        self.Options = {'display_module_ev_outputs':True}

        TarsierModules = tarsier_scrapper.ScrapTarsierFolder()
        SepiaModules, SepiaTypes, SepiaUtilities = sepia_scrapper.ScrapSepiaFile()
        ChameleonModules = chameleon_scrapper.ScrapChameleonFolder()

        self.AvailableModules = {}
        for ModuleName, Module in list(TarsierModules.items()):
            self.AvailableModules[ModuleName] = Module
        for ModuleName, Module in list(SepiaModules.items()):
            self.AvailableModules[ModuleName] = Module
        for ModuleName, Module in list(ChameleonModules.items()):
            self.AvailableModules[ModuleName] = Module

        self.BaseTypes = {framework_abstractor.NoneEventType['name']: framework_abstractor.NoneEventType}
        for TypeName, Type in list(SepiaTypes.items()):
            self.BaseTypes[TypeName] = Type
        self.AvailableTypes = dict(self.BaseTypes)

        self.AvailableUtilities = {}
        for UtilityName, Utility in SepiaUtilities.items():
            self.AvailableUtilities[UtilityName] = Utility

        self.UserDefinedVariableTypes = ['Event type']
        self.MenuParams = {'event_stream_type': (self.AvailableTypes, self._OnEventTypeTemplateChange, self._OnNewEventTypeTemplate), 'Event': (self.AvailableTypes, self._OnEventTypeTemplateChange, self._OnNewEventTypeTemplate)}

        self.MainWindow = Tk.Tk()
        self.MainWindow.bind("<F4>", lambda event:self.MainWindow.destroy())
        self.MainWindow.title('Beaver - {0}'.format(framework_abstractor.DEFAULT_NAME))

        MainMenu = Tk.Menu(self.MainWindow)
        self.MainWindow.config(menu=MainMenu)
        filemenu = Tk.Menu(MainMenu)
        MainMenu.add_cascade(label="File", menu = filemenu)
        filemenu.add_command(label="New", command=self.GenerateEmptyFramework)
        filemenu.add_command(label="Open...", command=self.open_command)
        filemenu.add_command(label="Save", command=self.save_command)
        filemenu.add_command(label="Save as...", command=self.saveas_command)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self._on_closing) 

        insertmenu = Tk.Menu(MainMenu)
        MainMenu.add_cascade(label="Insert", menu = insertmenu)
        newmenu = Tk.Menu(insertmenu)
        insertmenu.add_cascade(label = "New", menu = newmenu)
        for Type in self.UserDefinedVariableTypes:
            newmenu.add_command(label=Type, command=partial(self.AddType, Type))
        insertmenu.add_separator()

        def FirstUp(string):
            return string[0].upper()+string[1:]

        Menus = {'sepia':Tk.Menu(insertmenu), 'tarsier':Tk.Menu(insertmenu), 'chameleon':Tk.Menu(insertmenu)}
        HasSeparator = {Key: False for Key in Menus.keys()}
        for origin, Menu in Menus.items():
            insertmenu.add_cascade(label = FirstUp(origin), menu = Menu)
        for ModuleName in sorted(self.AvailableModules.keys()):
            if ModuleName not in UNSUPPORTED_MODULES:
                Module = self.AvailableModules[ModuleName]
                Menus[Module['origin']].add_command(label=ModuleName, command=partial(self.AddModule, str(ModuleName)))
        for UtilityName in sorted(self.AvailableUtilities.keys()):
            Utility = self.AvailableUtilities[UtilityName]
            if not HasSeparator[Utility['origin']]:
                Menus[Utility['origin']].add_separator()
                HasSeparator[Utility['origin']] = True
            Menus[Utility['origin']].add_command(label=UtilityName, command=partial(self.AddUtility, str(UtilityName)))
        

        helpmenu = Tk.Menu(MainMenu)
        MainMenu.add_cascade(label="Help", menu=helpmenu)
        helpmenu.add_command(label="About...", command=about_command)

        self.MainWindow.grid_columnconfigure(0, weight=1)
        self.MainWindow.grid_rowconfigure(0, weight=1)

        self.Display = Figure(figsize=(5,5), dpi=150)
        self.DisplayAx = self.Display.add_subplot(111)
        self.DisplayAx.tick_params('both', bottom = 'off', left = 'off', labelbottom = 'off', labelleft = 'off')
        self.Display.tight_layout()
        
        self.DisplayCanvas = FigureCanvasTkAgg(self.Display, self.MainWindow)
        cid = self.DisplayCanvas.mpl_connect('button_press_event', self._onDisplayClick)
        self.DisplayCanvas.show()
        self.DisplayCanvas.get_tk_widget().grid(row = 0, column = 0)

        self.AutoAddBGR = False
        self.AvailablesModulesPositions = []
        self.SelectedAvailableModulePosition = 0
        self.SelectedAvailableChameleonModulePosition = 0
        self.ModulesDiameter = 2.
        self.HModulesTilingDistance = 6.
        self.VModulesTilingDistance = 4.
        self.DisplayedModulesPositions = {}

        self.DisplayedLinks = {}
        self.ActiveItem = None
        
        self.DisplayCodeLinkFrame = Tk.Frame(self.MainWindow)
        self.DisplayCodeLinkFrame.grid(row = 0, column = 1)
        self.DisplayWorkFrame = Tk.Frame(self.DisplayCodeLinkFrame, bd = 4, relief='groove')
        self.DisplayWorkFrame.grid(row = 0, column = 0)
        ErasePicture = Tk.PhotoImage(file = 'Icons/erase.png')
        self.RemoveModuleButton = Tk.Button(self.DisplayWorkFrame, image=ErasePicture, command = self.RemoveModule)
        self.RemoveModuleButton.image = ErasePicture
        self.RemoveModuleButton.grid(row = 0, column = 0)
        RoutePicture = Tk.PhotoImage(file = 'Icons/route.png')
        self.RouteModuleButton = Tk.Button(self.DisplayWorkFrame, image=RoutePicture, command = self.RouteModule)
        self.RouteModuleButton.image = RoutePicture
        self.RouteModuleButton.grid(row = 1, column = 0)
        self.WaitingForRoute = None

        self.CodeWorkFrame = Tk.Frame(self.DisplayCodeLinkFrame, bd = 4, relief='groove')
        self.CodeWorkFrame.grid(row = 1, column = 0)
        self.ModuleCodeDisplayButton = Tk.Button(self.CodeWorkFrame, text = '?', command = self.DisplayModuleCode, font = tkFont.Font(size = 20))
        self.ModuleCodeDisplayButton.grid(row = 0, column = 0)

        self.TempFiles = {}

        self.DefaultFile = framework_abstractor.GENERAL_FILENAME
        self.CodeFrame = Tk.Frame(self.MainWindow)
        self.CodeFrame.grid(row = 0, column = 2)
        self.CurrentCodeFile = list(self.Framework.Files(Bare = True).keys())[0]
        self.CodeFileVar = Tk.StringVar(self.MainWindow)
        self.CodeFileVar.set(self.CurrentCodeFile)
        self.CodeFileMenu = Tk.OptionMenu(self.CodeFrame, self.CodeFileVar, *self.Framework.Data['files'])
        self.CodeFileMenu.grid(row = 0, column = 0)
        self.CodePad = ScrolledText.ScrolledText(self.CodeFrame, width=120, height=40, bg = 'white')
        self.CodePad.bind("<<TextModified>>", self._onCodeModification)
        def _tab(arg):
            self.CodePad.insert(Tk.INSERT, framework_abstractor.CPP_TAB)
            return 'break'
        self.CodePad.bind("<Tab>", _tab)
        self.CodePad.grid(row = 1, column = 0)
        self.SortedFiles = []
        
        self.ParamsFrame = Tk.Frame(self.MainWindow, width = 100, bd = 4, relief='groove')
        self.ParamsFrame.grid(row = 2, column = 0, rowspan = 1, columnspan = 1, sticky=Tk.N+Tk.S+Tk.E+Tk.W)
        self.ParamsTitleFrame = Tk.Frame(self.ParamsFrame)
        self.ParamsTitleFrame.grid(row = 0, column = 0, columnspan = 2, sticky=Tk.N+Tk.S+Tk.W)

        self.ParamsValuesFrame = Tk.Frame(self.ParamsFrame, bd = 2, relief='groove')
        self.ParamsValuesFrame.grid(row = 1, column = 0, sticky = Tk.N+Tk.S+Tk.E+Tk.W)
        self.ParamsButtonsFrame = Tk.Frame(self.ParamsFrame)
        self.ParamsButtonsFrame.grid(row = 1, column = 1, sticky = Tk.N+Tk.S+Tk.E)
        self.ParamsUpperButton = Tk.Button(self.ParamsButtonsFrame, text = '^', height = 10, command = partial(self.UpdateDisplayedParams, -1))
        self.ParamsLowerButton = Tk.Button(self.ParamsButtonsFrame, text = 'v', height = 10, command = partial(self.UpdateDisplayedParams, +1))
        self.ParamsUpperButton.grid(row = 0, column = 0)
        self.ParamsLowerButton.grid(row = 1, column = 0)
        self.DisplayedParams = []
        self.NFieldsDisplayed = 13
        self.CurrentMinParamDisplayed = 0


        self.CompilationFrame = Tk.Frame(self.MainWindow)
        self.CompilationFrame.grid(row = 1, column = 2, sticky=Tk.N+Tk.S)
        self.CodeGenerationButton = Tk.Button(self.CompilationFrame, text = 'C++', command = self.GenerateCode, font = tkFont.Font(size = 15))
        self.CodeGenerationButton.grid(row = 0, column = 0)
        self.Premake4Button = Tk.Button(self.CompilationFrame, text = 'Premake4', command = self.GenerateBuild, font = tkFont.Font(size = 15))
        self.Premake4Button.grid(row = 0, column = 1)
        self.CompileButton = Tk.Button(self.CompilationFrame, text = 'Compile', command = self.GenerateBinary, font = tkFont.Font(size = 15))
        self.CompileButton.grid(row = 0, column = 2)

        self.ConsolePad = ScrolledText.ScrolledText(self.MainWindow, width=120, height=10, bg = 'black', fg = 'white')
        self.ConsolePad.grid(row = 2, column = 2, sticky=Tk.N+Tk.S)
        self.MAX_LOG_LINES = 50
        
        self.GUIUpdate('__init__')

        self.Log("Ready !")
        self.MainWindow.mainloop()

    def _on_closing(self):
        if MessageBox.askokcancel("Quit", "Do you really want to quit?"):
            self.MainWindow.quit()
            self.MainWindow.destroy()

    def UpdateAvailableTypes(self):
        self.AvailableTypes = dict(self.BaseTypes)
        for TypeName in self.Framework.UserDefinedTypes.keys():
            self.AvailableTypes[TypeName] = self.Framework.UserDefinedTypes[TypeName]

    def _onDisplayClick(self, event):
        if not self.Framework.Modules:
            return None
        Click = np.array([event.xdata, event.ydata])
        for Module in self.Framework.Modules:
            if (abs(self.DisplayedModulesPositions[Module['id']] - Click) < self.ModulesDiameter/2.).all():
                if type(Module) == framework_abstractor.LambdaModuleClass and Module['default']:
                    self.SelectedAvailableModulePosition = -Module['id'] - 1
                if not self.WaitingForRoute is None:
                     self.RouteModule(Module)
                self.GUIUpdate('_onDisplayClick', ActiveItemValue = Module)
                return None
        self.WaitingForRoute = None
        for LinkStr, LinkText in list(self.DisplayedLinks.items()):
            Contains, AddDict = LinkText.contains(event)
            if Contains:
                self.GUIUpdate('_onDisplayClick', ActiveItemValue = LinkStr)
                return None

        for nPosition, PositionAndParent in enumerate(self.AvailablesModulesPositions):
            if (abs(PositionAndParent[0] - Click) < self.ModulesDiameter/2.).all():
                if PositionAndParent[1:].count(None) == 0: # Only case where were have a parent AND a child, that are not actually that.
                    self.SelectedAvailableChameleonModulePosition = nPosition
                else:
                    self.SelectedAvailableModulePosition = nPosition
                self.GUIUpdate('_onDisplayClick', SetActiveItem = False)
                return None
        self.GUIUpdate('_onDisplayClick', ActiveItemValue = None)

    def GenerateEmptyFramework(self):
        if self.Framework.Modules:
            if not MessageBox.askokcancel("New", "Unsaved framework. Erase anyway ?"):
                return None
        with FileDialog.asksaveasfile(mode='w', initialdir = PROJECTS_DIR, defaultextension='.json', title = "New project", filetypes=[("JSON","*.json")]) as file:
            if file is None:
                return None
            self.Framework = framework_abstractor.FrameworkAbstraction(LogFunction = self.Log)
            self.Framework.Data['name'] = file.name.split('/')[-1].split('.json')[0]

            self.FrameworkFileName = file.name
            self.MainWindow.title('Beaver - {0}'.format(self.Framework.Data['name']))

            self.TempFiles = {}
            self.DisplayedParams = []
            self.DisplayedModulesPositions = {}

        self.GUIUpdate('GenerateEmptyFramework')

    def save_command(self):
        self.RegisterCurrentCodePad()
        if self.FrameworkFileName:
            with open(self.FrameworkFileName, "w") as f:
                if not f is None:
                    json.dump(self.Framework.ToDict(), f, protocol=json.HIGHEST_PROTOCOL)
                    self.Log("Saved.")
                else:
                    self.Error("Something went wrong while saving project.")
        else:
            self.saveas_command()

    def saveas_command(self):
        self.RegisterCurrentCodePad()
        with FileDialog.asksaveasfile(mode='w', initialdir = PROJECTS_DIR, initialfile = self.Framework.Data['name'], defaultextension='.json', title = "Save as...", filetypes=[("JSON","*.json")]) as f:
            if not f is None:
                NewName =  f.name.split('/')[-1].split('.json')[0]
                if not self.Framework.Data['name'] or (NewName != self.Framework.Data['name'] and MessageBox.askyesno("Name changed", "Do you want to change project name from \n{0} \nto {1} ?".format(self.Framework.Data['name'], NewName))):
                    self.Framework.Data['name'] = NewName
                    self.MainWindow.title('Beaver - {0}'.format(self.Framework.Data['name']))

                json.dump(self.Framework.ToDict(), f)
                self.FrameworkFileName = f.name
                self.Log("Saved.")
        
    def open_command(self):
        with FileDialog.askopenfile(parent=self.MainWindow,mode='r', initialdir = PROJECTS_DIR, title='Open...', defaultextension='.json', filetypes=[("JSON","*.json")]) as file:
            if file != None:
                Data = json.load(file)
                self.Framework = framework_abstractor.FrameworkAbstraction(Data, self.Log)
                self.FrameworkFileName = file.name
                self.MainWindow.title('Beaver - {0}'.format(self.Framework.Data['name']))

                self.TempFiles = {}
                self.DisplayedParams = []
                self.DisplayedModulesPositions = {}
                
        self.GUIUpdate('open_command')

    def RegisterCurrentCodePad(self, OriginFunction):
        if self.CurrentCodeFile in list(self.TempFiles.keys()):
            return None
        CurrentText = self.CodePad.get('1.0', Tk.END+'-1c')
        self.Framework.Files()[self.CurrentCodeFile]['data'] = CurrentText

    def AddModule(self, ModuleName):
        if self.AvailableModules[ModuleName]['origin'] == 'chameleon':
            self.AddChameleonModule(ModuleName)
            self.GUIUpdate('AddModule', ActiveItemValue = self.Framework.Modules[-1])
            return None

        ModuleNames = [Module['name'] for Module in self.Framework.Modules]
        AskedModuleName = ModuleName
        N = 0
        while AskedModuleName in ModuleNames:
            N += 1
            AskedModuleName = ModuleName + '_{0}'.format(N)

        self.Log("Adding " + AskedModuleName)
        self.Framework.AddModule(self.AvailableModules[ModuleName], AskedModuleName)
        NewModule = self.Framework.ReferenceModulesDictionnary['name'][AskedModuleName]

        if self.SelectedAvailableModulePosition < 0: # We replace here lambda function
            DefaultLambdaFunctionID = -self.SelectedAvailableModulePosition - 1
            ParentID = self.Framework.ReferenceModulesDictionnary['id'][DefaultLambdaFunctionID]['parent_ids'][0]
            self.AddLink(ParentID, NewModule['id'])
        else:
            ChildrenID = self.AvailablesModulesPositions[self.SelectedAvailableModulePosition][2]
            if not ChildrenID is None:
                self.AddLink(NewModule['id'], ChildrenID) # Even if ChildrenID is None, we add the link. In this case, it will be a link to a default lambda function

        self.GUIUpdate('AddModule', ActiveItemValue = NewModule)

    def AddChameleonModule(self, ModuleName, AddBGC = True): # As Chameleon modules are quite uniques, we add them apart
        ModuleNames = [Module['name'] for Module in self.Framework.Modules]
        AskedModuleName = ModuleName
        N = 0
        while AskedModuleName in ModuleNames:
            N += 1
            AskedModuleName = ModuleName + '_{0}'.format(N)

        self.Log("Adding " + AskedModuleName)
        Tile = self.AvailablesModulesPositions[self.SelectedAvailableChameleonModulePosition][1:]
        if Tile not in list(self.Framework.ChameleonTiles.keys()):
            self.Framework.ChameleonTiles[Tile] = []
        if self.AutoAddBGR and AddBGC and ModuleName != 'background_cleaner':
            FoundBGC = False
            for ModuleID in self.Framework.ChameleonTiles[Tile]:
                if self.Framework.ReferenceModulesDictionnary['id'][ModuleID]['module']['name'] == 'background_cleaner':
                    FoundBGC = True
                    break
            if not FoundBGC:
                self.AddChameleonModule('background_cleaner', AddBGC = False)
        NewModule = self.Framework.ReferenceModulesDictionnary['name'][AskedModuleName]
        self.Framework.ChameleonTiles[Tile] += [NewModule['id']]

        self.AddChameleonModuleDisplay(NewModule)

    def AddUtility(self, UtilityName):
        None

    def AddChameleonModuleDisplay(self, Module):
        print("Adding chameleon module display for ", Module)
        self.DisplayedModulesPositions[Module['id']] = self.AvailablesModulesPositions[self.SelectedAvailableChameleonModulePosition][0]

    def GetChameleonModulePosition(self, Tile, nModule):
        if not list(self.Framework.ChameleonTiles.values()):
            TilesSizes = 0
        else:
            TilesSizes = max([len(IDs) for IDs in list(self.Framework.ChameleonTiles.values())])
        return self.ChameleonInitialTilePosition + np.array([Tile[0] * (TilesSizes*self.ModulesDiameter + self.HModulesTilingDistance), - Tile[1] * self.VModulesTilingDistance/1.5]) + nModule * np.array([self.ModulesDiameter, 0])

    def RemoveModule(self, Item = None):
        if Item is None:
            Item = self.ActiveItem
        if Item is None:
            return None
        if type(Item) == framework_abstractor.ModuleClass:
            self.Log("Removing {0}".format(Item['name']))
            self.Framework.RemoveModule(Item)

        elif type(Item) == tuple:
            LinkStr = Item
            ParentID, ChildID = self.Framework.GetParentAndChildFromLinkStr(LinkStr)
            self.Log("Removed link from {0} to {1}".format(self.Framework.ReferenceModulesDictionnary['id'][ParentID]['name'], self.Framework.ReferenceModulesDictionnary['id'][ChildID]['name']))
            self.Framework.RemoveLink(ParentID, ChildID)

        self.GUIUpdate('RemoveModule')

    def RouteModule(self, SecondRoutedModule):
        if type(SecondRoutedModule) != framework_abstractor.ModuleClass:
            return None
        
        if self.WaitingForRoute is None:
            if SecondRoutedModule['origin'] == 'chameleon':
                self.Error('Chameleon modules cannot output events.')
                return None
            HandlersParamsIndexes = SecondRoutedModule.FindModuleHandlers()
            FreeSlot = False
            for HandlerIndex in HandlersParamsIndexes:
                if SecondRoutedModule['parameters'][HandlerIndex] == '@' + framework_abstractor.LAMBDA_FUNCTION_FROM.format(SecondRoutedModule['name'], SecondRoutedModule['module']['parameters'][HandlerIndex]['name']):
                    FreeSlot = True
                    break
            if not FreeSlot: # This work since, even for a chameleon module, needs a free slot that is actually a lambda function by default
                self.Error("Selected module cannot have any more outputs")
                return None
            self.WaitingForRoute = SecondRoutedModule['id'] # Will be the parent
            self.Log('Selected a child module to link to...')
            return None

        if not SecondRoutedModule.HasOperator():
            self.WaitingForRoute = None
            self.Error('Selected module cannot receive any input')
            return None
    
        if SecondRoutedModule['id'] == self.WaitingForRoute:
            self.WaitingForRoute = None
            self.Error('Cannot link a module to itself')
            return None

        NewParentsIDs = self.Framework.ReferenceModulesDictionnary['id'][self.WaitingForRoute]['parent_ids']
        while NewParentsIDs:
            OlderGen = []
            for ParentID in NewParentsIDs:
                for OlderParentID in self.Framework.ReferenceModulesDictionnary['id'][ParentID]['parent_ids']:
                    if OlderParentID not in OlderGen:
                        OlderGen += [OlderParentID]
                        if OlderParentID == SecondRoutedModule['id']:
                            self.Error('Cannot link create circular dependancies')
                            self.WaitingForRoute = None
                            return None
                NewParentsIDs = list(OlderGen)

        self.Log("Linking {0} to {1}".format(self.Framework.ReferenceModulesDictionnary['id'][self.WaitingForRoute]['name'], SecondRoutedModule['name']))
        self.AddLink(self.WaitingForRoute, SecondRoutedModule['id'])

        self.WaitingForRoute = None
        self.GUIUpdate('RouteModule')

    def GetDescendance(self, ElderID):
        AllDescendance = [ElderID]
        NewChilds = self.Framework.GetChildrenIDs(ElderID)
        while NewChilds:
            NextGenChilds = []
            for ID in NewChilds:
                for NewChildID in self.Framework.GetChildrenIDs(ID):
                    if NewChildID not in NextGenChilds:
                        NextGenChilds += [NewChildID]
            AllDescendance += NextGenChilds
            NewChilds = list(NextGenChilds)
        return AllDescendance

    def AddLink(self, ParentID, ChildrenID):
        self.Framework.AddLink(ParentID, ChildrenID)

    def AddType(self, Type):
        if Type == 'Event type':
            self.Framework.AddNewType()
            self.ActiveItem = framework_abstractor.TYPES_DEF_FILE
            self.Update(Mod = 0)

    def _OnRemoveType(self, TypeName):
        self.Framework.RemoveType(TypeName)
        self.Framework.WriteTypesFile()

        self.GUIUpdate('_OnRemoveType')

    def GenerateCode(self):
        if not self.Framework.Data['name'] or not self.FrameworkFileName:
            self.saveas_command()
        self.Framework.GenerateCode()

    def GenerateBuild(self):
        if not self.FrameworkFileName:
            self.saveas_command()
            if not self.FrameworkFileName:
                return None
        LuaFilename = self.Framework.GenerateBuild()

    def GenerateBinary(self):
        None

    def DisplayModuleCode(self):
        for Key, Value in self.ActiveItem.items():
            print(Key, Value)
        if not self.ActiveItem is None and type(self.ActiveItem) == framework_abstractor.ModuleClass:
            Module = self.ActiveItem
            if Module['origin'] == 'tarsier':
                self.TempFiles[Module['module']['name'] + '.hpp'] = '\n'.join(tarsier_scrapper.GetTarsierCode(Module['module']['name'] + '.hpp', Full = True))
            elif Module['origin'] == 'sepia':
                SepiaCode = sepia_scrapper.GetSepiaCode(Full = True)
                ModuleStartLine = sepia_scrapper.FindTemplateFunctions(SepiaCode, Module['module']['name'])
                while sepia_scrapper.TEMPLATE_LINE_INDICATOR not in SepiaCode[ModuleStartLine] and ModuleStartLine > 0:
                    ModuleStartLine -= 1
                if ModuleStartLine > 0 and sepia_scrapper.COMMENT_INDICATOR in SepiaCode[ModuleStartLine-1]:
                    ModuleStartLine -= 1
                Lines = ["Starting at line {0}".format(ModuleStartLine + 1), ""]
                nOpen = 0
                nClose = 0
                while nOpen == 0 or nOpen > nClose:
                    CurrentLine = SepiaCode[ModuleStartLine]
                    Lines += [CurrentLine]
                    CurrentLine = CurrentLine.split(sepia_scrapper.COMMENT_INDICATOR)[-1]
                    nOpen += CurrentLine.count('{')
                    nClose += CurrentLine.count('}')
                    ModuleStartLine += 1
                self.TempFiles[Module['module']['name'] + '.hpp'] = '\n'.join(Lines)
            else:
                return None
            self.GUIUpdate('DisplayModuleCode', TmpFile = Module['module']['name'] + '.hpp')

    def UpdateCodeMenu(self, OriginFunction):
        Menu = self.CodeFileMenu['menu']
        Menu.delete(0, "end") 
        for FileName in self.Framework.Files().keys():
            Menu.add_command(label = FileName, command = partial(self._OnCodefileSelection, FileName))

    def _OnCodefileSelection(self, Filename):
        self.GUIUpdate('_OnCodefileSelection', ActiveItemValue = Filename)

    def UpdateDisplayedFile(self, OriginFunction, TmpFile = None):
        self.CodePad.delete('1.0', Tk.END)
        if not TmpFile is None:
            self.CodePad.insert(Tk.END, self.TempFiles[TmpFile])
        else:
            self.CodePad.insert(Tk.END, self.Framework.Files()[self.CurrentCodeFile]['data'])

    def _onCodeModification(self):
        None

    def Log(self, string):
        self.ConsolePad.config(state=Tk.NORMAL)
        if string[-1] != '\n':
            string = string+'\n'
        self.ConsolePad.insert(Tk.END, string)
        CurrentText = self.ConsolePad.get('1.0', Tk.END+'-1c')
        if CurrentText.count('\n') > self.MAX_LOG_LINES:
            CurrentText = '\n'.join(CurrentText.split('\n')[-self.MAX_LOG_LINES:])
            self.ConsolePad.delete('1.0', Tk.END)
            self.ConsolePad.insert(Tk.END, CurrentText)
        self.ConsolePad.see('end')
        self.ConsolePad.config(state=Tk.DISABLED)

    def Warning(self, string):
        self.Log("WARNING : "+string)
    def Error(self, string):
        self.Log("Error : "+string)

    def RegenerateChameleonAvailableSlots(self):
        self.SelectedAvailableChameleonModulePosition = len(self.AvailablesModulesPositions)
        AddedTiles = []
        if not list(self.Framework.ChameleonTiles.keys()):
            AddedTiles += [(0,0)]
        for Tile, IDs in list(self.Framework.ChameleonTiles.items()):
            for nModule, ModuleID in enumerate(IDs):
                self.DisplayedModulesPositions[ModuleID] = self.GetChameleonModulePosition(Tile, nModule)
            self.AvailablesModulesPositions += [(self.GetChameleonModulePosition(Tile, nModule+1), Tile[0], Tile[1])]

            NextTiles = [(Tile[0], Tile[1] + 1), (Tile[0] + 1, Tile[1]), (Tile[0] + 1, Tile[1] + 1)]
            for NextTile in NextTiles:
                if NextTile not in list(self.Framework.ChameleonTiles.keys()) and NextTile not in AddedTiles:
                    AddedTiles += [NextTile]

        for Tile in AddedTiles:
            self.AvailablesModulesPositions += [(self.GetChameleonModulePosition(Tile, 0), Tile[0], Tile[1])]
    
    def ExtractArboresence(self):
        self.Arboresence = {}
        self.CitedModules = []
        self.OriginModules = []

        for Module in self.Framework.Modules:
            if Module['origin'] == 'chameleon':
                continue
            if not Module.HasOperator():
                self.OriginModules += [Module['id']]
            if Module['id'] not in self.Arboresence.keys():
                self.Arboresence[Module['id']] = {'children':[], 'parents': []}
                if Module.HasOperator():
                    self.Arboresence[Module['id']]['parents'] += [-1]
            HandlersParamsIndexes = Module.FindModuleHandlers()
            for HandlerIndex in HandlersParamsIndexes:
                HandlerName = Module['module']['parameters'][HandlerIndex]['name']
                HandlerParamFuncName = framework_abstractor.LAMBDA_FUNCTION_FROM.format(Module['name'], HandlerName)
                ChildrenName = Module['parameters'][HandlerIndex].split('@')[-1]
                ChildrenModule = self.Framework.ReferenceModulesDictionnary['name'][ChildrenName]
                self.Arboresence[Module['id']]['children'] += [ChildrenModule['id']]
                if ChildrenModule['id'] not in self.Arboresence.keys():
                    self.Arboresence[ChildrenModule['id']] = {'children':[], 'parents': []}
                    if ChildrenModule.HasOperator():
                        self.Arboresence[ChildrenModule['id']]['parents'] += [-1]
                self.Arboresence[ChildrenModule['id']]['parents'] += [Module['id']]
                if ChildrenModule['id'] not in self.CitedModules:
                    self.CitedModules += [ChildrenModule['id']]
        print("Arbo : ", self.Arboresence)

    def UpdateDisplayPositions(self, OriginFunction):
        self.ExtractArboresence()
        
        self.DisplayedModulesPositions = {}
        self.AvailablesModulesPositions = []

        if not [Module['id'] for Module in self.Framework.Modules if Module['origin'] != 'chameleon']:
            self.AvailablesModulesPositions += [(np.array([0., 0.]), None, None)]
            self.ChameleonInitialTilePosition = np.array([0., -self.VModulesTilingDistance])
            self.SelectedAvailableModulePosition = 0
            self.SelectedAvailableChameleonModulePosition = len(self.AvailablesModulesPositions)
            self.RegenerateChameleonAvailableSlots()
            return None

        AskedHeights = {}
        for ModuleID in self.OriginModules:
            AskedHeights[ModuleID] = 0
        if not self.OriginModules:
            for ModuleID in self.Arboresence.keys():
                if ModuleID in self.CitedModules:
                    continue
                AskedHeights[ModuleID] = 0
        
        nLoops = {key:0 for key in list(self.Arboresence.keys())}
        while not len(AskedHeights.keys()) == len(self.Arboresence.keys()):
            for ModuleID in self.Arboresence.keys():
                if ModuleID in AskedHeights.keys():
                    continue
                nLoops[ModuleID] += 1
                ParentMissing = False
                for ParentID in self.Arboresence[ModuleID]['parents']:
                    if ParentID == -1:
                        continue
                    LowestHeight = 0.
                    if ParentID in AskedHeights.keys():
                        LowestHeight = AskedHeights[ParentID] - self.VModulesTilingDistance
                    else:
                        ParentMissing = True
                        break
                if (self.Arboresence[ModuleID]['parents'].count(-1) == len(self.Arboresence[ModuleID]['parents']) or ParentMissing):
                    if nLoops[ModuleID] < 100:
                        continue
                    else:
                        if not self.Arboresence[ModuleID]['children']:
                            LowestHeight = max(list(AskedHeights.values()))
                        else:
                            LowestHeight = min(list(AskedHeights.values()))
                            for ChildrenID in self.Arboresence[ModuleID]['children']:
                                if ChildrenID in AskedHeights.keys():
                                    LowestHeight = max(LowestHeight, AskedHeights[ChildrenID] + self.VModulesTilingDistance)
                AskedHeights[ModuleID] = LowestHeight

        Heights = list(AskedHeights.values())
        Heights += [min(Heights) - self.VModulesTilingDistance, max(Heights) + self.VModulesTilingDistance]
        SortedIndexes = np.argsort(Heights)
        print(SortedIndexes)

        self.ChameleonInitialTilePosition = np.array([0., min(Heights) - self.VModulesTilingDistance])
        
        for LocalIndex in reversed(SortedIndexes):
            HeightConsidered = Heights[LocalIndex]
            print(LocalIndex, " at ", HeightConsidered)
            Items = []
            for ModuleID in self.Arboresence.keys():
                if abs(AskedHeights[ModuleID] - HeightConsidered) < self.VModulesTilingDistance/2:
                    Items += [ModuleID]
                if -1 in self.Arboresence[ModuleID]['parents'] and abs(AskedHeights[ModuleID] + self.VModulesTilingDistance - HeightConsidered) < self.VModulesTilingDistance/2:
                    Items += [(np.array([0., AskedHeights[ModuleID] + self.VModulesTilingDistance]), None, ModuleID)]
                #if -1 in self.Arboresence[ModuleID]['children'] and abs(AskedHeights[ModuleID] - self.VModulesTilingDistance - HeightConsidered) < self.VModulesTilingDistance/2:
                #    for i in range(self.Arboresence[ModuleID]['children'].count(-1)):
                #        Items += [(np.array([0., AskedHeights[ModuleID] - self.VModulesTilingDistance]), ModuleID, None)]

            print("Items : ", Items)
            for nItem, Item in enumerate(Items):
                X = self.HModulesTilingDistance * (-len(Items) / 2. + nItem + 0.5)
                if type(Item) == int:
                    if Item in self.DisplayedModulesPositions.keys():
                        continue
                    self.DisplayedModulesPositions[Item] = np.array([X, AskedHeights[Item]])
                else:
                    Add = True
                    for AddedAvlbPos in self.AvailablesModulesPositions:
                        if Item[1:] == AddedAvlbPos[1:]:
                            Add = False
                            break
                    if Add:
                        Item[0][0] = X
                        self.AvailablesModulesPositions += [Item]

                    self.ChameleonInitialTilePosition[0] = min(self.ChameleonInitialTilePosition[0], X)

        for Module in self.Framework.Modules:
            if type(Module) == framework_abstractor.LambdaModuleClass and Module['default']:
                self.SelectedAvailableModulePosition = -Module['id']-1
                break
        else:
            self.SelectedAvailableModulePosition = len(self.AvailablesModulesPositions)-1
        self.RegenerateChameleonAvailableSlots()

#    def UpdateOld(self, Regenerate = False, Mod = None):
#        if type(self.ActiveItem) == framework_abstractor.ModuleClass:
#            self.UpdateDisplayedCodefile(self.ActiveItem.FileName(), SaveCurrentFile = False)
#        elif type(self.ActiveItem) == framework_abstractor.LambdaModuleClass:
#            pass
#        elif self.ActiveItem == framework_abstractor.TYPES_DEF_FILE:
#            self.UpdateDisplayedCodefile(framework_abstractor.TYPES_DEF_FILE, SaveCurrentFile = False)
#        elif self.ActiveItem is None:
#            self.UpdateDisplayedCodefile(self.DefaultFile, SaveCurrentFile = False)
#        if Regenerate:
#            self.UpdateDisplayPositions()
#        self.UpdateDrawing()
#        self.ChangeDisplayedParams(Mod)

    def GUIUpdate(self, OriginFunction, **kwargs):
        UpdateOriginFunctions = ['__init__', '_onDisplayClick', '_OnCodefileSelection', 'GenerateEmptyFramework', 'open_command', 'AddModule', 'AddUtility', 'RemoveModule', 'RouteModule', '_OnRemoveType', 'GenerateCode', 'GenerateBuild', 'GenerateBinary', 'DisplayModuleCode', '_OnAddedParameterChange', '_OnFrameworkNameChange', '_OnEventTypeTemplateChange', '_OnNewEventTypeTemplate', '_OnAddGlobalVariable', '_OnRemoveGlobalVariable', '_OnGlobalVariableChange', '_OnDefinedEventTypeFieldChange', '_OnDefinedEventTypeFieldAddRemove']
        if not callable(getattr(self, OriginFunction)):
            print("Ill defined call to GUI Update. Function not specified")
            return None
        if OriginFunction not in UpdateOriginFunctions:
            print("Not implemented GUI update from function {0}".format(OriginFunction))
            return None

        FunctionsOrder = [self.RegisterCurrentCodePad, self.UpdateFocus, self.UpdateDisplayPositions, self.UpdateDrawing, self.UpdateCodeMenu, self.UpdateDisplayedFile, self.UpdateDisplayedParams]

        FunctionsLinks = {}
        FunctionsLinks[self.UpdateFocus] =                                              ['__init__', '_onDisplayClick', '_OnCodefileSelection', 'GenerateEmptyFramework', 'open_command', 'AddModule', 'RemoveModule', 'AddType', '_OnRemoveType', 'GenerateCode', 'GenerateBuild', 'GenerateBinary', '_OnNewEventTypeTemplate']

        FunctionsLinks[self.UpdateDisplayPositions] =                                   ['__init__', 'GenerateEmptyFramework', 'open_command', 'AddModule', 'RemoveModule', 'RouteModule']
        FunctionsLinks[self.UpdateDrawing] =             FunctionsLinks[self.UpdateDisplayPositions] +  ['_onDisplayClick', '_OnCodefileSelection', '_OnRemoveType', '_OnAddedParameterChange', '_OnEventTypeTemplateChange', '_OnNewEventTypeTemplate', '_OnDefinedEventTypeFieldChange']

        FunctionsLinks[self.RegisterCurrentCodePad] =                                   [] #TODO
        FunctionsLinks[self.UpdateCodeMenu] =                                           ['__init__', '_onDisplayClick', '_OnCodefileSelection', 'GenerateEmptyFramework', 'open_command', 'AddModule', 'RemoveModule', 'AddType', '_OnRemoveType', 'GenerateCode', 'GenerateBuild', 'GenerateBinary', 'DisplayModuleCode', '_OnNewEventTypeTemplate']
        FunctionsLinks[self.UpdateDisplayedFile] =      FunctionsLinks[self.UpdateCodeMenu] +       ['_OnAddedParameterChange', '_OnFrameworkNameChange', '_OnEventTypeTemplateChange', '_OnAddGlobalVariable', '_OnRemoveGlobalVariable', '_OnGlobalVariableChange', '_OnDefinedEventTypeFieldChange', '_OnDefinedEventTypeFieldAddRemove']

        FunctionsLinks[self.UpdateDisplayedParams] =                                    ['__init__', '_onDisplayClick', '_OnCodefileSelection', 'GenerateEmptyFramework', 'open_command', 'AddModule', 'RemoveModule', '_OnRemoveType', '_OnNewEventTypeTemplate', '_OnAddGlobalVariable', '_OnRemoveGlobalVariable', '_OnDefinedEventTypeFieldAddRemove']

        for Function in FunctionsOrder:
            if OriginFunction in FunctionsLinks[Function]:
                args, _, _ = inspect.getargs(Function.__code__)
                CallDict = {key: value for key, value in kwargs.items() if key in args}
                Function(OriginFunction, **CallDict)

    def UpdateFocus(self, OriginFunction, SetActiveItem = True, ActiveItemValue = None): # Master switch to change focus of the GUI.
        if not SetActiveItem:
            return None
        if OriginFunction in ['__init__', 'GenerateEmptyFramework', 'open_command', 'RemoveModule']:
            self.ActiveItem = None
            self.CurrentCodeFile = framework_abstractor.GENERAL_FILENAME
        elif OriginFunction in ['_onDisplayClick', 'AddModule']:
            self.ActiveItem = ActiveItemValue
            if self.ActiveItem is None:
                self.CurrentCodeFile = framework_abstractor.GENERAL_FILENAME
            else:
                self.CurrentCodeFile = self.ActiveItem.FileName()
        elif OriginFunction == '_OnCodefileSelection':
            self.CurrentCodeFile = ActiveItemValue    
            if self.CurrentCodeFile == framework_abstractor.TYPES_DEF_FILE or self.CurrentCodeFile == framework_abstractor.GENERAL_FILENAME:
                self.ActiveItem = None
            else:
                self.ActiveItem= self.Framework.ReferenceModulesDictionnary['name'][self.CurrentCodeFile.split(framework_abstractor.HANDLERS_FILE_NAME_SUFFIX)[0]]
        elif OriginFunction in ['AddType', '_OnNewEventTypeTemplate']:
            self.ActiveItem = None
            self.CurrentCodeFile == framework_abstractor.TYPES_DEF_FILE
        elif OriginFunction == '_OnRemoveType':
            if not self.Framework.UserDefinedTypes:
                self.ActiveItem = None
                self.CurrentCodeFile = framework_abstractor.GENERAL_FILENAME
        else:
            print("Non implemented UpdateFocus caller {0}".format(OriginFunction))
        self.CodeFileVar.set(self.CurrentCodeFile)

    def UpdateDrawing(self, OriginFunction):
        print(self.ActiveItem)
        minValues = np.array([0., 0.])
        maxValues = np.array([0., 0.])

        self.DisplayAx.clear()
        self.DisplayedLinks = {} 
        for Module in self.Framework.Modules:
            alpha = 1.
            if not self.WaitingForRoute is None and self.WaitingForRoute == Module['id']:
                Color = 'k'
            else:
                if type(Module) == framework_abstractor.LambdaModuleClass and Module['default']:
                    Color = 'grey'
                    Style = '--'
                    if Module['id'] == -self.SelectedAvailableModulePosition - 1:
                        alpha = 1.
                    else:
                        alpha = 0.4
                else:
                    if self.Framework.WellDefinedModule(Module):
                        Color = 'g'
                    else:
                        Color = 'r'
            if not self.ActiveItem is None and (type(self.ActiveItem) == framework_abstractor.ModuleClass or type(self.ActiveItem) == framework_abstractor.LambdaModuleClass) and Module['id'] == self.ActiveItem['id']:
                Style = '-'
                alpha = 1.
            else:
                Style = '--'
            self.DrawModule(Module, Style, Color, alpha)
            minValues = np.minimum(minValues, self.DisplayedModulesPositions[Module['id']] - 1.5*self.ModulesDiameter)
            maxValues = np.maximum(maxValues, self.DisplayedModulesPositions[Module['id']] + 1.5*self.ModulesDiameter)

            self.DrawLinksToChildrens(Module, Color)

        for nSlot, AvailableSlotAndParent in enumerate(self.AvailablesModulesPositions):
            Color = 'grey'
            Style = '--'
            if nSlot == self.SelectedAvailableModulePosition or nSlot == self.SelectedAvailableChameleonModulePosition:
                alpha = 1.
            else:
                alpha = 0.4
            self.DrawModule({'nSlot':nSlot, 'id': None}, Style, Color, alpha)
            minValues = np.minimum(minValues, AvailableSlotAndParent[0] - self.ModulesDiameter)
            maxValues = np.maximum(maxValues, AvailableSlotAndParent[0] + self.ModulesDiameter)
        self.DrawAvailableParentsLinks()

        Center = (minValues + maxValues)/2.
        MaxAxis = (maxValues - minValues).max()
        minValues = Center - MaxAxis/2.
        maxValues = Center + MaxAxis/2.
        self.DisplayAx.set_xlim(minValues[0], maxValues[0])
        self.DisplayAx.set_ylim(minValues[1], maxValues[1])
        self.Display.canvas.show()
        #self.Log("Done.")
        
    def DrawModule(self, Module, Style, Color, alpha = 1.):
        if 'nSlot' in list(Module.keys()):
            ModulePosition = self.AvailablesModulesPositions[Module['nSlot']][0]
            ModuleName = ''
            ModuleEvFields = []
            ModuleOutputFields = []
        elif type(Module) == framework_abstractor.ModuleClass:
            ModulePosition = self.DisplayedModulesPositions[Module['id']]
            ModuleName = Module['name']
            ModuleEvFields = Module['module']['ev_fields']
            ModuleOutputFields = Module['ev_outputs']
        elif type(Module) == framework_abstractor.LambdaModuleClass:
            ModulePosition = self.DisplayedModulesPositions[Module['id']]
            ModuleName = Module['name']
            ModuleEvFields = []
            ModuleOutputFields = []

        DXs = (self.ModulesDiameter/2 * np.array([np.array([-1, -1]), np.array([-1, 1]), np.array([1, 1]), np.array([1, -1])])).tolist()
        for nDX in range(len(DXs)):
            self.DisplayAx.plot([(ModulePosition + DXs[nDX])[0], (ModulePosition + DXs[(nDX+1)%4])[0]], [(ModulePosition + DXs[nDX])[1], (ModulePosition + DXs[(nDX+1)%4])[1]], ls = Style, color = Color, alpha = alpha)
        NameTextPosition = ModulePosition + self.ModulesDiameter/2 * 0.8 * np.array([-1, -1])
        self.DisplayAx.text(NameTextPosition[0], NameTextPosition[1], s = ModuleName, color = Color, alpha = alpha, fontsize = 8)
        if not self.ActiveItem is None and type(self.ActiveItem) == framework_abstractor.ModuleClass and Module['id'] == self.ActiveItem['id'] and len(ModuleEvFields) > 1:
            if ModulePosition[0] < 0:
                HAlign = 'right'
                FieldsTextPosition = ModulePosition + self.ModulesDiameter/2 * 1.2 * np.array([-1., 0])
            else:
                HAlign = 'left'
                FieldsTextPosition = ModulePosition + self.ModulesDiameter/2 * 1.2 * np.array([1., 0])
            ModuleFieldsString = 'Required fields for {0}:\n'.format(ModuleEvFields[0]) + ', '.join(ModuleEvFields[1:])
            if self.Options['display_module_ev_outputs']:
                if list(ModuleOutputFields.keys()):
                    ModuleFieldsString = ModuleFieldsString + '\nOutputs :'
                    for handle, Fields in list(ModuleOutputFields.items()):
                        ModuleFieldsString = ModuleFieldsString + '\n* ' + handle 
                        for Field in Fields:
                            ModuleFieldsString += '\n  -> {0} {1}'.format(Field['type'], Field['name'])
            self.DisplayAx.text(FieldsTextPosition[0], FieldsTextPosition[1], s = ModuleFieldsString, bbox={'facecolor': Color, 'alpha': 1, 'pad': 2}, horizontalalignment=HAlign, verticalalignment='center', zorder=10, fontsize = 8)
    
    def DrawAvailableParentsLinks(self):
        Color = 'grey'
        Style = ':'
        for nAvailablePos, AvailablePos in enumerate(self.AvailablesModulesPositions):
            if AvailablePos[2] is None:
                continue
            if not AvailablePos[1] is None:
                continue
            if nAvailablePos == self.SelectedAvailableModulePosition:
                alpha = 1.
            else:
                alpha = 0.4
            ChildrenModule = self.Framework.ReferenceModulesDictionnary['id'][AvailablePos[2]]
            Start = AvailablePos[0] + np.array([0., -1.]) * self.ModulesDiameter/2
            End = self.DisplayedModulesPositions[AvailablePos[2]] + np.array([-1., 1.]) * self.ModulesDiameter/2 + np.array([1., 0.]) * self.ModulesDiameter * (len(ChildrenModule['parent_ids'])+1.)/(len(ChildrenModule['parent_ids'])+2.)
            YStep = (Start + End)/2
            self.DisplayAx.plot([Start[0], Start[0]], [Start[1], YStep[1]], ls = Style, color = Color, alpha = alpha)
            self.DisplayAx.plot([Start[0], End[0]], [YStep[1], YStep[1]], ls = Style, color = Color, alpha = alpha)
            self.DisplayAx.plot([End[0], End[0]], [YStep[1], End[1]], ls = Style, color = Color, alpha = alpha)

    def DrawLinksToChildrens(self, Module, ModuleColor):
        if type(Module) == framework_abstractor.LambdaModuleClass:
            return None
        HandlersParamsIndexes = Module.FindModuleHandlers()
        Links = []
        nUnused = 0
        for HandlerIndex in HandlersParamsIndexes:
            ChildrenName = Module['parameters'][HandlerIndex].split('@')[1]
            ChildrenModule = self.Framework.ReferenceModulesDictionnary['name'][ChildrenName]
            Links += [(Module['id'], ChildrenModule['id'], 1.-(ChildrenModule['parent_ids'].index(Module['id'])+1.+ChildrenModule.HasOperator())/(len(ChildrenModule['parent_ids'])+1.+ChildrenModule.HasOperator()), Module.returned_event_type[Module.module['parameters'][HandlerIndex]['name']]['name'])]

        for nLink, Link in enumerate(Links):
            ChildrenModule = self.Framework.ReferenceModulesDictionnary['id'][Link[1]]
            if ChildrenModule['origin'] == framework_abstractor.USER_DEFINED and ChildrenModule['default']:
                Color = 'grey'
            else:
                Color = ModuleColor
            LinkStr = framework_abstractor.GetLinkStr(Link[0], Link[1])
            if not self.ActiveItem is None and type(self.ActiveItem) == str and self.ActiveItem == LinkStr:
                Style = '-'
            else:
                Style = ':'
            if (self.SelectedAvailableModulePosition < 0 and -self.SelectedAvailableModulePosition - 1 == Link[1]):
                alpha = 1.
            else:
                alpha = 0.4
            Start = self.DisplayedModulesPositions[Link[0]] + np.array([-1., -1.]) * self.ModulesDiameter/2 +np.array([1., 0.]) * self.ModulesDiameter * (1. + nLink) / (1. + len(Links))
            End = self.DisplayedModulesPositions[Link[1]] + np.array([-1., 1.]) * self.ModulesDiameter/2 + np.array([1., 0.]) * self.ModulesDiameter * Link[2]
            YStep = (Start + End)/2
            self.DisplayAx.plot([Start[0], Start[0]], [Start[1], YStep[1]], ls = Style, color = Color, alpha = alpha)
            self.DisplayAx.plot([Start[0], End[0]], [YStep[1], YStep[1]], ls = Style, color = Color, alpha = alpha)
            self.DisplayAx.plot([End[0], End[0]], [YStep[1], End[1]], ls = Style, color = Color, alpha = alpha)

            LinkStr = framework_abstractor.GetLinkStr(Link[0], Link[1])
            self.DisplayedLinks[LinkStr] = self.DisplayAx.text(YStep[0], YStep[1], s = Link[3], zorder = 5, bbox={'facecolor': 'white', 'alpha': 1, 'pad': 2, 'ls': Style}, horizontalalignment='center', verticalalignment='center')

    def _OnParameterChange(self, StringVar, ParamIndex, DisplayIndex):
        print("Parameter : {0}, {1}".format(ParamIndex, DisplayIndex))
        self.ActiveItem['parameters'][ParamIndex] = StringVar.get()
        self.DisplayedParams[DisplayIndex][0]['foreground'] = self.GetParamDisplayColor(ParamIndex)

    def _OnAddedParameterChange(self, StringVar, ParamIndex, DisplayIndex):
        if type(self.ActiveItem) == framework_abstractor.ModuleClass:
            AddedParamName = self._GetModuleAddedParams()[ParamIndex]['name']
        elif type(self.ActiveItem) == str:
            AddedParamName = self._GetLinkAddedParams()[ParamIndex]['name']
        # First check if name is ok and available
        if AddedParamName == 'Name':
            AskedName = StringVar.get()
            CursorIndex = self.DisplayedParams[DisplayIndex][-1].index(Tk.INSERT)
            if not self._AddedParamValidity(AddedParamName, AskedName):
                self.DisplayedParams[DisplayIndex][0]['foreground'] = 'red'
                if not self.ActiveItem is None:
                    return None
            else:
                self.DisplayedParams[DisplayIndex][0]['foreground'] = 'black'

            if type(self.ActiveItem) == framework_abstractor.ModuleClass:
                self.Framework.ChangeModuleName(self.ActiveItem, AskedName)

                self.GUIUpdate('_OnAddedParameterChange')
                #self.DisplayedParams[DisplayIndex][-1].focus_set()
                #self.DisplayedParams[DisplayIndex][-1].icursor(CursorIndex)

    def _OnFrameworkNameChange(self, StrVar):
        AskedName = StrVar.get()
        self.Framework.Data['name'] = AskedName
        if not AskedName:
            AskedName = framework_abstractor.DEFAULT_NAME
        self.MainWindow.title('Beaver - {0}'.format(AskedName))
        self.GUIUpdate('_OnFrameworkNameChange')

    def _OnTemplateChange(self, StringVar, TemplateIndex, DisplayIndex):
        print("Template : {0}, {1}".format(TemplateIndex, DisplayIndex))
        self.ActiveItem['templates'][TemplateIndex] = StringVar.get()
        self.DisplayedParams[DisplayIndex][0]['foreground'] = self.GetTemplateDisplayColor(TemplateIndex)

    def _OnEventTypeTemplateChange(self, StrVar, TemplateIndex, DisplayIndex, TypeName):
        print("Inserting type" + TypeName)
        StrVar.set(TypeName)
        if TypeName == framework_abstractor.NoneEventType['name']:
            self.DisplayedParams[DisplayIndex][0]['foreground'] = 'red'
        else:
            self.DisplayedParams[DisplayIndex][0]['foreground'] = 'green'

        self.ActiveItem.SetEventTemplate(self.AvailableTypes[TypeName])
        self.GUIUpdate('_OnEventTypeTemplateChange')

    def _OnNewEventTypeTemplate(self, StringVar, TemplateIndex, DisplayIndex):
        self.Framework.AddNewType()
        self.GUIUpdate('_OnNewEventTypeTemplate')

    def _OnAddGlobalVariable(self):
        self.Framework.AddGlobalVariable()
        self.Framework.UpdateVariablesFile()
        self.GUIUpdate('_OnAddGlobalVariable')

    def _OnRemoveGlobalVariable(self, VarName):
        for nVariable, Variable in enumerate(self.Framework.GlobalVariables):
            if Variable['name'] == VarName:
                break
        self.Framework.GlobalVariables.pop(nVariable)
        self.Framework.UpdateVariablesFile()
        self.GUIUpdate('_OnRemoveGlobalVariable')

    def _OnGlobalVariableChange(self, StrVar, nVar, ModValue, DisplayNumber):
        StrValue = StrVar.get()
        print(StrValue)
        self.Framework.GlobalVariables[nVar][ModValue] = StrValue
        self.Framework.UpdateVariablesFile()
        self.GUIUpdate('_OnGlobalVariableChange')

    def _AddedParamValidity(self, AddedParamName, AddedParamValue):
        if AddedParamName == 'Name':
            if AddedParamValue == '':
                return False
            if type(self.ActiveItem) == framework_abstractor.ModuleClass:
                return self.Framework.ModuleNameValidity(self.ActiveItem, AddedParamValue)

    def _GetModuleAddedParams(self):
        return [{'name': 'Name', 'type': 'str', 'default': self.ActiveItem['name']}]

    def _GetLinkAddedParams(self):
        return []

    def UpdateDisplayedParams(self, OriginFunction, Mod = None):
        for Line in self.DisplayedParams:
            for Field in Line:
                Field.destroy()
        if self.ActiveItem is None:
            return self.DisplayGlobalVariables(Mod)
            
        elif type(self.ActiveItem) == framework_abstractor.ModuleClass:
            AddedParams = self._GetModuleAddedParams()
            ModuleParameters = self.ActiveItem['module']['parameters']
            ModuleTemplates = self.ActiveItem['module']['templates']
        elif type(self.ActiveItem) == tuple:
            AddedParams = self._GetLinkAddedParams()
            ModuleParameters = []
            ModuleTemplates = []

        elif self.ActiveItem.__class__ == framework_abstractor.LambdaModuleClass:
            AddedParams = self._GetModuleAddedParams()
            ModuleParameters = []
            ModuleTemplates = []

        elif type(self.ActiveItem) == str:
            if self.ActiveItem == framework_abstractor.TYPES_DEF_FILE:
                return self.DisplayTypesParameters(Mod)
            else:
                return self.DisplayGlobalVariables(Mod)

        else:
            print("Not implemented ActiveItem type")
            return None

        ItemsFields = []
        if AddedParams or ModuleParameters:
            ItemsFields += [{'name':'Parameter', 'type': 'Type', 'value': 'Value'}]
        ItemsFields += AddedParams
        ItemsFields += ModuleParameters
        if ModuleTemplates:
            ItemsFields += [{'name':'Template', 'type': 'Type', 'value': 'Value'}]
        ItemsFields += ModuleTemplates

        if Mod == 0:
            self.CurrentMinParamDisplayed = 0
        elif not Mod is None:
            self.CurrentMinParamDisplayed = max(0, min(len(ItemsFields) - self.NFieldsDisplayed, self.CurrentMinParamDisplayed + Mod))
        self.DisplayedParams = []
        self.CurrentParams = {}

        if self.CurrentMinParamDisplayed != 0:
            FirstLine = '...'
        else:
            FirstLine = ''
        self.DisplayedParams += [[Tk.Label(self.ParamsValuesFrame, text = FirstLine, width = 20, anchor = Tk.W)]]
        self.DisplayedParams[-1][0].grid(row=len(self.DisplayedParams)-1, column = 0)

        for NField in range(self.CurrentMinParamDisplayed, min(len(ItemsFields), self.CurrentMinParamDisplayed + self.NFieldsDisplayed)):
            EntryEnabled = True
            Field = ItemsFields[NField]
            self.DisplayedParams += [[]]
            if Field in AddedParams:
                nField = AddedParams.index(Field)
                Color = self.GetAddedParamDisplayColor(Field['name'], Field['default'])
                StrVar = Tk.StringVar(self.MainWindow)
                CBFunction = self._OnAddedParameterChange
                if 'default' in Field.keys():
                    StrVar.set(Field['default'])
                if type(self.ActiveItem) == framework_abstractor.LambdaModuleClass:
                    EntryEnabled = False

            elif Field in ModuleParameters:
                nField = ModuleParameters.index(Field)
                Color = self.GetParamDisplayColor(ModuleParameters.index(Field))
                StrVar = Tk.StringVar(self.MainWindow)
                CBFunction = self._OnParameterChange
                if self.ActiveItem['parameters'][Field['param_number']]:
                    StrVar.set(self.ActiveItem['parameters'][Field['param_number']])
                else:
                    if 'default' in list(Field.keys()):
                        StrVar.set(Field['default'])

            elif Field in ModuleTemplates:
                nField = ModuleTemplates.index(Field)
                Color = self.GetTemplateDisplayColor(ModuleTemplates.index(Field))
                StrVar = Tk.StringVar(self.MainWindow)
                if Field['name'] in self.MenuParams.keys(): # Case for specific parameter
                    ParamDict = self.MenuParams[Field['name']][0]
                    CBFunction = self.MenuParams[Field['name']][1]
                    AddNewFunction = self.MenuParams[Field['name']][2]
                    if self.ActiveItem['templates'][Field['template_number']]:
                        StrVar.set(self.ActiveItem['templates'][Field['template_number']])
                    else:
                        StrVar.set(sorted(ParamDict.keys())[0])
                else:
                    CBFunction = self._OnTemplateChange
                    if self.ActiveItem['templates'][Field['template_number']]:
                        StrVar.set(self.ActiveItem['templates'][Field['template_number']])
                    else:
                        if 'default' in list(Field.keys()):
                            StrVar.set(Field['default'])
                            if Field['default'] and Field['default'][0] == '#':
                                EntryEnabled = False

            else:
                Color = 'black'
                StrVar = None
                CBFunction = None
                nField = None
                EntryEnabled = False

            self.DisplayedParams[-1] += [Tk.Label(self.ParamsValuesFrame, text = Field['name'], width = 20, anchor = Tk.W, foreground = Color)]
            self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=0, sticky = Tk.N)

            self.DisplayedParams[-1] += [Tk.Label(self.ParamsValuesFrame, text = Field['type'], width = 20, anchor = Tk.W)]
            self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=1, sticky = Tk.N)

            if not CBFunction is None:
                if Field['name'] in self.MenuParams.keys():
                    self.DisplayedParams[-1] += [Tk.OptionMenu(self.ParamsValuesFrame, StrVar, *self.AvailableTypes)]
                    self.DisplayedParams[-1][-1]['menu'].delete(0, "end")
                    for Param in sorted(ParamDict.keys()):
                        self.DisplayedParams[-1][-1]['menu'].add_command(label=Param, command=lambda param = Param, func = CBFunction, sv=StrVar, LocalNumber = nField, DisplayNumber = len(self.DisplayedParams)-1: func(sv, LocalNumber, DisplayNumber, param))
                    if not AddNewFunction is None:
                        self.DisplayedParams[-1][-1]['menu'].add_separator()
                        self.DisplayedParams[-1][-1]['menu'].add_command(label='New...', command=lambda func = AddNewFunction, sv=StrVar, LocalNumber = nField, DisplayNumber = len(self.DisplayedParams)-1: func(sv, LocalNumber, DisplayNumber))
                else:
                    StrVar.trace("w", lambda name, index, mode, sv=StrVar, func = CBFunction, LocalNumber = nField, DisplayNumber = len(self.DisplayedParams)-1: func(sv, LocalNumber, DisplayNumber))
                    self.DisplayedParams[-1] += [Tk.Entry(self.ParamsValuesFrame, textvariable = StrVar, width = 45, bg = 'white')]

                if not EntryEnabled:
                    self.DisplayedParams[-1][-1].config(state = 'disabled')
            else:
                self.DisplayedParams[-1] += [Tk.Label(self.ParamsValuesFrame, text = Field['value'], width = 45, anchor = Tk.W)]
            self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=2, sticky = Tk.N+Tk.E+Tk.W)
        if self.CurrentMinParamDisplayed + self.NFieldsDisplayed < len(ItemsFields):
            self.DisplayedParams += [[Tk.Label(self.ParamsValuesFrame, text = '...', width = 20, anchor = Tk.W)]]
            self.DisplayedParams[-1][0].grid(row=len(self.DisplayedParams)-1, column = 0)

    def DisplayGlobalVariables(self, Mod):
        VariablesParams = [{'name': 'Framework name', 'type': 'str', 'value': self.Framework.Data['name']}] + self.Framework.GlobalVariables
        NItemsFields = len(VariablesParams) + 1 # for + button

        if Mod == 0:
            self.CurrentMinParamDisplayed = 0
        elif not Mod is None:
            self.CurrentMinParamDisplayed = max(0, min(NItemsFields - self.NFieldsDisplayed, self.CurrentMinParamDisplayed + Mod))
        self.DisplayedParams = []
        self.CurrentParams = {}

        if self.CurrentMinParamDisplayed != 0:
            FirstLine = '...'
        else:
            FirstLine = ''
        self.DisplayedParams += [[Tk.Label(self.ParamsValuesFrame, text = FirstLine, width = 20, anchor = Tk.W)]]
        self.DisplayedParams[-1][0].grid(row=len(self.DisplayedParams)-1, column = 0)

        DisplayedFieldsIndexes = list(range(self.CurrentMinParamDisplayed, min(NItemsFields, self.CurrentMinParamDisplayed + self.NFieldsDisplayed)))
        nFieldPossible = 0
        for nVariable, Variable in enumerate(VariablesParams):
            if nFieldPossible in DisplayedFieldsIndexes:
                self.DisplayedParams += [[]]
                if nVariable == 0:
                    self.DisplayedParams[-1] += [Tk.Label(self.ParamsValuesFrame, text = Variable['name'], width = 20, anchor = Tk.W, foreground = 'black')]
                    self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=0, sticky = Tk.N)
                    self.DisplayedParams[-1] += [Tk.Label(self.ParamsValuesFrame, text = Variable['type'], width = 20, anchor = Tk.W, foreground = 'black')]
                    self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=1, sticky = Tk.N)

                    StrVar = Tk.StringVar(self.MainWindow)
                    StrVar.set(Variable['value'])
                    StrVar.trace("w", lambda name, index, mode, sv=StrVar: self._OnFrameworkNameChange(sv))
                    self.DisplayedParams[-1] += [Tk.Entry(self.ParamsValuesFrame, text = StrVar, width = 45, foreground = 'black')]
                    self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=2, columnspan=2, sticky = Tk.N)
                    continue

                for nField, FieldName in enumerate(['name', 'type', 'value']):
                    Width = [20, 20, 40][nField]

                    StrVar = Tk.StringVar(self.MainWindow)
                    StrVar.set(Variable[FieldName])
                    StrVar.trace("w", lambda name, index, mode, sv=StrVar, nVar = nVariable-1, DisplayNumber = len(self.DisplayedParams)-1, ModValue = FieldName: self._OnGlobalVariableChange(sv, nVar, ModValue, DisplayNumber))
                    self.DisplayedParams[-1] += [Tk.Entry(self.ParamsValuesFrame, text = StrVar, width = Width, foreground = 'black')]
                    self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=nField, sticky = Tk.N+Tk.W)

                self.DisplayedParams[-1] += [Tk.Button(self.ParamsValuesFrame, text = '-', command = lambda VarName = Variable['name']: self._OnRemoveGlobalVariable(VarName))]
                self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=3, sticky = Tk.N+Tk.E+Tk.W)
            nFieldPossible += 1
        if nFieldPossible in DisplayedFieldsIndexes:
            self.DisplayedParams += [[Tk.Button(self.ParamsValuesFrame, text = '+', command = lambda :self._OnAddGlobalVariable())]]
            self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=0, columnspan = 4, sticky = Tk.N+Tk.E+Tk.W)
        nFieldPossible += 1
        if self.CurrentMinParamDisplayed + self.NFieldsDisplayed < NItemsFields:
            self.DisplayedParams += [[Tk.Label(self.ParamsValuesFrame, text = '...', width = 20, anchor = Tk.W)]]
            self.DisplayedParams[-1][0].grid(row=len(self.DisplayedParams)-1, column = 0)

    def DisplayTypesParameters(self, Mod):
        NItemsFields = 0
        for TypeName in self.Framework.UserDefinedTypes.keys():
            NItemsFields += 2 # One for the name, one for the '+' button
            NItemsFields += len(self.Framework.UserDefinedTypes[TypeName]['fields'])

        if Mod == 0:
            self.CurrentMinParamDisplayed = 0
        elif not Mod is None:
            self.CurrentMinParamDisplayed = max(0, min(NItemsFields - self.NFieldsDisplayed, self.CurrentMinParamDisplayed + Mod))
        self.DisplayedParams = []
        self.CurrentParams = {}

        if self.CurrentMinParamDisplayed != 0:
            FirstLine = '...'
        else:
            FirstLine = ''
        self.DisplayedParams += [[Tk.Label(self.ParamsValuesFrame, text = FirstLine, width = 20, anchor = Tk.W)]]
        self.DisplayedParams[-1][0].grid(row=len(self.DisplayedParams)-1, column = 0)

        DisplayedFieldsIndexes = list(range(self.CurrentMinParamDisplayed, min(NItemsFields, self.CurrentMinParamDisplayed + self.NFieldsDisplayed)))
        nFieldPossible = 0
        for TypeName in self.Framework.UserDefinedTypes.keys():
            if nFieldPossible in DisplayedFieldsIndexes:
                self.DisplayedParams += [[]]
                self.DisplayedParams[-1] += [Tk.Label(self.ParamsValuesFrame, text = 'Event type', width = 20, anchor = Tk.W, foreground = 'black')]
                self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=0, sticky = Tk.N)
                StrVar = Tk.StringVar(self.MainWindow)
                StrVar.set(TypeName)
                StrVar.trace("w", lambda name, index, mode, sv=StrVar, TypeName = TypeName, nField = None, DisplayNumber = len(self.DisplayedParams)-1, ModValue = 'name': self._OnDefinedEventTypeFieldChange(sv, TypeName, nField, ModValue, DisplayNumber))
                self.DisplayedParams[-1] += [Tk.Entry(self.ParamsValuesFrame, textvariable = StrVar, width = 60, bg = 'white')]
                self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=1, sticky = Tk.N)

                self.DisplayedParams[-1] += [Tk.Button(self.ParamsValuesFrame, text = '-', command = lambda TypeName = TypeName: self._OnRemoveType(TypeName))]
                self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=2, sticky = Tk.N+Tk.E+Tk.W)
            nFieldPossible += 1
            for nFieldInType, Field in enumerate(self.Framework.UserDefinedTypes[TypeName]['fields']):
                if nFieldPossible in DisplayedFieldsIndexes:
                    self.DisplayedParams += [[]]
                    StrVar = Tk.StringVar(self.MainWindow)
                    StrVar.set(Field['type'])
                    StrVar.trace("w", lambda name, index, mode, sv=StrVar, TypeName = TypeName, nField = nFieldInType, DisplayNumber = len(self.DisplayedParams)-1, ModValue = 'type': self._OnDefinedEventTypeFieldChange(sv, TypeName, nField, ModValue, DisplayNumber))
                    self.DisplayedParams[-1] += [Tk.Entry(self.ParamsValuesFrame, textvariable = StrVar, width = 20, bg = 'white')]
                    self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=0, sticky = Tk.N)

                    StrVar = Tk.StringVar(self.MainWindow)
                    StrVar.set(Field['name'])
                    StrVar.trace("w", lambda name, index, mode, sv=StrVar, TypeName = TypeName, nField = nFieldInType, DisplayNumber = len(self.DisplayedParams)-1, ModValue = 'name': self._OnDefinedEventTypeFieldChange(sv, TypeName, nField, ModValue, DisplayNumber))
                    self.DisplayedParams[-1] += [Tk.Entry(self.ParamsValuesFrame, textvariable = StrVar, width = 60, bg = 'white')]
                    self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=1, sticky = Tk.N)

                    self.DisplayedParams[-1] += [Tk.Button(self.ParamsValuesFrame, text = '-', command = lambda TypeName = TypeName, nField = nFieldInType: self._OnDefinedEventTypeFieldAddRemove(TypeName, nField))]
                    self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=2, sticky = Tk.N+Tk.E+Tk.W)

                nFieldPossible += 1
            if nFieldPossible in DisplayedFieldsIndexes:
                self.DisplayedParams += [[Tk.Button(self.ParamsValuesFrame, text = '+', command = lambda TypeName = TypeName, nField = None: self._OnDefinedEventTypeFieldAddRemove(TypeName, nField))]]
                self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=0, columnspan = 3, sticky = Tk.N+Tk.E+Tk.W)
            nFieldPossible += 1
        if self.CurrentMinParamDisplayed + self.NFieldsDisplayed < NItemsFields:
            self.DisplayedParams += [[Tk.Label(self.ParamsValuesFrame, text = '...', width = 20, anchor = Tk.W)]]
            self.DisplayedParams[-1][0].grid(row=len(self.DisplayedParams)-1, column = 0)

    def _OnDefinedEventTypeFieldChange(self, StrVar, TypeName, nField, ModValue, DisplayIndex):
        if ModValue == 'type':
            ColumnIndex = 0
        elif ModValue == 'name':
            ColumnIndex = 1
        CursorIndex = self.DisplayedParams[DisplayIndex][ColumnIndex].index(Tk.INSERT)
        if nField is None:
            PreviousName = TypeName
            NewName = StrVar.get()
            self.Framework.UserDefinedTypes[NewName] = self.Framework.UserDefinedTypes[PreviousName]
            self.Framework.UserDefinedTypes[NewName]['name'] = NewName
            del self.Framework.UserDefinedTypes[PreviousName]
#TODO : change references to this event type
            self.Framework.WriteTypesFile()

        else:
            self.Framework.UserDefinedTypes[TypeName]['fields'][nField][ModValue] = StrVar.get()
            self.Framework.WriteTypesFile()

        self.GUIUpdate('_OnDefinedEventTypeFieldChange')
        self.DisplayedParams[DisplayIndex][ColumnIndex].focus_set()
        self.DisplayedParams[DisplayIndex][ColumnIndex].icursor(CursorIndex)

    def _OnDefinedEventTypeFieldAddRemove(self, TypeName, nField):
        if nField is None:
            self.Framework.UserDefinedTypes[TypeName]['fields'] += [{'type':'', 'name': ''}]
        else:
            self.Framework.UserDefinedTypes[TypeName]['fields'].pop(nField)
            self.Framework.WriteTypesFile()
        self.GUIUpdate('_OnDefinedEventTypeFieldAddRemove')

    def GetAddedParamDisplayColor(self, ParamName, ParamValue):
        if not self._AddedParamValidity(ParamName, ParamValue):
            return 'red'
        else:
            return 'black'

    def GetParamDisplayColor(self, NParam):
        ModuleParameters = self.ActiveItem['module']['parameters']
        TypeCanBeenChecked, ValueWasChecked = framework_abstractor.CheckParameterValidity(ModuleParameters[NParam]['type'], self.ActiveItem['parameters'][NParam])
        if not TypeCanBeenChecked:
            Color = 'black'
        else:
            if ValueWasChecked:
                Color = 'green'
            else:
                Color = 'red'
        return Color

    def GetTemplateDisplayColor(self, NTemplate):
        if self.ActiveItem['module']['templates'][NTemplate]['type'] == 'sepia::type':
            if not self.ActiveItem['templates'][NTemplate] in self.AvailableTypes.keys() or self.AvailableTypes[self.ActiveItem['templates'][NTemplate]]['origin'] != 'sepia':
                return 'red'
            return 'green'
        if not self.ActiveItem['templates'][NTemplate]:
            return 'red'
        return 'black'

G = GUI()
