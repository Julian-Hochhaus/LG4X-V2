from lmfit.models import ExponentialGaussianModel, SkewedGaussianModel, SkewedVoigtModel, DoniachModel, \
    BreitWignerModel, LognormalModel
from lmfit.models import GaussianModel, LorentzianModel, VoigtModel, PseudoVoigtModel, ThermalDistributionModel, \
    PolynomialModel, StepModel
from usrmodel import ConvGaussianDoniachDublett, ConvGaussianDoniachSinglett, FermiEdgeModel, singlett, fft_convolve
from PyQt5 import QtWidgets, QtCore
import numpy as np
import os
import numpy as np

def autoscale_y(ax, margin=0.1):
    """Rescales the y-axis based on the visible data given the current xlim of the axis.

    Args:
        ax (matplotlib.axes.Axes): The axes object to autoscale.
        margin (float, optional): The fraction of the total height of the y-data to pad the upper ylims. Default is 0.1.

    Returns:
        None.
    """

    def get_bottom_top(line):
        """Helper function to get the minimum and maximum y-values for a given line.

        Args:
            line (matplotlib.lines.Line2D): The line object to get the y-data from.

        Returns:
            tuple: A tuple containing the minimum and maximum y-values.
        """
        xd = line.get_xdata()
        yd = line.get_ydata()
        lo, hi = ax.get_xlim()
        if not np.max(yd) == np.min(yd):
            if lo<hi:
                y_displayed = yd[((xd > lo) & (xd < hi))]
            else:
                y_displayed= yd[((xd < lo) & (xd > hi))]
            h = np.max(y_displayed) - np.min(y_displayed)
            if np.min(y_displayed) - 2 * margin * h > 0:
                bot = np.min(y_displayed) - 2 * margin * h
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

def model_selector(index: int, strind: str, index_pk: int):
    """
    Returns a model based on the index parameter.

    Args:
        index (int): An integer index to select the model.
        prefix (str): A string prefix to identify the model.
        index_pk (int): An integer index to identify the peak.

    Returns:
        Model: A model selected based on the index parameter.
    """
    model_options = {
        0: GaussianModel(prefix=strind + str(index_pk + 1) + '_'),
        1: LorentzianModel(prefix=strind + str(index_pk + 1) + '_'),
        2: VoigtModel(prefix=strind + str(index_pk + 1) + '_'),
        3: PseudoVoigtModel(prefix=strind + str(index_pk + 1) + '_'),
        4: ExponentialGaussianModel(prefix=strind + str(index_pk + 1) + '_'),
        5: SkewedGaussianModel(prefix=strind + str(index_pk + 1) + '_'),
        6: SkewedVoigtModel(prefix=strind + str(index_pk + 1) + '_'),
        7: BreitWignerModel(prefix=strind + str(index_pk + 1) + '_'),
        8: LognormalModel(prefix=strind + str(index_pk + 1) + '_'),
        9: DoniachModel(prefix=strind + str(index_pk + 1) + '_'),
        10: ConvGaussianDoniachDublett(prefix=strind + str(index_pk + 1) + '_'),
        11: ConvGaussianDoniachSinglett(prefix=strind + str(index_pk + 1) + '_'),
        12: FermiEdgeModel(prefix=strind + str(index_pk + 1) + '_')
    }

    selected_model = model_options.get(index)

    if selected_model is not None:
        return selected_model
    else:
        raise ValueError(f"No model found for index {index}.")


class Window_CrossSection(QtWidgets.QWidget):
    """
      A class to create a widget for cross-section calculations.

      Attributes:
          dataset_cross_sections (list): a list of cross-section data.
          tougaard_params (list): a list of default Tougaard parameters.

      """

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
        btn_add.clicked.connect(self.add_cross_section)
        layout_bottom.addWidget(btn_add)
        self.btn_cc = QtWidgets.QPushButton('Use current cross-section', self)
        self.btn_cc.resize(self.btn_cc.sizeHint())
        #self.btn_cc.clicked.connect(self.pushToMain)
        layout_bottom.addWidget(self.btn_cc)
        self.layout.addLayout(layout_top)
        self.layout.addLayout(layout_bottom)
    def load_elements(self):
        """
        Loads the elements from a CSV file and updates the dataset_cross_sections list.

        Args:
            None.

        Returns:
            list: A list of elements loaded from the CSV file.

        """
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
    def add_cross_section(self):
        """
        Adds a new cross section to the CSV file and updates the list of elements.

        Args:
            None.

        Returns:
            None.

        """
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
        """
          Sets the selected element's parameters in the Tougaard table.
        """

        idx=self.elements.currentIndex()
        for j in range(6):
            if j<4:
             self.tougaard_params[j]=self.dataset_cross_sections[idx][j+2]
            item = QtWidgets.QTableWidgetItem(str(self.dataset_cross_sections[idx][j]))
            self.tougaard_tab.setItem(0,j, item)
        self.tougaard_tab.resizeColumnsToContents()
        self.tougaard_tab.resizeRowsToContents()

class Element:
    """
    Represents an element with its corresponding Tougaard parameters.

    Args:
        name (str): The name of the element. Default is 'standard value'.
        atomic_number (int): The atomic number of the element. Default is 0.
        tb (int): The value of the Tougaard parameter B for the element. Default is 2866.
        tc (int): The value of the Tougaard parameter C for the element. Default is 1643.
        tcd (int): The value of the Tougaard parameter C* for the element. Default is 1.
        td (int): The value of the Tougaard parameter D for the element. Default is 1.
    """
    def __init__(self, name=None, atomic_number=None, tb=None, tc=None, tcd=None, td=None):
        self.name = name if name is not None else 'standard value'
        self.atomic_number = atomic_number if atomic_number is not None else 0
        self.tb = tb if tb is not None else 2866
        self.tc = tc if tc is not None else 1643
        self.tcd = tcd if tcd is not None else 1
        self.td = td if td is not None else 1
        self.tougaard_params = [self.atomic_number, self.tb, self.tc, self.tcd, self.td]
def cross_section():
    window_cross_section = Window_CrossSection()
    window_cross_section.show()
