from PyQt5.QtGui import QDoubleValidator, QValidator
from PyQt5.QtWidgets import QItemDelegate, QLineEdit
from lmfit.models import ExponentialGaussianModel, SkewedGaussianModel, SkewedVoigtModel, DoniachModel, \
    BreitWignerModel, LognormalModel
from lmfit.models import GaussianModel, LorentzianModel, VoigtModel, PseudoVoigtModel, ThermalDistributionModel, \
    PolynomialModel, StepModel
from lmfitxps.models import (ConvGaussianDoniachDublett, ConvGaussianDoniachSinglett, FermiEdgeModel)
from lmfitxps.lineshapes import singlett, fft_convolve
from PyQt5 import QtWidgets, QtCore
import numpy as np
import os
import traceback
import logging
import pandas as pd
import configparser
import webbrowser
config = configparser.ConfigParser()
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

class DoubleValidator(QDoubleValidator):
    """Subclass of QDoubleValidator that emits a signal if the input is not valid."""

    # Define a custom signal that will be emitted when the input is not valid.
    validationChanged = QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setNotation(QDoubleValidator.StandardNotation)
        self.setLocale(QtCore.QLocale(QtCore.QLocale.C))
    def validate(self, input_str, pos):
        state, input_str, pos = super().validate(input_str, pos)
        if input_str == "" and state == QValidator.Acceptable:
            state = QValidator.Intermediate
        validate_state = [state, input_str, pos]
        self.validationChanged.emit(validate_state)
        return state, input_str, pos


class TableItemDelegate(QItemDelegate):
    """Delegate class for QTableWidget cells that validates user input.

    This class creates a line edit widget as the editor for each cell in a
    QTableWidget. It adds a DoubleValidator to the line edit widget to ensure
    that the user input is a valid double (floating-point) value.

    Attributes:
        None

    Methods:
        createEditor(parent, option, index): Creates a line edit widget as the
            editor for the cell at the specified index. Returns the editor.

    """

    def createEditor(self, parent, option, index):
        """Create a line edit widget as the editor for the cell at the specified index.

        Args:
            parent (QWidget): The parent widget of the editor.
            option (QStyleOptionViewItem): The style options for the editor.
            index (QModelIndex): The model index of the cell being edited.

        Returns:
            editor (QLineEdit): The line edit widget used as the editor.

        """
        self.editor = DoubleLineEdit(parent)
        self.editor.setToolTip('Only double values are valid inputs!')
        validator = DoubleValidator()
        self.editor.setValidator(validator)
        validator.validationChanged.connect(self.onValidationChanged)
        return self.editor

    def onValidationChanged(self, validate_return):
        """Display a message box when the user enters an invalid input."""
        state = validate_return[0]
        if state == QValidator.Invalid:
            print('Value ' + validate_return[1] + " was entered. However, only double values are valid!")


