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

        TarsierModules = tarsier_scrapper.ScrapTarsierFolder()
        SepiaModules, SepiaTypes = sepia_scrapper.ScrapSepiaFile()
        ChameleonModules = chameleon_scrapper.ScrapChameleonFolder()

        self.AvailableModules = {}
        for ModuleName, Module in list(TarsierModules.items()):
            self.AvailableModules[ModuleName] = Module
        for ModuleName, Module in list(SepiaModules.items()):
            self.AvailableModules[ModuleName] = Module
        for ModuleName, Module in list(ChameleonModules.items()):
            self.AvailableModules[ModuleName] = Module

        self.AvailableTypes = {}
        for TypeName, Type in list(SepiaTypes.items()):
            self.AvailableTypes[TypeName] = Type

        self.UserDefinedVariableTypes = ['Struct', 'Packed struct', 'Lambda Function']

        self.MainWindow = Tk.Tk()
        self.MainWindow.title('Beaver - Untitled')

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
            newmenu.add_command(label=Type, command=partial(self.AddNewType, Type))
        insertmenu.add_separator()

        tarsiermenu = Tk.Menu(insertmenu)
        insertmenu.add_cascade(label = "Tarsier", menu = tarsiermenu)
        for Module in list(TarsierModules.keys()):
            if Module not in UNSUPPORTED_MODULES:
                tarsiermenu.add_command(label=Module, command=partial(self.AddModule, str(Module)))
        chameleonmenu = Tk.Menu(insertmenu)
        insertmenu.add_cascade(label = "Chameleon", menu = chameleonmenu)
        for Module in list(ChameleonModules.keys()):
            if Module not in UNSUPPORTED_MODULES:
                chameleonmenu.add_command(label=Module, command=partial(self.AddModule, str(Module)))
        sepiamenu = Tk.Menu(insertmenu)
        insertmenu.add_cascade(label = "Sepia", menu = sepiamenu)
        for Module in list(SepiaModules.keys()):
            if Module not in UNSUPPORTED_MODULES:
                sepiamenu.add_command(label=Module, command=partial(self.AddModule, str(Module)))
        sepiamenu.add_separator()
        for Type in list(SepiaTypes.keys()):
            sepiamenu.add_command(label=Type, command=lambda : self.SetType(Type))


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
        cid = self.DisplayCanvas.mpl_connect('button_press_event', self._OnDisplayClick)
        self.DisplayCanvas.show()
        self.DisplayCanvas.get_tk_widget().grid(row = 0, column = 0)

        self.AutoAddBGR = False
        self.AvailablesModulesPositions = []
        self.SelectedAvailableModulePosition = 0
        self.SelectedAvailableChameleonModulePosition = 0
        self.ModulesDiameter = 2.
        self.ModulesTilingDistance = 4.
        self.DisplayedModulesPositions = {}

        self.OffsetLinks = {}
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

        self.CodeFrame = Tk.Frame(self.MainWindow)
        self.CodeFrame.grid(row = 0, column = 2)
        self.CurrentCodeFile = list(self.Framework.Files.keys())[0]
        self.CurrentCodeType = self.Framework.Files[self.CurrentCodeFile]['type']
        self.CodeFileVar = Tk.StringVar(self.MainWindow)
        self.CodeFileVar.set(self.CurrentCodeFile)
        self.CodeFileMenu = Tk.OptionMenu(self.CodeFrame, self.CodeFileVar, *self.Framework.Files)
        self.CodeFileMenu.grid(row = 0, column = 0)
        self.CodePad = ScrolledText.ScrolledText(self.CodeFrame, width=120, height=40, bg = 'white')
        self.CodePad.bind("<<TextModified>>", self._onCodeModification)
        self.CodePad.grid(row = 1, column = 0)
        self.UpdateCodeMenu()
        self.SetDisplayedCodefile(self.CurrentCodeFile, SaveCurrentFile = False)
        
        self.ParamsFrame = Tk.Frame(self.MainWindow, width = 100, bd = 4, relief='groove')
        self.ParamsFrame.grid(row = 2, column = 0, rowspan = 1, columnspan = 1, sticky=Tk.N+Tk.S+Tk.E+Tk.W)
        self.ParamsTitleFrame = Tk.Frame(self.ParamsFrame)
        self.ParamsTitleFrame.grid(row = 0, column = 0, columnspan = 2, sticky=Tk.N+Tk.S+Tk.W)

        self.ParamsValuesFrame = Tk.Frame(self.ParamsFrame, bd = 2, relief='groove')
        self.ParamsValuesFrame.grid(row = 1, column = 0, sticky = Tk.N+Tk.S+Tk.E+Tk.W)
        self.ParamsButtonsFrame = Tk.Frame(self.ParamsFrame)
        self.ParamsButtonsFrame.grid(row = 1, column = 1, sticky = Tk.N+Tk.S+Tk.E)
        self.ParamsUpperButton = Tk.Button(self.ParamsButtonsFrame, text = '^', height = 10, command = partial(self.ChangeDisplayedParams, -1))
        self.ParamsLowerButton = Tk.Button(self.ParamsButtonsFrame, text = 'v', height = 10, command = partial(self.ChangeDisplayedParams, +1))
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
        
        self.RegenerateAvailableSlots()
        self.DrawFramework()
        self.ChangeDisplayedParams(0)

        self.Log("Ready !")
        self.MainWindow.mainloop()

    def _on_closing(self):
        if MessageBox.askokcancel("Quit", "Do you really want to quit?"):
            self.MainWindow.quit()
            self.MainWindow.destroy()

    def _OnDisplayClick(self, event):
        if not self.Framework.Modules:
            return None
        Click = np.array([event.xdata, event.ydata])
        for Module in self.Framework.Modules:
            if (abs(self.DisplayedModulesPositions[Module['id']] - Click) < self.ModulesDiameter/2.).all():
                self.ActiveItem = Module
                self.DrawFramework()
                self.ChangeDisplayedParams(0)
                if not self.WaitingForRoute is None:
                    self.RouteModule()
                return None
        self.WaitingForRoute = None
        for LinkTuple, LinkText in list(self.DisplayedLinks.items()):
            Contains, AddDict = LinkText.contains(event)
            if Contains:
                self.ActiveItem = LinkTuple
                self.DrawFramework()
                self.ChangeDisplayedParams(0)
                return None

        for nPosition, PositionAndParent in enumerate(self.AvailablesModulesPositions):
            if (abs(PositionAndParent[0] - Click) < self.ModulesDiameter/2.).all():
                if PositionAndParent[1:].count(None) == 0: # Only case where were have a parent AND a child, that are not actually that.
                    self.SelectedAvailableChameleonModulePosition = nPosition
                else:
                    self.SelectedAvailableModulePosition = nPosition
                self.DrawFramework()
                self.ChangeDisplayedParams(0)
                return None
        self.ActiveItem = None
        self.DrawFramework()
        self.ChangeDisplayedParams(0)

    def GenerateEmptyFramework(self):
        if self.Framework.Modules:
            if not MessageBox.askokcancel("New", "Unsaved framework. Erase anyway ?"):
                return None
        with FileDialog.asksaveasfile(mode='w', initialdir = PROJECTS_DIR, defaultextension='.json', title = "New project", filetypes=[("JSON","*.json")]) as file:
            if file is None:
                return None
            self.Framework = framework_abstractor.FrameworkAbstraction(LogFunction = self.Log)
            self.Framework.Data['name'] = file.name.split('/')[-1].split('.json')[0]

            self.SetDisplayedCodefile(self.CurrentCodeFile, SaveCurrentFile = False)
            self.FrameworkFileName = file.name
            self.MainWindow.title('Beaver - {0}'.format(self.Framework.Data['name']))

            self.TempFiles = {}
            self.DisplayedParams = []
            self.CurrentMinParamDisplayed = 0
            self.RegenerateAvailableSlots()
            self.DisplayedModulesPositions = {}
            self.OffsetLinks = {}

            self.UpdateCodeMenu()
            self.ActiveItem = None
        self.DrawFramework()
        self.ChangeDisplayedParams(0)

    def save_command(self):
        self.RegisterCurrentCodePad()
        if self.FrameworkFileName:
            with open(self.FrameworkFileName, "w") as file:
                if not file is None:
                    json.dump(self.Framework.Data, file)
                    self.Log("Saved.")
                else:
                    self.Log("Something went wrong while saving project.")
        else:
            self.saveas_command()

    def saveas_command(self):
        self.RegisterCurrentCodePad()
        with FileDialog.asksaveasfile(mode='w', initialdir = PROJECTS_DIR, initialfile = self.Framework.Data['name'], defaultextension='.json', title = "Save as...", filetypes=[("JSON","*.json")]) as file:
            if not file is None:
                NewName =  file.name.split('/')[-1].split('.json')[0]
                if not self.Framework.Data['name'] or (NewName != self.Framework.Data['name'] and MessageBox.askyesno("Name changed", "Do you want to change project name from \n{0} \nto {1} ?".format(self.Framework.Data['name'], NewName))):
                    self.Framework.Data['name'] = NewName
                    self.MainWindow.title('Beaver - {0}'.format(self.Framework.Data['name']))

                json.dump(self.Framework.Data, file)
                self.FrameworkFileName = file.name
                self.Log("Saved.")
        self.ChangeDisplayedParams(0)
        
    def open_command(self):
        with FileDialog.askopenfile(parent=self.MainWindow,mode='rb', initialdir = PROJECTS_DIR, title='Open...', defaultextension='.json', filetypes=[("JSON","*.json")]) as file:
            if file != None:
                Data = json.load(file)
                self.Framework = framework_abstractor.FrameworkAbstraction(Data, self.Log)
                self.FrameworkFileName = file.name
                self.MainWindow.title('Beaver - {0}'.format(self.Framework.Data['name']))

                self.TempFiles = {}
                self.DisplayedParams = []
                self.CurrentMinParamDisplayed = 0
                self.RegenerateAvailableSlots()
                self.DisplayedModulesPositions = {}
                
                self.OffsetLinks = {}

                self.UpdateCodeMenu()
                for Module in self.Framework.Modules:
                    self.AddModuleDisplay(Module, AutoDraw = False)
                self.ActiveItem = None
                self.ChangeDisplayedParams(0)
                try:
                    self.SetDisplayedCodefile('Documentation', SaveCurrentFile = False)
                except:
                    self.SetDisplayedCodefile(list(self.Framework.Files.keys())[0], SaveCurrentFile = False)
        self.DrawFramework()
        self.ChangeDisplayedParams(0)

    def RegisterCurrentCodePad(self):
        if self.CurrentCodeFile in list(self.TempFiles.keys()):
            return None
        CurrentText = self.CodePad.get('1.0', Tk.END+'-1c')
        self.Framework.Files[self.CurrentCodeFile]['data'] = CurrentText

    def AddModule(self, ModuleName):
        if self.AvailableModules[ModuleName]['origin'] == 'chameleon':
            self.AddChameleonModule(ModuleName)
            return None

        ModuleNames = [Module['name'] for Module in self.Framework.Modules]
        AskedModuleName = ModuleName
        N = 0
        while AskedModuleName in ModuleNames:
            N += 1
            AskedModuleName = ModuleName + '_{0}'.format(N)

        self.Log("Adding " + AskedModuleName)
        ParentID = self.AvailablesModulesPositions[self.SelectedAvailableModulePosition][1]
        ChildrenID = self.AvailablesModulesPositions[self.SelectedAvailableModulePosition][2]
        NewModule = self.Framework.AddModule(self.AvailableModules[ModuleName], AskedModuleName)
        if not ParentID is None:
            self.AddLink(ParentID, NewModule['id'])
        if not ChildrenID is None:
            self.AddLink(NewModule['id'], ChildrenID)

        self.AddModuleDisplay(self.Framework.Modules[-1], AutoDraw = True)

    def AddModuleDisplay(self, Module, AutoDraw):
        self.DisplayedModulesPositions[Module['id']] = self.AvailablesModulesPositions[self.SelectedAvailableModulePosition][0]
        self.RegenerateAvailableSlots()
        if AutoDraw:
            self.ActiveItem = self.Framework.Modules[-1]
            self.DrawFramework()
            self.ChangeDisplayedParams(0)

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
                if self.Framework.GetModuleByID(ModuleID)['module']['name'] == 'background_cleaner':
                    FoundBGC = True
                    break
            if not FoundBGC:
                self.AddChameleonModule('background_cleaner', AddBGC = False)
        NewModule = self.Framework.AddModule(self.AvailableModules[ModuleName], AskedModuleName)
        self.Framework.ChameleonTiles[Tile] += [NewModule['id']]

        self.AddChameleonModuleDisplay(self.Framework.Modules[-1], AutoDraw = True)


    def AddChameleonModuleDisplay(self, Module, AutoDraw):
        self.DisplayedModulesPositions[Module['id']] = self.AvailablesModulesPositions[self.SelectedAvailableChameleonModulePosition][0]
        self.RegenerateAvailableSlots()
        if AutoDraw:
            self.ActiveItem = self.Framework.Modules[-1]
            self.DrawFramework()
            self.ChangeDisplayedParams(0)

    def RegenerateAvailableSlots(self):
        self.AvailablesModulesPositions = []
        if not [Module['id'] for Module in self.Framework.Modules if Module['module']['origin'] != 'chameleon']:
            self.AvailablesModulesPositions += [(np.array([0., 0.]), None, None)]
            self.ChameleonInitialTilePosition = np.array([0., -self.ModulesTilingDistance])
            self.SelectedAvailableModulePosition = 0
            self.SelectedAvailableChameleonModulePosition = len(self.AvailablesModulesPositions)
            self.RegenerateChameleonAvailableSlots()
            return None

        PossibleSlots = []
        AskedSlotsByHeight = {}
        TakenSlotsByHeight = {}

        for Module in self.Framework.Modules:
            if Module['module']['origin'] == 'chameleon':
                continue
            ModuleID = Module['id']
            ModulePosition = self.DisplayedModulesPositions[ModuleID]
            ModuleType = Module['module']
            
            NOutputs = len([Module['parameters'][nParam] for nParam in framework_abstractor.FindModuleHandlers(ModuleType) if not Module['parameters'][nParam]])
            if NOutputs:
                if ModulePosition[1] - self.ModulesTilingDistance not in list(AskedSlotsByHeight.keys()):
                    AskedSlotsByHeight[ModulePosition[1] - self.ModulesTilingDistance] = []
                if ModulePosition[1] - self.ModulesTilingDistance not in list(TakenSlotsByHeight.keys()):
                    TakenSlotsByHeight[ModulePosition[1] - self.ModulesTilingDistance] = []
                AskedSlotsByHeight[ModulePosition[1] - self.ModulesTilingDistance] += [(ModulePosition[0], ModuleID, -1)] * NOutputs
            
            if ModuleType['has_operator']:
                if ModulePosition[1] + self.ModulesTilingDistance not in list(AskedSlotsByHeight.keys()):
                    AskedSlotsByHeight[ModulePosition[1] + self.ModulesTilingDistance] = []
                if ModulePosition[1] + self.ModulesTilingDistance not in list(TakenSlotsByHeight.keys()):
                    TakenSlotsByHeight[ModulePosition[1] + self.ModulesTilingDistance] = []
                AskedSlotsByHeight[ModulePosition[1] + self.ModulesTilingDistance] += [(ModulePosition[0], -1, ModuleID)]

            if ModulePosition[1] not in list(TakenSlotsByHeight.keys()):
                TakenSlotsByHeight[ModulePosition[1]] = []
            if ModulePosition[1] not in list(AskedSlotsByHeight.keys()):
                AskedSlotsByHeight[ModulePosition[1]] = []
            TakenSlotsByHeight[ModulePosition[1]] += [(ModulePosition[0], ModuleID, ModuleID)]

        MinX = np.inf
        for Height in list(AskedSlotsByHeight.keys()):
            FinalLine = []
            Line = AskedSlotsByHeight[Height] + TakenSlotsByHeight[Height]
            for nIndex, Index in enumerate(np.argsort(np.array(Line)[:,0]).tolist()):
                FinalLine += [(nIndex * self.ModulesTilingDistance, Line[Index][1], Line[Index][2])]
            Avg = (np.array(FinalLine)[:,0]).mean()

            def ReplaceNegs(Value):
                if Value == -1:
                    return None
                else:
                    return Value

            for Item in FinalLine:
                MinX = min(MinX, Item[0])
                if -1 in Item:
                    self.AvailablesModulesPositions += [(np.array([Item[0] - Avg, Height]), ReplaceNegs(Item[1]), ReplaceNegs(Item[2]))]
                else:
                    self.DisplayedModulesPositions[Item[1]] = np.array([Item[0] - Avg, Height])

        self.SelectedAvailableModulePosition = 0
        self.SelectedAvailableChameleonModulePosition = len(self.AvailablesModulesPositions)

        MinHeight = min(AskedSlotsByHeight.keys())
        ChameleonMaxHeight = MinHeight - self.ModulesTilingDistance
        self.ChameleonInitialTilePosition = np.array([MinX, ChameleonMaxHeight])
        self.RegenerateChameleonAvailableSlots()

    def RegenerateChameleonAvailableSlots(self):
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
    
    def GetChameleonModulePosition(self, Tile, nModule):
        if not list(self.Framework.ChameleonTiles.values()):
            TilesSizes = 0
        else:
            TilesSizes = max([len(IDs) for IDs in list(self.Framework.ChameleonTiles.values())])
        return self.ChameleonInitialTilePosition + np.array([Tile[0] * (TilesSizes*self.ModulesDiameter + self.ModulesTilingDistance), - Tile[1] * self.ModulesTilingDistance/1.5]) + nModule * np.array([self.ModulesDiameter, 0])

    def RemoveModule(self):
        if self.ActiveItem is None:
            return None
        if type(self.ActiveItem) == dict:
            ModuleName = self.ActiveItem['name']
            AvailableToRemove = []
            del self.DisplayedModulesPositions[self.ActiveItem['id']]
            for ParentID in self.ActiveItem['parent_ids']:
                ParentModule = self.Framework.GetModuleByID(ParentID)
                self.RemoveLink(ParentID, self.ActiveItem['id'])
            for nParameter in framework_abstractor.FindModuleHandlers(self.ActiveItem['module']):
                if self.ActiveItem['parameters'][nParameter]:
                    self.RemoveLink(self.ActiveItem['id'], self.Framework.GetModuleByName(self.ActiveItem['parameters'][nParameter].split('@')[1])['id'])
            self.Framework.Modules.remove(self.ActiveItem)
            self.ActiveItem = None

            self.RegenerateAvailableSlots()
            self.DrawFramework()
            self.ChangeDisplayedParams(0)
            self.Log("Removed {0}".format(ModuleName))
        elif type(self.ActiveItem) == tuple:
            ParentID, ChildID = self.Framework.GetParentAndChildFromLinkTuple(self.ActiveItem)
            self.RemoveLink(ParentID, ChildID)
            self.ActiveItem = None

            self.RegenerateAvailableSlots()
            self.DrawFramework()
            self.ChangeDisplayedParams(0)
            self.Log("Removed link from {0} to {1}".format(self.Framework.GetModuleByID(ParentID)['name'], self.Framework.GetModuleByID(ChildID)['name']))

    def RouteModule(self):
        if self.ActiveItem is None or type(self.ActiveItem) != dict:
            return None
        
        if self.WaitingForRoute is None:
            HandlersParamsIndexes = framework_abstractor.FindModuleHandlers(self.ActiveItem['module'])
            FreeSlot = False
            for nParam in HandlersParamsIndexes:
                if not self.ActiveItem['parameters'][nParam]:
                    FreeSlot = True
                    break
            if not FreeSlot:
                return None
            self.WaitingForRoute = self.ActiveItem['id'] # Will be the parent
            self.Log('Selected a child module to link to...')
            self.DrawFramework()
            return None

        if not self.ActiveItem['module']['has_operator']:
            self.WaitingForRoute = None
            self.Log('Selected module cannot receive more inputs')
            return None
    
        if self.ActiveItem['id'] == self.WaitingForRoute:
            self.WaitingForRoute = None
            self.Log('Cannot link a module to itself')
            return None

        NewParentsIDs = self.Framework.GetModuleByID(self.WaitingForRoute)['parent_ids']
        while NewParentsIDs:
            OlderGen = []
            for ParentID in NewParentsIDs:
                for OlderParentID in self.Framework.GetModuleByID(ParentID)['parent_ids']:
                    if OlderParentID not in OlderGen:
                        OlderGen += [OlderParentID]
                        if OlderParentID == self.ActiveItem['id']:
                            self.Log('Cannot link create circular dependancies')
                            self.WaitingForRoute = None
                            return None
                NewParentsIDs = list(OlderGen)

        self.Log("Linking {0} to {1}".format(self.Framework.GetModuleByID(self.WaitingForRoute)['name'], self.ActiveItem['name']))
        self.AddLink(self.WaitingForRoute, self.ActiveItem['id'])
        if self.DisplayedModulesPositions[self.WaitingForRoute][1] <= self.DisplayedModulesPositions[self.ActiveItem['id']][1]:
            self.Log('Remapping')

            VOffset = -(self.DisplayedModulesPositions[self.WaitingForRoute][1] - self.ModulesTilingDistance - self.DisplayedModulesPositions[self.ActiveItem['id']][1])
            LinkTuple = framework_abstractor.GetLinkTuple(self.WaitingForRoute, self.ActiveItem['id'])
            self.OffsetLinks[LinkTuple] = VOffset
            AllDescendance = self.GetDescendance(self.ActiveItem['id'])
            for ID in AllDescendance:
                self.DisplayedModulesPositions[ID] = self.DisplayedModulesPositions[ID] + np.array([0., -1.]) * self.OffsetLinks[LinkTuple]

        self.WaitingForRoute = None
        self.RegenerateAvailableSlots()
        self.DrawFramework()
        self.ChangeDisplayedParams(0)
        self.WaitingForRoute = None

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
        Success = self.Framework.AddLink(ParentID, ChildrenID)
        if not Success:
            return None

    def RemoveLink(self, ParentID, ChildrenID):
        LinkTuple = framework_abstractor.GetLinkTuple(ParentID, ChildrenID)
        if LinkTuple in list(self.OffsetLinks.keys()):
            AllDescendance = self.GetDescendance(ChildrenID)
            for ID in AllDescendance:
                self.DisplayedModulesPositions[ID] = self.DisplayedModulesPositions[ID] - np.array([0., -1.]) * self.OffsetLinks[LinkTuple]
            del self.OffsetLinks[LinkTuple]
        Success = self.Framework.RemoveLink(ParentID, ChildrenID)

    def AddNewType(self, Type):
        TmpName = Type
        if TmpName in self.Framework.UserWrittenCode:
            self.Log("Already underdefined type {0} in this project. Fill in a name first before defining a new one.".format(Type))
            self.SetDisplayedCodefile(TmpName)
            return None
        self.Framework.UserWrittenCode += [TmpName]
        self.Framework.Files[TmpName] = {'data': GenerateNewType(Type), 'type': Type}

        self.UpdateCodeMenu()
        self.SetDisplayedCodefile(TmpName)

    def SetType(self, Type):
        None

    def GenerateCode(self):
        self.Framework.GenerateCode()

    def GenerateBuild(self):
        if not self.FrameworkFileName:
            self.saveas_command()
            if not self.FrameworkFileName:
                return None
        LuaFilename = self.Framework.GenerateBuild()
        self.UpdateCodeMenu()
        self.SetDisplayedCodefile(LuaFilename)

    def GenerateBinary(self):
        None

    def DisplayModuleCode(self):
        if not self.ActiveItem is None and type(self.ActiveItem) == dict:
            Module = self.ActiveItem
            if Module['module']['origin'] == 'tarsier':
                self.TempFiles[Module['module']['name'] + '.hpp'] = '\n'.join(tarsier_scrapper.GetTarsierCode(Module['module']['name'] + '.hpp', Full = True))
            elif Module['module']['origin'] == 'sepia':
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
            self.SetDisplayedCodefile(Module['module']['name'] + '.hpp')

    def UpdateCodeMenu(self):
        Menu = self.CodeFileMenu['menu']
        Menu.delete(0, "end") 
        for FileName in list(self.Framework.Files.keys()):
            Menu.add_command(label = FileName, command = partial(self.SetDisplayedCodefile, FileName))

    def SetDisplayedCodefile(self, Codefile, SaveCurrentFile = True):
        if SaveCurrentFile:
            self.RegisterCurrentCodePad()
        self.CodePad.delete('1.0', Tk.END)
        self.CurrentCodeFile = Codefile
        self.CodeFileVar.set(self.CurrentCodeFile)
        if self.CurrentCodeFile in list(self.Framework.Files.keys()):
            self.CodePad.insert(Tk.END, self.Framework.Files[self.CurrentCodeFile]['data'])
            self.CurrentCodeType = self.Framework.Files[self.CurrentCodeFile]['type']
        else:
            self.CodePad.insert(Tk.END, self.TempFiles[self.CurrentCodeFile])
            self.CurrentCodeType = 'tmp' 

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

    def DrawFramework(self):
        #self.Log("Drawing...")
        minValues = np.array([0., 0.])
        maxValues = np.array([0., 0.])

        self.DisplayAx.clear()
        self.DisplayedLinks = {} 
        for Module in self.Framework.Modules:
            if not self.WaitingForRoute is None and self.WaitingForRoute == Module['id']:
                Color = 'k'
            else:
                if self.Framework.WellDefinedModule(Module):
                    Color = 'g'
                else:
                    Color = 'r'
            if not self.ActiveItem is None and type(self.ActiveItem) == dict and Module['id'] == self.ActiveItem['id']:
                Style = '-'
            else:
                Style = '--'
            self.DrawModule(Module, Style, Color)
            minValues = np.minimum(minValues, self.DisplayedModulesPositions[Module['id']] - 1.5*self.ModulesDiameter)
            maxValues = np.maximum(maxValues, self.DisplayedModulesPositions[Module['id']] + 1.5*self.ModulesDiameter)

            self.DrawLinksToChildrens(Module, Color)

        for nSlot, AvailableSlotAndParent in enumerate(self.AvailablesModulesPositions):
            Color = 'grey'
            if nSlot == self.SelectedAvailableModulePosition or nSlot == self.SelectedAvailableChameleonModulePosition:
                Style = '-'
                alpha = 1.
            else:
                Style = '--'
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
        else:
            ModulePosition = self.DisplayedModulesPositions[Module['id']]
            ModuleName = Module['name']
            ModuleEvFields = Module['module']['ev_fields']
            ModuleOutputFields = Module['module']['ev_outputs']

        DXs = (self.ModulesDiameter/2 * np.array([np.array([-1, -1]), np.array([-1, 1]), np.array([1, 1]), np.array([1, -1])])).tolist()
        for nDX in range(len(DXs)):
            self.DisplayAx.plot([(ModulePosition + DXs[nDX])[0], (ModulePosition + DXs[(nDX+1)%4])[0]], [(ModulePosition + DXs[nDX])[1], (ModulePosition + DXs[(nDX+1)%4])[1]], ls = Style, color = Color, alpha = alpha)
        NameTextPosition = ModulePosition + self.ModulesDiameter/2 * 0.8 * np.array([-1, -1])
        self.DisplayAx.text(NameTextPosition[0], NameTextPosition[1], s = ModuleName, color = Color, alpha = alpha, fontsize = 8)
        if not self.ActiveItem is None and type(self.ActiveItem) == dict and Module['id'] == self.ActiveItem['id'] and (ModuleEvFields):
            if ModulePosition[0] < 0:
                HAlign = 'right'
                FieldsTextPosition = ModulePosition + self.ModulesDiameter/2 * 1.2 * np.array([-1., 0])
            else:
                HAlign = 'left'
                FieldsTextPosition = ModulePosition + self.ModulesDiameter/2 * 1.2 * np.array([1., 0])
            ModuleFieldsString = 'Input fields :\n' + ', '.join(ModuleEvFields)
            if list(ModuleOutputFields.keys()):
                ModuleFieldsString = ModuleFieldsString + '\nOutputs :'
                for handle, Fields in list(ModuleOutputFields.items()):
                    ModuleFieldsString = ModuleFieldsString + '\n* ' + handle + '\n  ->' + '\n  ->'.join(Fields)
            self.DisplayAx.text(FieldsTextPosition[0], FieldsTextPosition[1], s = ModuleFieldsString, bbox={'facecolor': Color, 'alpha': 0.5, 'pad': 2}, horizontalalignment=HAlign, verticalalignment='center')
    
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
            ChildrenModule = self.Framework.GetModuleByID(AvailablePos[2])
            Start = AvailablePos[0] + np.array([0., -1.]) * self.ModulesDiameter/2
            End = self.DisplayedModulesPositions[AvailablePos[2]] + np.array([-1., 1.]) * self.ModulesDiameter/2 + np.array([1., 0.]) * self.ModulesDiameter * (1.)/(len(ChildrenModule['parent_ids'])+2.)
            YStep = (Start + End)/2
            self.DisplayAx.plot([Start[0], Start[0]], [Start[1], YStep[1]], ls = Style, color = Color, alpha = alpha)
            self.DisplayAx.plot([Start[0], End[0]], [YStep[1], YStep[1]], ls = Style, color = Color, alpha = alpha)
            self.DisplayAx.plot([End[0], End[0]], [YStep[1], End[1]], ls = Style, color = Color, alpha = alpha)

    def DrawLinksToChildrens(self, Module, ModuleColor):
        HandlersParamsIndexes = framework_abstractor.FindModuleHandlers(Module['module'])
        Links = []
        nUnused = 0
        for HandleIndex in HandlersParamsIndexes:
            if not Module['parameters'][HandleIndex]:
                AvailableChildren = [nAvailablePos for nAvailablePos, AvailablePos in enumerate(self.AvailablesModulesPositions) if AvailablePos[1] == Module['id']]
                Links += [(Module['id'], -AvailableChildren[nUnused]-1, 0.5)]
                nUnused += 1

            elif '@' in Module['parameters'][HandleIndex]:
                ChildrenName = Module['parameters'][HandleIndex].split('@')[1]
                for ChildrenModule in self.Framework.Modules:
                    if ChildrenModule['name'] == ChildrenName:
                        Links += [(Module['id'], ChildrenModule['id'], (ChildrenModule['parent_ids'].index(Module['id'])+1.+ChildrenModule['module']['has_operator'])/(len(ChildrenModule['parent_ids'])+1.+ChildrenModule['module']['has_operator']))]

        for nLink, Link in enumerate(Links):
            if Link[1] >= 0:
                Color = ModuleColor
                LinkTuple = framework_abstractor.GetLinkTuple(Link[0], Link[1])
                if not self.ActiveItem is None and type(self.ActiveItem) == tuple and self.ActiveItem == framework_abstractor.GetLinkTuple(Link[0], Link[1]):
                    Style = '-'
                else:
                    Style = ':'

                Start = self.DisplayedModulesPositions[Link[0]] + np.array([-1., -1.]) * self.ModulesDiameter/2 +np.array([1., 0.]) * self.ModulesDiameter * (1. + nLink) / (1. + len(Links))
                End = self.DisplayedModulesPositions[Link[1]] + np.array([-1., 1.]) * self.ModulesDiameter/2 + np.array([1., 0.]) * self.ModulesDiameter * Link[2]
                YStep = (Start + End)/2
                self.DisplayAx.plot([Start[0], Start[0]], [Start[1], YStep[1]], ls = Style, color = Color)
                self.DisplayAx.plot([Start[0], End[0]], [YStep[1], YStep[1]], ls = Style, color = Color)
                self.DisplayAx.plot([End[0], End[0]], [YStep[1], End[1]], ls = Style, color = Color)

                LinkType = self.Framework.LinksTypes[framework_abstractor.GetLinkTuple(Link[0], Link[1])]
                if LinkType is None:
                    LinkType = '?'
                self.DisplayedLinks[LinkTuple] = self.DisplayAx.text(YStep[0], YStep[1], s = LinkType, zorder = 10, bbox={'facecolor': 'white', 'alpha': 1, 'pad': 2, 'ls': Style}, horizontalalignment='center', verticalalignment='center')
            else:
                Style = ':'
                Color = 'grey'
                nSlot = -Link[1]-1
                if nSlot == self.SelectedAvailableModulePosition:
                    alpha = 1.
                else:
                    alpha = 0.4
                Start = self.DisplayedModulesPositions[Link[0]] + np.array([-1., -1.]) * self.ModulesDiameter/2 +np.array([1., 0.]) * self.ModulesDiameter * (1. + nLink) / (1. + len(Links))
                End = self.AvailablesModulesPositions[nSlot][0] + np.array([-1., 1.]) * self.ModulesDiameter/2 + np.array([1., 0.]) * self.ModulesDiameter * Link[2]
                YStep = (Start + End)/2
                self.DisplayAx.plot([Start[0], Start[0]], [Start[1], YStep[1]], ls = Style, color = Color, alpha = alpha)
                self.DisplayAx.plot([Start[0], End[0]], [YStep[1], YStep[1]], ls = Style, color = Color, alpha = alpha)
                self.DisplayAx.plot([End[0], End[0]], [YStep[1], End[1]], ls = Style, color = Color, alpha = alpha)

    def _OnParameterChange(self, StringVar, ParamIndex, DisplayIndex):
        print("Parameter : {0}, {1}".format(ParamIndex, DisplayIndex))
        self.ActiveItem['parameters'][ParamIndex] = StringVar.get()
        self.DisplayedParams[DisplayIndex][0]['foreground'] = self.GetParamDisplayColor(ParamIndex)

    def _OnAddedParameterChange(self, StringVar, ParamIndex, DisplayIndex):
        print("Added : {0}, {1}".format(ParamIndex, DisplayIndex))
        AddedParamName = self._GetBlankAddedParams()[ParamIndex]['name']
        # First check if name is ok and available
        if AddedParamName == 'Name':
            AskedName = StringVar.get()
            if not self._AddedParamValidity(AddedParamName, AskedName):
                self.DisplayedParams[DisplayIndex][0]['foreground'] = 'red'
                if not self.ActiveItem is None:
                    return None
            else:
                self.DisplayedParams[DisplayIndex][0]['foreground'] = 'black'

            if not self.ActiveItem is None and type(self.ActiveItem) == dict:
                PreviousName = self.ActiveItem['name']
                self.ActiveItem['name'] = AskedName
                for ParentID in self.ActiveItem['parent_ids']:
                    if not ParentID is None:
                        for Module in self.Framework.Modules:
                            if Module['id'] == ParentID:
                                for nParam, Param in enumerate(Module['parameters']):
                                    if '@' in Param and Param.split('@')[1] == PreviousName:
                                        Module['parameters'][nParam] = '@' + AskedName
                self.DrawFramework()
            elif self.ActiveItem is None:
                self.Framework.Data['name'] = AskedName
                self.MainWindow.title('Beaver - {0}'.format(AskedName))

    def _OnTemplateChange(self, StringVar, TemplateIndex, DisplayIndex):
        print("Template : {0}, {1}".format(TemplateIndex, DisplayIndex))
        self.ActiveItem['templates'][TemplateIndex] = StringVar.get()
        self.DisplayedParams[DisplayIndex][0]['foreground'] = self.GetTemplateDisplayColor(TemplateIndex)

    def _AddedParamValidity(self, AddedParamName, AddedParamValue):
        if AddedParamName == 'Name':
            if AddedParamValue == '':
                return False
            for Module in self.Framework.Modules:
                if Module['name'] == AddedParamValue and (self.ActiveItem is None or type(self.ActiveItem) == tuple or Module['id'] != self.ActiveItem['id']):
                    return False
            return True

    def _GetModuleAddedParams(self):
        return [{'name': 'Name', 'type': 'str', 'default': self.ActiveItem['name']}]

    def _GetBlankAddedParams(self):
        return [{'name': 'Name', 'type': 'str', 'default': self.Framework.Data['name']}]

    def _GetLinkAddedParams(self):
        return []

    def ChangeDisplayedParams(self, Mod):
        for Trio in self.DisplayedParams:
            for Field in Trio:
                Field.destroy()
        if self.ActiveItem is None:
            AddedParams = self._GetBlankAddedParams()
            ModuleParameters = []
            ModuleTemplates = []
            
        elif type(self.ActiveItem) == dict:
            AddedParams = self._GetModuleAddedParams()
            ModuleParameters = self.ActiveItem['module']['parameters']
            ModuleTemplates = self.ActiveItem['module']['templates']
        elif type(self.ActiveItem) == tuple:
            AddedParams = self._GetLinkAddedParams()
            ModuleParameters = []
            ModuleTemplates = []

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
        else:
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
            Field = ItemsFields[NField]
            self.DisplayedParams += [[]]
            if Field in AddedParams:
                nField = AddedParams.index(Field)
                Color = self.GetAddedParamDisplayColor(Field['name'], Field['default'])
                StrVar = Tk.StringVar(self.MainWindow)
                CBFunction = self._OnAddedParameterChange
                if 'default' in Field.keys():
                    StrVar.set(Field['default'])

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
                CBFunction = self._OnTemplateChange
                if self.ActiveItem['templates'][Field['template_number']]:
                    StrVar.set(self.ActiveItem['templates'][Field['template_number']])
                else:
                    if 'default' in list(Field.keys()):
                        StrVar.set(Field['default'])

            else:
                Color = 'black'
                StrVar = None
                CBFunction = None
                nField = None

            self.DisplayedParams[-1] += [Tk.Label(self.ParamsValuesFrame, text = Field['name'], width = 20, anchor = Tk.W, foreground = Color)]
            self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=0, sticky = Tk.N)

            self.DisplayedParams[-1] += [Tk.Label(self.ParamsValuesFrame, text = Field['type'], width = 20, anchor = Tk.W)]
            self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=1, sticky = Tk.N)

            print(Field['name'])
            print(CBFunction)
            if not CBFunction is None:
                #StrVar.trace("w", lambda name, index, mode, sv=StrVar, LocalNumber = nField, DisplayNumber = len(self.DisplayedParams)-1: CBFunction(sv, LocalNumber, DisplayNumber))
                StrVar.trace("w", lambda name, index, mode, sv=StrVar, func = CBFunction, LocalNumber = nField, DisplayNumber = len(self.DisplayedParams)-1: func(sv, LocalNumber, DisplayNumber))
                self.DisplayedParams[-1] += [Tk.Entry(self.ParamsValuesFrame, textvariable = StrVar, width = 45, bg = 'white')]
            else:
                print("CB None")
                self.DisplayedParams[-1] += [Tk.Label(self.ParamsValuesFrame, text = Field['value'], width = 45, anchor = Tk.W)]
            self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=2, sticky = Tk.N+Tk.E)
        if self.CurrentMinParamDisplayed + self.NFieldsDisplayed < len(ItemsFields):
            self.DisplayedParams += [[Tk.Label(self.ParamsValuesFrame, text = '...', width = 20, anchor = Tk.W)]]
            self.DisplayedParams[-1][0].grid(row=len(self.DisplayedParams)-1, column = 0)


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

def GenerateNewType(Type):
    if Type == 'Struct':
        File = 'struct {\n};'
    elif Type == 'Packed struct':
        File = 'SEPIA_PACK(struct {\n});'
    elif Type == 'Lambda Function':
        File = '[&]() {\n}'
    return File

G = GUI()
