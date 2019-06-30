import numpy as np

import matplotlib
import matplotlib.pyplot as pyl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

import Tkinter as Tk
import ttk
import ScrolledText
import tkMessageBox
import tkFileDialog
import tkFont

import os
import json
from functools import partial
matplotlib.use("TkAgg")

import tarsier_scrapper
import sepia_scrapper
import framework_abstractor

PROJECTS_DIR = 'Projects/'

def about_command():
    label = tkMessageBox.showinfo("About", "Tarsier code geneerator\nWork In Progress, be kind\nPlease visit https://github.com/neuromorphic-paris/")

        
class GUI:
    def __init__(self):
        self.Framework = framework_abstractor.FrameworkAbstraction(LogFunction = self.Log)
        self.FrameworkFileName = ''

        TarsierModules = tarsier_scrapper.ScrapTarsierFolder()
        SepiaModules, SepiaTypes = sepia_scrapper.ScrapSepiaFile()

        self.AvailableModules = {}
        for ModuleName, Module in TarsierModules.items():
            self.AvailableModules[ModuleName] = Module
        for ModuleName, Module in SepiaModules.items():
            self.AvailableModules[ModuleName] = Module

        self.AvailableTypes = {}
        for TypeName, Type in SepiaTypes.items():
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
        for Module in TarsierModules.keys():
            tarsiermenu.add_command(label=Module, command=partial(self.AddModule, str(Module)))
        sepiamenu = Tk.Menu(insertmenu)
        insertmenu.add_cascade(label = "Sepia", menu = sepiamenu)
        for Module in SepiaModules.keys():
            sepiamenu.add_command(label=Module, command=partial(self.AddModule, str(Module)))
        sepiamenu.add_separator()
        for Type in SepiaTypes.keys():
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
        self.DisplayCanvas.show()
        self.DisplayCanvas.get_tk_widget().grid(row = 0, column = 0)

        self.AvailablesModulesPositions = [(np.array([0,0]), None)]
        self.SelectedAvailableModulePosition = 0
        self.ModulesDiameter = 2.
        self.ModulesTilingDistance = 4.
        self.DisplayedModulesPositions = {}
        self.ActiveModule = None
        
        self.DisplayCodeLinkFrame = Tk.Frame(self.MainWindow)
        self.DisplayCodeLinkFrame.grid(row = 0, column = 1)
        self.ModuleCodeDisplayButton = Tk.Button(self.DisplayCodeLinkFrame, text = '?', command = self.DisplayModuleCode, font = tkFont.Font(size = 20))
        self.ModuleCodeDisplayButton.grid(row = 0, column = 0)
        self.CodeGenerationButton = Tk.Button(self.DisplayCodeLinkFrame, text = 'C++', command = self.GenerateCode, font = tkFont.Font(size = 20))
        self.CodeGenerationButton.grid(row = 1, column = 0)

        self.TempFiles = {}

        self.CodeFrame = Tk.Frame(self.MainWindow)
        self.CodeFrame.grid(row = 0, column = 2)
        self.CurrentCodeFile = self.Framework.Files.keys()[0]
        self.CurrentCodeType = self.Framework.Files[self.CurrentCodeFile]['type']
        self.CodeFileVar = Tk.StringVar(self.MainWindow)
        self.CodeFileVar.set(self.CurrentCodeFile)
        self.CodeFileMenu = Tk.OptionMenu(self.CodeFrame, self.CodeFileVar, *self.Framework.Files)
        self.CodeFileMenu.grid(row = 0, column = 0)
        self.CodePad = ScrolledText.ScrolledText(self.CodeFrame, width=120, height=40, bg = 'white')
        self.CodePad.bind("<<TextModified>>", self.OnCodeModification)
        self.CodePad.grid(row = 1, column = 0)
        self.UpdateCodeMenu()
        self.SetDisplayedCodefile(self.CurrentCodeFile, SaveCurrentFile = False)
        
        self.ParamsFrame = Tk.Frame(self.MainWindow, width = 100, bd = 4, relief='groove')
        self.ParamsFrame.grid(row = 2, column = 0, rowspan = 1, columnspan = 1, sticky=Tk.N+Tk.S+Tk.E+Tk.W)
        self.ParamsTitleFrame = Tk.Frame(self.ParamsFrame)
        self.ParamsTitleFrame.grid(row = 0, column = 0, columnspan = 2, sticky=Tk.N+Tk.S+Tk.W)
        NameLabel = Tk.Label(self.ParamsTitleFrame, text = 'Name', width = 20, justify = 'left')
        NameLabel.grid(row = 0, column = 0, sticky = Tk.W)
        TypeLabel = Tk.Label(self.ParamsTitleFrame, text = 'Type', width = 20, justify = 'left')
        TypeLabel.grid(row = 0, column = 1)
        ValueLabel = Tk.Label(self.ParamsTitleFrame, text = 'Value', width = 10, justify = 'left')
        ValueLabel.grid(row = 0, column = 2, sticky = Tk.E)

        self.ParamsValuesFrame = Tk.Frame(self.ParamsFrame, bd = 2, relief='groove')
        self.ParamsValuesFrame.grid(row = 1, column = 0, sticky = Tk.N+Tk.S+Tk.E+Tk.W)
        self.ParamsButtonsFrame = Tk.Frame(self.ParamsFrame)
        self.ParamsButtonsFrame.grid(row = 1, column = 1, sticky = Tk.N+Tk.S+Tk.E)
        self.ParamsUpperButton = Tk.Button(self.ParamsButtonsFrame, text = '^', height = 10, command = partial(self.ChangeDisplayedParams, -1))
        self.ParamsLowerButton = Tk.Button(self.ParamsButtonsFrame, text = 'v', height = 10, command = partial(self.ChangeDisplayedParams, +1))
        self.ParamsUpperButton.grid(row = 0, column = 0)
        self.ParamsLowerButton.grid(row = 1, column = 0)
        self.CurrentParams = []
        self.DisplayedParams = []
        self.NParamsDisplayed = 10
        self.CurrentMinParamDisplayed = 0


        self.CompilationFrame = Tk.Frame(self.MainWindow)
        self.CompilationFrame.grid(row = 1, column = 2, sticky=Tk.N+Tk.S)
        self.Premake4Button = Tk.Button(self.CompilationFrame, text = 'Premake4', command = self.GenerateBuild, font = tkFont.Font(size = 15))
        self.Premake4Button.grid(row = 0, column = 0)
        self.CompileButton = Tk.Button(self.CompilationFrame, text = 'Compile', command = self.GenerateBinary, font = tkFont.Font(size = 15))
        self.CompileButton.grid(row = 0, column = 1)

        self.ConsolePad = ScrolledText.ScrolledText(self.MainWindow, width=120, height=10, bg = 'black', fg = 'white')
        self.ConsolePad.grid(row = 2, column = 2, sticky=Tk.N+Tk.S)
        self.MAX_LOG_LINES = 50
        
        self.DrawFramework()
        self.ChangeDisplayedParams(0)

        self.Log("Ready !")
        self.MainWindow.mainloop()

    def _on_closing(self):
        if tkMessageBox.askokcancel("Quit", "Do you really want to quit?"):
            self.MainWindow.quit()
            self.MainWindow.destroy()

    def GenerateEmptyFramework(self):
        if self.Framework.Modules:
            if not tkMessageBox.askokcancel("New", "Unsaved framework. Erase anyway ?"):
                return None
        with tkFileDialog.asksaveasfile(mode='w', initialdir = PROJECTS_DIR, defaultextension='.json', title = "New project", filetypes=[("JSON","*.json")]) as file:
            if file is None:
                return None
            self.Framework = framework_abstractor.FrameworkAbstraction(LogFunction = self.Log)
            self.Framework.Data['name'] = file.name.split('/')[-1].split('.json')[0]

            self.SetDisplayedCodefile(self.CurrentCodeFile, SaveCurrentFile = False)
            self.FrameworkFileName = file.name
            self.MainWindow.title('Beaver - {0}'.format(self.Framework.Data['name']))

        self.DrawFramework()

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
        with tkFileDialog.asksaveasfile(mode='w', initialdir = PROJECTS_DIR, initialfile = self.Framework.Data['name'], defaultextension='.json', title = "Save as...", filetypes=[("JSON","*.json")]) as file:
            if not file is None:
                NewName =  file.name.split('/')[-1].split('.json')[0]
                if self.Framework.Data['name']:
                    if NewName != self.Framework.Data['name'] and tkMessageBox.askyesno("Name changed", "Do you want to change project name from \n{0} \nto {1} ?"):
                        self.Framework.Data['name'] = NewName
                        self.MainWindow.title('Beaver - {0}'.format(self.Framework.Data['name']))
                else:
                    self.Framework.Data['name'] = NewName
                    self.MainWindow.title('Beaver - {0}'.format(self.Framework.Data['name']))

                json.dump(self.Framework.Data, file)
                self.FrameworkFileName = file.name
                self.Log("Saved.")
        
    def open_command(self):
        with tkFileDialog.askopenfile(parent=self.MainWindow,mode='rb', initialdir = PROJECTS_DIR, title='Open...', defaultextension='.json', filetypes=[("JSON","*.json")]) as file:
            if file != None:
                Data = json.load(file)
                self.Framework = framework_abstractor.FrameworkAbstraction(Data, self.Log)
                self.FrameworkFileName = file.name
                self.MainWindow.title('Beaver - {0}'.format(self.Framework.Data['name']))

                self.TempFiles = {}
                self.CurrentParams = []
                self.DisplayedParams = []
                self.CurrentMinParamDisplayed = 0
                self.AvailablesModulesPositionsAndParents = [(np.array([0,0]), None)]
                self.SelectedAvailableModulePosition = 0
                self.DisplayedModulesPositions = {}

                self.UpdateCodeMenu()
                for Module in self.Framework.Modules:
                    self.AddModuleDisplay(Module, AutoDraw = False)
                self.ActiveModule = 0
                self.ChangeDisplayedParams(0)
                try:
                    self.SetDisplayedCodefile('Documentation', SaveCurrentFile = False)
                except:
                    self.SetDisplayedCodefile(self.Framework.Files.keys()[0], SaveCurrentFile = False)
        self.DrawFramework()

    def RegisterCurrentCodePad(self):
        if self.CurrentCodeFile in self.TempFiles.keys():
            return None
        CurrentText = self.CodePad.get('1.0', Tk.END+'-1c')
        self.Framework.Files[self.CurrentCodeFile]['data'] = CurrentText

    def AddModule(self, ModuleName):
        self.Log("Adding " + ModuleName)
        self.Framework.AddModule(self.AvailableModules[ModuleName], self.AvailablesModulesPositions[self.SelectedAvailableModulePosition][1])
        self.AddModuleDisplay(self.Framework.Modules[-1], AutoDraw = True)

    def AddModuleDisplay(self, Module, AutoDraw):
        self.DisplayedModulesPositions[Module['id']] = self.AvailablesModulesPositions[self.SelectedAvailableModulePosition][0]
        self.AvailablesModulesPositions.pop(self.SelectedAvailableModulePosition)
        self.AddAvailableSlots(self.DisplayedModulesPositions[Module['id']], Module['module'], Module['id'])
        if AutoDraw:
            self.ActiveModule = len(self.Framework.Modules)-1
            self.DrawFramework()
            self.ChangeDisplayedParams(0)

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
        if not self.ActiveModule is None:
            Module = self.Framework.Modules[self.ActiveModule]
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
        for FileName in self.Framework.Files.keys():
            Menu.add_command(label = FileName, command = partial(self.SetDisplayedCodefile, FileName))

    def SetDisplayedCodefile(self, Codefile, SaveCurrentFile = True):
        if SaveCurrentFile:
            self.RegisterCurrentCodePad()
        self.CodePad.delete('1.0', Tk.END)
        self.CurrentCodeFile = Codefile
        self.CodeFileVar.set(self.CurrentCodeFile)
        if self.CurrentCodeFile in self.Framework.Files.keys():
            self.CodePad.insert(Tk.END, self.Framework.Files[self.CurrentCodeFile]['data'])
            self.CurrentCodeType = self.Framework.Files[self.CurrentCodeFile]['type']
        else:
            self.CodePad.insert(Tk.END, self.TempFiles[self.CurrentCodeFile])
            self.CurrentCodeType = 'tmp' 

    def OnCodeModification(self):
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
        for Module in self.Framework.Modules:
            if self.Framework.WellDefinedModule(Module):
                color = 'g'
            else:
                color = 'r'
            self.DrawModule(self.DisplayedModulesPositions[Module['id']], Module['module']['name'], color)
            minValues = np.minimum(minValues, self.DisplayedModulesPositions[Module['id']] - self.ModulesDiameter)
            maxValues = np.maximum(maxValues, self.DisplayedModulesPositions[Module['id']] + self.ModulesDiameter)
        for nSlot, AvailableSlotAndParent in enumerate(self.AvailablesModulesPositions):
            if nSlot == self.SelectedAvailableModulePosition:
                alpha = 0.7
            else:
                alpha = 0.3
            self.DrawModule(AvailableSlotAndParent[0], '', 'grey', alpha)
            minValues = np.minimum(minValues, AvailableSlotAndParent[0] - self.ModulesDiameter)
            maxValues = np.maximum(maxValues, AvailableSlotAndParent[0] + self.ModulesDiameter)
        Center = (minValues + maxValues)/2.
        MaxAxis = (maxValues - minValues).max()
        minValues = Center - MaxAxis/2.
        maxValues = Center + MaxAxis/2.
        self.DisplayAx.set_xlim(minValues[0], maxValues[0])
        self.DisplayAx.set_ylim(minValues[1], maxValues[1])
        self.Display.canvas.show()
        #self.Log("Done.")
        
    def DrawModule(self, ModulePosition, ModuleName, color, alpha = 1):
        DXs = (self.ModulesDiameter/2 * np.array([np.array([-1, -1]), np.array([-1, 1]), np.array([1, 1]), np.array([1, -1])])).tolist()
        for nDX in range(len(DXs)):
            self.DisplayAx.plot([(ModulePosition + DXs[nDX])[0], (ModulePosition + DXs[(nDX+1)%4])[0]], [(ModulePosition + DXs[nDX])[1], (ModulePosition + DXs[(nDX+1)%4])[1]], color = color, alpha = alpha)
        TextPosition = ModulePosition + self.ModulesDiameter/2 * 0.8 * np.array([-1, -1])
        self.DisplayAx.text(TextPosition[0], TextPosition[1], s = ModuleName, color = color, alpha = alpha, fontsize = 8)
    
    def AddAvailableSlots(self, LastAddedPosition, AddedModule, ParentModuleID):
        NOutputs = framework_abstractor.CountEventsHandlers(AddedModule)
        if AddedModule['name'] != 'merge':
            NInputs = 3
        PossibleChildrenAdds = [(self.ModulesTilingDistance * np.array([dX, -1.])) for dX in (np.array(list(range(NOutputs))) - NOutputs/2. + 0.5).tolist()]
        for PossibleAdd in PossibleChildrenAdds:
            if self.DisplayedModulesPositions.values() and (abs(np.array(self.DisplayedModulesPositions.values()) - (LastAddedPosition + PossibleAdd)) < self.ModulesDiameter).all(axis = 1).any(axis = 0):
                continue
            self.AvailablesModulesPositions += [(LastAddedPosition + PossibleAdd, ParentModuleID)]
    
    def _OnParameterChange(self, StringVar):
        ParamIndex = self.CurrentParams.index(StringVar)
        self.Framework.Modules[self.ActiveModule]['parameters'][ParamIndex] = StringVar.get()
        self.DisplayedParams[ParamIndex][1]['foreground'] = self.GetParamDisplayColor(ParamIndex)

    def ChangeDisplayedParams(self, Mod):
        for Trio in self.DisplayedParams:
            for Field in Trio:
                Field.destroy()
        if not self.ActiveModule is None:
            ModuleParameters = self.Framework.Modules[self.ActiveModule]['module']['parameters']
            if Mod == 0:
                self.CurrentMinParamDisplayed = 0
            else:
                self.CurrentMinParamDisplayed = max(0, min(len(ModuleParameters) - self.NParamsDisplayed, self.CurrentMinParamDisplayed + Mod))
            self.DisplayedParams = []
            self.CurrentParams = []
            for NParam in range(self.CurrentMinParamDisplayed, min(len(ModuleParameters), self.CurrentMinParamDisplayed + self.NParamsDisplayed)):
                self.DisplayedParams += [[]]
                self.DisplayedParams[-1] += [Tk.Label(self.ParamsValuesFrame, text = ModuleParameters[NParam]['name'], width = 20, anchor = Tk.W)]
                self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=0, sticky = Tk.N)

                Color = self.GetParamDisplayColor(NParam)
                self.DisplayedParams[-1] += [Tk.Label(self.ParamsValuesFrame, text = ModuleParameters[NParam]['type'], width = 20, anchor = Tk.W, foreground = Color)]
                self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=1, sticky = Tk.N)

                self.CurrentParams += [Tk.StringVar(self.MainWindow)]
                self.CurrentParams[-1].trace("w", lambda name, index, mode, sv=self.CurrentParams[-1]: self._OnParameterChange(sv))
                self.DisplayedParams[-1] += [Tk.Entry(self.ParamsValuesFrame, textvariable = self.CurrentParams[-1], width = 40, bg = 'white')]
                self.DisplayedParams[-1][-1].grid(row=len(self.DisplayedParams)-1, column=2, sticky = Tk.N+Tk.E)
                if 'default' in ModuleParameters[NParam].keys():
                    self.CurrentParams[-1].set(ModuleParameters[NParam]['default'])

    def GetParamDisplayColor(self, NParam):
        ModuleParameters = self.Framework.Modules[self.ActiveModule]['module']['parameters']
        TypeCanBeenChecked, ValueWasChecked = framework_abstractor.CheckParameterValidity(ModuleParameters[NParam]['type'], self.Framework.Modules[self.ActiveModule]['parameters'][NParam])
        if not TypeCanBeenChecked:
            Color = 'black'
        else:
            if ValueWasChecked:
                Color = 'green'
            else:
                Color = 'red'
        return Color

def GenerateNewType(Type):
    if Type == 'Struct':
        File = 'struct {\n};'
    elif Type == 'Packed struct':
        File = 'SEPIA_PACK(struct {\n});'
    elif Type == 'Lambda Function':
        File = '[&]() {\n}'
    return File

G = GUI()