class DoubleLineEdit(QLineEdit):
    """Custom QLineEdit widget that uses DoubleValidator to validate user input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.validator = DoubleValidator()
        self.setValidator(self.validator)
        self.validator.validationChanged.connect(self.onValidationChanged)

    def onValidationChanged(self, validate_return):
        """Display a message box when the user enters an invalid input."""
        state = validate_return[0]
        if state == QValidator.Invalid:
            print('Value ' + validate_return[1] + " was entered. However, only double values are valid!")


class SubWindow(QtWidgets.QWidget):
    def __init__(self, params_tab):
        super(SubWindow, self).__init__()
        self.layout = QtWidgets.QGridLayout(self)
        self.resize(800, 500)
        self.setWindowTitle("Limits")
        self.layout.addWidget(params_tab, 0, 0, 5, 4)


class LayoutHline(QtWidgets.QFrame):
    def __init__(self):
        super(LayoutHline, self).__init__()
        self.setFrameShape(self.HLine)
        self.setFrameShadow(self.Sunken)
class RemoveHeaderDialog(QtWidgets.QDialog):
    removeOptionChanged = QtCore.pyqtSignal(int, str)
    def __init__(self, header_label, header_texts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Header")
        self.setLayout(QtWidgets.QVBoxLayout())

        self.lineEdit = QLineEdit()
        self.lineEdit.setText(header_label)
        self.layout().addWidget(self.lineEdit)

        self.remove_combo = QtWidgets.QComboBox()
        self.remove_combo.addItem('--')
        self.remove_combo.addItem("Remove Last Column")
        for header in header_texts:
            self.remove_combo.addItem(header)
        self.layout().addWidget(self.remove_combo)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout().addWidget(button_box)

    def getHeaderText(self):
        return self.lineEdit.text()

    def getRemoveOption(self):
        return self.remove_combo.currentIndex(), self.remove_combo.currentText()

    def accept(self):
        remove_idx, remove_text = self.getRemoveOption()
        self.removeOptionChanged.emit(remove_idx,remove_text)
        super().accept()
class FitThread(QtCore.QThread):
    thread_started = QtCore.pyqtSignal()
    fitting_finished = QtCore.pyqtSignal(object)
    error_occurred = QtCore.pyqtSignal(str)
    def __init__(self, model=None, data=None, params=None, x=None,weights=None, y=None):
        super().__init__()
        self.fit_interrupted = False
        self.model = model
        self.data = data
        self.params = params
        self.x = x
        self.weights = weights
        self.y= y
        self.result=None

    def run(self):
        try:
            self.fit_interrupted = False
            self.thread_started.emit()
            self.result = self.model.fit(
                self.data,
                params=self.params,
                x=self.x,
                weights=self.weights,
                iter_cb=self.per_iteration,
                y=self.y
            )
            self.fitting_finished.emit(self.result)
        except Exception as e:
            error_message = f"Exception occurred in FitThread: {e}\n{traceback.format_exc()}"
            logging.error(error_message)
            self.error_occurred.emit(error_message)

    def per_iteration(self, pars, iteration, resid, *args, **kws):
        if self.fit_interrupted:
            return True
    def interrupt_fit(self):
        self.fit_interrupted = True

class RemoveAndEditTableWidget(QtWidgets.QTableWidget):
    headerTextChanged = QtCore.pyqtSignal(int, str)
    removeOptionChanged = QtCore.pyqtSignal(int, str)

    def __init__(self, rows, columns,editable_condition, parent=None):
        super().__init__(rows, columns, parent)
        # Enable editing of column headers
        self.horizontalHeader().sectionDoubleClicked.connect(self.editHeader)
        # Store the editable condition
        self.editable_condition = editable_condition
    def setHeaderTooltips(self):
        for logicalIndex in range(self.columnCount()):
            if self.editable_condition(logicalIndex):
                header_item = self.horizontalHeaderItem(logicalIndex)
                if header_item is not None:
                    header_item.setToolTip("Double-click to edit \n header text or remove column.")

    def editHeader(self, logicalIndex):
        if self.editable_condition(logicalIndex):
            header_label = self.horizontalHeaderItem(logicalIndex).text()
            header_texts = []
            for column in range(int(self.columnCount()+1/2)):
                header_item = self.horizontalHeaderItem(int(column*2+1))
                if header_item is not None:
                    header_texts.append(header_item.text())
            dialog = RemoveHeaderDialog(header_label,header_texts, self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                new_label = dialog.getHeaderText()
                remove_idx, remove_text = dialog.getRemoveOption()
                if new_label != header_label:
                    self.horizontalHeaderItem(logicalIndex).setText(new_label)
                    self.headerTextChanged.emit(logicalIndex, new_label)

                if remove_idx > 0:  # Only emit the signal if a valid removal option is selected
                    self.removeOptionChanged.emit(remove_idx, remove_text)
class EditHeaderDialog(QtWidgets.QDialog):
    def __init__(self, header_label, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Header")
        self.setLayout(QtWidgets.QVBoxLayout())

        self.lineEdit = QLineEdit()
        self.lineEdit.setText(header_label)
        self.layout().addWidget(self.lineEdit)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout().addWidget(button_box)

    def getHeaderText(self):
        return self.lineEdit.text()
class EditableHeaderTableWidget(QtWidgets.QTableWidget):
    headerTextChanged = QtCore.pyqtSignal(int, str)

    def __init__(self, rows, columns,editable_condition, parent=None):
        super().__init__(rows, columns, parent)
        # Enable editing of column headers
        self.horizontalHeader().sectionDoubleClicked.connect(self.editHeader)
        # Store the editable condition
        self.editable_condition = editable_condition
    def setHeaderTooltips(self):
        for logicalIndex in range(self.columnCount()):
            if self.editable_condition(logicalIndex):
                header_item = self.horizontalHeaderItem(logicalIndex)
                if header_item is not None:
                    header_item.setToolTip("Double-click to edit")

    def editHeader(self, logicalIndex):
        if self.editable_condition(logicalIndex):
            header_label = self.horizontalHeaderItem(logicalIndex).text()
            dialog = EditHeaderDialog(header_label, self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                new_label = dialog.getHeaderText()
                self.horizontalHeaderItem(logicalIndex).setText(new_label)
                self.headerTextChanged.emit(logicalIndex, new_label)


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
        with open (dirPath+'/../Databases/CrossSections/cross_sections.csv') as f:
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
# from numpy import amax, amin
# make x and y lists (arrays) in the range between xmin and xmax
import numpy as np


def fit_range(x, y, xmin, xmax):
    # print(xmin, xmax)
    if xmin > xmax:
        xmin0 = xmin
        xmin = xmax
        xmax = xmin0

    if x[0] < x[-1]:
        # XAS in photon energy scale or XPS in kinetic energy scale
        if x[0] < xmin or xmax < x[len(x) - 1]:
            if xmax < x[len(x) - 1]:
                for i in range(len(x) - 1, -1, -1):
                    if x[i] <= xmax:
                        rmidx = i
                        break
            else:
                rmidx = len(x) - 1

            if x[0] < xmin:
                for i in range(0, len(x) - 1):
                    if x[i] >= xmin:
                        lmidx = i
                        break
            else:
                lmidx = 0

            xn = x[lmidx:rmidx + 1].copy()
            yn = y[lmidx:rmidx + 1].copy()
        # print(len(x), len(xn), xn[0], xn[len(xn)-1])
        else:
            xn = x
            yn = y
    else:
        # XPS in binding energy scale
        if x[len(x) - 1] < xmin or xmax < x[0]:
            if xmax < x[0]:
                for i in range(0, len(x) - 1):
                    if x[i] <= xmax:
                        lmidx = i
                        break
            else:
                lmidx = 0

            if x[len(x) - 1] < xmin:
                for i in range(len(x) - 1, -1, -1):
                    if x[i] >= xmin:
                        rmidx = i
                        break
            else:
                rmidx = len(x) - 1

            xn = x[lmidx:rmidx + 1].copy()
            yn = y[lmidx:rmidx + 1].copy()
        # print(len(x), len(xn), xn[0], xn[len(xn)-1])
        else:
            xn = x
            yn = y

    # return [array(xn), array(yn)]
    return [xn, yn]

separator_mapping = {
    "Comma: [,]": ",",
    "Semicolon: [;]": ";",
    "Whitespace(s)/TAB": r'\s+',
    "User Defined": None  # Placeholder for user-defined separator
}
class PreviewDialog(QtWidgets.QDialog):
    settings_changed = QtCore.pyqtSignal(bool)
    def __init__(self, file_path, config, config_file_path):
        super().__init__()
        self.file_path = file_path
        self.fname= os.path.basename(file_path)
        self.selected_separator = r'\s+' if file_path.endswith('.txt') else ","
        self.selected_columns = []
        self.header_row = 0  # Row index where the header is located
        self.has_header=True
        self.data = None
        self.df=None
        self.available_columns = []
        self.config = config
        config.read(config_file_path)
        self.config_file_path= config_file_path
        self.is_accepted = False
        self.initUI()

    def read_config(self):
        self.selected_separator = self.config.get('Import', 'separator')
        for description, value in separator_mapping.items():
            if self.selected_separator == value:
                self.separator_combobox.setCurrentText(description)
                break
            else:
                self.separator_combobox.setCurrentText("User Defined")

        self.selected_columns = eval(self.config.get('Import', 'columns'))
        if len(self.selected_columns) == 2:
            self.column1_combobox.setCurrentIndex(self.selected_columns[0])
            self.column2_combobox.setCurrentIndex(self.selected_columns[1])

        self.header_row = int(self.config.get('Import', 'header_row'))
        self.header_row_spinbox.setValue(self.header_row)

        self.has_header = self.config.getboolean('Import', 'has_header')
        self.no_header_checkbox.setChecked(not self.has_header)


    def initUI(self):
        layout = QtWidgets.QVBoxLayout()
        self.message_label = QtWidgets.QLabel()
        self.load_data()

        self.table_widget = QtWidgets.QTableWidget()
        if self.data is not None:
            self.table_widget.setRowCount(self.data.shape[0])
            self.table_widget.setColumnCount(self.data.shape[1])
            self.table_widget.setHorizontalHeaderLabels(self.data.columns)

            for i in range(self.data.shape[0]):
                for j in range(self.data.shape[1]):
                    item = QtWidgets.QTableWidgetItem(str(self.data.iat[i, j]))
                    self.table_widget.setItem(i, j, item)

            self.table_widget.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
            self.table_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.table_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

            layout.addWidget(self.table_widget)

        if self.data is not None:
            separator_label = QtWidgets.QLabel("Choose Separator:")
            self.separator_combobox = QtWidgets.QComboBox()
            self.separator_combobox.addItems(["Comma: [,]", "Semicolon: [;]", "Whitespace(s)/TAB", "User Defined"])
            self.separator_combobox.setCurrentText(self.get_sep_text())
            self.separator_combobox.currentTextChanged.connect(self.update_preview)

            self.custom_separator_input = QtWidgets.QLineEdit()
            self.custom_separator_input.setPlaceholderText("Enter Custom Separator")

            layout.addWidget(separator_label)
            layout.addWidget(self.separator_combobox)
            layout.addWidget(self.custom_separator_input)

            self.column1_combobox = QtWidgets.QComboBox()
            self.column2_combobox = QtWidgets.QComboBox()

            layout.addWidget(QtWidgets.QLabel("Select Energy (x) column:"))
            layout.addWidget(self.column1_combobox)
            layout.addWidget(QtWidgets.QLabel("Select intensity (y) column:"))
            layout.addWidget(self.column2_combobox)


            self.header_row_spinbox = QtWidgets.QSpinBox()
            self.header_row_spinbox.setRange(0, 10)
            self.header_row_spinbox.setValue(self.header_row)
            self.header_row_spinbox.valueChanged.connect(self.update_preview)
            layout.addWidget(QtWidgets.QLabel("Row index where the header is located \n (assuming, that data follows after header row)/rows to skip:"))
            layout.addWidget(self.header_row_spinbox)
            self.no_header_checkbox = QtWidgets.QCheckBox("File has no column headers")
            layout.addWidget(self.no_header_checkbox)
            self.no_header_checkbox.stateChanged.connect(self.update_preview)

            self.remember_settings_checkbox = QtWidgets.QCheckBox("Remember Settings")
            self.remember_settings_checkbox.stateChanged.connect(self.emit_settings_changed)
            layout.addWidget(self.remember_settings_checkbox)
            self.read_config()
            self.update_column_comboboxes()

        layout.addWidget(self.message_label)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_inputs)
        button_box.rejected.connect(self.reject_dialog)

        layout.addWidget(button_box)
        self.setLayout(layout)
        self.setWindowTitle("Preview and Load Data")

    def emit_settings_changed(self, state):
        if state == QtCore.Qt.Checked:
            self.settings_changed.emit(True)
        else:
            self.settings_changed.emit(False)

    def get_sep_text(self):
        for key, val in separator_mapping.items():
            if val == self.selected_separator:
                return key
        return None

    def load_data(self):
        try:
            if self.has_header:
                self.data = pd.read_csv(self.file_path, delimiter=self.selected_separator, header=self.header_row, engine='python',nrows=0,  on_bad_lines='skip')
                if self.data.columns.values.tolist()[0] == '#':
                    self.data = pd.read_csv(self.file_path, delimiter=self.selected_separator, engine="python",
                                        names=self.data.columns.values.tolist()[1:], skiprows=self.header_row+1,  on_bad_lines='skip')
                else:
                    self.data = pd.read_csv(self.file_path, delimiter=self.selected_separator, engine="python", skiprows=self.header_row,  on_bad_lines='skip')
            else:
                self.data = pd.read_csv(self.file_path, delimiter=self.selected_separator, engine="python", skiprows=self.header_row, header=None,  on_bad_lines='skip')
                self.data.columns = [f"col{i+1}" for i in range(len(self.data.columns))]
            self.available_columns=self.data.columns
            if not self.selected_columns:
                self.selected_columns = list(range(len(self.data.columns)))
            self.data = self.data.iloc[:, self.selected_columns]
            self.message_label.setText("Data loaded successfully.")
        except Exception as e:
            self.data = None
            self.message_label.setText(f"Failed to load data: {e}\nPlease try with different parameters.")


    def get_separator(self):
        sep = self.separator_combobox.currentText()
        return separator_mapping[sep]

    def update_preview(self):
        selected_separator = self.get_separator()
        if selected_separator == "User Defined":
            custom_separator = self.custom_separator_input.text()
            self.selected_separator = custom_separator
        else:
            self.selected_separator = selected_separator
        if self.column1_combobox.currentIndex() == self.column2_combobox.currentIndex():
            self.message_label.setText("Please select different columns for Energy (x) and Intensity (y).")
            return
        self.selected_columns = [self.column1_combobox.currentIndex(), self.column2_combobox.currentIndex()]
        self.has_header = not self.no_header_checkbox.isChecked()
        self.header_row = self.header_row_spinbox.value()
        self.load_data()
        self.update_column_comboboxes()
        if self.data is not None:
            self.table_widget.clear()
            self.table_widget.setRowCount(self.data.shape[0])
            self.table_widget.setColumnCount(self.data.shape[1])
            self.table_widget.setHorizontalHeaderLabels(self.data.columns)

            for i in range(self.data.shape[0]):
                for j in range(self.data.shape[1]):
                    item = QtWidgets.QTableWidgetItem(str(self.data.iat[i, j]))
                    self.table_widget.setItem(i, j, item)

    def accept_inputs(self):
        if self.data is not None:
            self.update_preview()
            if self.data.columns.size==2:
                self.df=self.data
                if self.remember_settings_checkbox.isChecked():
                    self.config.set('Import', 'separator', self.selected_separator)
                    self.config.set('Import', 'columns', str(self.selected_columns))
                    self.config.set('Import', 'header_row', str(self.header_row))
                    self.config.set('Import', 'has_header', str(self.has_header))
                    self.config.set('Import', 'remember_settings', str(self.remember_settings_checkbox.isChecked()))
                    with open(self.config_file_path, 'w') as configfile:
                        self.config.write(configfile)
                self.is_accepted = True
                self.accept()
            else:
                self.message_label.setText("Data not in correct format. Please select exactly 2 columns.")
        else:
            self.message_label.setText("Data not in correct format. Please select correct separator and columns.")

    def get_is_accepted(self):
        return self.is_accepted
    def reject_dialog(self):
        self.is_accepted = False
        self.reject()
    def get_options(self):
        if self.data is None:
            return None, None

        return self.selected_separator, self.selected_columns

    def update_column_comboboxes(self):
        if self.data is not None:
            self.column1_combobox.blockSignals(True)  # Block signal emission
            self.column2_combobox.blockSignals(True)  # Block signal emission

            self.column1_combobox.clear()
            self.column2_combobox.clear()
            self.column1_combobox.addItems(self.available_columns)
            self.column2_combobox.addItems(self.available_columns)
            self.column1_combobox.setCurrentText(self.available_columns.values.tolist()[self.selected_columns[0]])
            self.column2_combobox.setCurrentText(self.available_columns.values.tolist()[self.selected_columns[1]])

            self.column1_combobox.blockSignals(False)  # Unblock signal emission
            self.column2_combobox.blockSignals(False)  # Unblock signal emission

            self.column1_combobox.currentTextChanged.connect(self.update_preview)
            self.column2_combobox.currentTextChanged.connect(self.update_preview)


class DataSet():
    def __init__(self, df, filepath, pe):
        self.df = df
        self.filepath = filepath
        self.filename= os.path.basename(filepath)
        self.pe = pe


def createMenuBar(parent):
    """Create a reusable menu bar and return it."""
    menubar = parent.menuBar()

    # File Menu
    # File Menu
    fileMenu = menubar.addMenu('&File')

    # Import Submenu
    importSubmenu = fileMenu.addMenu('&Import')
    actions_import = [
        ('Import &csv', 'Ctrl+Shift+X', lambda: parent.clickOnBtnImp(idx=1)),
        ('Import &txt', 'Ctrl+Shift+Y', lambda: parent.clickOnBtnImp(idx=2)),
        ('Import &vms', 'Ctrl+Shift+V', lambda: parent.clickOnBtnImp(idx=3)),
        ('Open directory (.txt and .csv)', 'Ctrl+Shift+D', lambda: parent.clickOnBtnImp(idx=4)),
        ('Open directory (only .csv)', 'Ctrl+Shift+C', lambda: parent.clickOnBtnImp(idx=5)),
        ('Open directory (only .txt)', 'Ctrl+Shift+T', lambda: parent.clickOnBtnImp(idx=6))
    ]

    for name, shortcut, func in actions_import:
        action = QtWidgets.QAction(name, parent)
        action.setShortcut(shortcut)
        action.triggered.connect(func)
        importSubmenu.addAction(action)

    # Export Submenu
    exportSubmenu = fileMenu.addMenu('&Export')
    actions_export = [
        ('&Results', 'Ctrl+Shift+R', parent.exportResults),
        ('Re&sults + Data', 'Ctrl+Shift+A', parent.export_all)
    ]

    for name, shortcut, func in actions_export:
        action = QtWidgets.QAction(name, parent)
        action.setShortcut(shortcut)
        action.triggered.connect(func)
        exportSubmenu.addAction(action)

    # Exit Application Action
    exitAction = QtWidgets.QAction('E&xit', parent)
    exitAction.setShortcut('Ctrl+Q')
    exitAction.setStatusTip('Exit application')
    exitAction.triggered.connect(QtWidgets.qApp.quit)

    fileMenu.addSeparator()
    fileMenu.addAction(exitAction)

    # Preset Menu
    presetMenu = menubar.addMenu('&Preset')

    actions_preset = [
        ('&New', 'Ctrl+Shift+N', lambda: parent.clickOnBtnPreset(idx=1)),
        ('&Load', 'Ctrl+Shift+L', lambda: parent.clickOnBtnPreset(idx=2)),
        ('&Append', 'Ctrl+Shift+A', lambda: parent.clickOnBtnPreset(idx=3)),
        ('&Save', None, lambda: parent.clickOnBtnPreset(idx=4)),
        ('&C1s', None, lambda: parent.clickOnBtnPreset(idx=5)),
        ('C &K edge', None, lambda: parent.clickOnBtnPreset(idx=6)),
        ('Periodic &Table', None, lambda: parent.clickOnBtnPreset(idx=7))
    ]

    for name, shortcut, func in actions_preset:
        action = QtWidgets.QAction(name, parent)

        if shortcut:
            action.setShortcut(shortcut)  # Add shortcuts only if defined

        action.triggered.connect(func)
        presetMenu.addAction(action)

    # Background Menu
    bgMenu = menubar.addMenu('&Choose BG')

    # Define actions for background menu
    bg_actions = [
        ('&Active &Shirley BG', None, parent.clickOnBtnBG, True),
        ('&Static &Shirley BG', None, parent.clickOnBtnBG, True),
        ('&Active &Tougaard BG', None, parent.clickOnBtnBG, True),
        ('&Static &Tougaard BG', None, parent.clickOnBtnBG, True),
        ('&Polynomial BG', 'Ctrl+Alt+P', parent.clickOnBtnBG, True),
        ('&Slope BG', 'Ctrl+Alt+S', parent.clickOnBtnBG, True),
        ('&Arctan BG', None, parent.clickOnBtnBG, True),
        ('&Erf BG', None, parent.clickOnBtnBG, True),
        ('&VBM/Cutoff BG', None, parent.clickOnBtnBG, True)
    ]

    # Add actions to background menu
    for name, shortcut, func, checkable in bg_actions:
        action = QtWidgets.QAction(name, parent)
        if shortcut:
            action.setShortcut(shortcut)
        action.setCheckable(checkable)
        action.triggered.connect(func)
        bgMenu.addAction(action)

    # Tougaard Cross Section Action
    btn_tougaard_cross_section = QtWidgets.QAction('Tougaard &Cross Section ', parent)
    btn_tougaard_cross_section.triggered.connect(parent.clicked_cross_section)

    bgMenu.addSeparator()
    bgMenu.addAction(btn_tougaard_cross_section)

    # Settings Menu
    settings_menu = menubar.addMenu('&Settings')

    btn_settings = QtWidgets.QAction('&Open Settings', parent)
    btn_settings.triggered.connect(parent.open_settings_window)

    settings_menu.addAction(btn_settings)

    # Help/Info Menu
    links_menu = menubar.addMenu('&Help/Info')

    github_link = QtWidgets.QAction('See on &Github', parent)
    github_link.triggered.connect(lambda: webbrowser.open('https://github.com/Julian-Hochhaus/LG4X-V2'))

    about_link = QtWidgets.QAction('&How to cite?', parent)
    about_link.triggered.connect(parent.show_citation_dialog)

    links_menu.addAction(github_link)
    links_menu.addAction(about_link)

