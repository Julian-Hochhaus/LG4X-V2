# LG4X: lmfit gui for xps curve fitting, Copyright (C) 2021, Hideki NAKAJIMA, Synchrotron Light Research Institute,
# Thailand modified by Julian Hochhaus, TU Dortmund University.

import ast
import math
import sys
import pickle
import webbrowser
import matplotlib.pyplot as plt
import pandas as pd
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import QItemDelegate, QLineEdit
from PyQt5.QtGui import QDoubleValidator
from usrmodel import TougaardBG, ShirleyBG, SlopeBG
from lmfit import Model
from matplotlib import style
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.widgets import RectangleSelector

import vamas_export as vpy
import xpspy as xpy
from periodictable import PeriodicTable
from scipy import integrate
from helpers import *
import threading

import traceback  # error handling
import logging  # error handling

# style.use('ggplot')
style.use('seaborn-v0_8-colorblind')
dictBG = {
    '0': 'static Shirley BG',
    '100': 'active Shirley BG ',
    '1': 'static Tougaard BG',
    '101': 'active Tougaard BG',
    '2': 'Polynomial BG',
    '3': 'arctan',
    '4': 'Error function',
    '5': 'CutOff',
    '6': 'Slope BG',

}


class PrettyWidget(QtWidgets.QMainWindow):
    def __init__(self):
        super(PrettyWidget, self).__init__()
        # super(PrettyWidget, self).__init__()
        self.rows_lightened = 1
        self.export_out = None
        self.export_pars = None
        self.pre = [[], [], [], []]
        self.results = []
        self.res_label = None
        self.pars_label = None
        self.stats_label = None
        self.list_shape = None
        self.list_vamas = None
        self.parText = None
        self.res_tab = None
        self.fitp0 = None
        self.addition = None
        self.comboBox_file = None
        self.list_file = None
        self.toolbar = None
        self.list_component = None
        self.stats_tab = None
        self.fitp1 = None
        self.result = None
        self.canvas = None
        self.figure = None
        self.df = None
        self.filePath = None
        self.pt = None
        self.floating = None
        self.version = None
        self.parameter_history_list = []
        self.go_back_in_parameter_history = False
        self.event_stop = threading.Event()
        self.error_dialog = QtWidgets.QErrorMessage()
        self.displayChoosenBG = QtWidgets.QLabel()
        self.delegate = TableItemDelegate()
        self.initUI()

    def initUI(self):
        self.version = 'LG4X: LMFit GUI for XPS curve fitting v2.0.4'
        self.floating = '.4f'
        self.setGeometry(700, 500, 1600, 900)
        self.center()
        self.setWindowTitle(self.version)
        self.statusBar().showMessage(
            'Copyright (C) 2022, Julian Hochhaus, TU Dortmund University')
        self.pt = PeriodicTable()
        self.pt.setWindowTitle('Periodic Table')
        # data template
        # self.df = pd.DataFrame()
        self.df = []
        self.result = pd.DataFrame()
        outer_layout = QtWidgets.QVBoxLayout()

        self.idx_imp = 0

        self.idx_bg = [2]

        self.idx_pres = 0
        self.addition = 0
        # Menu bar
        menubar = self.menuBar()
        ## Import sub menue
        fileMenu = menubar.addMenu('&File')

        btn_imp_csv = QtWidgets.QAction('Import &csv', self)
        btn_imp_csv.setShortcut('Ctrl+Shift+C')
        btn_imp_csv.triggered.connect(lambda: self.clickOnBtnImp(idx=1))

        btn_imp_txt = QtWidgets.QAction('Import &txt', self)
        btn_imp_txt.setShortcut('Ctrl+Shift+T')
        btn_imp_txt.triggered.connect(lambda: self.clickOnBtnImp(idx=2))

        btn_imp_vms = QtWidgets.QAction('Import &vms', self)
        btn_imp_vms.setShortcut('Ctrl+Shift+V')
        btn_imp_vms.triggered.connect(lambda: self.clickOnBtnImp(idx=3))

        btn_open_dir = QtWidgets.QAction('Open directory', self)
        btn_open_dir.setShortcut('Ctrl+Shift+D')
        btn_open_dir.triggered.connect(lambda: self.clickOnBtnImp(idx=4))

        importSubmenu = fileMenu.addMenu('&Import')
        importSubmenu.addAction(btn_imp_csv)
        importSubmenu.addAction(btn_imp_txt)
        importSubmenu.addAction(btn_imp_vms)
        importSubmenu.addAction(btn_open_dir)
        ### Export submenu
        btn_exp_results = QtWidgets.QAction('&Results', self)
        btn_exp_results.setShortcut('Ctrl+Shift+R')
        btn_exp_results.triggered.connect(self.exportResults)

        btn_exp_all_results = QtWidgets.QAction('Re&sults + Data', self)
        btn_exp_all_results.setShortcut('Ctrl+Shift+S')
        btn_exp_all_results.triggered.connect(self.export_all)

        exportSubmenu = fileMenu.addMenu('&Export')
        exportSubmenu.addAction(btn_exp_results)
        exportSubmenu.addAction(btn_exp_all_results)

        # exit application
        exitAction = QtWidgets.QAction('E&xit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(QtWidgets.qApp.quit)

        fileMenu.addAction(exitAction)

        ## Preset sub menue
        presetMenu = menubar.addMenu('&Preset')

        btn_preset_new = QtWidgets.QAction('&New', self)
        btn_preset_new.setShortcut('Ctrl+Shift+N')
        btn_preset_new.triggered.connect(lambda: self.clickOnBtnPreset(idx=1))

        btn_preset_load = QtWidgets.QAction('&Load', self)
        btn_preset_load.setShortcut('Ctrl+Shift+L')
        btn_preset_load.triggered.connect(lambda: self.clickOnBtnPreset(idx=2))

        btn_preset_append = QtWidgets.QAction('&Append', self)
        btn_preset_append.setShortcut('Ctrl+Shift+A')
        btn_preset_append.triggered.connect(lambda: self.clickOnBtnPreset(idx=3))

        btn_preset_save = QtWidgets.QAction('&Save', self)
        # btn_preset_save.setShortcut('Ctrl+Shift+S')
        btn_preset_save.triggered.connect(lambda: self.clickOnBtnPreset(idx=4))

        btn_preset_c1s = QtWidgets.QAction('&C1s', self)
        # btn_preset_c1s.setShortcut('Ctrl+Shift+')
        btn_preset_c1s.triggered.connect(lambda: self.clickOnBtnPreset(idx=5))

        btn_preset_ckedge = QtWidgets.QAction('C &K edge', self)
        # btn_preset_ckedge.setShortcut('Ctrl+Shift+')
        btn_preset_ckedge.triggered.connect(lambda: self.clickOnBtnPreset(idx=6))

        btn_preset_ptable = QtWidgets.QAction('Periodic &Table', self)
        # btn_preset_ptable.setShortcut('Ctrl+Shift+')
        btn_preset_ptable.triggered.connect(lambda: self.clickOnBtnPreset(idx=7))

        presetMenu.addAction(btn_preset_new)
        presetMenu.addAction(btn_preset_load)
        presetMenu.addAction(btn_preset_append)
        presetMenu.addAction(btn_preset_save)
        presetMenu.addAction(btn_preset_c1s)
        presetMenu.addAction(btn_preset_ckedge)
        menubar.addAction(btn_preset_ptable)

        self.bgMenu = menubar.addMenu('&Choose BG')

        self.btn_bg_shirley_act = QtWidgets.QAction('&Active &Shirley BG', self, checkable=True)
        self.btn_bg_shirley_act.triggered.connect(self.clickOnBtnBG)

        self.btn_bg_shirley_static = QtWidgets.QAction('&Static &Shirley BG', self, checkable=True)
        self.btn_bg_shirley_static.triggered.connect(self.clickOnBtnBG)

        self.btn_bg_tougaard_act = QtWidgets.QAction('&Active &Tougaard BG', self, checkable=True)
        self.btn_bg_tougaard_act.triggered.connect(self.clickOnBtnBG)

        self.btn_bg_tougaard_static = QtWidgets.QAction('&Static &Tougaard BG', self, checkable=True)
        self.btn_bg_tougaard_static.triggered.connect(self.clickOnBtnBG)

        self.btn_bg_polynomial = QtWidgets.QAction('&Polynomial BG', self, checkable=True)
        self.btn_bg_polynomial.setShortcut('Ctrl+Alt+P')
        self.btn_bg_polynomial.triggered.connect(self.clickOnBtnBG)

        self.btn_bg_slope = QtWidgets.QAction('&Slope BG', self, checkable=True)
        self.btn_bg_slope.setShortcut('Ctrl+Alt+S')
        self.btn_bg_slope.triggered.connect(self.clickOnBtnBG)

        self.btn_bg_arctan = QtWidgets.QAction('&Arctan BG', self, checkable=True)
        self.btn_bg_arctan.triggered.connect(self.clickOnBtnBG)

        self.btn_bg_erf = QtWidgets.QAction('&Erf BG', self, checkable=True)
        self.btn_bg_erf.triggered.connect(self.clickOnBtnBG)

        self.btn_bg_vbm = QtWidgets.QAction('&VBM/Cutoff BG', self, checkable=True)
        self.btn_bg_vbm.triggered.connect(self.clickOnBtnBG)

        # Add the checkable actions to the menu
        self.bgMenu.addAction(self.btn_bg_shirley_act)
        self.bgMenu.addAction(self.btn_bg_shirley_static)
        self.bgMenu.addAction(self.btn_bg_tougaard_act)
        self.bgMenu.addAction(self.btn_bg_tougaard_static)
        self.bgMenu.addAction(self.btn_bg_polynomial)
        self.bgMenu.addAction(self.btn_bg_slope)
        self.bgMenu.addAction(self.btn_bg_arctan)
        self.bgMenu.addAction(self.btn_bg_erf)
        self.bgMenu.addAction(self.btn_bg_vbm)

        btn_tougaard_cross_section = QtWidgets.QAction('Tougaard &Cross Section ', self)
        btn_tougaard_cross_section.triggered.connect(self.clicked_cross_section)
        self.bgMenu.addSeparator()
        self.bgMenu.addAction(btn_tougaard_cross_section)

        menubar.addSeparator()
        links_menu = menubar.addMenu('&Help/Info')
        # manual_link= QtWidgets.QAction('&Manual', self)
        # manual_link.triggered.connect(lambda: webbrowser.open('https://julian-hochhaus.github.io/LG4X-V2/'))
        # links_menu.addAction(manual_link)
        github_link = QtWidgets.QAction('See on &Github', self)
        github_link.triggered.connect(lambda: webbrowser.open('https://github.com/Julian-Hochhaus/LG4X-V2'))
        links_menu.addAction(github_link)
        about_link = QtWidgets.QAction('&How to cite', self)
        about_link.triggered.connect(self.show_citation_dialog)
        links_menu.addAction(about_link)

        # central widget layout
        widget = QtWidgets.QWidget(self)
        self.setCentralWidget(widget)
        widget.setLayout(outer_layout)

        # Home directory
        self.filePath = QtCore.QDir.homePath()

        self.figure, (self.ar, self.ax) = plt.subplots(2, sharex=True,
                                                       gridspec_kw={'height_ratios': [1, 5], 'hspace': 0})
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setMaximumHeight(20)
        self.toolbar.setMinimumHeight(15)
        self.toolbar.setStyleSheet("QToolBar { border: 0px }")

        # layout top row
        toprow_layout = QtWidgets.QHBoxLayout()
        bottomrow_layout = QtWidgets.QHBoxLayout()
        # button layout

        layout_top_left = QtWidgets.QVBoxLayout()
        fitbuttons_layout = QtWidgets.QHBoxLayout()
        # Fit Button
        btn_fit = QtWidgets.QPushButton('Fit', self)
        btn_fit.resize(btn_fit.sizeHint())
        btn_fit.clicked.connect(self.fit)
        fitbuttons_layout.addWidget(btn_fit)
        # Evaluate Button
        btn_eva = QtWidgets.QPushButton('Evaluate', self)
        btn_eva.resize(btn_eva.sizeHint())
        btn_eva.clicked.connect(self.eva)
        fitbuttons_layout.addWidget(btn_eva)
        # Undo Fit Button
        btn_undoFit = QtWidgets.QPushButton('undo Fit', self)
        btn_undoFit.resize(btn_undoFit.sizeHint())
        btn_undoFit.clicked.connect(self.one_step_back_in_params_history)
        fitbuttons_layout.addWidget(btn_undoFit)
        # Interrupt fit Button
        btn_interrupt = QtWidgets.QPushButton('Interrupt fitting (not implemented)', self)
        btn_interrupt.resize(btn_interrupt.sizeHint())
        btn_interrupt.clicked.connect(self.interrupt_fit)
        fitbuttons_layout.addWidget(btn_interrupt)
        layout_top_left.addLayout(fitbuttons_layout)

        # lists of dropdown menus
        self.list_file = ['File list', 'Clear list']
        # DropDown file list
        self.comboBox_file = QtWidgets.QComboBox(self)
        self.comboBox_file.addItems(self.list_file)
        self.comboBox_file.currentIndexChanged.connect(self.plot)
        layout_top_left.addWidget(self.comboBox_file)
        layout_top_left.addWidget(LayoutHline())
        plottitle_form = QtWidgets.QFormLayout()
        self.plottitle = QtWidgets.QLineEdit()
        plottitle_form.addRow("Plot title: ", self.plottitle)
        plot_settings_layout = QtWidgets.QHBoxLayout()
        min_form = QtWidgets.QFormLayout()
        self.xmin_item = DoubleLineEdit()
        self.xmin = 270
        self.xmin_item.setText(str(self.xmin))
        self.xmin_item.textChanged.connect(self.update_com_vals)
        min_form.addRow("x_min: ", self.xmin_item)
        plot_settings_layout.addLayout(min_form)
        max_form = QtWidgets.QFormLayout()
        self.xmax_item = DoubleLineEdit()
        self.xmax = 300
        self.xmax_item.setText(str(self.xmax))
        self.xmax_item.textChanged.connect(self.update_com_vals)
        max_form.addRow("x_max: ", self.xmax_item)
        plot_settings_layout.addLayout(max_form)
        hv_form = QtWidgets.QFormLayout()
        self.hv_item = DoubleLineEdit()
        self.hv = 1486.6
        self.hv_item.setText(str(self.hv))
        self.hv_item.textChanged.connect(self.update_com_vals)
        hv_form.addRow("hv: ", self.hv_item)
        plot_settings_layout.addLayout(hv_form)
        wf_form = QtWidgets.QFormLayout()
        self.wf_item = DoubleLineEdit()
        self.wf = 4
        self.wf_item.setText(str(self.wf))
        self.wf_item.textChanged.connect(self.update_com_vals)
        wf_form.addRow("wf: ", self.wf_item)
        plot_settings_layout.addLayout(wf_form)
        correct_energy_form = QtWidgets.QFormLayout()
        self.correct_energy_item = DoubleLineEdit()
        self.correct_energy = 0
        self.correct_energy_item.setText(str(self.correct_energy))
        self.correct_energy_item.textChanged.connect(self.update_com_vals)
        correct_energy_form.addRow("shift energy: ", self.correct_energy_item)
        plot_settings_layout.addLayout(correct_energy_form)
        layout_top_left.addLayout(plottitle_form)
        layout_top_left.addLayout(plot_settings_layout)
        layout_top_left.addStretch(1)

        layout_bottom_left = QtWidgets.QVBoxLayout()
        layout_bottom_left.addWidget(self.toolbar)
        layout_bottom_left.addWidget(self.canvas)

        toprow_layout.addLayout(layout_top_left, 4)
        bottomrow_layout.addLayout(layout_bottom_left, 4)

        layout_top_mid = QtWidgets.QVBoxLayout()
        layout_bottom_mid = QtWidgets.QVBoxLayout()
        # PolyBG Table
        list_bg_col = ['bg_c0', 'bg_c1', 'bg_c2', 'bg_c3', 'bg_c4']
        list_bg_row = ['Shirley (cv, it, k, c)', 'Tougaard(B, C, C*, D, extend)', 'Polynomial', 'Slope(k)',
                       'arctan (amp, ctr, sig)', 'erf (amp, ctr, sig)', 'cutoff (ctr, d1-4)']
        self.fitp0 = QtWidgets.QTableWidget(len(list_bg_row), len(list_bg_col) * 2)

        self.fitp0.setItemDelegate(self.delegate)
        list_bg_colh = ['', 'bg_c0', '', 'bg_c1', '', 'bg_c2', '', 'bg_c3', '', 'bg_c4']

        self.fitp0.setHorizontalHeaderLabels(list_bg_colh)
        self.fitp0.setVerticalHeaderLabels(list_bg_row)
        # set BG table checkbox
        for row in range(len(list_bg_row)):
            for col in range(len(list_bg_colh)):
                if (row == 2 or row > 3 or (row == 3 and col < 2) or (row == 0 and 8 > col >= 4) or (
                        row == 1 and col == 0)) and col % 2 == 0:
                    item = QtWidgets.QTableWidgetItem()
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                    item.setCheckState(QtCore.Qt.Unchecked)
                    item.setToolTip('Check to keep fixed during fit procedure')
                    self.fitp0.setItem(row, col, item)
                else:
                    item = QtWidgets.QTableWidgetItem()
                    item.setText('')
                    self.fitp0.setItem(row, col, item)
        # set BG table default
        pre_bg = [['', 1e-06, '', 10, 2, 0.0003, 2, 1000, '', ''],
                  [2, 2866.0, '', 1643.0, '', 1.0, '', 1.0, '', 50],
                  [2, 0, 2, 0, 2, 0, 2, 0, 2, 0],
                  [2, 0.0, '', '', '', '', '', '', '', '', '']]
        # self.setPreset([0], pre_bg, [])

        self.fitp0.resizeColumnsToContents()
        self.fitp0.resizeRowsToContents()
        bg_fixedLayout = QtWidgets.QHBoxLayout()
        self.fixedBG = QtWidgets.QCheckBox('Keep background fixed')
        self.displayChoosenBG.setText(
            'Choosen Background: {}'.format('+ '.join([dictBG[str(idx)] for idx in self.idx_bg])))
        self.displayChoosenBG.setStyleSheet("font-weight: bold")

        bg_fixedLayout.addWidget(self.displayChoosenBG)
        bg_fixedLayout.addWidget(self.fixedBG)

        layout_top_mid.addWidget(self.fitp0)
        layout_top_mid.addLayout(bg_fixedLayout)
        # Add Button

        componentbuttons_layout = QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton('add component', self)
        btn_add.resize(btn_add.sizeHint())
        btn_add.clicked.connect(self.add_col)
        componentbuttons_layout.addWidget(btn_add)

        # Remove Button
        btn_rem = QtWidgets.QPushButton('rem component', self)
        btn_rem.resize(btn_rem.sizeHint())
        btn_rem.clicked.connect(lambda: self.removeCol(idx=None,text=None ))
        componentbuttons_layout.addWidget(btn_rem)

        btn_limit_set = QtWidgets.QPushButton('&Set/Show Limits', self)
        btn_limit_set.resize(btn_limit_set.sizeHint())
        btn_limit_set.clicked.connect(self.setLimits)
        componentbuttons_layout.addWidget(btn_limit_set)

        # indicator for limits
        self.status_label = QtWidgets.QLabel()
        self.status_label.setFixedSize(18, 18)
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("background-color: grey; border-radius: 9px")

        # Create a QLabel for the status text
        self.status_text = QtWidgets.QLabel("Limits not used")
        self.status_text.setAlignment(QtCore.Qt.AlignLeft)
        self.status_text.setAlignment(QtCore.Qt.AlignVCenter)

        # Create a QVBoxLayout to hold the status widgets
        status_layout = QtWidgets.QHBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.status_text)
        status_layout.setAlignment(QtCore.Qt.AlignVCenter)
        componentbuttons_layout.addLayout(status_layout)
        componentbuttons_layout.setAlignment(QtCore.Qt.AlignVCenter)

        layout_bottom_mid.addLayout(componentbuttons_layout)

        # set Fit Table
        list_col = ['C_1']
        list_row = ['model', 'center', 'amplitude', 'lorentzian (sigma/gamma)', 'gaussian(sigma)', 'asymmetry(gamma)',
                    'frac', 'skew', 'q', 'kt', 'soc',
                    'height_ratio',
                    'fct_coster_kronig', 'center_ref', 'ctr_diff', 'amp_ref', 'ratio', 'lorentzian_ref', 'ratio',
                    'gaussian_ref', 'ratio',
                    'asymmetry_ref', 'ratio', 'soc_ref', 'ratio', 'height_ref', 'ratio']
        def comps_edit_condition(logicalIndex):
            return logicalIndex % 2 != 0
        self.fitp1=RemoveAndEditTableWidget(len(list_row), len(list_col) * 2, comps_edit_condition)
        self.fitp1.headerTextChanged.connect(self.updateHeader_lims)
        self.fitp1.removeOptionChanged.connect(self.removeCol)
        self.fitp1.setItemDelegate(self.delegate)
        list_colh = ['', 'C_1']
        self.fitp1.setHorizontalHeaderLabels(list_colh)
        self.fitp1.setVerticalHeaderLabels(list_row)
        self.list_row_limits = [
            'center', 'amplitude', 'lorentzian (sigma/gamma)', 'gaussian(sigma)', 'asymmetry(gamma)', 'frac', 'skew',
            'q', 'kt', 'soc',
            'height', "fct_coster_kronig", 'ctr_diff', 'amp_ratio', 'lorentzian_ratio', 'gaussian_ratio',
            'asymmetry_ratio', 'soc_ratio', 'height_ratio']
        list_colh_limits = ['C_1', 'min', 'max']

        def lims_edit_condition(logicalIndex):
            return logicalIndex % 3 == 0
        self.fitp1_lims = EditableHeaderTableWidget(len(self.list_row_limits), len(list_col) * 3, lims_edit_condition)
        self.fitp1_lims.headerTextChanged.connect(self.updateHeader_comps)
        self.fitp1_lims.setItemDelegate(self.delegate)

        self.fitp1_lims.setHorizontalHeaderLabels(list_colh_limits)
        self.fitp1_lims.setVerticalHeaderLabels(self.list_row_limits)
        self.fitp1_lims.cellChanged.connect(self.lims_changed)

        # self.list_shape = ['g', 'l', 'v', 'p']
        self.list_shape = ['g: Gaussian', 'l: Lorentzian', 'v: Voigt', 'p: PseudoVoigt', 'e: ExponentialGaussian',
                           's: SkewedGaussian', 'a: SkewedVoigt', 'b: BreitWigner', 'n: Lognormal', 'd: Doniach',
                           'gdd: Convolution Gaussian/Doniach-Dublett', 'gds: Convolution Gaussian/Doniach-Singlett',
                           'fe:Convolution FermiDirac/Gaussian']
        self.list_component = ['', 'C_1']

        # set DropDown component model
        for col in range(len(list_col)):
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_shape)
            # comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(0, 2 * col + 1, comboBox)
        # set DropDown ctr_ref component selection
        for i in range(7):
            for col in range(len(list_col)):
                comboBox = QtWidgets.QComboBox()
                comboBox.addItems(self.list_component)
                comboBox.setMaximumWidth(55)
                self.fitp1.setCellWidget(13 + 2 * i, 2 * col + 1, comboBox)

        # set checkbox and dropdown in fit table
        for row in range(len(list_row)):
            for col in range(len(list_colh)):
                if col % 2 == 0:
                    item = QtWidgets.QTableWidgetItem()
                    item.setToolTip('Check to keep fixed during fit procedure')
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                    if 0 < row < 13:
                        item.setCheckState(QtCore.Qt.Checked)
                        self.fitp1.setItem(row, col, item)
                    if 13 <= row:
                        if row % 2 == 0:
                            item.setCheckState(QtCore.Qt.Unchecked)
                            self.fitp1.setItem(row, col, item)
                        else:
                            item = QtWidgets.QTableWidgetItem()
                            item.setText('')
                            self.fitp1.setItem(row, col, item)
                elif col % 2 != 0 and (row == 0 or (12 <= row and row % 2 == 1)):
                    comboBox = QtWidgets.QComboBox()
                    if row == 0:
                        comboBox.addItems(self.list_shape)
                        comboBox.currentTextChanged.connect(self.activeParameters)
                    else:
                        comboBox.addItems(self.list_component)
                    self.fitp1.setCellWidget(row, col, comboBox)
                else:
                    item = QtWidgets.QTableWidgetItem()
                    item.setText('')
                    self.fitp1.setItem(row, col, item)
        # set checkbox in limits table
        for row in range(len(self.list_row_limits)):
            for col in range(len(list_colh_limits)):
                item = QtWidgets.QTableWidgetItem()
                if col % 3 == 0:
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                    item.setCheckState(QtCore.Qt.Unchecked)
                    item.setToolTip('Check to use limit during fit procedure')
                else:
                    item.setText("")
                self.fitp1_lims.setItem(row, col, item)
        # load default preset
        # pre_pk = [[0,0],[2,0],[2,0],[2,0],[2,0],[2,0],[2,0],[2,0]]
        pre_pk = [[0, 0], [2, 284.6], [0, 20000], [2, 0.2], [2, 0.2], [2, 0.02], [2, 0], [2, 0], [2, 0.0], [2, 0.026],
                  [2, 1], [2, 0.7], [2, 1], [0, 0], [2, 0.1], [0, 0], [2, 0.5], [0, 0], [2, 1], [0, 0], [2, 1],
                  [0, 0], [2, 1], [0, 0], [2, 1], [0, 0], [2, 1]]
        self.pre = [[self.idx_bg, self.xmin, self.xmax, self.hv, self.wf, self.correct_energy], pre_bg, pre_pk, [[0, '', '']] * 19]
        self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
        self.fitp1.resizeColumnsToContents()
        self.fitp1.resizeRowsToContents()
        self.fitp1.setHeaderTooltips()
        layout_bottom_mid.addWidget(self.fitp1)

        toprow_layout.addLayout(layout_top_mid, 4)
        bottomrow_layout.addLayout(layout_bottom_mid, 3)
        outer_layout.addLayout(toprow_layout, 1)

        outer_layout.addWidget(LayoutHline())
        outer_layout.addLayout(bottomrow_layout, 6)
        layout_top_right = QtWidgets.QVBoxLayout()
        layout_bottom_right = QtWidgets.QVBoxLayout()
        self.fitp1_lims.resizeColumnsToContents()
        self.fitp1_lims.resizeRowsToContents()
        self.fitp1_lims.setHeaderTooltips()
        list_res_row = ['gaussian_fwhm', 'lorentzian_fwhm_p1', 'lorentzian_fwhm_p2', 'fwhm_p1', 'fwhm_p2', 'height_p1',
                        'height_p2', 'approx. area_p1', 'approx. area_p2', 'area_total']

        def res_edit_condition(logicalIndex):
            return logicalIndex % 1 == 0
        self.res_tab = EditableHeaderTableWidget(len(list_res_row), len(list_col) , res_edit_condition)
        self.res_tab.setHorizontalHeaderLabels(list_col)
        self.res_tab.setVerticalHeaderLabels(list_res_row)
        self.res_tab.headerTextChanged.connect(self.updateHeader_res)
        self.res_tab.resizeColumnsToContents()
        self.res_tab.resizeRowsToContents()
        layout_bottom_right.addWidget(self.res_tab)
        toprow_layout.addLayout(layout_top_right, 1)
        bottomrow_layout.addLayout(layout_bottom_right, 2)
        list_stats_row = ['success?', 'message', 'nfev', 'nvary', 'ndata', 'nfree', 'chisqr', 'redchi', 'aic', 'bic']
        list_stats_col = ['Fit stats']
        self.stats_tab = QtWidgets.QTableWidget(len(list_stats_row), 1)
        self.stats_tab.setHorizontalHeaderLabels(list_stats_col)
        self.stats_tab.setVerticalHeaderLabels(list_stats_row)
        self.stats_tab.resizeColumnsToContents()
        self.stats_tab.resizeRowsToContents()
        layout_bottom_right.addWidget(self.stats_tab)
        self.stats_label = QtWidgets.QLabel()
        self.stats_label.setText("Fit statistics:")
        self.stats_label.setStyleSheet("font-weight: bold; font-size:12pt")
        # grid..addWidget(self.stats_label, 5, 7, 1, 1)
        self.pars_label = QtWidgets.QLabel()
        self.pars_label.setText("Peak parameters:")
        self.pars_label.setStyleSheet("font-weight: bold; font-size:12pt")
        # grid..addWidget(self.pars_label, 3, 3, 1, 1)
        self.res_label = QtWidgets.QLabel()
        self.res_label.setText("Fit results:")
        self.res_label.setStyleSheet("font-weight: bold; font-size:12pt")
        # grid..addWidget(self.res_label, 7, 7, 1, 1)
        self.activeParameters()
        self.show()
    def duplicateComponentNames(self, new_label):
        if new_label in self.list_component:
            QtWidgets.QMessageBox.warning(self, "Duplicate Name", "Component name already exists.\n Defaulted to next free name in format 'C_xx' ")
            corrected_label=self.nextFreeComponentName()
            return corrected_label
        else:
            return new_label
    def nextFreeComponentName(self):
        max_num=0
        for comp_name in self.list_component:
            if 'C_' in comp_name:
                num=int(comp_name.split('_')[1])
                if num>max_num:
                    max_num=num
        return 'C_'+str(max_num+1)

    def updateHeader_lims(self, logicalIndex, new_label):
        if logicalIndex%2!=0:
            new_label=self.duplicateComponentNames(new_label)
            self.fitp1_lims.horizontalHeaderItem(int((logicalIndex-1)/2*3)).setText(new_label)
            self.res_tab.horizontalHeaderItem(int((logicalIndex-1)/2)).setText(new_label)
            self.updateDropdown()

    def updateHeader_comps(self, logicalIndex, new_label):
        if logicalIndex%3==0:
            new_label=self.duplicateComponentNames(new_label)
            self.fitp1.horizontalHeaderItem(int(logicalIndex/3*2+1)).setText(new_label)
            self.res_tab.horizontalHeaderItem(int(logicalIndex / 3)).setText(new_label)
            self.updateDropdown()

    def updateHeader_res(self, logicalIndex, new_label):
        new_label = self.duplicateComponentNames(new_label)
        self.fitp1.horizontalHeaderItem(int(logicalIndex * 2 + 1)).setText(new_label)
        self.fitp1_lims.horizontalHeaderItem(int(logicalIndex * 3)).setText(new_label)
        self.updateDropdown()
    def updateDropdown(self, colposition=None):
        if colposition is None:
            colPosition_fitp1 = self.fitp1.columnCount()
        else:
            colPosition_fitp1 = colposition
        header_texts = ['']
        for column in range(int(self.fitp1.columnCount() / 2)):
            header_item = self.fitp1.horizontalHeaderItem(int(column * 2 + 1))
            if header_item is not None:
                header_texts.append(header_item.text())
        self.list_component=header_texts
        for i in range(7):
            for col in range(int(colPosition_fitp1 / 2 + 1)):
                if col < int(colPosition_fitp1 / 2):
                    index = self.fitp1.cellWidget(13 + 2 * i, 2 * col + 1).currentIndex()
                comboBox = QtWidgets.QComboBox()
                comboBox.addItems(self.list_component)
                comboBox.setMaximumWidth(55)
                if index > 0 and col < int(colPosition_fitp1 / 2):
                    comboBox.setCurrentIndex(index)
                self.fitp1.setCellWidget(13 + 2 * i, 2 * col + 1, comboBox)

    def show_citation_dialog(self):
        citation_text = 'J. A. Hochhaus and H. Nakajima, LG4X-V2 (Zenodo, 2023), DOI:10.5281/zenodo.7871174'
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle('How to cite')
        msg_box.setTextFormat(QtCore.Qt.RichText)
        msg_box.setText(citation_text)
        copy_button = msg_box.addButton('Copy to clipboard', QtWidgets.QMessageBox.AcceptRole)
        open_zenodo_button = msg_box.addButton('Open on Zenodo(DOI)', QtWidgets.QMessageBox.ActionRole)

        msg_box.exec_()
        if msg_box.clickedButton() == copy_button:
            # Copy citation text to clipboard
            QtWidgets.QApplication.clipboard().setText(citation_text)
        elif msg_box.clickedButton() == open_zenodo_button:
            # Open web link
            url = 'https://zenodo.org/record/7871174'
            webbrowser.open(url)

    def setButtonState(self, indices):
        for i in indices:
            if i == 0:
                self.btn_bg_shirley_static.setChecked(True)
            elif i == 1:
                self.btn_bg_tougaard_static.setChecked(True)
            elif i == 2:
                self.btn_bg_polynomial.setChecked(True)
            elif i == 3:
                self.btn_bg_arctan.setChecked(True)
            elif i == 4:
                self.btn_bg_erf.setChecked(True)
            elif i == 5:
                self.btn_bg_vbm.setChecked(True)
            elif i == 6:
                self.btn_bg_slope.setChecked(True)
            elif i == 100:
                self.btn_bg_shirley_act.setChecked(True)
            elif i == 101:
                self.btn_bg_tougaard_act.setChecked(True)

    def lims_changed(self, row=0, column=0):
        """Handle the cellChanged signal emitted by fitp1 table (the limits table)
          Args:
              row (int): The row index of the changed cell.
              column (int): The column index of the changed cell.

          Returns:
              None
          """
        checked = False
        for c in range(int(self.fitp1_lims.columnCount() / 3)):
            for r in range(self.fitp1_lims.rowCount()):
                item = self.fitp1_lims.item(r, 3 * c)
                if item is not None and item.checkState():
                    checked = True
        if checked:
            self.set_status('limit_set')
        else:
            self.set_status('unset')

    def set_status(self, status):
        """
        Update the status text and color of the status indicator.

        Args:
            status: A string representing the status according to which color and text are updated.

        """
        if status == "limit_reached":
            self.status_label.setStyleSheet("background-color: red; border-radius: 9px")
            self.status_text.setText("Limit reached!")
        elif status == "unset":
            self.status_label.setStyleSheet("background-color: grey; border-radius: 9px")
            self.status_text.setText("Status: Limits not used")
        elif status == "limit_set":
            self.status_label.setStyleSheet("background-color: green; border-radius: 9px")
            self.status_text.setText("Limits active")
        elif status == 'at_zero':
            self.status_label.setStyleSheet("background-color: yellow; border-radius: 9px")
            self.status_text.setText("Limit at 0. ")
            self.status_text.setToolTip(
                "<html><head/><body><p>If a limit reaches zero, a warning is displayed. Usually, such a case is intended because several parameters such as the amplitude and the assymetry are limited to positive values.</p></body></html>")
        else:
            self.status_label.setStyleSheet("background-color: blue; border-radius: 9px")
            self.status_text.setText("Error, Unknown state!")

    def clicked_cross_section(self):
        window_cross_section = Window_CrossSection()

        window_cross_section.show()
        window_cross_section.btn_cc.clicked.connect(lambda: self.setCrossSection(window_cross_section))

    def setCrossSection(self, window):
        window.choosenElement()
        tougaard = window.tougaard_params
        self.savePreset()
        for idx in range(4):
            self.pre[1][1][2 * idx + 1] = tougaard[idx]
        self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])

    def activeParameters(self):
        nrows = self.fitp0.rowCount()
        ncols = self.fitp0.columnCount()

        for col in range(ncols):
            for row in range(nrows):
                self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                   col).flags() & ~QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsEnabled & ~QtCore.Qt.ItemIsSelectable)

        for idx in self.idx_bg:
            for col in range(ncols):
                for row in range(nrows):
                    if idx == 0 and row == 0 and col < 4:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    elif idx == 100 and row == 0:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    elif idx == 1 and row == 1:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    elif idx == 101 and row == 1:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    elif idx == 6 and row == 3 and col < 2:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    elif idx == 3 and row == 4:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    elif idx == 2 and row == 2:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

                    elif idx == 4 and row == 5:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    elif idx == 5 and row == 6:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        nrows = self.fitp1.rowCount()
        ncols = self.fitp1.columnCount()
        ncols = int(ncols / 2)
        for col in range(ncols):
            for row in range(nrows - 1):
                if self.fitp1.item(row + 1, 2 * col + 1) is None and self.fitp1.cellWidget(row + 1,
                                                                                           2 * col + 1) is not None:
                    self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(False)
                if self.fitp1.item(row + 1, 2 * col + 1) is not None:
                    self.fitp1.item(row + 1, 2 * col).setFlags(self.fitp1.item(row + 1,
                                                                               2 * col).flags() & ~ QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsEnabled & ~QtCore.Qt.ItemIsSelectable)
                    self.fitp1.item(row + 1, 2 * col + 1).setFlags(self.fitp1.item(row + 1,
                                                                                   2 * col + 1).flags() & ~ QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsEnabled & ~QtCore.Qt.ItemIsSelectable)
        for col in range(ncols):
            idx = self.fitp1.cellWidget(0, 2 * col + 1).currentIndex()
            for row in range(nrows - 1):
                if row == 0 or row == 1 or row == 13 or row == 15:
                    self.fitp1.item(row + 1, 2 * col).setFlags(self.fitp1.item(row + 1,
                                                                               2 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    self.fitp1.item(row + 1, 2 * col + 1).setFlags(self.fitp1.item(row + 1,
                                                                                   2 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if row == 12 or row == 14:
                    self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(True)
                if idx == 1 or idx == 2 or idx == 3 or idx == 6 or idx == 9 or idx == 10 or idx == 11:
                    if row == 2 or row == 17:
                        self.fitp1.item(row + 1, 2 * col).setFlags(self.fitp1.item(row + 1,
                                                                                   2 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(self.fitp1.item(row + 1,
                                                                                       2 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    if row == 16:
                        self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(True)
                if idx == 0 or idx == 2 or idx == 5 or idx == 6 or idx == 7 or idx == 8 or idx == 10 or idx == 11 or idx == 12:
                    if row == 3 or row == 19:
                        self.fitp1.item(row + 1, 2 * col).setFlags(self.fitp1.item(row + 1,
                                                                                   2 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(self.fitp1.item(row + 1,
                                                                                       2 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    if row == 18:
                        self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(True)
                if idx == 4 or idx == 5 or idx == 9 or idx == 10 or idx == 11:
                    if row == 4 or row == 21:
                        self.fitp1.item(row + 1, 2 * col).setFlags(self.fitp1.item(row + 1,
                                                                                   2 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(self.fitp1.item(row + 1,
                                                                                       2 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    if row == 20:
                        self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(True)

                if idx == 3:
                    if row == 5:
                        self.fitp1.item(row + 1, 2 * col).setFlags(self.fitp1.item(row + 1,
                                                                                   2 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(self.fitp1.item(row + 1,
                                                                                       2 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

                if idx == 6:
                    if row == 6:
                        self.fitp1.item(row + 1, 2 * col).setFlags(self.fitp1.item(row + 1,
                                                                                   2 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(self.fitp1.item(row + 1,
                                                                                       2 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

                if idx == 7:
                    if row == 7:
                        self.fitp1.item(row + 1, 2 * col).setFlags(self.fitp1.item(row + 1,
                                                                                   2 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(self.fitp1.item(row + 1,
                                                                                       2 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if idx == 12:
                    if row == 8:
                        self.fitp1.item(row + 1, 2 * col).setFlags(self.fitp1.item(row + 1,
                                                                                   2 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(self.fitp1.item(row + 1,
                                                                                       2 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if idx == 10:
                    if row == 9 or row == 23 or row == 10 or row == 25 or row == 11:
                        self.fitp1.item(row + 1, 2 * col).setFlags(self.fitp1.item(row + 1,
                                                                                   2 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(self.fitp1.item(row + 1,
                                                                                       2 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    if row == 22 or row == 24:
                        self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(True)
        nrows = self.fitp1_lims.rowCount()
        ncols = self.fitp1_lims.columnCount()
        ncols = int(ncols / 3)
        for col in range(ncols):
            for row in range(nrows):
                if self.fitp1_lims.item(row, 3 * col + 1) is not None:
                    self.fitp1_lims.item(row, 3 * col).setFlags(self.fitp1_lims.item(row,
                                                                                     3 * col).flags() & ~ QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsEnabled & ~QtCore.Qt.ItemIsSelectable)
                    self.fitp1_lims.item(row, 3 * col + 1).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col + 1).flags() & ~ QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsEnabled & ~QtCore.Qt.ItemIsSelectable)
                    self.fitp1_lims.item(row, 3 * col + 2).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col + 2).flags() & ~ QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsEnabled & ~QtCore.Qt.ItemIsSelectable)
        for col in range(ncols):
            idx = self.fitp1.cellWidget(0, 2 * col + 1).currentIndex()
            for row in range(nrows):
                if row == 0 or row == 1 or row == 12 or row == 13:
                    self.fitp1_lims.item(row, 3 * col).setFlags(self.fitp1_lims.item(row,
                                                                                     3 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    self.fitp1_lims.item(row, 3 * col + 1).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    self.fitp1_lims.item(row, 3 * col + 2).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col + 2).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if idx == 1 or idx == 2 or idx == 3 or idx == 6 or idx == 9 or idx == 10 or idx == 11:
                    if row == 2 or row == 14:
                        self.fitp1_lims.item(row, 3 * col).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 2).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

                if idx == 0 or idx == 2 or idx == 6 or idx == 7 or idx == 8 or idx == 10 or idx == 11 or idx == 12:
                    if row == 3 or row == 15:
                        self.fitp1_lims.item(row, 3 * col).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 2).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

                if idx == 4 or idx == 5 or idx == 9 or idx == 10 or idx == 11:
                    if row == 4 or row == 16:
                        self.fitp1_lims.item(row, 3 * col).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 2).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

                if idx == 3:
                    if row == 5:
                        self.fitp1_lims.item(row, 3 * col).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 2).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

                if idx == 6:
                    if row == 6:
                        self.fitp1_lims.item(row, 3 * col).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 2).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

                if idx == 7:
                    if row == 7:
                        self.fitp1_lims.item(row, 3 * col).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 2).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if idx == 12:
                    if row == 8:
                        self.fitp1_lims.item(row, 3 * col).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 2).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if idx == 10:
                    if row == 9 or row == 10 or row == 11 or row == 17 or row == 18:
                        self.fitp1_lims.item(row, 3 * col).setFlags(self.fitp1_lims.item(row,
                                                                                         3 * col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 1).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(self.fitp1_lims.item(row,
                                                                                             3 * col + 2).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

    def update_com_vals(self):
        try:
            self.xmin = float(self.xmin_item.text().strip())
        except ValueError:
            self.xmin = 0
        try:
            self.xmax = float(self.xmax_item.text().strip())
        except ValueError:
            self.xmax = 0
        try:
            self.hv = float(self.hv_item.text().strip())
        except ValueError:
            self.hv = 0
        try:
            self.wf = float(self.wf_item.text().strip())
        except ValueError:
            self.wf = 0
        try:
            self.correct_energy = float(self.correct_energy_item.text().strip())
        except ValueError:
            self.correct_energy = 0
        self.pre[0] = [self.idx_bg, self.xmin, self.xmax, self.hv, self.wf, self.correct_energy]

    def setLimits(self):
        self.sub_window = SubWindow(params_tab=self.fitp1_lims)
        self.sub_window.show()

    def raise_error(self, window_title: str, error_message: str) -> None:
        """
        Display an error message box with a custom error message and log the error.

        Args:
            window_title (str): The title of the error message box.
            error_message (str): The custom error message to be displayed.

        Returns:
            None
        """
        self.error_dialog.setWindowTitle(window_title)
        error_message = error_message + r'\n *******************\n' + traceback.format_exc()
        self.error_dialog.showMessage(error_message)
        logging.error(error_message)

    def add_col(self):
        rowPosition = self.fitp1.rowCount()
        colPosition_fitp1 = self.fitp1.columnCount()
        colPosition_fitp1_lims = self.fitp1_lims.columnCount()
        colPosition_res = self.res_tab.columnCount()
        self.res_tab.insertColumn(colPosition_res)
        self.fitp1.insertColumn(colPosition_fitp1)
        self.fitp1.insertColumn(colPosition_fitp1 + 1)
        self.fitp1_lims.insertColumn(colPosition_fitp1_lims)
        self.fitp1_lims.insertColumn(colPosition_fitp1_lims + 1)
        self.fitp1_lims.insertColumn(colPosition_fitp1_lims + 2)
        # add DropDown component model
        comboBox = QtWidgets.QComboBox()
        comboBox.addItems(self.list_shape)
        comboBox.currentTextChanged.connect(self.activeParameters)
        # comboBox.setMaximumWidth(55)
        self.fitp1.setCellWidget(0, colPosition_fitp1 + 1, comboBox)
        # setup new component parameters
        for row in range(rowPosition):
            add_fac = 0
            if row == 0:
                add_fac = -float(self.fitp1.item(row + 3, colPosition_fitp1 - 1).text()) * 2
            if row == 1:
                add_fac = -1 * float(self.fitp1.item(row + 1, colPosition_fitp1 - 1).text()) / 2
            if self.fitp1.item(row + 1, colPosition_fitp1 - 1) is not None \
                    and row != 12 and row != 14 and row != 16 \
                    and row != 18 and row != 20 and row != 22 and row != 24:
                if len(self.fitp1.item(row + 1, colPosition_fitp1 - 1).text()) > 0:
                    item = QtWidgets.QTableWidgetItem(
                        str(format(float(self.fitp1.item(row + 1, colPosition_fitp1 - 1).text()) + add_fac,
                                   self.floating)))
                    self.fitp1.setItem(row + 1, colPosition_fitp1 + 1, item)

        # add table header
        comp_name=self.nextFreeComponentName()
        item = QtWidgets.QTableWidgetItem()
        self.fitp1.setHorizontalHeaderItem(colPosition_fitp1, item)
        item = QtWidgets.QTableWidgetItem(comp_name)
        self.fitp1.setHorizontalHeaderItem(colPosition_fitp1 + 1, item)

        item = QtWidgets.QTableWidgetItem(comp_name)
        self.res_tab.setHorizontalHeaderItem(colPosition_res, item)
        self.res_tab.resizeColumnsToContents()
        self.res_tab.resizeRowsToContents()
        item = QtWidgets.QTableWidgetItem(comp_name)
        self.fitp1_lims.setHorizontalHeaderItem(colPosition_fitp1_lims, item)
        item = QtWidgets.QTableWidgetItem('min')
        self.fitp1_lims.setHorizontalHeaderItem(colPosition_fitp1_lims + 1, item)
        item = QtWidgets.QTableWidgetItem('max')
        self.fitp1_lims.setHorizontalHeaderItem(colPosition_fitp1_lims + 2, item)
        self.fitp1_lims.resizeColumnsToContents()
        self.fitp1_lims.resizeRowsToContents()
        self.fitp1.setHeaderTooltips()
        self.fitp1_lims.setHeaderTooltips()
        self.fitp1.resizeColumnsToContents()
        for column in range(self.fitp1.columnCount()):
            if column % 2 == 1:
                self.fitp1.setColumnWidth(column, 55)


        # add DropDown component selection for amp_ref and ctr_ref and keep values as it is
        self.updateDropdown(colposition=colPosition_fitp1)

        # add checkbox
        for row in range(rowPosition - 1):
            item = QtWidgets.QTableWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            item.setToolTip('Check to keep fixed during fit procedure')
            if row < 12:
                # item.setCheckState(QtCore.Qt.Checked)
                if self.fitp1.item(row + 1, colPosition_fitp1 - 2).checkState() == 2:
                    item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)
            if 12 < row and row % 2 == 1:
                if self.fitp1.item(row + 1, colPosition_fitp1 - 2).checkState() == 2:
                    item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)

            else:
                item.setText('')
            self.fitp1.setItem(row + 1, colPosition_fitp1, item)

        # add checkbox and entries in limits table
        for row in range(self.fitp1_lims.rowCount()):
            item = QtWidgets.QTableWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            item.setCheckState(QtCore.Qt.Unchecked)
            item.setToolTip('Check to use limit during fit procedure')
            self.fitp1_lims.setItem(row, colPosition_fitp1_lims, item)
            item = QtWidgets.QTableWidgetItem()
            item.setText('')
            self.fitp1_lims.setItem(row, colPosition_fitp1_lims + 1, item)
            item = QtWidgets.QTableWidgetItem()
            item.setText('')
            self.fitp1_lims.setItem(row, colPosition_fitp1_lims + 2, item)

        self.activeParameters()


    def removeCol(self, idx=None, text=None):
        if text=='--':
            pass
        else:
            if idx==None or text=="Remove Last Column":
                colPosition = self.fitp1.columnCount()-2
                colPosition_lims = self.fitp1_lims.columnCount()-3
                colPosition_res = self.res_tab.columnCount()-1
            elif idx!=None:
                colPosition = (idx-2)*2
                colPosition_lims = int((idx-2)*3)
                colPosition_res = int(idx-2)
            if self.res_tab.columnCount() > 1 and self.fitp1_lims.columnCount() > 3 and self.fitp1.columnCount() > 2:
                self.res_tab.removeColumn(colPosition_res)
                self.fitp1_lims.removeColumn(colPosition_lims+2)
                self.fitp1_lims.removeColumn(colPosition_lims+1)
                self.fitp1_lims.removeColumn(colPosition_lims)
                self.fitp1.removeColumn(colPosition+1)
                self.fitp1.removeColumn(colPosition)
                self.updateDropdown()
            else:
                print('Cannot remove the last remaining column.')
    def rem_col(self):
        colPosition = self.fitp1.columnCount()
        colPosition_lims = self.fitp1_lims.columnCount()
        colPosition_res = self.res_tab.columnCount()
        if colPosition_res > 1:
            self.res_tab.removeColumn(colPosition_res - 1)
        if colPosition_lims > 3:
            self.fitp1_lims.removeColumn(colPosition_lims - 1)
            self.fitp1_lims.removeColumn(colPosition_lims - 2)
            self.fitp1_lims.removeColumn(colPosition_lims - 3)
        if colPosition > 2:
            self.fitp1.removeColumn(colPosition - 1)
            self.fitp1.removeColumn(colPosition - 2)
            self.list_component.remove(str(int(colPosition / 2)))
            # remove component in dropdown menu and keep values as it is
            for i in range(7):
                for col in range(int(colPosition / 2) - 1):
                    if col < int(colPosition / 2):
                        index = self.fitp1.cellWidget(13 + 2 * i, 2 * col + 1).currentIndex()
                    comboBox = QtWidgets.QComboBox()
                    comboBox.addItems(self.list_component)
                    comboBox.setMaximumWidth(55)
                    if index > 0 and col < int(colPosition / 2):
                        comboBox.setCurrentIndex(index)
                    self.fitp1.setCellWidget(13 + 2 * i, 2 * col + 1, comboBox)

    def clickOnBtnPreset(self, idx):
        self.idx_pres = idx
        self.preset()

    def reformat_pre(self):
        temp_pre = self.pre
        if temp_pre[0] == 0:
            if temp_pre[1][1][10] == 2:
                temp_pre[0] += 100
        if temp_pre[0] == 1:
            if temp_pre[1][2][10] == 2:
                temp_pre[0] += 100

        self.pre[0] = [temp_pre[0], temp_pre[1][0][1], temp_pre[1][0][3], temp_pre[1][0][7], temp_pre[1][0][9]]
        temp = []
        for i in range(len(temp_pre[1]) - 2):
            if i == 0:
                entry = []
                for j in range(int(len(temp_pre[1][i + 1]) / 2 - 1)):
                    if j < 2:
                        entry.append('')
                    else:
                        entry.append(0)
                    entry.append(temp_pre[1][i + 1][2 * j + 1])
                entry.append('')
                entry.append('')
            elif i == 1:
                entry = [0]
                for j in range(int(len(temp_pre[1][i + 1]) / 2 - 1)):
                    entry.append(temp_pre[1][i + 1][2 * j + 1])
                    entry.append('')
                entry.append('')
            else:
                entry = [elem for elem in temp_pre[1][i + 1][:-1]]
            temp.append(entry)
        self.pre[1] = temp
        self.pre[1][2][8] = 2
        self.pre[1][2][9] = 0
        temp = temp_pre[2][0:2]
        temp.append(temp_pre[2][4])
        temp.append(temp_pre[2][2])
        temp.append(temp_pre[2][11])
        temp.append(temp_pre[2][3])
        temp.extend(temp_pre[2][5:11])
        temp.append(temp_pre[2][12])
        temp.extend(temp_pre[2][13:17])
        temp.extend(temp_pre[2][23:25])
        temp.extend(temp_pre[2][21:23])
        temp.append(['', 0] * int(len(temp_pre[2][0]) / 2))
        temp.append([2, 1] * int(len(temp_pre[2][0]) / 2))
        temp.extend(temp_pre[2][17:21])
        self.pre[2] = temp
        self.pre.append([[0, '', '']] * 19)  # currently, limits of old format are ignored!

    def preset(self):
        index = self.idx_pres
        colPosition = self.fitp1.columnCount()

        if index == 1:
            if colPosition > 2:
                for col in range(int(colPosition / 2) - 1):
                    self.removeCol(idx=None)
            # load default preset
            if self.comboBox_file.currentIndex() > 0:
                # self.df = np.loadtxt(str(self.comboBox_file.currentText()),	delimiter=',', skiprows=1)
                x0 = self.df[:, 0]
                y0 = self.df[:, 1]
                pre_pk = [[0, 0], [0, x0[abs(y0 - y0.max()).argmin()]], [0, y0[abs(y0 - y0.max()).argmin()]], [2, 0],
                          [0, abs(x0[0] - x0[-1]) / (0.2 * len(x0))], [2, 0], [2, 0], [2, 0], [2, 0], [2, 0], [2, 0],
                          [2, 0], [2, 0]]
            else:
                pre_pk = [[0, 0], [0, 285], [0, 20000], [2, 0], [0, 0.2], [2, 0], [2, 0], [2, 0], [2, 0], [2, 0],
                          [2, 0], [2, 0], [2, 0]]
            self.setPreset([0], [], pre_pk)
        if index == 2:
            try:
                self.loadPreset()
            except Exception as e:
                return self.raise_error(window_title="Error: Could not load parameters!",
                                        error_message='Loading parameters failed. The following traceback may help to solve the issue:')
            # print(self.df[0], self.df[1], self.df[2])
            if len(str(self.pre[0])) != 0 and len(self.pre[1]) != 0 and len(self.pre[2]) != 0 and len(self.pre) == 3:
                # old format, reorder data!
                self.reformat_pre()
                self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
            elif len(str(self.pre[0])) != 0 and len(self.pre[1]) != 0 and len(self.pre[2]) != 0 and len(
                    self.pre[3]) != 0:
                # new format
                self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
        if index == 3:
            try:
                self.addPreset()
            except Exception as e:
                return self.raise_error(window_title="Error: Could not add parameters!",
                                        error_message='Adding parameters failed. The following traceback may help to solve the issue:')
            # print(self.df[0], self.df[1], self.df[2])
            if len(str(self.pre[0])) != 0 and len(self.pre[1]) != 0 and len(self.pre[2]) != 0 and len(self.pre) == 3:
                # old format, reorder data!
                self.reformat_pre()
                self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
            elif len(str(self.pre[0])) != 0 and len(self.pre[1]) != 0 and len(self.pre[2]) != 0 and len(
                    self.pre[3]) != 0:
                # new format
                self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
        if index == 4:
            try:
                self.savePreset()
            except Exception as e:
                return self.raise_error(window_title="Error: Could not save parameters!",
                                        error_message='Save parameters failed. The following traceback may help to solve the issue:')
            try:
                self.savePresetDia()
            except Exception as e:
                return self.raise_error(window_title="Error: Could not save!",
                                        error_message='Saving data failed. The following traceback may help to solve the issue:')
        if index == 5:  # reformat inputs [bug]
            # load C1s component preset
            pre_bg = [[2, 295, 2, 275, '', '', '', '', '', ''], ['cv', 1e-06, 'it', 10, '', '', '', '', '', ''],
                      ['B', 2866.0, 'C', 1643.0, 'C*', 1.0, 'D', 1.0, 'Keep fixed?', 0],
                      [2, 0, 2, 0, 2, 0, 2, 0, '', '']]
            if self.comboBox_file.currentIndex() > 0:
                # self.df = np.loadtxt(str(self.comboBox_file.currentText()),	delimiter=',', skiprows=1)
                # x0 = self.df[:, 0]
                y0 = self.df[:, 1]
                pre_pk = [[0, 0, 0, 0, 0, 0, 0, 0], [2, 284.6, 2, 286.5, 2, 288.0, 2, 291.0],
                          [2, 0.85, 2, 0.85, 2, 1.28, 2, 1.28], [2, 0.85, 2, 0.85, 2, 1.28, 2, 1.28],
                          [0, y0[abs(y0 - y0.max()).argmin()] * 2.5 * 0.85, 0,
                           y0[abs(y0 - y0.max()).argmin()] * 2.5 * 0.85 * 0.1, 0,
                           y0[abs(y0 - y0.max()).argmin()] * 2.5 * 0.85 * 0.05, 0,
                           y0[abs(y0 - y0.max()).argmin()] * 2.5 * 0.85 * 0.05], [2, 0.5, 2, 0.5, 2, 0.5, 2, 0.5]]
            else:
                pre_pk = [[0, 0, 0, 0, 0, 0, 0, 0], [2, 284.6, 2, 286.5, 2, 288.0, 2, 291.0],
                          [2, 0.85, 2, 0.85, 2, 1.28, 2, 1.28], [2, 0.85, 2, 0.85, 2, 1.28, 2, 1.28],
                          [0, 20000, 0, 2000, 0, 750, 0, 750], [2, 0.5, 2, 0.5, 2, 0.5, 2, 0.5]]
            self.setPreset([0], pre_bg, pre_pk)
        if index == 6:  # reformat inputs [bug]
            # load C K edge preset
            pre_bg = [[2, 270.7, 2, 320.7, '', '', '', '', '', ''], ['cv', 1e-06, 'it', 10.0, '', '', '', '', '', ''],
                      ['B', 2866.0, 'C', 1643.0, 'C*', 1.0, 'D', 1.0, 'Keep fixed?', 0],
                      [2, 0.07, 2, 0.0, 2, 0.0, 2, 0.0, '', ''], [2, 12.05, 2, 43.36, 2, 0.05, 0, '', '', ''],
                      [2, 0.27, 2, 291.82, 2, 0.72, 0, '', '', ''], [0, '', 0, '', 0, '', 0, '', '', '']]

            pre_pk = [['', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0],
                      [0, 284.95, 0, 286.67, 0, 287.57, 0, 289.0, 0, 290.69, 0, 292.27, 2, 296.0, 2, 302.0, 2, 310.0],
                      [0, 0.67, 0, 0.5, 0, 0.8, 0, 0.8, 0, 1.0, 0, 1.5, 0, 3.0, 0, 5.0, 0, 5.0],
                      [2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0],
                      [0, 0.51, 0, 0.1, 0, 0.32, 0, 0.37, 0, 0.28, 0, 0.29, 0, 0.59, 0, 1.21, 0, 0.2],
                      [2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0, 2, 0.0],
                      [2, '', 2, '', 2, '', 2, '', 2, '', 2, '', 2, '', 2, '', 2, ''],
                      [2, '', 2, '', 2, '', 2, '', 2, '', 2, '', 2, '', 2, '', 2, ''],
                      ['', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0],
                      ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
                      ['', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0],
                      ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
                      [0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, ''],
                      [0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, ''],
                      [2, 0.5, 2, 0.5, 2, 0.5, 2, 0.5, 2, 0.5, 2, 1.0, 2, 2.0, 2, 2.0, 2, 2.0],
                      [2, 0.8, 2, 0.8, 2, 0.8, 2, 0.8, 2, 1.0, 2, 1.5, 2, 3.0, 2, 5.0, 2, 5.0],
                      [0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, ''],
                      [0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, '', 0, ''],
                      [2, 0.1, 2, 0.1, 2, 0.1, 2, 0.1, 2, 0.0, 2, 0.1, 2, 0.1, 2, 0.1, 2, 0.0]]
            self.setPreset([4], pre_bg, pre_pk)
        if index == 7:
            self.pt.show()
            self.pt.refresh_button.clicked.connect(self.plot_pt)
            self.pt.clear_button.clicked.connect(self.plot_pt)
            if not self.pt.isActiveWindow():
                self.pt.close()
                self.pt.show()

        self.idx_pres = 0
        self.fitp1.resizeColumnsToContents()
        self.fitp1.resizeRowsToContents()

    def setPreset(self, list_pre_com, list_pre_bg, list_pre_pk, list_pre_pk_lims=[[0, '', '']] * 19):
        if len(list_pre_com) == 1:
            pass
        else:
            self.xmin = list_pre_com[1]
            self.xmin_item.setText(str(format(self.xmin, self.floating)))
            self.xmax = list_pre_com[2]
            self.xmax_item.setText(str(format(self.xmax, self.floating)))
            self.hv = list_pre_com[3]
            self.hv_item.setText(str(format(self.hv, self.floating)))
            self.wf = list_pre_com[4]
            self.wf_item.setText(str(format(self.wf, self.floating)))
            if len(list_pre_com)==6:
                self.correct_energy = list_pre_com[5]
                self.correct_energy_item.setText(str(format(self.correct_energy, self.floating)))
        self.displayChoosenBG.setText(
            'Choosen Background: {}'.format('+ '.join([dictBG[str(idx)] for idx in self.idx_bg])))
        # load preset for bg
        if len(list_pre_bg) != 0 and self.addition == 0:
            for row in range(len(list_pre_bg)):
                for col in range(len(list_pre_bg[0])):
                    item = self.fitp0.item(row, col)
                    if (row == 2 or row > 3 or (row == 3 and col < 2) or (row == 0 and 8 > col >= 4) or (
                            row == 1 and col == 0)) and col % 2 == 0:
                        if list_pre_bg[row][col] == 2:
                            item.setCheckState(QtCore.Qt.Checked)
                        else:
                            item.setCheckState(QtCore.Qt.Unchecked)
                    elif row <= 1 and col % 2 == 0:
                        item.setText('')
                    else:
                        item.setText(str(list_pre_bg[row][col]))
        # load preset for components
        # adjust ncomponent before load
        if len(list_pre_pk) != 0:
            colPosition = int(self.fitp1.columnCount() / 2)
            if self.addition == 0:
                # print(int(colPosition), int(len(list_pre_pk[0])/2), list_pre_pk[0])
                if colPosition > int(len(list_pre_pk[0]) / 2):
                    for col in range(colPosition - int(len(list_pre_pk[0]) / 2)):
                        self.removeCol(idx=None)
                if colPosition < int(len(list_pre_pk[0]) / 2):
                    for col in range(int(len(list_pre_pk[0]) / 2) - colPosition):
                        self.add_col()
            else:
                for col in range(int(len(list_pre_pk[0]) / 2)):
                    self.add_col()

        for row in range(len(list_pre_pk)):
            for col in range(len(list_pre_pk[0])):
                if (col % 2) != 0:
                    if row == 0 or row == 13 or row == 15 or row == 17 or row == 19 or row == 21 or row == 23 or row == 25:
                        comboBox = QtWidgets.QComboBox()
                        if row == 0:
                            comboBox.addItems(self.list_shape)
                            comboBox.currentTextChanged.connect(self.activeParameters)
                        else:
                            comboBox.addItems(self.list_component)
                        if self.addition == 0:
                            self.fitp1.setCellWidget(row, col, comboBox)
                            comboBox.setCurrentIndex(int(list_pre_pk[row][col]))
                        else:
                            self.fitp1.setCellWidget(row, col + colPosition * 2, comboBox)
                            if list_pre_pk[row][col] != 0:
                                if row == 0:
                                    comboBox.setCurrentIndex(int(list_pre_pk[row][col]))
                                else:
                                    comboBox.setCurrentIndex(int(list_pre_pk[row][col] + colPosition))
                            else:
                                comboBox.setCurrentIndex(int(list_pre_pk[row][col]))
                    else:
                        if self.addition == 0:
                            item = self.fitp1.item(row, col)
                            if str(list_pre_pk[row][col]) == '':
                                item.setText('')
                            else:
                                item.setText(str(format(list_pre_pk[row][col], self.floating)))
                        else:
                            item = self.fitp1.item(row, col + colPosition * 2)
                            if str(list_pre_pk[row][col]) == '':
                                item.setText('')
                            else:
                                item.setText(str(format(list_pre_pk[row][col], self.floating)))


                else:
                    if row != 0 and row != 13 and row != 15 and row != 17 and row != 19 and row != 21 and row != 23 and row != 25:
                        if self.addition == 0:
                            item = self.fitp1.item(row, col)
                        else:
                            item = self.fitp1.item(row, col + colPosition * 2)
                        item.setText('')
                        if list_pre_pk[row][col] == 2:
                            item.setCheckState(QtCore.Qt.Checked)
                        else:
                            item.setCheckState(QtCore.Qt.Unchecked)
            for row in range(len(list_pre_pk_lims)):
                for col in range(len(list_pre_pk_lims[0])):
                    if self.addition == 0:
                        item = self.fitp1_lims.item(row, col)
                    else:
                        item = self.fitp1_lims.item(row, col + colPosition * 3)
                    if (col % 3) != 0:
                        if str(list_pre_pk_lims[row][col]) == '':
                            item.setText('')
                        else:
                            item.setText(str(format(list_pre_pk_lims[row][col], self.floating)))
                    else:
                        if list_pre_pk_lims[row][col] == 2:
                            item.setCheckState(QtCore.Qt.Checked)
                        else:
                            item.setCheckState(QtCore.Qt.Unchecked)
        self.activeParameters()
        self.lims_changed()

    def loadPreset(self):
        cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open data file', self.filePath, "DAT Files (*.dat)")
        if cfilePath != "":
            print(cfilePath)
            self.filePath = cfilePath
            with open(cfilePath, 'r') as file:
                temp_pre = file.read()
            file.close()
            # print(self.pre, type(self.pre))
            self.pre = ast.literal_eval(temp_pre)
            if type(self.pre[0][0]) == int:  # backwards compatibility for old presets which only allowed one single BG
                self.idx_bg = [self.pre[0][0]]
            else:
                self.idx_bg = self.pre[0][0]
            self.setButtonState(self.idx_bg)
            # self.pre = json.loads(self.pre) #json does not work due to the None issue
            # print(self.pre, type(self.pre))
            # self.comboBox_pres.clear()
            # self.comboBox_pres.setCurrentIndex(0)
            self.idx_pres = 0
            self.addition = 0
        else:
            self.pre = [[], [], [], []]

    def addPreset(self):
        cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open data file', self.filePath, "DAT Files (*.dat)")
        if cfilePath != "":
            print(cfilePath)
            self.filePath = cfilePath
            with open(cfilePath, 'r') as file:
                temp_pre = file.read()
            file.close()
            # print(self.pre, type(self.pre))
            self.pre = ast.literal_eval(temp_pre)
            # self.pre = json.loads(self.pre) #json does not work due to the None issue
            # print(self.pre, type(self.pre))
            # self.comboBox_pres.clear()
            # self.comboBox_pres.setCurrentIndex(0)
            self.idx_pres = 0
            self.addition = 1
        else:
            self.pre = [[], [], [], []]

    def savePreset(self):
        rowPosition = self.fitp0.rowCount()
        colPosition = self.fitp0.columnCount()
        list_pre_bg = []
        # save preset for bg
        for row in range(rowPosition):
            new = []
            for col in range(colPosition):
                if ((col % 2) != 0):
                    if self.fitp0.item(row, col) is None or len(self.fitp0.item(row, col).text()) == 0:
                        new.append('')
                    else:
                        new.append(float(self.fitp0.item(row, col).text()))
                else:
                    if self.fitp0.item(row, col) is None:
                        new.append('')
                    elif (row == 0 and col in [0, 2, 8]) or (row == 1 and col in [2, 4, 6, 8]):
                        new.append('')
                    else:
                        if self.fitp0.item(row, col).checkState() == 2:
                            new.append(2)
                        else:
                            new.append(0)
            list_pre_bg.append(new)
        rowPosition = self.fitp1.rowCount()
        colPosition = self.fitp1.columnCount()
        list_pre_pk = []
        # save preset for components
        for row in range(rowPosition):
            new = []
            for col in range(colPosition):
                if (col % 2) != 0:  #
                    if row == 0 or row == 13 or row == 15 or row == 17 or row == 19 or row == 21 or row == 23 or row == 25:
                        new.append(self.fitp1.cellWidget(row, col).currentIndex())
                    else:
                        if self.fitp1.item(row, col) is None or len(self.fitp1.item(row, col).text()) == 0:
                            new.append('')
                        else:
                            new.append(float(self.fitp1.item(row, col).text()))
                else:
                    if row != 0 and row != 13 and row != 15 and row != 17 and row != 19 and row != 21 and row != 23 and row != 25:
                        if self.fitp1.item(row, col).checkState() == 2:
                            new.append(2)
                        else:
                            new.append(0)
                    else:
                        if self.fitp1.item(row, col) is None or len(self.fitp1.item(row, col).text()) == 0:
                            new.append('')
                        else:
                            new.append(self.fitp1.item(row, col).text())
            list_pre_pk.append(new)
        rowPosition = self.fitp1_lims.rowCount()
        colPosition = self.fitp1_lims.columnCount()
        list_pre_lims = []
        for row in range(rowPosition):
            new = []
            for col in range(colPosition):
                if (col % 3) != 0:
                    if self.fitp1_lims.item(row, col) is None or len(self.fitp1_lims.item(row, col).text()) == 0:
                        new.append('')
                    else:
                        new.append(float(self.fitp1_lims.item(row, col).text()))
                else:
                    if self.fitp1_lims.item(row, col).checkState() == 2:
                        new.append(2)
                    else:
                        new.append(0)
            list_pre_lims.append(new)
        # self.parText = self.version + 'parameters\n\n[[Data file]]\n\n' + self.comboBox_file.currentText() + '\n\n[
        # [BG type]]\n\n' + str(self.comboBox_bg.currentIndex()) + '\n\n[[BG parameters]]\n\n' + str(list_pre_bg) +
        # '\n\n[[component parameters]]\n\n' + str(list_pre_pk) print(Text)

        self.parText = [[self.idx_bg, self.xmin, self.xmax, self.hv, self.wf, self.correct_energy]]
        self.parText.append(list_pre_bg)
        self.parText.append(list_pre_pk)
        self.parText.append(list_pre_lims)
        self.pre = [[self.idx_bg, self.xmin, self.xmax, self.hv, self.wf, self.correct_energy]]
        self.pre.append(list_pre_bg)
        self.pre.append(list_pre_pk)
        self.pre.append(list_pre_lims)

    def savePresetDia(self):
        if self.comboBox_file.currentIndex() > 0:
            cfilePath = os.path.dirname(str(self.comboBox_file.currentText()))
            fileName = os.path.basename(str(self.comboBox_file.currentText()))
            fileName = os.path.splitext(fileName)[0] + '_pars'
        else:
            cfilePath = self.filePath
            fileName = 'sample_pars'

        # S_File will get the directory path and extension.
        cfilePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Preset file',
                                                             cfilePath + os.sep + fileName + '.dat',
                                                             "DAT Files (*.dat)")
        if cfilePath != "":
            self.filePath = cfilePath
            # Finally, this will Save your file to the path selected.
            with open(cfilePath, 'w') as file:
                file.write(str(self.parText))
            file.close()

    def export_all(self):
        try:
            self.exportResults()
        except Exception as e:
            return self.raise_error(window_title="Error: could not export the results.",
                                    error_message='Exporting results failed. The following traceback may help to solve the issue:')
        try:
            self.savePreset()
        except Exception as e:
            return self.raise_error(window_title="Error: could not save parameters.",
                                    error_message='Saving parameters failed. The following traceback may help to solve the issue:')
        try:
            self.savePresetDia()
        except Exception as e:
            return self.raise_error(window_title="Error: could not save parameters /export data.",
                                    error_message='Saving parameters /exporting data failed. The following traceback may help to solve the issue:')

    def export_pickle(self, path_for_export: str):

        """
        Exporting all parameters as parText, export_pars and export_out.results as a dictionary in to pickle file.
            It taks path from exportResults function so path_for_export should end with ".txt"
        """

        ### this is an approche to export lmfit_results but  mod = PolynomialModel(3, prefix='pg_') is lockal and causing problems
        # lmfit_attr_dict = {}
        # for attr, value in self.export_out.__dict__.items():
        #     if attr == 'model':
        #         lmfit_attr_dict[attr] = value._reprstring() # Convert moodel to a string becaus pickle dos not work with local objects. bad: "mod = PolynomialModel(3, prefix='pg_')"
        #     else:
        #         lmfit_attr_dict[attr] = value

        with open(path_for_export.replace('.txt', '.pickle'), 'wb') as handle:
            pickle.dump({
                'LG4X_parameters': self.parText,
                'lmfit_parameters': self.export_pars,
                # 'lmfit_report':self.export_out.fit_report(min_correl=0.1)
                # 'lmfit_report': lmfit_attr_dict
                'lmfit_result': self.export_out.result
            },
                handle,
                protocol=pickle.HIGHEST_PROTOCOL)

    def exportResults(self):
        if not self.result.empty:
            if self.comboBox_file.currentIndex() > 0:
                # print(self.export_pars)
                # print(self.export_out.fit_report(min_correl=0.5))

                cfilePath = os.path.dirname(str(self.comboBox_file.currentText()))
                fileName = os.path.basename(str(self.comboBox_file.currentText()))
                fileName = os.path.splitext(fileName)[0]
            else:
                cfilePath = self.filePath
                fileName = 'sample'

            # S_File will get the directory path and extension.
            cfilePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Fit file',
                                                                 cfilePath + os.sep + fileName + '_fit.txt',
                                                                 "Text Files (*.txt)")
            if cfilePath != "":
                self.filePath = cfilePath
                if self.comboBox_file.currentIndex() == 0:
                    strmode = 'simulation mode'
                else:
                    strmode = self.comboBox_file.currentText()
                Text = self.version + '\n\n[[Data file]]\n\n' + strmode + '\n\n[[Fit results]]\n\n'

                # fit results to be checked
                # for key in self.export_out.params:
                # Text += str(key) + '\t' + str(self.export_out.params[key].value) + '\n'
                indpk = 0
                indpar = 0
                strpk = ''
                # strpar = ''
                ncomponent = self.fitp1.columnCount()
                ncomponent = int(ncomponent / 2)
                pk_name = np.array([None] * int(ncomponent), dtype='U')
                par_name = ['amplitude', 'center', 'sigma', 'gamma', 'fwhm', 'height', 'fraction', 'skew',
                            'q']  # [bug] add new params
                par_list = np.array([[None] * 9] * int(ncomponent), dtype='f')
                for key in self.export_out.params:
                    if str(key)[1] == 'g':
                        Text += str(key) + '\t' + str(self.export_out.params[key].value) + '\n'
                    else:
                        if len(strpk) > 0:
                            if str(key)[:int(str(key).find('_'))] == strpk:
                                strpar = str(key)[int(str(key).find('_')) + 1:]
                                for indpar in range(len(par_name)):
                                    if strpar == par_name[indpar]:
                                        par_list[indpk][indpar] = str(self.export_out.params[key].value)
                                        strpk = str(key)[:int(str(key).find('_'))]
                            else:
                                indpk += 1
                                indpar = 0
                                par_list[indpk][indpar] = str(self.export_out.params[key].value)
                                strpk = str(key)[:int(str(key).find('_'))]
                                pk_name[indpk] = strpk
                        else:
                            par_list[indpk][indpar] = str(self.export_out.params[key].value)
                            strpk = str(key)[:int(str(key).find('_'))]
                            pk_name[indpk] = strpk

                Text += '\n'
                for indpk in range(ncomponent):
                    Text += '\t' + pk_name[indpk]
                for indpar in range(9):
                    Text += '\n' + par_name[indpar] + '\t'
                    for indpk in range(ncomponent):
                        Text += str(par_list[indpk][indpar]) + '\t'

                self.savePreset()
                Text += '\n\n[[LG4X parameters]]\n\n' + str(self.parText) + '\n\n[[lmfit parameters]]\n\n' + str(
                    self.export_pars) + '\n\n' + str(self.export_out.fit_report(min_correl=0.1))

                self.export_pickle(cfilePath)  # export las fit parameters as dict int po pickle file

                with open(cfilePath, 'w') as file:
                    file.write(str(Text))
                file.close()
                # print(filePath)
                if cfilePath.split("_")[-1] == "fit.txt":
                    with open(cfilePath.rsplit("_", 1)[0] + '_fit.csv', 'w') as f:
                        f.write('#No of rows lightened (2D detector)' + str(
                            self.rows_lightened) + "(if not using 2D detector, value is 1 and can be ignored!)\n")
                        self.result.to_csv(f, index=False, mode='a')
                else:
                    with open(cfilePath.rsplit(".", 1)[0] + '.csv', 'w') as f:
                        f.write('#No of rows lightened (2D detector)' + str(
                            self.rows_lightened) + "(if not using 2D detector, value is 1 and can be ignored!)\n")
                        self.result.to_csv(f, index=False, mode='a')
                # print(self.result)

    def clickOnBtnImp(self, idx):
        self.plottitle.setText('')  # reset text in plot title QlineEdit, otherwise the old one will remain
        self.idx_imp = idx
        self.imp()

    def imp(self):
        index = self.idx_imp
        if index == 1 or index == 2:
            if index == 1:
                cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open csv file', self.filePath,
                                                                     'CSV Files (*.csv)')
            else:
                cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open tab-separated text file',
                                                                     self.filePath, 'TXT Files (*.txt)')
            if cfilePath != "":
                # print (cfilePath)
                self.filePath = cfilePath
                self.list_file.append(str(cfilePath))
                self.comboBox_file.clear()
                self.comboBox_file.addItems(self.list_file)
                index = self.comboBox_file.findText(str(cfilePath), QtCore.Qt.MatchFixedString)
                if index >= 0:
                    self.comboBox_file.setCurrentIndex(index)
                self.plot()
        if index == 3:
            cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open VAMAS file', self.filePath,
                                                                 'VMS Files (*.vms *.npl)')
            if cfilePath != "":
                # print (cfilePath)
                try:
                    self.list_vamas = vpy.list_vms(cfilePath)
                except Exception as e:
                    return self.raise_error(window_title="Error: could not load VAMAS file.",
                                            error_message='Loading VAMAS file failed. The following traceback may help to solve the issue:')
                try:
                    wf = vpy.get_wf(cfilePath)
                    if isinstance(wf, float):
                        self.wf= abs(wf)
                        self.wf_item.setText(str(abs(wf))) #we assume in the following, that the wf is defined positive
                        self.pre[0][4]=self.wf
                    else:
                        self.wf=4.0
                        self.wf_item.setText(str(4.0))
                        self.pre[0][4]=self.wf
                        raise Exception('Different work functions were detected for the different blocks in your Vamas file. Work function is defaulted to 4.0eV and needs to be adjusted manually.')
                except Exception as e:
                    return self.raise_error(window_title="Error: could not load VAMAS work function.",
                                            error_message=e.args[0])
                try:
                    hv = vpy.get_hv(cfilePath)
                    if isinstance(hv, float):
                        self.hv = hv
                        self.hv_item.setText(str(hv))
                        self.pre[0][3] = self.hv
                    else:
                        self.hv = 1486.6
                        self.hv_item.setText(str(1486.6))
                        self.pre[0][3] = self.hv

                        raise Exception(
                            'Different source energies were detected for the different blocks in your Vamas file. Source energy (hv) is defaulted to 1486.6eV and needs to be adjusted manually.')
                except Exception as e:
                    return self.raise_error(window_title="Error: could not load VAMAS source energy.",
                                            error_message=e.args[0])

                self.list_file.extend(self.list_vamas)

                # print (self.list_file)
                self.comboBox_file.clear()
                self.comboBox_file.addItems(self.list_file)
                index = self.comboBox_file.findText(str(self.list_vamas[0]), QtCore.Qt.MatchFixedString)
                if index > 0:
                    self.comboBox_file.setCurrentIndex(index)
                self.plot()
        if index == 4:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Open Directory", self.filePath,
                                                                   QtWidgets.QFileDialog.ShowDirsOnly)
            if directory != "":
                entries = os.listdir(directory)
                entries.sort()
                for entry in entries:
                    if os.path.splitext(entry)[1] == '.csv' or os.path.splitext(entry)[1] == '.txt':
                        self.list_file.append(str(directory + os.sep + entry))
                self.comboBox_file.clear()
                self.comboBox_file.addItems(self.list_file)
        self.idx_imp = 0

    def plot_pt(self):
        # component elements from periodic table window selection
        while len(self.ax.texts) > 0:
            for txt in self.ax.texts:
                txt.remove()
            self.canvas.draw()
            self.repaint()
            # self.ax.texts.remove()
        if self.pt.selected_elements:
            if self.pre[0][3] == None:
                if len(self.hv)==0:
                    self.pre[0][3]=1486.6
                    self.hv=1486.6
                else:
                    self.pre[0][3] = self.hv
            if self.pre[0][4] == None:
                if len(self.wf)==0:
                    self.pre[0][4]=4
                    self.wf=4
                else:
                    self.pre[0][4]=self.wf
            if self.pre[0][5] == None:
                if len(self.correct_energy) == 0:
                    self.pre[0][5] = 0
                    self.correct_energy = 0
                else:
                    self.pre[0][5] = self.correct_energy
            self.hv_item.setText(str(self.hv))
            self.wf_item.setText(str(self.wf))
            self.correct_energy_item.setText(str(self.correct_energy))
            hv=self.hv
            wf=self.wf

            ymin, ymax = self.ax.get_ylim()
            xmin, xmax = self.ax.get_xlim()
            for obj in self.pt.selected_elements:
                alka = ast.literal_eval(obj['alka'].values[0])
                if len(alka['trans']) > 0:
                    for orb in range(len(alka['trans'])):
                        if xmin > xmax:
                            en = float(alka['be'][orb])
                        else:
                            en = hv - wf - float(alka['be'][orb])-self.correct_energy
                        if (xmin > xmax and xmin > en > xmax) or (xmin < xmax and xmin < en < xmax):
                            elem_x = np.asarray([en])
                            elem_y = np.asarray([float(alka['rsf'][orb])])
                            elem_z = alka['trans'][orb]
                            # obj.symbol+elem_z, color="r", rotation="vertical")
                            self.ax.text(elem_x, ymin + (ymax - ymin) * math.log(elem_y + 1, 10) / 2,
                                         obj['symbol'].values[0] + elem_z, color="r", rotation="vertical")
                aes = ast.literal_eval(obj['aes'].values[0])
                if len(aes['trans']) > 0:
                    for orb in range(len(aes['trans'])):
                        if xmin > xmax:
                            en = hv - wf - float(aes['ke'][orb])-self.correct_energy
                        else:
                            en = float(aes['ke'][orb])
                        if (xmin > xmax and xmin > en > xmax) or (xmin < xmax and xmin < en < xmax):
                            elem_x = np.asarray([en])
                            elem_y = np.asarray([float(aes['rsf'][orb])])
                            elem_z = aes['trans'][orb]
                            # obj.symbol+elem_z, color="g", rotation="vertical")
                            self.ax.text(elem_x, ymin + (ymax - ymin) * math.log(elem_y + 1, 10),
                                         obj['symbol'].values[0] + elem_z,
                                         color="g", rotation="vertical")
            self.canvas.draw()
            self.repaint()

    def plot(self):
        plottitle = self.comboBox_file.currentText().split('/')[-1]
        # when file list is selected
        if self.comboBox_file.currentIndex() == 1:
            self.comboBox_file.clear()
            self.list_file = ['File list', 'Clear list']
            self.comboBox_file.addItems(self.list_file)
            self.comboBox_file.setCurrentIndex(0)
        elif self.comboBox_file.currentIndex() > 1:
            # self.df = np.loadtxt(str(self.comboBox_file.currentText()), delimiter=',', skiprows=1)
            fileName = os.path.basename(self.comboBox_file.currentText())
            if os.path.splitext(fileName)[1] == '.csv':
                try:  # change import, so that export file is detected
                    data = np.genfromtxt(str(self.comboBox_file.currentText()), dtype='str', delimiter=',', max_rows=2)
                    if all(elem in data for elem in ['x', 'raw_y', 'sum_fit']):
                        self.df = np.loadtxt(str(self.comboBox_file.currentText()), delimiter=',', skiprows=2,
                                             usecols=(0, 1))
                    else:
                        self.df = np.loadtxt(str(self.comboBox_file.currentText()), delimiter=',', skiprows=1)
                    # self.df = pd.read_csv(str(self.comboBox_file.currentText()), dtype = float,  skiprows=1,
                    # header=None)
                    strpe = np.loadtxt(str(self.comboBox_file.currentText()), dtype='str', delimiter=',', usecols=1,
                                       max_rows=1)
                    f = open(str(self.comboBox_file.currentText()), 'r')
                    header_line = str(f.readline())
                    if 'rows_lightened' in header_line:
                        self.rows_lightened = int(header_line.split('=')[1])
                    else:
                        self.rows_lightened = 1

                except Exception as e:
                    return self.raise_error(window_title="Error: could not load .csv file.",
                                            error_message='The input .csv is not in the correct format!. The following traceback may help to solve the issue:')


            else:
                try:
                    self.df = np.loadtxt(str(self.comboBox_file.currentText()), delimiter='\t', skiprows=1)
                    # self.df = pd.read_csv(str(self.comboBox_file.currentText()), dtype = float,  skiprows=1,
                    # header=None, delimiter = '\t')
                    strpe = np.loadtxt(str(self.comboBox_file.currentText()), dtype='str', delimiter='\t', usecols=1,
                                       max_rows=1)
                    f = open(str(self.comboBox_file.currentText()), 'r')
                    header_line = str(f.readline())
                    if 'rows_lightened' in header_line:
                        self.rows_lightened = int(header_line.split('=')[1])
                    else:
                        self.rows_lightened = 1
                except Exception as e:
                    return self.raise_error(window_title="Error: could not load input file.",
                                            error_message='The input file is not in the correct format!. The following traceback may help to solve the issue:')

            # I have moved the error handling here directly to the import, there may exist situations, where already the
            # Import would fail. I still left the following error handling there, but I am not sure if there are cases
            # where this second error handling still will be necessary. However, we should check, if x0 and y0 have same
            # lenght I think

            try:
                x0 = self.df[:, 0]
            except Exception as e:
                return self.raise_error(window_title="Error: could not load .csv file.",
                                        error_message='The input .csv is not in the correct format!. The following traceback may help to solve the issue:')
            try:
                y0 = self.df[:, 1]
            except Exception as e:
                return self.raise_error(window_title="Error: could not load .csv file.",
                                        error_message='The input .csv is not in the correct format!. The following traceback may help to solve the issue:')
            strpe = (str(strpe).split())

            if strpe[0] == 'PE:' and strpe[2] == 'eV':
                pe = float(strpe[1])
                print('Current Pass energy is PE= ', pe, 'eV')
                #item = QtWidgets.QTableWidgetItem(str(pe))
                #self.fitp0.setItem(0, 9, item)
                #self.fitp0.setItem(0, 8, QtWidgets.QTableWidgetItem('Pass energy (eV)'))
            # plt.cla()
            self.ar.cla()
            self.ax.cla()
            # ax = self.figure.add_subplot(221)
            # self.ax.plot(x0, y0, 'o', color="b", label="raw")
            self.ax.plot(x0, y0, linestyle='-', color="b", label="raw")
            if x0[0] > x0[-1]:
                # self.ax.invert_xaxis()
                self.ax.set_xlabel('Binding energy (eV)', fontsize=11)
            else:
                self.ax.set_xlabel('Energy (eV)', fontsize=11)

            plt.xlim(x0[0], x0[-1])
            self.ax.set_ylabel('Intensity (arb. unit)', fontsize=11)
            self.ax.grid(True)
            self.ax.legend(loc=0)
            self.canvas.draw()

            # item = QtWidgets.QTableWidgetItem(str(x0[0]))
            # self.fitp0.setItem(0, 1, item)
            # item = QtWidgets.QTableWidgetItem(str(x0[len(x0) - 1]))
            # self.fitp0.setItem(0, 3, item)

            # print(str(plt.get_fignums()))
        # select file list index ==0 to clear figure for simulation
        if self.comboBox_file.currentIndex() == 0 and self.comboBox_file.count() > 1:
            # plt.cla()
            self.ar.cla()
            self.ax.cla()
            self.canvas.draw()
        # macOS's compatibility issue on pyqt5, add below to update window
        self.repaint()

    def eva(self):
        # simulation mode if no data in file list, otherwise evaluation mode
        if self.comboBox_file.currentIndex() == 0:
            if self.xmin is not None and self.xmax is not None and len(str(self.xmin)) > 0 and len(str(self.xmax)) > 0:
                x1 = float(self.xmin)
                x2 = float(self.xmax)
            points = 999
            self.df = np.random.random_sample((points, 2)) + 0.01
            self.df[:, 0] = np.linspace(x1, x2, points)
            self.ana('sim')
        else:
            self.ana('eva')

    def fit(self):
        if self.comboBox_file.currentIndex() > 0:
            try:
                self.ana("fit")
                # self.fitter = Fitting(self.ana, "fit")
                # self.threadpool.start(self.fitter)
            except Exception as e:
                return self.raise_error(window_title="Error: Fitting failed!",
                                        error_message='Fitting was not successful. The following traceback may help to solve the issue:')
        else:
            print('No Data present, Switching to simulation mode!')
            if self.xmin is not None and self.xmax is not None and len(str(self.xmin)) > 0 and len(str(self.xmax)) > 0:
                x1 = float(self.xmin)
                x2 = float(self.xmax)
            points = 999
            self.df = np.random.random_sample((points, 2)) + 0.01
            self.df[:, 0] = np.linspace(x1, x2, points)
            self.ana('sim')

    def interrupt_fit(self):
        print("does nothing yet")

    def one_step_back_in_params_history(self):
        """
        Is called if button undo Fit is prest.
        """
        self.go_back_in_parameter_history = True
        self.fit()

    def history_manager(self, pars):
        """
        Manages saving of the fit parameters and presets (e.g. how many components, aktive backgrounds and so on) in a list.
        In this approach the insane function ana() must be extended. The ana() should be destroyd! and replaaced by couple of smaller methods for better readability

        Parameters
        ----------
            pars: list:
                parameters of the fit, whitch have to be saved
        return
            list: [self.pars, self.parText]
            or
            None: if self.go_back_in_parameter_history is False do nothing

        """
        if self.go_back_in_parameter_history is True:
            try:
                pars, pre = self.parameter_history_list.pop()
                self.go_back_in_parameter_history = False
                return pars, pre
            except IndexError:
                self.go_back_in_parameter_history = False
                return self.raise_error(window_title="Error: History empty!",
                                        error_message='First entry in parameter history reached. No further steps saved. The following traceback may help to solve the issue:')

        else:
            self.savePreset()
            self.parameter_history_list.append([pars, self.pre])
            return None

    def clickOnBtnBG(self):
        checked_actions = [action for action in self.bgMenu.actions() if action.isChecked()]
        idx_bg = set()
        for checked_action in checked_actions:
            if checked_action.text() == '&Static &Shirley BG' and '&Static &Tougaard BG' not in [
                checked_act.text() for checked_act in checked_actions]:
                idx_bg.add(0)
            elif checked_action.text() == '&Active &Shirley BG' and '&Static &Shirley BG' in [checked_act.text() for
                                                                                                  checked_act in
                                                                                                  checked_actions]:
                QtWidgets.QMessageBox.warning(self, 'Warning', 'You cannot choose both Active Shirley BG and Static '
                                                               'Shirley BG at the same time! Static Shirley BG set! To use Active Shirley BG, please uncheck Static '
                                                               'Shirley BG!')
                checked_action.setChecked(False)
                idx_bg.add(0)
            elif checked_action.text() == '&Active &Shirley BG' and '&Static &Shirley BG' not in [checked_act.text() for
                                                                                                  checked_act in
                                                                                                  checked_actions]:
                idx_bg.add(100)
            elif checked_action.text() == '&Static &Tougaard BG' and '&Static &Shirley BG' not in [
                checked_act.text() for checked_act in checked_actions]:
                idx_bg.add(1)
            elif checked_action.text() == '&Active &Tougaard BG' and '&Static &Tougaard BG' in [
                checked_act.text() for checked_act in checked_actions]:
                QtWidgets.QMessageBox.warning(self, 'Warning',
                                              'You cannot choose both Active Tougaard BG and Static Tougaard BG at '
                                              'the same time! Static Tougaard BG set! To use Active Tougaard BG, '
                                              'please uncheck Static Tougaard BG!')
                idx_bg.add(1)
                checked_action.setChecked(False)
            elif checked_action.text() == '&Active &Tougaard BG' and '&Static &Tougaard BG' not in [checked_act.text()
                                                                                                    for checked_act in
                                                                                                    checked_actions]:
                idx_bg.add(101)
            elif checked_action.text() == '&Polynomial BG':
                idx_bg.add(2)
            elif checked_action.text() == '&Slope BG':
                idx_bg.add(6)
            elif checked_action.text() == '&Arctan BG':
                idx_bg.add(3)
            elif checked_action.text() == '&Erf BG':
                idx_bg.add(4)
            elif checked_action.text() == '&VBM/Cutoff BG':
                idx_bg.add(5)
        if '&Static &Shirley BG' in [
            checked_act.text() for checked_act in checked_actions] and '&Static &Tougaard BG' in [
            checked_act.text() for checked_act in checked_actions]:
            QtWidgets.QMessageBox.warning(self, 'Warning',
                                      'You cannot choose both Static Shirley BG and Static Tougaard BG at '
                                      'the same time! Background was set to Static Shirley BG.')
            idx_bg.add(0)
            for checked_action in checked_actions:
                if checked_action.text() == '&Static &Tougaard BG':
                    checked_action.setChecked(False)
        if len(checked_actions) == 0:
            QtWidgets.QMessageBox.information(self, 'Info',
                                              'No background was choosen, a polynomial BG was set as default.')
            idx_bg.add(2)  # if no background was selected, a polynomial will be used
        self.idx_bg = sorted(idx_bg)

        self.pre[0][0] = self.idx_bg
        self.displayChoosenBG.setText(
            'Choosen Background: {}'.format('+ '.join([dictBG[str(idx)] for idx in self.idx_bg])))
        self.activeParameters()

    def write_pars(self, pars):
        return None

    def bgSelector(self, x, y, mode, idx_bg):
        if idx_bg == 0:
            shA = self.pre[1][0][1]
            shB = self.pre[1][0][3]
            pars = None
            mod = None
            bg_mod = xpy.shirley_calculate(x, y, shA, shB)
        if idx_bg == 100:
            if mode == "eva":
                shA = self.pre[1][0][1]
                shB = self.pre[1][0][3]
                pars = None
                mod = None
                bg_mod = xpy.shirley_calculate(x, y, shA, shB)
            else:
                mod = ShirleyBG(independent_vars=["y"], prefix='bg_shirley_')
                k = self.pre[1][0][5]
                const = self.pre[1][0][7]
                pars = mod.make_params()
                pars['bg_shirley_k'].value = float(k)
                pars['bg_shirley_const'].value = float(const)
                if self.pre[1][0][4] == 2:
                    pars['bg_shirley_k'].vary = False
                if self.pre[1][0][6] == 2:
                    pars['bg_shirley_const'].vary = False
                bg_mod = 0
        if idx_bg == 1:
            toB = self.pre[1][1][1]
            toC = self.pre[1][1][3]
            toCd = self.pre[1][1][5]
            toD = self.pre[1][1][7]
            toT0 = self.pre[1][1][9]
            pars = None
            mod = None
            if mode == 'fit':
                toM = self.pre[1][0][3]
                [bg_mod, bg_toB] = xpy.tougaard_calculate(x, y, toB, toC, toCd, toD, toM)
            else:
                toM = 1
                [bg_mod, bg_toB] = xpy.tougaard_calculate(x, y, toB, toC, toCd, toD, toM)
            self.pre[1][1][1] = bg_toB
        if idx_bg == 101:
            mod = TougaardBG(independent_vars=["x", "y"], prefix='bg_tougaard_')
            if self.pre[1][1][1] is None or self.pre[1][1][3] is None or self.pre[1][1][5] is None \
                    or self.pre[1][1][7] is None or self.pre[1][1][9] is None or len(
                str(self.pre[1][1][1])) == 0 or len(str(self.pre[1][1][3])) == 0 \
                    or len(str(self.pre[1][1][5])) == 0 or len(str(self.pre[1][1][7])) == 0 or len(
                str(self.pre[1][1][9])) == 0:
                pars = mod.guess(y, x=x, y=y)
            else:
                pars = mod.make_params()
                pars['bg_tougaard_B'].value = self.pre[1][1][1]
                if self.pre[1][1][0] == 2:
                    pars['bg_tougaard_B'].vary = False
                pars['bg_tougaard_C'].value = self.pre[1][1][3]
                pars['bg_tougaard_C'].vary = False
                pars['bg_tougaard_C_d'].value = self.pre[1][1][5]
                pars['bg_tougaard_C_d'].vary = False
                pars['bg_tougaard_D'].value = self.pre[1][1][7]
                pars['bg_tougaard_D'].vary = False
                pars['bg_tougaard_extend'].value = self.pre[1][1][9]
                pars['bg_tougaard_extend'].vary = False
            bg_mod = 0
        if idx_bg == 3:
            mod = StepModel(prefix='bg_arctan_', form='arctan')
            if self.pre[1][idx_bg + 1][1] is None or self.pre[1][idx_bg + 1][3] is None or self.pre[1][idx_bg + 1][
                5] is None \
                    or len(str(self.pre[1][idx_bg + 1][1])) == 0 or len(str(self.pre[1][idx_bg + 1][3])) == 0 \
                    or len(str(self.pre[1][idx_bg + 1][5])) == 0:
                pars = mod.guess(y, x=x)
            else:
                pars = mod.make_params()
                pars['bg_arctan_amplitude'].value = self.pre[1][idx_bg + 1][1]
                if self.pre[1][idx_bg + 1][0] == 2:
                    pars['bg_arctan_amplitude'].vary = False
                pars['bg_arctan_center'].value = self.pre[1][idx_bg + 1][3]
                if self.pre[1][idx_bg + 1][2] == 2:
                    pars['bg_arctan_center'].vary = False
                pars['bg_arctan_sigma'].value = self.pre[1][idx_bg + 1][5]
                if self.pre[1][idx_bg + 1][4] == 2:
                    pars['bg_arctan_sigma'].vary = False
            bg_mod = 0
        if idx_bg == 4:
            mod = StepModel(prefix='bg_step_', form='erf')
            if self.pre[1][idx_bg + 1][1] is None or self.pre[1][idx_bg + 1][3] is None or self.pre[1][idx_bg + 1][
                5] is None \
                    or len(str(self.pre[1][idx_bg + 1][1])) == 0 or len(str(self.pre[1][idx_bg + 1][3])) == 0 \
                    or len(str(self.pre[1][idx_bg + 1][5])) == 0:
                pars = mod.guess(y, x=x)
            else:
                pars = mod.make_params()
                pars['bg_step_amplitude'].value = self.pre[1][idx_bg + 1][1]
                if self.pre[1][idx_bg + 1][0] == 2:
                    pars['bg_step_amplitude'].vary = False
                pars['bg_step_center'].value = self.pre[1][idx_bg + 1][3]
                if self.pre[1][idx_bg + 1][2] == 2:
                    pars['bg_step_center'].vary = False
                pars['bg_step_sigma'].value = self.pre[1][idx_bg + 1][5]
                if self.pre[1][idx_bg + 1][4] == 2:
                    pars['bg_step_sigma'].vary = False
            bg_mod = 0

        if idx_bg == 5:
            if (x[0] > x[-1] and y[0] > y[-1]) or (x[0] < x[-1] and y[0] < y[-1]):
                # VBM
                def poly2vbm(x, ctr, d1, d2, d3, d4):
                    return (d1 * (x - ctr) + d2 * (x - ctr) ** 2 + d3 * (x - ctr) ** 3 + d4 * (x - ctr) ** 4) * (
                            x >= ctr)
            else:
                # cutoff/wf
                def poly2vbm(x, ctr, d1, d2, d3, d4):
                    return (d1 * (x - ctr) + d2 * (x - ctr) ** 2 + d3 * (x - ctr) ** 3 + d4 * (x - ctr) ** 4) * (
                            x <= ctr)

            mod = Model(poly2vbm, prefix='bg_vbm_')
            pars = mod.make_params()
            if self.pre[1][idx_bg + 1][1] is None or self.pre[1][idx_bg + 1][3] is None or self.pre[1][idx_bg + 1][
                5] is None \
                    or self.pre[1][idx_bg + 1][7] is None or self.pre[1][idx_bg + 1][9] is None \
                    or len(str(self.pre[1][idx_bg + 1][1])) == 0 or len(str(self.pre[1][idx_bg + 1][3])) == 0 \
                    or len(str(self.pre[1][idx_bg + 1][5])) == 0 or len(str(self.pre[1][idx_bg + 1][7])) == 0 \
                    or len(str(self.pre[1][idx_bg + 1][9])) == 0:
                pars['bg_vbm_ctr'].value = (x[0] + x[-1]) / 2
                pars['bg_vbm_d1'].value = 0
                pars['bg_vbm_d2'].value = 0
                pars['bg_vbm_d3'].value = 0
                pars['bg_vbm_d4'].value = 0
            else:
                pars['bg_vbm_ctr'].value = self.pre[1][idx_bg + 1][1]
                if self.pre[1][idx_bg + 1][0] == 2:
                    pars['bg_vbm_ctr'].vary = False
                pars['bg_vbm_d1'].value = self.pre[1][idx_bg + 1][3]
                if self.pre[1][idx_bg + 1][2] == 2:
                    pars['bg_vbm_d1'].vary = False
                pars['bg_vbm_d2'].value = self.pre[1][idx_bg + 1][5]
                if self.pre[1][idx_bg + 1][5] == 2:
                    pars['bg_vbm_d2'].vary = False
                pars['bg_vbm_d3'].value = self.pre[1][idx_bg + 1][7]
                if self.pre[1][idx_bg + 1][6] == 2:
                    pars['bg_vbm_d3'].vary = False
                pars['bg_vbm_d4'].value = self.pre[1][idx_bg + 1][9]
                if self.pre[1][idx_bg + 1][8] == 2:
                    pars['bg_vbm_d4'].vary = False
            bg_mod = 0
        if idx_bg == 2:
            mod = PolynomialModel(4, prefix='bg_poly_')
            bg_mod = 0
            if self.pre[1][2][1] is None or self.pre[1][2][3] is None or self.pre[1][2][5] is None \
                    or self.pre[1][2][7] is None or self.pre[1][2][9] is None or len(str(self.pre[1][2][1])) == 0 \
                    or len(str(self.pre[1][2][3])) == 0 or len(str(self.pre[1][2][5])) == 0 \
                    or len(str(self.pre[1][2][7])) == 0 or len(str(self.pre[1][2][9])) == 0:
                pars = mod.guess(y, x=x)
            else:
                pars = mod.make_params()
                for index in range(5):
                    pars['bg_poly_c' + str(index)].value = self.pre[1][2][2 * index + 1]
                    if self.pre[1][2][2 * index] == 2:
                        pars['bg_poly_c' + str(index)].vary = False
        if idx_bg == 6:
            mod = SlopeBG(independent_vars=['y'], prefix='bg_slope_')
            bg_mod = 0
            if self.pre[1][3][1] is None or len(str(self.pre[1][3][1])) == 0:
                pars = mod.guess(y, x=x)
            else:
                pars = mod.make_params()
                pars['bg_slope_k'].value = self.pre[1][3][1]
                if self.pre[1][3][0] == 2:
                    pars['bg_slope_k'].vary = False
        if self.fixedBG.isChecked() and pars!=None:
            for par in pars:
                pars[par].vary = False
        return [mod, bg_mod, pars]

    def PeakSelector(self, mod):
        pars_all = []
        ncomponent = self.fitp1.columnCount()
        nrows = self.fitp1.rowCount()
        ncomponent = int(ncomponent / 2)
        for index_pk in range(ncomponent):
            index = self.pre[2][0][2 * index_pk + 1]
            strind = self.list_shape[index]
            strind = strind.split(":", 1)[0]
            modp = model_selector(index, strind, index_pk)
            if mod is not None:
                mod += modp
            else:
                mod=modp
            if index_pk == 0:
                pars = modp.make_params()
            else:
                pars.update(modp.make_params())
            # fit parameters from self.pre
            if self.pre[2][1][2 * index_pk + 1] is not None and len(str(self.pre[2][1][2 * index_pk + 1])) > 0:
                pars[strind + str(index_pk + 1) + '_center'].value = float(self.pre[2][1][2 * index_pk + 1])
                if self.pre[2][1][2 * index_pk] == 2:
                    pars[strind + str(index_pk + 1) + '_center'].vary = False
            if self.pre[2][2][2 * index_pk + 1] is not None and len(str(self.pre[2][2][2 * index_pk + 1])) > 0:
                pars[strind + str(index_pk + 1) + '_amplitude'].value = float(self.pre[2][2][2 * index_pk + 1])
                pars[strind + str(index_pk + 1) + '_amplitude'].min = 0.0
                if self.pre[2][2][2 * index_pk] == 2:
                    pars[strind + str(index_pk + 1) + '_amplitude'].vary = False
            if self.pre[2][14][2 * index_pk + 1] is not None and len(str(self.pre[2][14][2 * index_pk + 1])) > 0:
                pars.add(strind + str(index_pk + 1) + "_center_diff", value=float(self.pre[2][14][2 * index_pk + 1]))
                if self.pre[2][14][2 * index_pk] == 2:
                    pars[strind + str(index_pk + 1) + '_center_diff'].vary = False
            if self.pre[2][16][2 * index_pk + 1] is not None and len(str(self.pre[2][16][2 * index_pk + 1])) > 0:
                pars.add(strind + str(index_pk + 1) + "_amp_ratio", value=float(self.pre[2][16][2 * index_pk + 1]),
                         min=0)
                if self.pre[2][16][2 * index_pk] == 2:
                    pars[strind + str(index_pk + 1) + '_amp_ratio'].vary = False
            if index == 0 or index == 2 or index == 4 or index == 5 or index == 6 or index == 7 or index == 8 or index == 12:
                if self.pre[2][4][2 * index_pk + 1] is not None and len(str(self.pre[2][4][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_sigma'].value = float(self.pre[2][4][2 * index_pk + 1])
                    pars[strind + str(index_pk + 1) + '_sigma'].min = 0
                    if self.pre[2][4][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_sigma'].vary = False
                if self.pre[2][20][2 * index_pk + 1] is not None and len(str(self.pre[2][20][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_gaussian_ratio",
                             value=float(self.pre[2][20][2 * index_pk + 1]), min=0)
                    if self.pre[2][20][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gaussian_ratio'].vary = False
            if index == 10 or index == 11:
                if self.pre[2][4][2 * index_pk + 1] is not None and len(str(self.pre[2][4][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_gaussian_sigma'].value = float(self.pre[2][4][2 * index_pk + 1])
                    pars[strind + str(index_pk + 1) + '_gaussian_sigma'].min = 0
                    if self.pre[2][4][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gaussian_sigma'].vary = False
                if self.pre[2][20][2 * index_pk + 1] is not None and len(str(self.pre[2][20][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_gaussian_ratio",
                             value=float(self.pre[2][20][2 * index_pk + 1]), min=0)
                    if self.pre[2][20][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gaussian_ratio'].vary = False
            if index == 1 or index == 3 or index == 9 or index == 10 or index == 11:
                if self.pre[2][3][2 * index_pk + 1] is not None and len(str(self.pre[2][3][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_sigma'].value = float(self.pre[2][3][2 * index_pk + 1])
                    pars[strind + str(index_pk + 1) + '_sigma'].min = 0
                    if self.pre[2][3][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_sigma'].vary = False
                if self.pre[2][18][2 * index_pk + 1] is not None and len(str(self.pre[2][18][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_lorentzian_ratio",
                             value=float(self.pre[2][18][2 * index_pk + 1]), min=0)
                    if self.pre[2][18][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_lorentzian_ratio'].vary = False
            if index == 2 or index == 6:
                if self.pre[2][3][2 * index_pk + 1] is not None and len(str(self.pre[2][3][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_gamma'].value = float(self.pre[2][3][2 * index_pk + 1])
                    pars[strind + str(index_pk + 1) + '_gamma'].min = 0
                    if self.pre[2][3][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gamma'].vary = False
                if self.pre[2][18][2 * index_pk + 1] is not None and len(str(self.pre[2][18][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_lorentzian_ratio",
                             value=float(self.pre[2][18][2 * index_pk + 1]), min=0)
                    if self.pre[2][18][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_lorentzian_ratio'].vary = False
            if index == 4 or index == 5 or index == 9 or index == 10 or index == 11:
                if self.pre[2][5][2 * index_pk + 1] is not None and len(str(self.pre[2][5][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_gamma'].value = float(self.pre[2][5][2 * index_pk + 1])
                    pars[strind + str(index_pk + 1) + '_gamma'].min = 0
                    pars[strind + str(index_pk + 1) + '_gamma'].max=1
                    if self.pre[2][5][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gamma'].vary = False
                if self.pre[2][22][2 * index_pk + 1] is not None and len(str(self.pre[2][22][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_gamma_ratio",
                             value=float(self.pre[2][22][2 * index_pk + 1]), min=0)
                    if self.pre[2][22][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gamma_ratio'].vary = False
            if index == 3:
                if self.pre[2][6][2 * index_pk + 1] is not None and len(str(self.pre[2][6][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_fraction'].value = float(self.pre[2][6][2 * index_pk + 1])
                    pars[strind + str(index_pk + 1) + '_fraction'].min = 0
                    pars[strind + str(index_pk + 1) + '_fraction'].max = 1
                    if self.pre[2][6][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_fraction'].vary = False
            if index == 6:
                if self.pre[2][7][2 * index_pk + 1] is not None and len(str(self.pre[2][7][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_skew'].value = float(self.pre[2][7][2 * index_pk + 1])
                    pars[strind + str(index_pk + 1) + '_skew'].min = -1
                    pars[strind + str(index_pk + 1) + '_skew'].max = 1
                    if self.pre[2][7][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_skew'].vary = False
            if index == 7:
                if self.pre[2][8][2 * index_pk + 1] is not None and len(str(self.pre[2][8][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_q'].value = float(self.pre[2][8][2 * index_pk + 1])
                    if self.pre[2][8][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_q'].vary = False
            if index == 12:
                if self.pre[2][9][2 * index_pk + 1] is not None and len(str(self.pre[2][9][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_kt'].value = float(self.pre[2][9][2 * index_pk + 1])
                    pars[strind + str(index_pk + 1) + '_kt'].min = 0
                    pars[strind + str(index_pk + 1) + '_kt'].max = 1
                    if self.pre[2][9][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_kt'].vary = False

            if index == 10:
                if self.pre[2][10][2 * index_pk + 1] is not None and len(str(self.pre[2][10][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_soc'].value = float(self.pre[2][10][2 * index_pk + 1])
                    if self.pre[2][10][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_soc'].vary = False
                if self.pre[2][24][2 * index_pk + 1] is not None and len(str(self.pre[2][24][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_soc_ratio", value=float(self.pre[2][24][2 * index_pk + 1]), min=0)
                    if self.pre[2][24][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_soc_ratio'].vary = False
                if self.pre[2][11][2 * index_pk + 1] is not None and len(str(self.pre[2][11][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_height_ratio'].value = float(self.pre[2][11][2 * index_pk + 1])
                    pars[strind + str(index_pk + 1) + '_height_ratio'].min = 0
                    if self.pre[2][11][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_height_ratio'].vary = False
                if self.pre[2][26][2 * index_pk + 1] is not None and len(str(self.pre[2][26][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_rel_height_ratio",
                             value=float(self.pre[2][26][2 * index_pk + 1]), min=0)
                    if self.pre[2][26][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_rel_height_ratio'].vary = False
                if self.pre[2][12][2 * index_pk + 1] is not None and len(str(self.pre[2][12][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_fct_coster_kronig'].value = float(self.pre[2][12][2 * index_pk + 1])
                    pars[strind + str(index_pk + 1) + '_fct_coster_kronig'].min = 0
                    if self.pre[2][12][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_fct_coster_kronig'].vary = False
            pars = self.ratio_setup(pars, index_pk, strind, index)
            pars_all.append(pars)
        return [mod, pars]

    def ratio_setup(self, pars, index_pk, strind, index):
        if index == 2 or index == 6:  # unset default expression which sets sigma and gamma for the voigt and skewed-voigt always to the same value
            pars[strind + str(index_pk + 1) + '_gamma'].expr = ''
            pars[strind + str(index_pk + 1) + '_gamma'].vary = True
        # amp ratio setup
        if self.pre[2][15][2 * index_pk + 1] > 0:
            pktar = self.pre[2][15][2 * index_pk + 1]
            strtar = self.list_shape[self.pre[2][0][2 * pktar - 1]]
            strtar = strtar.split(":", 1)[0]
            if self.pre[2][16][2 * index_pk + 1] is not None and len(str(self.pre[2][16][2 * index_pk + 1])) > 0:
                pars[strind + str(index_pk + 1) + '_amplitude'].expr = strtar + str(
                    pktar) + '_amplitude * ' + str(strind + str(index_pk + 1) + '_amp_ratio')

        # BE diff setup
        if self.pre[2][13][2 * index_pk + 1] > 0:
            pktar = self.pre[2][13][2 * index_pk + 1]
            strtar = self.list_shape[self.pre[2][0][2 * pktar - 1]]
            strtar = strtar.split(":", 1)[0]
            if self.pre[2][14][2 * index_pk + 1] is not None and len(str(self.pre[2][14][2 * index_pk + 1])) > 0:
                pars[strind + str(index_pk + 1) + '_center'].expr = strtar + str(
                    pktar) + '_center + ' + str(strind + str(index_pk + 1) + '_center_diff')

        # lorentzian sigma ref setup
        if self.pre[2][17][2 * index_pk + 1] > 0:
            pktar = self.pre[2][17][2 * index_pk + 1]
            strtar = self.list_shape[self.pre[2][0][2 * pktar - 1]]
            strtar = strtar.split(":", 1)[0]
            if self.pre[2][18][2 * index_pk + 1] is not None and len(str(self.pre[2][18][2 * index_pk + 1])) > 0:
                if index == 1 or index == 3 or index == 9 or index == 10 or index == 11:
                    if strtar in ['v', 'a']:
                        pars[strind + str(index_pk + 1) + '_sigma'].expr = strtar + str(
                            pktar) + '_gamma * ' + str(strind + str(index_pk + 1) + '_lorentzian_ratio')
                    else:

                        pars[strind + str(index_pk + 1) + '_sigma'].expr = strtar + str(
                            pktar) + '_sigma * ' + str(strind + str(index_pk + 1) + '_lorentzian_ratio')
                if index == 2 or index == 6:
                    if strtar not in ['v', 'a']:
                        pars[strind + str(index_pk + 1) + '_gamma'].expr = strtar + str(
                            pktar) + '_sigma * ' + str(strind + str(index_pk + 1) + '_lorentzian_ratio')
                    else:
                        pars[strind + str(index_pk + 1) + '_gamma'].expr = strtar + str(
                            pktar) + '_gamma * ' + str(strind + str(index_pk + 1) + '_lorentzian_ratio')

        # gaussian sigma ref setup
        if self.pre[2][19][2 * index_pk + 1] > 0:
            pktar = self.pre[2][19][2 * index_pk + 1]
            strtar = self.list_shape[self.pre[2][0][2 * pktar - 1]]
            strtar = strtar.split(":", 1)[0]
            if self.pre[2][20][2 * index_pk + 1] is not None and len(str(self.pre[2][20][2 * index_pk + 1])) > 0:
                if index == 0 or index == 2 or index == 4 or index == 5 or index == 6 or index == 7 or index == 8 or index == 12:
                    if strtar in ['gds', 'gdd']:
                        pars[strind + str(index_pk + 1) + '_sigma'].expr = strtar + str(
                            pktar) + '_gaussian_sigma * ' + str(strind + str(index_pk + 1) + '_gaussian_ratio')
                    else:
                        pars[strind + str(index_pk + 1) + '_sigma'].expr = strtar + str(
                            pktar) + '_sigma * ' + str(strind + str(index_pk + 1) + '_gaussian_ratio')
                if index == 10 or index == 11:
                    if strtar not in ['gds', 'gdd']:
                        pars[strind + str(index_pk + 1) + '_gaussian_sigma'].expr = strtar + str(
                            pktar) + '_sigma * ' + str(strind + str(index_pk + 1) + '_gaussian_ratio')
                    else:
                        pars[strind + str(index_pk + 1) + '_gaussian_sigma'].expr = strtar + str(
                            pktar) + '_gaussian_sigma * ' + str(strind + str(index_pk + 1) + '_gaussian_ratio')

        # gamma ref setup
        if self.pre[2][21][2 * index_pk + 1] > 0:
            pktar = self.pre[2][21][2 * index_pk + 1]
            strtar = self.list_shape[self.pre[2][0][2 * pktar - 1]]
            strtar = strtar.split(":", 1)[0]
            if self.pre[2][22][2 * index_pk + 1] is not None and len(str(self.pre[2][22][2 * index_pk + 1])) > 0:
                if (index == 9 or index == 10 or index == 11) and (strtar in ['d', 'gdd', 'gds']):
                    pars[strind + str(index_pk + 1) + '_gamma'].expr = strtar + str(pktar) + '_gamma * ' + str(
                        strind + str(index_pk + 1) + '_gamma_ratio')
                if index == 4 and strtar == 'e':
                    pars[strind + str(index_pk + 1) + '_gamma'].expr = strtar + str(pktar) + '_gamma * ' + str(
                        strind + str(index_pk + 1) + '_gamma_ratio')
                if index == 5 and strtar == 's':
                    pars[strind + str(index_pk + 1) + '_gamma'].expr = strtar + str(pktar) + '_gamma * ' + str(
                        strind + str(index_pk + 1) + '_gamma_ratio')
        # soc ref and height ratio ref setup
        if index == 10:
            if self.pre[2][23][2 * index_pk + 1] > 0:
                pktar = self.pre[2][23][2 * index_pk + 1]
                strtar = self.list_shape[self.pre[2][0][2 * pktar - 1]]
                strtar = strtar.split(":", 1)[0]
                if self.pre[2][24][2 * index_pk + 1] is not None and len(str(self.pre[2][24][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_soc'].expr = strtar + str(pktar) + '_soc * ' + str(
                        strind + str(index_pk + 1) + '_soc_ratio')

            if self.pre[2][25][2 * index_pk + 1] > 0:
                pktar = self.pre[2][25][2 * index_pk + 1]
                strtar = self.list_shape[self.pre[2][0][2 * pktar - 1]]
                strtar = strtar.split(":", 1)[0]
                if self.pre[2][26][2 * index_pk + 1] is not None and len(str(self.pre[2][26][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_height_ratio'].expr = strtar + str(
                        pktar) + '_height_ratio * ' + str(strind + str(index_pk + 1) + '_rel_height_ratio')
        return pars

    def peak_limits(self, pars):
        nrows = self.fitp1_lims.rowCount()
        ncols = self.fitp1_lims.columnCount()
        ncols = int(ncols / 3)
        for index_pk in range(ncols):
            index = self.pre[2][0][2 * index_pk + 1]
            strind = self.list_shape[index]
            strind = strind.split(":", 1)[0]
            for row in range(nrows):
                if row == 0 and self.pre[3][row][3 * index_pk] == 2:
                    if self.pre[3][row][3 * index_pk + 1] is not None and len(
                            str(self.pre[3][row][3 * index_pk + 1])) > 0:
                        pars[strind + str(index_pk + 1) + '_center'].min = self.pre[3][row][3 * index_pk + 1]
                    if self.pre[3][row][3 * index_pk + 2] is not None and len(
                            str(self.pre[3][row][3 * index_pk + 2])) > 0:
                        pars[strind + str(index_pk + 1) + '_center'].max = self.pre[3][row][3 * index_pk + 2]
                if row == 1 and self.pre[3][row][3 * index_pk] == 2:
                    if self.pre[3][row][3 * index_pk + 1] is not None and len(
                            str(self.pre[3][row][3 * index_pk + 1])) > 0:
                        pars[strind + str(index_pk + 1) + '_amplitude'].min = self.pre[3][row][3 * index_pk + 1]
                    if self.pre[3][row][3 * index_pk + 2] is not None and len(
                            str(self.pre[3][row][3 * index_pk + 2])) > 0:
                        pars[strind + str(index_pk + 1) + '_amplitude'].max = self.pre[3][row][3 * index_pk + 2]
                if row == 12 and self.pre[3][row][3 * index_pk] == 2:
                    if self.pre[3][row][3 * index_pk + 1] is not None and len(
                            str(self.pre[3][row][3 * index_pk + 1])) > 0:
                        pars[strind + str(index_pk + 1) + '_center_diff'].min = self.pre[3][row][3 * index_pk + 1]
                    if self.pre[3][row][3 * index_pk + 2] is not None and len(
                            str(self.pre[3][row][3 * index_pk + 2])) > 0:
                        pars[strind + str(index_pk + 1) + '_center_diff'].max = self.pre[3][row][3 * index_pk + 2]
                if row == 13 and self.pre[3][row][3 * index_pk] == 2:
                    if self.pre[3][row][3 * index_pk + 1] is not None and len(
                            str(self.pre[3][row][3 * index_pk + 1])) > 0:
                        pars[strind + str(index_pk + 1) + '_amp_ratio'].min = self.pre[3][row][3 * index_pk + 1]
                    if self.pre[3][row][3 * index_pk + 2] is not None and len(
                            str(self.pre[3][row][3 * index_pk + 2])) > 0:
                        pars[strind + str(index_pk + 1) + '_amp_ratio'].max = self.pre[3][row][3 * index_pk + 2]
                if index == 0 or index == 2 or index == 4 or index == 5 or index == 6 or index == 7 or index == 8 or index == 12:
                    if row == 3 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_sigma'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_sigma'].max = self.pre[3][row][3 * index_pk + 2]
                    if row == 15 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_gaussian_ratio'].min = self.pre[3][row][
                                3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_gaussian_ratio'].max = self.pre[3][row][
                                3 * index_pk + 2]
                if index == 10 or index == 11:
                    if row == 3 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_gaussian_sigma'].min = self.pre[3][row][
                                3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_gaussian_sigma'].max = self.pre[3][row][
                                3 * index_pk + 2]
                    if row == 15 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_gaussian_ratio'].min = self.pre[3][row][
                                3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_gaussian_ratio'].max = self.pre[3][row][
                                3 * index_pk + 2]
                if index == 1 or index == 3 or index == 9 or index == 10 or index == 11:
                    if row == 2 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_sigma'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_sigma'].max = self.pre[3][row][3 * index_pk + 2]
                    if row == 14 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_lorentzian_ratio'].min = self.pre[3][row][
                                3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_lorentzian_ratio'].max = self.pre[3][row][
                                3 * index_pk + 2]
                if index == 2 or index == 6:
                    if row == 2 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_gamma'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_gamma'].max = self.pre[3][row][3 * index_pk + 2]
                    if row == 14 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_lorentzian_ratio'].min = self.pre[3][row][
                                3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_lorentzian_ratio'].max = self.pre[3][row][
                                3 * index_pk + 2]
                if index == 4 or index == 5 or index == 9 or index == 10 or index == 11:
                    if row == 4 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_gamma'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_gamma'].max = self.pre[3][row][3 * index_pk + 2]
                    if row == 16 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_gamma_ratio'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_gamma_ratio'].max = self.pre[3][row][3 * index_pk + 2]
                if index == 3:
                    if row == 5 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_fraction'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_fraction'].max = self.pre[3][row][3 * index_pk + 2]
                if index == 6:
                    if row == 6 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_skew'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_skew'].max = self.pre[3][row][3 * index_pk + 2]
                if index == 7:
                    if row == 7 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_q'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_q'].max = self.pre[3][row][3 * index_pk + 2]
                if index == 12:
                    if row == 8 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_kt'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_kt'].max = self.pre[3][row][3 * index_pk + 2]

                if index == 10:
                    if row == 9 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_soc'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_soc'].max = self.pre[3][row][3 * index_pk + 2]
                    if row == 17 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_soc_ratio'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_soc_ratio'].max = self.pre[3][row][3 * index_pk + 2]
                    if row == 10 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_height_ratio'].min = self.pre[3][row][3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_height_ratio'].max = self.pre[3][row][3 * index_pk + 2]
                    if row == 18 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_rel_height_ratio'].min = self.pre[3][row][
                                3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_rel_height_ratio'].max = self.pre[3][row][
                                3 * index_pk + 2]
                    if row == 11 and self.pre[3][row][3 * index_pk] == 2:
                        if self.pre[3][row][3 * index_pk + 1] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 1])) > 0:
                            pars[strind + str(index_pk + 1) + '_fct_coster_kronig'].min = self.pre[3][row][
                                3 * index_pk + 1]
                        if self.pre[3][row][3 * index_pk + 2] is not None and len(
                                str(self.pre[3][row][3 * index_pk + 2])) > 0:
                            pars[strind + str(index_pk + 1) + '_fct_coster_kronig'].max = self.pre[3][row][
                                3 * index_pk + 2]
        return pars

    def bgResult2Pre(self, out_params, mode, idx_bgs):
        for idx_bg in idx_bgs:
            if idx_bg == 6:
                self.pre[1][3][1] = out_params['bg_slope_k'].value
            if idx_bg == 100:
                if mode != "eva":
                    self.pre[1][0][5] = out_params['bg_shirley_k'].value
                    self.pre[1][0][7] = out_params['bg_shirley_const'].value
            if idx_bg == 101:
                self.pre[1][1][1] = out_params['bg_tougaard_B'].value
                self.pre[1][1][3] = out_params['bg_tougaard_C'].value
                self.pre[1][1][5] = out_params['bg_tougaard_C_d'].value
                self.pre[1][1][7] = out_params['bg_tougaard_D'].value
                self.pre[1][1][9] = out_params['bg_tougaard_extend'].value
            if idx_bg == 3:
                self.pre[1][idx_bg + 1][1] = out_params['bg_arctan_amplitude'].value
                self.pre[1][idx_bg + 1][3] = out_params['bg_arctan_center'].value
                self.pre[1][idx_bg + 1][5] = out_params['bg_arctan_sigma'].value

            if idx_bg == 4:
                self.pre[1][idx_bg + 1][1] = out_params['bg_step_amplitude'].value
                self.pre[1][idx_bg + 1][3] = out_params['bg_step_center'].value
                self.pre[1][idx_bg + 1][5] = out_params['bg_step_sigma'].value
            if idx_bg == 5:
                self.pre[1][idx_bg + 1][1] = out_params['bg_vbm_ctr'].value
                self.pre[1][idx_bg + 1][3] = out_params['bg_vbm_d1'].value
                self.pre[1][idx_bg + 1][5] = out_params['bg_vbm_d2'].value
                self.pre[1][idx_bg + 1][7] = out_params['bg_vbm_d3'].value
                self.pre[1][idx_bg + 1][9] = out_params['bg_vbm_d4'].value
            if idx_bg == 2:
                for index in range(5):
                    self.pre[1][2][2 * index + 1] = out_params['bg_poly_c' + str(index)].value

    def peakResult2Pre(self, out_params, mode):
        ncomponent = self.fitp1.columnCount()
        nrows = self.fitp1.rowCount()
        ncomponent = int(ncomponent / 2)
        for index_pk in range(ncomponent):
            index = self.pre[2][0][2 * index_pk + 1]
            strind = self.list_shape[index]
            strind = strind.split(":", 1)[0]
            # fit parameters from self.pre
            self.pre[2][1][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_center'].value
            self.pre[2][2][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_amplitude'].value
            self.pre[2][14][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_center_diff'].value
            self.pre[2][16][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_amp_ratio'].value
            if index == 0 or index == 2 or index == 4 or index == 5 or index == 6 or index == 7 or index == 8 or index == 12:
                self.pre[2][4][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_sigma'].value
                self.pre[2][20][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_gaussian_ratio'].value
            if index == 10 or index == 11:
                self.pre[2][4][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_gaussian_sigma'].value
                self.pre[2][20][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_gaussian_ratio'].value
            if index == 1 or index == 3 or index == 9 or index == 10 or index == 11:
                self.pre[2][3][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_sigma'].value
                self.pre[2][18][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_lorentzian_ratio'].value
            if index == 2 or index == 6:
                self.pre[2][3][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_gamma'].value
                self.pre[2][18][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_lorentzian_ratio'].value
            if index == 4 or index == 5 or index == 9 or index == 10 or index == 11:
                self.pre[2][5][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_gamma'].value
                self.pre[2][22][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_gamma_ratio'].value
            if index == 3:
                self.pre[2][6][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_fraction'].value
            if index == 6:
                self.pre[2][7][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_skew'].value
            if index == 7:
                self.pre[2][8][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_q'].value
            if index == 12:
                self.pre[2][9][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_kt'].value

            if index == 10:
                self.pre[2][10][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_soc'].value
                self.pre[2][24][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_soc_ratio'].value
                self.pre[2][11][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_height_ratio'].value
                self.pre[2][26][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_rel_height_ratio'].value
                self.pre[2][12][2 * index_pk + 1] = out_params[strind + str(index_pk + 1) + '_fct_coster_kronig'].value

    def result2Par(self, out_params, mode):
        self.bgResult2Pre(out_params, mode, self.idx_bg)
        self.peakResult2Pre(out_params, mode)

    def fillTabResults(self, x, y, out):
        y_components = [0 for idx in range(len(y))]
        nrows = len(self.pre[2])
        ncols = int(len(self.pre[2][0]) / 2)
        for index_pk in range(int(len(self.pre[2][0]) / 2)):
            index = self.pre[2][0][2 * index_pk + 1]
            strind = self.list_shape[index]
            strind = strind.split(":", 1)[0]
            y_components += out.eval_components()[strind + str(index_pk + 1) + '_']
        area_components = integrate.simps([y for y, x in zip(y_components, x)])
        for index_pk in range(int(len(self.pre[2][0]) / 2)):
            index = self.pre[2][0][2 * index_pk + 1]
            strind = self.list_shape[index]
            strind = strind.split(":", 1)[0]
            if index == 0:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_fwhm'].value, self.floating)))
                self.res_tab.setItem(0, index_pk, item)
                item = QtWidgets.QTableWidgetItem('')
                self.res_tab.setItem(1, index_pk, item)
            if index == 1:
                item = QtWidgets.QTableWidgetItem('')
                self.res_tab.setItem(0, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_fwhm'].value, self.floating)))
                self.res_tab.setItem(1, index_pk, item)
            if index == 0 or index == 1 or index == 2 or index == 3 or index == 11:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_fwhm'].value, self.floating)))
                self.res_tab.setItem(3, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_height'].value, self.floating)))
                self.res_tab.setItem(5, index_pk, item)
                y_area = out.eval_components()[strind + str(index_pk + 1) + '_']
                area = abs(integrate.simps([y for y, x in zip(y_area, x)], x))
                item = QtWidgets.QTableWidgetItem(str(format(area, '.1f') + r' ({}%)'.format(format(100, '.2f'))))
                self.res_tab.setItem(7, index_pk, item)
                item = QtWidgets.QTableWidgetItem(str(format(area, '.1f') + r' ({}%)'.format(format(100, '.2f'))))
                self.res_tab.setItem(8, index_pk, item)
                item = QtWidgets.QTableWidgetItem('')
                self.res_tab.setItem(2, index_pk, item)
                item = QtWidgets.QTableWidgetItem('')
                self.res_tab.setItem(4, index_pk, item)
                item = QtWidgets.QTableWidgetItem('')
                self.res_tab.setItem(6, index_pk, item)
                item = QtWidgets.QTableWidgetItem('')
                self.res_tab.setItem(8, index_pk, item)
            if index == 4 or index == 5 or index == 6 or index == 7 or index == 8 or index == 9 or index == 12:
                rows = self.res_tab.rowCount()
                for row in range(rows):
                    if row != 7:
                        item = QtWidgets.QTableWidgetItem('')
                        self.res_tab.setItem(row, index_pk, item)
                    # included area
                    y_area = out.eval_components()[strind + str(index_pk + 1) + '_']
                    area = abs(integrate.simps([y for y, x in zip(y_area, x)], x))
                    item = QtWidgets.QTableWidgetItem(str(format(area, '.1f') + r' ({}%)'.format(format(100, '.2f'))))
                    self.res_tab.setItem(7, index_pk, item)
                    item = QtWidgets.QTableWidgetItem(str(format(area, '.1f') + r' ({}%)'.format(format(100, '.2f'))))
                    self.res_tab.setItem(9, index_pk, item)
            if index == 2:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_sigma'].value, self.floating)))
                self.res_tab.setItem(0, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_gamma'].value, self.floating)))
                self.res_tab.setItem(1, index_pk, item)
            if index == 3:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_sigma'].value, self.floating)))
                self.res_tab.setItem(0, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_sigma'].value, self.floating)))
                self.res_tab.setItem(1, index_pk, item)
            if index == 11:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_lorentzian_fwhm'].value, self.floating)))
                self.res_tab.setItem(1, index_pk, item)
                y_area = out.eval_components()[strind + str(index_pk + 1) + '_']
                if np.max(y_area) != 0:
                    y_temp = y_area / np.max(y_area)
                    x_ = [i for i, j in zip(x, y_temp) if j >= 0.5]
                    fwhm_temp = x_[-1] - x_[0]
                    item = QtWidgets.QTableWidgetItem(str(format(fwhm_temp, self.floating)))
                    self.res_tab.setItem(3, index_pk, item)
                else:
                    print("WARNING: Invalid value encountered in true division: Probably one of the amplitudes is "
                          "set to 0.")
                    item = QtWidgets.QTableWidgetItem("Error in calculation")
                    self.res_tab.setItem(3, index_pk, item)
                # included area
                area = abs(integrate.simps([y for y, x in zip(y_area, x)], x))
                item = QtWidgets.QTableWidgetItem(
                    str(format(area, '.1f') + r' ({}%)'.format(format(area / area_components * 100, '.2f'))))
                self.res_tab.setItem(7, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(area, '.1f') + r' ({}%)'.format(format(area / area_components * 100, '.2f'))))
                self.res_tab.setItem(9, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_height'].value, self.floating)))
                self.res_tab.setItem(5, index_pk, item)
            if index == 10:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_lorentzian_fwhm_p1'].value, self.floating)))
                self.res_tab.setItem(1, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_lorentzian_fwhm_p2'].value, self.floating)))
                self.res_tab.setItem(2, index_pk, item)
                # included fwhm
                y_area_p1 = singlett(x,
                                     amplitude=out.params[strind + str(index_pk + 1) + '_amplitude'].value,
                                     sigma=out.params[strind + str(index_pk + 1) + '_sigma'].value,
                                     gamma=out.params[strind + str(index_pk + 1) + '_gamma'].value,
                                     gaussian_sigma=out.params[
                                         strind + str(index_pk + 1) + '_gaussian_sigma'].value,
                                     center=out.params[strind + str(index_pk + 1) + '_center'].value)
                y_area_p2 = singlett(x, amplitude=out.params[strind + str(index_pk + 1) + '_amplitude'].value
                                                  * out.params[strind + str(index_pk + 1) + '_height_ratio'].value,
                                     sigma=out.params[strind + str(index_pk + 1) + '_sigma'].value
                                           * out.params[strind + str(index_pk + 1) + '_fct_coster_kronig'].value,
                                     gamma=out.params[strind + str(index_pk + 1) + '_gamma'].value,
                                     gaussian_sigma=out.params[
                                         strind + str(index_pk + 1) + '_gaussian_sigma'].value,
                                     center=out.params[strind + str(index_pk + 1) + '_center'].value
                                            - out.params[strind + str(index_pk + 1) + '_soc'].value)
                if np.max(y_area_p1) != 0 and np.max(y_area_p2) != 0:
                    y_temp_p1 = y_area_p1 / np.max(y_area_p1)
                    x_p1 = [i for i, j in zip(x, y_temp_p1) if j >= 0.5]
                    fwhm_temp_p1 = x_p1[-1] - x_p1[0]
                    item = QtWidgets.QTableWidgetItem(str(format(fwhm_temp_p1, self.floating)))
                    self.res_tab.setItem(3, index_pk, item)
                    y_temp_p2 = y_area_p2 / np.max(y_area_p2)
                    x_p2 = [i for i, j in zip(x, y_temp_p2) if j >= 0.5]
                    fwhm_temp_p2 = x_p2[-1] - x_p2[0]
                    item = QtWidgets.QTableWidgetItem(str(format(fwhm_temp_p2, self.floating)))
                    self.res_tab.setItem(4, index_pk, item)
                else:
                    print("WARNING: Invalid value encountered in true division: Probably one of the amplitudes is "
                          "set to 0.")
                    item = QtWidgets.QTableWidgetItem("Error in calculation")
                    self.res_tab.setItem(3, index_pk, item)
                    item = QtWidgets.QTableWidgetItem("Error in calculation")
                    self.res_tab.setItem(4, index_pk, item)

                    # included area
                area_p1 = integrate.simps([y for y, x in zip(y_area_p1, x)])
                area_p2 = integrate.simps([y for y, x in zip(y_area_p2, x)])
                area_ges = area_p1 + area_p2
                item = QtWidgets.QTableWidgetItem(
                    str(format(area_p1, '.1f') + r' ({}%)'.format(format(area_p1 / area_ges * 100, '.2f'))))
                self.res_tab.setItem(7, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(area_p2, '.1f') + r' ({}%)'.format(format(area_p2 / area_ges * 100, '.2f'))))
                self.res_tab.setItem(8, index_pk, item)
                y_area = out.eval_components()[strind + str(index_pk + 1) + '_']
                area = abs(integrate.simps([y for y, x in zip(y_area, x)], x))
                item = QtWidgets.QTableWidgetItem(
                    str(format(area, '.1f') + r' ({}%)'.format(format(area / area_components * 100, '.2f'))))
                self.res_tab.setItem(9, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_height_p1'].value, self.floating)))
                self.res_tab.setItem(5, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_height_p2'].value, self.floating)))
                self.res_tab.setItem(6, index_pk, item)
            self.res_tab.resizeColumnsToContents()
            self.res_tab.resizeRowsToContents()
            self.fitp1.resizeColumnsToContents()
            self.fitp1.resizeRowsToContents()

    def BGModCreator(self, x, y, mode):
        temp_res = self.bgSelector(x, y, mode=mode, idx_bg=self.idx_bg[0])
        mod = temp_res[0]
        bg_mod = temp_res[1]
        pars = temp_res[2]

        for idx_bg in self.idx_bg[1:]:
            temp_res = self.bgSelector(x, y, mode, idx_bg)
            if mod is None and temp_res[0] is None:
                mod = None
            elif mod is None and temp_res[0] is not None:
                mod = temp_res[0]
            elif mod is not None and temp_res[0] is None:
                mod = mod
            elif mod is not None and temp_res[0] is not None:
                mod += temp_res[0]
            bg_mod += temp_res[1]
            if pars is not None:
                pars.update(temp_res[2])
            else:
                pars=temp_res[2]
        return mod, bg_mod, pars

    def ana(self, mode):
        self.savePreset()
        plottitle = self.plottitle.text()
        # self.df = np.loadtxt(str(self.comboBox_file.currentText()), delimiter=',', skiprows=1)
        x0 = self.df[:, 0]
        x0_corrected=np.copy(x0)
        if self.correct_energy is not None:
            x0_corrected -= self.correct_energy
        y0 = self.df[:, 1]
        # print(x0[0], x0[len(x0)-1])

        # plot graph after selection data from popup
        # plt.clf()
        # plt.cla()
        self.ax.cla()
        self.ar.cla()
        # ax = self.figure.add_subplot(211)
        if mode == 'fit':
            self.ax.plot(x0_corrected, y0, 'o', color='b', label='raw')
        else:
            # simulation mode
            if mode == 'sim':
                self.ax.plot(x0_corrected, y0, ',', color='b', label='raw')
            # evaluation mode
            else:
                self.ax.plot(x0_corrected, y0, 'o', mfc='none', color='b', label='raw')

        if x0_corrected[0] > x0_corrected[-1]:
            self.ax.set_xlabel('Binding energy (eV)', fontsize=11)
        else:
            self.ax.set_xlabel('Energy (eV)', fontsize=11)
        plt.xlim(x0_corrected[0], x0_corrected[-1])
        self.ax.grid(True)
        self.ax.set_ylabel('Intensity (arb. unit)', fontsize=11)
        if len(plottitle) == 0:
            if mode == 'sim':
                # simulation mode
                self.ar.set_title('Simulation', fontsize=11)
            else:
                short_file_name = self.comboBox_file.currentText().split('/')[-1]
                self.ar.set_title(short_file_name, fontsize=11)
                self.plottitle.setText(short_file_name)
                self.ar.set_title(short_file_name, fontsize=11)
        else:
            self.ar.set_title(r"{}".format(plottitle), fontsize=11)

        # if no range is specified, fill it from data
        if self.pre[0][1] is None or len(str(self.pre[0][1])) == 0:
            self.pre[0][1] = x0_corrected[0]
        if self.pre[0][2] is None or len(str(self.pre[0][2])) == 0:
            self.pre[0][2] = x0_corrected[-1]
        # check if limits are out of of data range, If incorrect, back to default
        x1 = self.pre[0][1]
        if ((x1 > x0_corrected[0] or x1 < x0_corrected[-1]) and x0_corrected[0] > x0[-1]) or (
                (x1 < x0_corrected[0] or x1 > x0_corrected[-1]) and x0_corrected[0] < x0_corrected[-1]):
            x1 = x0_corrected[0]
            self.pre[0][1] = x1
        x2 = self.pre[0][2]
        if ((x2 < x0_corrected[-1] or x2 > x1) and x0_corrected[0] > x0_corrected[-1]) or (
                (x2 > x0_corrected[-1] or x2 < x1) and x0_corrected[0] < x0[-1]):
            x2 = x0_corrected[-1]
            self.pre[0][2] = x2

        [x, y] = xpy.fit_range(x0_corrected, y0, x1, x2)
        raw_y = y.copy()
        raw_x = x.copy()
        if self.correct_energy is not None:
            raw_x += self.correct_energy
        # BG model selection and call shirley and tougaard
        # colPosition = self.fitp1.columnCount()

        temp_res = self.BGModCreator(x, y, mode=mode)
        mod = temp_res[0]
        bg_mod = temp_res[1]
        pars = temp_res[2]
        self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
        # component model selection and construction
        y -= bg_mod
        temp_res = self.PeakSelector(mod)
        if pars != None:
            pars.update(temp_res[1])
        else:
            pars=temp_res[1]

        mod = temp_res[0]

        if mode == 'eva' or mode == 'sim':
            for par in pars:
                pars[par].vary = False
        else:
            temp = self.peak_limits(pars)
            pars.update(temp)  # update pars before using expr, to prevent missing pars

        # evaluate model and optimize parameters for fitting in lmfit
        if mode == 'eva':
            strmode = 'Evaluation'
        elif mode == 'sim':
            strmode = "Simulation"
        else:
            strmode = 'Fitting'
        self.statusBar().showMessage(strmode + ' running.', )
        init = mod.eval(pars, x=x, y=y)
        zeros_in_data=False
        if np.any(raw_y == 0):
            zeros_in_data=True
            print('There were 0\'s in your data. The residuals are therefore not weighted by sqrt(data)!')
        try:
            if mode == 'eva' or mode== 'sim':
                if zeros_in_data:
                    out = mod.fit(y, pars, x=x, weights=1 / (np.sqrt(self.rows_lightened)), y=y)
                else:
                    out = mod.fit(y, pars, x=x, weights=1 / (np.sqrt(raw_y) * np.sqrt(self.rows_lightened)), y=y)
            else:
                try_me_out = self.history_manager(pars)
                if try_me_out is not None:
                    pars, pre = try_me_out
                    self.pre = pre
                    self.setPreset(pre[0], pre[1], pre[2], pre[3])
                if zeros_in_data:
                    out = mod.fit(y, pars, x=x, weights=1 / (np.sqrt(self.rows_lightened)), y=raw_y)

                else:
                    out = mod.fit(y, pars, x=x, weights=1 / (np.sqrt(raw_y) * np.sqrt(self.rows_lightened)), y=raw_y)

        except Exception as e:
            return self.raise_error(window_title="Error: NaN in Model/data!.",
                                error_message=e.args[0])
        comps = out.eval_components(x=x)
        # fit results to be checked
        for key in out.params:
            print(key, "=", out.params[key].value)

        # fit results print

        results = strmode + ' done: ' + out.method + ', # data: ' + str(out.ndata) + ', # func evals: ' + str(
            out.nfev) + ', # varys: ' + str(out.nvarys) + ', r chi-sqr: ' + str(
            format(out.redchi, self.floating)) + ', Akaike info crit: ' + str(
            format(out.aic, self.floating)) + ', Last run finished: ' + QTime.currentTime().toString()
        self.statusBar().showMessage(results)

        # component results into table
        self.result2Par(out.params, mode)
        self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
        self.fillTabResults(x, y, out)
        # Fit stats to GUI:
        if mode == 'eva' or mode == "sim":
            for index_pk in range(int(len(self.pre[2][0]))):
                item = QtWidgets.QTableWidgetItem('Evaluation mode')
                self.res_tab.setItem(0, index_pk, item)
                for i in range(self.res_tab.columnCount() - 1):
                    item = QtWidgets.QTableWidgetItem('-')
                    self.res_tab.setItem(i, index_pk, item)
            item = QtWidgets.QTableWidgetItem('-')
            self.stats_tab.setItem(0, 0, item)
            item = QtWidgets.QTableWidgetItem('Evaluation mode.')
            self.stats_tab.setItem(1, 0, item)
            for i in range(2, 6, 1):
                item = QtWidgets.QTableWidgetItem('-')
                self.stats_tab.setItem(i, 0, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.chisqr, self.floating)))
            self.stats_tab.setItem(6, 0, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.redchi, self.floating)))
            self.stats_tab.setItem(7, 0, item)
            for i in range(8, 10, 1):
                item = QtWidgets.QTableWidgetItem('-')
                self.stats_tab.setItem(i, 0, item)
        else:
            item = QtWidgets.QTableWidgetItem(str(out.success))
            self.stats_tab.setItem(0, 0, item)
            message = '\n'.join(out.message[i:i + 64] for i in range(0, len(out.message), 64))
            item = QtWidgets.QTableWidgetItem(str(message))
            self.stats_tab.setItem(1, 0, item)
            item = QtWidgets.QTableWidgetItem(str(out.nfev))
            self.stats_tab.setItem(2, 0, item)
            item = QtWidgets.QTableWidgetItem(str(out.nvarys))
            self.stats_tab.setItem(3, 0, item)
            item = QtWidgets.QTableWidgetItem(str(out.ndata))
            self.stats_tab.setItem(4, 0, item)
            item = QtWidgets.QTableWidgetItem(str(out.nfree))
            self.stats_tab.setItem(5, 0, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.chisqr, self.floating)))
            self.stats_tab.setItem(6, 0, item)
            if zeros_in_data:
                item = QtWidgets.QTableWidgetItem(str(format(out.redchi, self.floating))+' not weigthed by sqrt(data)')
            else:
                item = QtWidgets.QTableWidgetItem(str(format(out.redchi, self.floating)))
            self.stats_tab.setItem(7, 0, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.aic, self.floating)))
            self.stats_tab.setItem(8, 0, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.bic, self.floating)))
            self.stats_tab.setItem(9, 0, item)
        self.stats_tab.resizeColumnsToContents()
        self.stats_tab.resizeRowsToContents()
        sum_background = np.array([0.] * len(x))
        self.bg_comps = dict()
        for key in comps:
            if 'bg_' in key:
                self.bg_comps[key] = comps[key]
                sum_background += comps[key]
        if mode == "sim":
            self.ar.set_title(r"Simulation mode", fontsize=11)
        if mode == 'eva':
            plottitle=self.plottitle.text()
            if len(plottitle) == 0:
                plottitle = self.comboBox_file.currentText().split('/')[-1]
            # ax.plot(x, init+bg_mod, 'b--', lw =2, label='initial')
            if plottitle != '':
                self.ar.set_title(r"{}".format(plottitle), fontsize=11)
            # self.ax.plot(x, out.best_fit + bg_mod, 'k-', lw=2, label='initial')
            len_idx_pk = int(self.fitp1.columnCount() / 2)
            for index_pk in range(len_idx_pk):
                # print(index_pk, color)
                strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
                strind = strind.split(":", 1)[0]
                self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + sum_background + bg_mod,
                                     sum_background + bg_mod, label=self.fitp1.horizontalHeaderItem(2*index_pk+1).text())
                self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + sum_background + bg_mod)
                if index_pk == len_idx_pk - 1:
                    self.ax.plot(x, + sum_background + bg_mod, label='BG')
            self.ax.set_xlim(left=self.xmin)
            self.ar.set_xlim(left=self.xmin)
            self.ax.set_xlim(right=self.xmax)
            self.ar.set_xlim(right=self.xmax)
            self.ax.plot(x, out.best_fit + bg_mod, 'r-', lw=2, label='sum')
            self.ar.plot(x, out.residual, 'g.', label='residual')
            autoscale_y(self.ax)

        else:
            # ax.plot(x, init+bg_mod, 'k:', label='initial')
            plottitle = self.plottitle.text()
            if len(plottitle) == 0:
                plottitle = self.comboBox_file.currentText().split('/')[-1]
            if plottitle != '':
                self.ar.set_title(r"{}".format(plottitle), fontsize=11)
            len_idx_pk = int(self.fitp1.columnCount() / 2)
            for index_pk in range(len_idx_pk):
                strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
                strind = strind.split(":", 1)[0]
                self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + bg_mod + sum_background,
                                     bg_mod + sum_background, label=self.fitp1.horizontalHeaderItem(2*index_pk+1).text())
                self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + bg_mod + sum_background)
                if index_pk == len_idx_pk - 1:
                    self.ax.plot(x, + bg_mod + sum_background, label="BG")
            self.ax.set_xlim(left=self.xmin)
            self.ar.set_xlim(left=self.xmin)
            self.ax.set_xlim(right=self.xmax)
            self.ar.set_xlim(right=self.xmax)
            self.ax.plot(x, out.best_fit + bg_mod, 'r-', lw=2, label='fit')
            self.ar.plot(x, out.residual, 'g.', label='residual')  # modify residual and red chi-squared [feature]
            lines = self.ax.get_lines()
            autoscale_y(self.ax)
        self.ax.legend(loc=0)
        self.ar.legend(loc=0)
        self.canvas.draw()

        # make fit results to be global to export
        self.export_pars = pars
        self.export_out = out
        # for key in out.params:
        # print(key, "=", out.params[key].value)
        # make dataFrame and concat to export
        df_raw_x = pd.DataFrame(raw_x, columns=['raw_x'])
        df_raw_y = pd.DataFrame(raw_y, columns=['raw_y'])
        df_corrected_x = pd.DataFrame(x, columns=['corrected x'])
        df_y = pd.DataFrame(raw_y - sum_background - bg_mod, columns=['data-bg'])
        df_pks = pd.DataFrame(out.best_fit - sum_background - bg_mod, columns=['sum_components'])
        df_sum = pd.DataFrame(out.best_fit, columns=['sum_fit'])
        df_b = pd.DataFrame(sum_background + bg_mod, columns=['bg'])
        self.result = pd.concat([df_raw_x, df_raw_y,df_corrected_x, df_y, df_pks, df_b, df_sum], axis=1)
        df_bg_comps = pd.DataFrame.from_dict(self.bg_comps, orient='columns')
        self.result = pd.concat([self.result, df_bg_comps], axis=1)
        for index_pk in range(int(self.fitp1.columnCount() / 2)):
            strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
            strind = strind.split(":", 1)[0]
            df_c = pd.DataFrame(comps[strind + str(index_pk + 1) + '_'], columns=[self.fitp1.horizontalHeaderItem(2*index_pk+1).text()])
            self.result = pd.concat([self.result, df_c], axis=1)
        print(out.fit_report())
        lim_reached = False
        at_zero = False
        for key in out.params:
            if (out.params[key].value == out.params[key].min or out.params[key].value == out.params[key].max):
                if out.params[key].value != 0:
                    lim_reached = True
                    print('Limit reached for ', key)
                else:
                    at_zero = True
                    print(key, ' is at limit. Value is at 0.0. That was probably intended and can be ignored!')

        if at_zero:
            self.set_status('at_zero')
        if lim_reached:
            self.set_status('limit_reached')
        # macOS's compatibility issue on pyqt5, add below to update window
        self.repaint()

    def center(self):
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def closeEvent(self, event):
        event.accept()
        sys.exit(0)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = PrettyWidget()
    sys.exit(app.exec_())
