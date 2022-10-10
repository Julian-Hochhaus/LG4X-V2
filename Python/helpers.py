from lmfit.models import ExponentialGaussianModel, SkewedGaussianModel, SkewedVoigtModel, DoniachModel, \
    BreitWignerModel, LognormalModel
from lmfit.models import GaussianModel, LorentzianModel, VoigtModel, PseudoVoigtModel, ThermalDistributionModel, \
    PolynomialModel, StepModel
from usrmodel import ConvGaussianDoniachDublett, ConvGaussianDoniachSinglett, FermiEdgeModel, singlett, fft_convolve
from PyQt5 import QtWidgets, QtCore
import numpy as np
import os
def autoscale_y(ax, margin=0.1):
    """This function rescales the y-axis based on the data that is visible given the current xlim of the axis.
    ax -- a matplotlib axes object
    margin -- the fraction of the total height of the y-data to pad the upper ylims"""

    import numpy as np

    def get_bottom_top(line):
        xd = line.get_xdata()
        yd = line.get_ydata()
        lo, hi = ax.get_xlim()
        if not np.max(yd) == np.min(yd):
            print(yd)
            print(xd)
            print(lo,hi)
            if lo<hi:
                y_displayed = yd[((xd > lo) & (xd < hi))]
            else:
                y_displayed= yd[((xd < lo) & (xd > hi))]
            h = np.max(y_displayed) - np.min(y_displayed)
            if np.min(y_displayed) - 2 * margin * (np.max(y_displayed) - np.min(y_displayed)) > 0:
                bot = np.min(y_displayed) - 2 * margin * (np.max(y_displayed) - np.min(y_displayed))
            else:
                bot = 0
            top = np.max(y_displayed) + margin * h
        else:
            bot, top = np.min(yd), np.max(yd)
        return bot, top

    lines = ax.get_lines()
    bot, top = np.inf, -np.inf

    for line in lines:
        new_bot, new_top = get_bottom_top(line)
        if new_bot < bot:
            bot = new_bot
        if new_top > top:
            top = new_top

    ax.set_ylim(bot, top)



def modelSelector(index, strind, index_pk):
    if index == 0:
        pk_mod = GaussianModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 1:
        pk_mod = LorentzianModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 2:
        pk_mod = VoigtModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 3:
        pk_mod = PseudoVoigtModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 4:
        pk_mod = ExponentialGaussianModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 5:
        pk_mod = SkewedGaussianModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 6:
        pk_mod = SkewedVoigtModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 7:
        pk_mod = BreitWignerModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 8:
        pk_mod = LognormalModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 9:
        pk_mod = DoniachModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 10:
        pk_mod = ConvGaussianDoniachDublett(prefix=strind + str(index_pk + 1) + '_')
    if index == 11:
        pk_mod = ConvGaussianDoniachSinglett(prefix=strind + str(index_pk + 1) + '_')
    if index == 12:
        pk_mod = FermiEdgeModel(prefix=strind + str(index_pk + 1) + '_')

    return pk_mod

class Window_CrossSection(QtWidgets.QWidget):
    dataset_cross_sections=[]
    tougaard_params=['standard value', 0,2886,1643,1,1]
    def __init__(self):
        super(Window_CrossSection, self).__init__()
        self.layout = QtWidgets.QVBoxLayout(self)
        #self.resize(800, 500)
        self.setWindowTitle("Cross Section")
        self.resize(400,120)
        list_col=['name', 'atomic_number','B', 'C', 'C*', 'D']
        list_row = ['']
        layout_top=QtWidgets.QHBoxLayout()
        self.elements=QtWidgets.QComboBox()

        self.list_elements=self.load_elements()
        self.elements.addItems((self.list_elements))
        self.elements.currentIndexChanged.connect(self.choosenElement)
        #btn_add.clicked.connect(self.save)
        self.tougaard_tab = QtWidgets.QTableWidget(len(list_row), len(list_col))
        self.tougaard_tab.setHorizontalHeaderLabels(list_col)
        self.tougaard_tab.setVerticalHeaderLabels(list_row)
        #init_vals
        init_vals=['standard value', 0,2886,1643,1,1]
        for i in range(6):
            item = QtWidgets.QTableWidgetItem(str(init_vals[i]))
            self.tougaard_tab.setItem(0, i, item)
        self.tougaard_tab.resizeColumnsToContents()
        self.tougaard_tab.resizeRowsToContents()
        layout_top.addWidget(self.elements)
        layout_top.addWidget(self.tougaard_tab)


        layout_bottom=QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton('Add cross section', self)
        btn_add.resize(btn_add.sizeHint())
        btn_add.clicked.connect(self.addCrossSection)
        layout_bottom.addWidget(btn_add)
        #btn_load = QtWidgets.QPushButton('Load cross section', self)
        #btn_load.resize(btn_load.sizeHint())
        #btn_load.clicked.connect(self.addCrossSection)
        self.btn_cc = QtWidgets.QPushButton('Use current cross-section', self)
        self.btn_cc.resize(self.btn_cc.sizeHint())
        #self.btn_cc.clicked.connect(self.pushToMain)
        layout_bottom.addWidget(self.btn_cc)
        self.layout.addLayout(layout_top)
        self.layout.addLayout(layout_bottom)
    def load_elements(self):
        dirPath = os.path.dirname(os.path.abspath(__file__))
        temp_elements=[]
        with open (dirPath+'/../CrossSections/cross_sections.csv') as f:
            next(f)
            lines=f.read().splitlines()
            for line in lines:
                temp_elements.append(line.split(',')[0])
                temp=[elem for elem in line.split(',')]
                if temp not in self.dataset_cross_sections:
                    self.dataset_cross_sections.append(temp)
        return(temp_elements)
    def addCrossSection(self):
        dirPath = os.path.dirname(os.path.abspath(__file__))
        temp_elements = []
        for i in range(self.tougaard_tab.columnCount()):
            temp_elements.append(self.tougaard_tab.item(0,i).text())
        if not temp_elements[0] in self.list_elements:
            str_temp_elements=''
            for i in range(len(temp_elements)-1):
                str_temp_elements+=str(temp_elements[i]+', ')
            str_temp_elements+= str(temp_elements[-1]+'\n')
            with open(dirPath + '/../CrossSections/cross_sections.csv', 'a') as f:
                f.write(str_temp_elements)
            self.list_elements = self.load_elements()
            self.elements.clear()
            self.elements.addItems((self.list_elements))
        else:
            print(temp_elements[0]+ ' is already part of the database, please choose a different name!')

    def choosenElement(self):
        idx=self.elements.currentIndex()
        for j in range(6):
            if j<4:
             self.tougaard_params[j]=self.dataset_cross_sections[idx][j+2]
            item = QtWidgets.QTableWidgetItem(str(self.dataset_cross_sections[idx][j]))
            self.tougaard_tab.setItem(0,j, item)
        self.tougaard_tab.resizeColumnsToContents()
        self.tougaard_tab.resizeRowsToContents()

class Element:
    def __init__(self, name,atomic_number, tb, tc, tcd, td):
        self.name = name if name is not None else 'standard value'
        self.atomic_number = atomic_number if atomic_number is not None else 0
        self.tb = tb if tb is not None else 2866
        self.tc = tc if tc is not None else 1643
        self.tcd = tcd if tcd is not None else 1
        self.td = td if td is not None else 1
        self.tougaard_params = [self.atomic_number,self.tb, self.tc, self.tcd, self.td]
def cross_section():
    window_cross_section = Window_CrossSection()
    window_cross_section.show()
