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
matplotlib.use("TkAgg")

import tarsier_scrapper
import sepia_scrapper
import framework_abstractor

PROJECTS_DIR = 'Projects/'
def about_command():
    label = tkMessageBox.showinfo("About", "Tarsier code geneerator\nWork In Progress, be kind\nPlease visit https://github.com/neuromorphic-paris/")
        
class GUI:
    def __init__(self):
        self.Framework = framework_abstractor.FrameworkAbstraction()

        TarsierModules = tarsier_scrapper.ScrapTarsierFolder()
        SepiaModules, SepiaTypes = sepia_scrapper.ScrapSepiaFile()

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
        tarsiermenu = Tk.Menu(insertmenu)
        insertmenu.add_cascade(label = "Tarsier", menu = tarsiermenu)
        for Module in TarsierModules.keys():
            tarsiermenu.add_command(label=Module, command=lambda : self.AddModule(Module))
        sepiamenu = Tk.Menu(insertmenu)
        insertmenu.add_cascade(label = "Sepia", menu = sepiamenu)
        for Module in SepiaModules.keys():
            sepiamenu.add_command(label=Module, command=lambda : self.AddModule(Module))
        sepiamenu.add_separator()
        for Type in SepiaTypes.keys():
            sepiamenu.add_command(label=Type, command=lambda : self.SetType(Type))


        helpmenu = Tk.Menu(MainMenu)
        MainMenu.add_cascade(label="Help", menu=helpmenu)
        helpmenu.add_command(label="About...", command=about_command)


        self.Display = Figure(figsize=(5,5), dpi=150)
        self.DisplayAx = self.Display.add_subplot(111)
        self.DisplayAx.tick_params('both', bottom = 'off', left = 'off', labelbottom = 'off', labelleft = 'off')
        self.Display.tight_layout()
        
        self.DisplayCanvas = FigureCanvasTkAgg(self.Display, self.MainWindow)
        self.DisplayCanvas.show()
        self.DisplayCanvas.get_tk_widget().grid(row = 0, column = 0)
        
        self.CodeGenerationButton = Tk.Button(self.MainWindow, text = '>', command = self.GenerateCode, font = tkFont.Font(size = 20))
        self.CodeGenerationButton.grid(row = 0, column = 1)

        self.CodeFrame = Tk.Frame(self.MainWindow)
        self.CodeFrame.grid(row = 0, column = 2)
        self.CodeCurrentFile = self.Framework.Files.keys()[0]
        self.CodeFileVar = Tk.StringVar(self.MainWindow)
        self.CodeFileVar.set(self.CodeCurrentFile)
        self.CodeFileMenu = Tk.OptionMenu(self.CodeFrame, self.CodeFileVar, *self.Framework.Files)
        self.CodeFileMenu.grid(row = 0, column = 0)
        self.CodePad = ScrolledText.ScrolledText(self.CodeFrame, width=100, height=60, bg = 'white')
        self.CodePad.grid(row = 1, column = 0)
        
        self.CompilationFrame = Tk.Frame(self.MainWindow)
        self.CompilationFrame.grid(row = 1, column = 2)
        self.Premake4Button = Tk.Button(self.CompilationFrame, text = 'Premake4', command = self.GenerateCode, font = tkFont.Font(size = 15))
        self.Premake4Button.grid(row = 0, column = 0)
        self.CompileButton = Tk.Button(self.CompilationFrame, text = 'Compile', command = self.GenerateCode, font = tkFont.Font(size = 15))
        self.CompileButton.grid(row = 0, column = 1)

        self.ConsolePad = ScrolledText.ScrolledText(self.MainWindow, width=100, height=10, bg = 'black', fg = 'white')
        self.ConsolePad.grid(row = 2, column = 2)
        
#        self.ConsoleFrame = Tk.Frame(self.MainWindow, width=700, height=400)
#        self.ConsoleFrame.grid(row = 1, column = 2)
#        wid = self.ConsoleFrame.winfo_id()
#        os.system('xterm -into %d -geometry 200x20 -sb &' % wid)

        self.MainWindow.mainloop()

    def _on_closing(self):
        if tkMessageBox.askokcancel("Quit", "Do you really want to quit?"):
            self.MainWindow.quit()
            self.MainWindow.destroy()

    def GenerateEmptyFramework(self):
        if self.Framework.Modules:
            if not tkMessageBox.askokcancel("New", "Unsaved framework. Erase anyway ?"):
                return None
        file = tkFileDialog.asksaveasfile(mode='w', initialdir = PROJECTS_DIR, defaultextension='.json', title = "New project", filetypes=[("JSON","*.json")])
        if file is None:
            return None
        self.Framework = framework_abstractor.FrameworkAbstraction()
        self.Framework.Name = file.name
        self.MainWindow.title('Beaver - {0}'.format(file.name))
        self.CodePad.delete('1.0', Tk.END)
        self.CodePad.insert(Tk.END, self.Framework.Files[self.CodeCurrentFile])

        self.DisplayUpdate()

    def save_command(self):
        None

    def saveas_command(self):
        file = tkFileDialog.asksaveasfile(mode='w')
        if not file is None:
            # slice off the last character from get, as an extra return is added
            data = self.CodePad.get('1.0', Tk.END+'-1c')
            file.write(data)
            file.close()
        
    def open_command(self):
        file = tkFileDialog.askopenfile(parent=self.MainWindow,mode='rb',title='Select a file')
        if file != None:
            contents = file.read()
            self.CodePad.delete('1.0', Tk.END)
            self.CodePad.insert('1.0',contents)
            file.close()

    def AddModule(self, Module):
        print "Adding " + Module

    def SetType(self, Type):
        None

    def GenerateCode(self):
        None

    def DisplayUpdate(self):
        None

G = GUI()
