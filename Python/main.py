# LG4X: lmfit gui for xps curve fitting, Copyright (C) 2021, Hideki NAKAJIMA, Synchrotron Light Research Institute,
# Thailand modified by Julian Hochhaus, TU Dortmund University.

import ast
import math
import os
import sys
import pickle

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThreadPool, QRunnable, pyqtSlot
from lmfit import Model
from lmfit.models import ExponentialGaussianModel, SkewedGaussianModel, SkewedVoigtModel, DoniachModel, \
    BreitWignerModel, LognormalModel
from lmfit.models import GaussianModel, LorentzianModel, VoigtModel, PseudoVoigtModel, ThermalDistributionModel, \
    PolynomialModel, StepModel
from matplotlib import style
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import vamas_export as vpy
import xpspy as xpy
from periodictable import PeriodicTable
from usrmodel import ConvGaussianDoniachDublett, ConvGaussianDoniachSinglett, FermiEdgeModel, singlett, fft_convolve
from scipy import integrate
from scipy import interpolate
from helpers import *
import threading

import traceback  # error handling
import logging  # error handling

# style.use('ggplot')    
style.use('seaborn-pastel')
dictBG = {
    '0': 'static ShirleyBG (+Polynomial BG)',
    '100': 'active ShirleyBG (+Polynomial BG)',
    '1': 'static TougaardBG (+Polynomial BG)',
    '101': 'active TougaardBG (+Polynomial BG)',
    '2': 'Polynomial BG',
    '3': 'arctan (+Polynomial BG)',
    '4': 'Error function (+Polynomial BG)',
    '5': 'CutOff (+Polynomial BG)',

}


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


class PrettyWidget(QtWidgets.QMainWindow):
    def __init__(self):
        super(PrettyWidget, self).__init__()
        # super(PrettyWidget, self).__init__()
        self.rows_lightened = 1
        self.idx_bg = None
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
        self.initUI()

    def initUI(self):
        self.version = 'LG4X: LMFit GUI for XPS curve fitting experimental version'
        self.floating = '.4f'
        self.setGeometry(700, 500, 1600, 900)
        self.center()
        self.setWindowTitle(self.version)
        self.statusBar().showMessage(
            'Copyright (C) 2022, Julian Hochhaus, TU Dortmund University')
        self.pt = PeriodicTable()
        self.pt.setWindowTitle('Periodic Table')
        self.pt.elementEmitted.connect(self.handleElementClicked)
        self.pt.selectedElements = []
        # data template
        # self.df = pd.DataFrame()
        self.df = []
        self.result = pd.DataFrame()
        outer_layout = QtWidgets.QVBoxLayout()

        self.idx_imp = 0

        self.idx_bg = 0

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

        btn_preset_ptable = QtWidgets.QAction('&Periodic Table', self)
        # btn_preset_ptable.setShortcut('Ctrl+Shift+')
        btn_preset_ptable.triggered.connect(lambda: self.clickOnBtnPreset(idx=7))

        presetMenu.addAction(btn_preset_new)
        presetMenu.addAction(btn_preset_load)
        presetMenu.addAction(btn_preset_append)
        presetMenu.addAction(btn_preset_save)
        presetMenu.addAction(btn_preset_c1s)
        presetMenu.addAction(btn_preset_ckedge)
        presetMenu.addAction(btn_preset_ptable)

        self.bgMenu = menubar.addMenu('&Choose BG')
        self.submenu_shirley = self.bgMenu.addMenu('&Shirley BG')
        btn_bg_shirley_act = QtWidgets.QAction('&Active approach', self)
        btn_bg_shirley_act.triggered.connect(lambda: self.clickOnBtnBG(idx=0, activeBG=True))
        btn_bg_shirley_static = QtWidgets.QAction('&Static approach', self)
        btn_bg_shirley_static.triggered.connect(lambda: self.clickOnBtnBG(idx=0, activeBG=False))
        self.submenu_shirley.addAction(btn_bg_shirley_act)
        self.submenu_shirley.addAction(btn_bg_shirley_static)
        self.submenu_tougaard = self.bgMenu.addMenu('&Tougaard BG')
        btn_bg_tougaard_act = QtWidgets.QAction('&Active approach', self)
        btn_bg_tougaard_act.triggered.connect(lambda: self.clickOnBtnBG(idx=1, activeBG=True))
        btn_bg_tougaard_static = QtWidgets.QAction('&Static approach', self)
        btn_bg_tougaard_static.triggered.connect(lambda: self.clickOnBtnBG(idx=1, activeBG=False))
        self.submenu_tougaard.addAction(btn_bg_tougaard_act)
        self.submenu_tougaard.addAction(btn_bg_tougaard_static)

        btn_bg_polynomial = QtWidgets.QAction('&Polynomial BG', self)
        btn_bg_polynomial.setShortcut('Ctrl+Alt+P')
        btn_bg_polynomial.triggered.connect(lambda: self.clickOnBtnBG(idx=2))
        btn_bg_arctan = QtWidgets.QAction('&Arctan BG', self)
        btn_bg_arctan.triggered.connect(lambda: self.clickOnBtnBG(idx=3))

        btn_bg_erf = QtWidgets.QAction('&Erf BG', self)
        btn_bg_erf.triggered.connect(lambda: self.clickOnBtnBG(idx=4))

        btn_bg_vbm = QtWidgets.QAction('&VBM/Cutoff BG', self)
        btn_bg_vbm.triggered.connect(lambda: self.clickOnBtnBG(idx=5))

        btn_tougaard_cross_section = QtWidgets.QAction('Tougaard &Cross Section ', self)
        btn_tougaard_cross_section.triggered.connect(self.clicked_cross_section)

        self.bgMenu.addAction(btn_bg_polynomial)
        self.bgMenu.addAction(btn_bg_arctan)
        self.bgMenu.addAction(btn_bg_erf)
        self.bgMenu.addAction(btn_bg_vbm)
        self.bgMenu.addSeparator()
        self.bgMenu.addAction(btn_tougaard_cross_section)
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
        self.xmin_item = QtWidgets.QLineEdit()
        self.xmin = 270
        self.xmin_item.insert(str(self.xmin))
        self.xmin_item.textChanged.connect(self.update_com_vals)
        min_form.addRow("x_min: ", self.xmin_item)
        plot_settings_layout.addLayout(min_form)
        max_form = QtWidgets.QFormLayout()
        self.xmax_item = QtWidgets.QLineEdit()
        self.xmax = 300
        self.xmax_item.insert(str(self.xmax))
        self.xmax_item.textChanged.connect(self.update_com_vals)
        max_form.addRow("x_max: ", self.xmax_item)
        plot_settings_layout.addLayout(max_form)
        hv_form = QtWidgets.QFormLayout()
        self.hv_item = QtWidgets.QLineEdit()
        self.hv = 1486.6
        self.hv_item.insert(str(self.hv))
        self.hv_item.textChanged.connect(self.update_com_vals)
        hv_form.addRow("hv: ", self.hv_item)
        plot_settings_layout.addLayout(hv_form)
        wf_form = QtWidgets.QFormLayout()
        self.wf_item = QtWidgets.QLineEdit()
        self.wf = 4
        self.wf_item.insert(str(self.wf))
        self.wf_item.textChanged.connect(self.update_com_vals)
        wf_form.addRow("wf: ", self.wf_item)
        plot_settings_layout.addLayout(wf_form)
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
        list_bg_row = ['Shirley (cv, it, k, c)', 'Tougaard(B, C, C*, D)', 'Polynomial',
                       'arctan (amp, ctr, sig)', 'erf (amp, ctr, sig)', 'cutoff (ctr, d1-4)']
        self.fitp0 = QtWidgets.QTableWidget(len(list_bg_row), len(list_bg_col) * 2)
        list_bg_colh = ['', 'bg_c0', '', 'bg_c1', '', 'bg_c2', '', 'bg_c3', '', 'bg_c4']
        self.fitp0.setHorizontalHeaderLabels(list_bg_colh)
        self.fitp0.setVerticalHeaderLabels(list_bg_row)
        # set BG table checkbox
        for row in range(len(list_bg_row)):
            for col in range(len(list_bg_colh)):
                if (row >= 2 or (row == 0 and 8 > col >= 4) or (row == 1 and col == 0)) and col % 2 == 0:
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
                  [2, 2866.0, '', 1643.0, '', 1.0, '', 1.0, '', ''],
                  [2, 0, 2, 0, 2, 0, 2, 0, 2, 0]]
        # self.setPreset([0], pre_bg, [])

        self.fitp0.resizeColumnsToContents()
        self.fitp0.resizeRowsToContents()
        bg_fixedLayout = QtWidgets.QHBoxLayout()
        self.fixedBG = QtWidgets.QCheckBox('Keep background fixed')
        self.displayChoosenBG.setText('Choosen Background:{}'.format(dictBG[str(self.idx_bg)]))
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
        btn_rem.clicked.connect(self.rem_col)
        componentbuttons_layout.addWidget(btn_rem)

        btn_limit_set = QtWidgets.QPushButton('&Set/Show Limits', self)
        btn_limit_set.resize(btn_limit_set.sizeHint())
        btn_limit_set.clicked.connect(self.setLimits)
        componentbuttons_layout.addWidget(btn_limit_set)

        layout_bottom_mid.addLayout(componentbuttons_layout)

        # set Fit Table
        list_col = ['C_1']
        list_row = ['model', 'center', 'amplitude', 'lorentzian (sigma/gamma)', 'gaussian(sigma)', 'asymmetry(gamma)',
                    'frac', 'skew', 'q', 'kt', 'soc',
                    'height_ratio',
                    'fct_coster_kronig', 'center_ref', 'ctr_diff', 'amp_ref', 'ratio', 'lorentzian_ref', 'ratio',
                    'gaussian_ref', 'ratio',
                    'asymmetry_ref', 'ratio', 'soc_ref', 'ratio', 'height_ref', 'ratio']

        self.fitp1 = QtWidgets.QTableWidget(len(list_row), len(list_col) * 2)
        list_colh = ['', 'C_1']
        self.fitp1.setHorizontalHeaderLabels(list_colh)
        self.fitp1.setVerticalHeaderLabels(list_row)
        list_row_limits = [
            'center', 'amplitude', 'lorentzian (sigma/gamma)', 'gaussian(sigma)', 'asymmetry(gamma)', 'frac', 'skew',
            'q', 'kt', 'soc',
            'height', "fct_coster_kronig", 'ctr_diff', 'amp_ratio', 'lorentzian_ratio', 'gaussian_ratio',
            'asymmetry_ratio', 'soc_ratio', 'height_ratio']
        list_colh_limits = ['C_1', 'min', 'max']
        self.fitp1_lims = QtWidgets.QTableWidget(len(list_row_limits), len(list_col) * 3)
        self.fitp1_lims.setHorizontalHeaderLabels(list_colh_limits)
        self.fitp1_lims.setVerticalHeaderLabels(list_row_limits)
        # self.list_shape = ['g', 'l', 'v', 'p']
        self.list_shape = ['g: Gaussian', 'l: Lorentzian', 'v: Voigt', 'p: PseudoVoigt', 'e: ExponentialGaussian',
                           's: SkewedGaussian', 'a: SkewedVoigt', 'b: BreitWigner', 'n: Lognormal', 'd: Doniach',
                           'gdd: Convolution Gaussian/Doniach-Dublett', 'gds: Convolution Gaussian/Doniach-Singlett',
                           'fe:Convolution FermiDirac/Gaussian']
        self.list_component = ['', '1']

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
        for row in range(len(list_row_limits)):
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
        self.pre = [[self.idx_bg, self.xmin, self.xmax, self.hv, self.wf], pre_bg, pre_pk, [[0, '', '']] * 19]
        self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])

        self.fitp1.resizeColumnsToContents()
        self.fitp1.resizeRowsToContents()
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
        list_res_row = ['gaussian_fwhm', 'lorentzian_fwhm_p1', 'lorentzian_fwhm_p2', 'fwhm_p1', 'fwhm_p2', 'height_p1',
                        'height_p2', 'approx. area_p1', 'approx. area_p2', 'area_total']
        self.res_tab = QtWidgets.QTableWidget(len(list_res_row), len(list_col))
        self.res_tab.setHorizontalHeaderLabels(list_col)
        self.res_tab.setVerticalHeaderLabels(list_res_row)
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

    def clicked_cross_section(self):
        window_cross_section = Window_CrossSection()

        window_cross_section.show()
        window_cross_section.btn_cc.clicked.connect(lambda: self.setCrossSection(window_cross_section))

    def setCrossSection(self, window):
        window.choosenElement()
        tougaard = window.tougaard_params
        for idx in range(4):
            self.pre[1][1][2 * idx + 1] = tougaard[idx]
        self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])

    def activeParameters(self):
        """

        """
        nrows = self.fitp0.rowCount()
        ncols = self.fitp0.columnCount()
        for col in range(ncols):
            for row in range(nrows):
                if not row == 2:
                    self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                       col).flags() & ~ QtCore.Qt.ItemIsEditable & ~QtCore.Qt.ItemIsEnabled & ~QtCore.Qt.ItemIsSelectable)
        idx = self.idx_bg
        for col in range(ncols):
            for row in range(nrows):
                if idx == 0:
                    if row == 0 and col < 4:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if idx == 100:
                    if row == 0:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if idx == 1:
                    if row == 1:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if idx == 101:
                    if row == 1:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if idx == 3:
                    if row == 3:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if idx == 4:
                    if row == 4:
                        self.fitp0.item(row, col).setFlags(self.fitp0.item(row,
                                                                           col).flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if idx == 5:
                    if row == 5:
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
                    print(row,col)
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
        self.xmin = float(self.xmin_item.text())
        self.xmax = float(self.xmax_item.text())
        self.hv = float(self.hv_item.text())
        self.wf = float(self.wf_item.text())
        self.pre[0] = [self.idx_bg, self.xmin, self.xmax, self.hv, self.wf]

    def setLimits(self):
        self.sub_window = SubWindow(params_tab=self.fitp1_lims)
        self.sub_window.show()

    def raise_error(self, windowTitle: str) -> None:
        self.error_dialog.setWindowTitle(windowTitle)
        self.error_dialog.showMessage(traceback.format_exc())
        logging.error(traceback.format_exc())
        return None

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
        new_comp = [[0 for x in range(2)] for y in range(rowPosition)]

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
                    new_comp[int(row+1)][1] = float(self.fitp1.item(row + 1, colPosition_fitp1 - 1).text())+ add_fac
                    item = QtWidgets.QTableWidgetItem(
                        str(format(float(self.fitp1.item(row + 1, colPosition_fitp1 - 1).text()) + add_fac,
                                   self.floating)))
                    self.fitp1.setItem(row + 1, colPosition_fitp1 + 1, item)
        # add DropDown component selection for amp_ref and ctr_ref and keep values as it is
        self.list_component.append(str(int(1 + colPosition_fitp1 / 2)))
        for i in range(7):
            for col in range(int(colPosition_fitp1 / 2) + 1):
                if col < int(colPosition_fitp1 / 2):
                    index = self.fitp1.cellWidget(13 + 2 * i, 2 * col + 1).currentIndex()
                comboBox = QtWidgets.QComboBox()
                comboBox.addItems(self.list_component)
                comboBox.setMaximumWidth(55)
                if index > 0 and col < int(colPosition_fitp1 / 2):
                    comboBox.setCurrentIndex(index)
                self.fitp1.setCellWidget(13 + 2 * i, 2 * col + 1, comboBox)
                new_comp[13 + 2 * i][1] = int(index)

        # add checkbox
        for row in range(rowPosition - 1):
            item = QtWidgets.QTableWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            item.setToolTip('Check to keep fixed during fit procedure')
            if (row < 12) or (12 < row and row % 2 == 1):
                # item.setCheckState(QtCore.Qt.Checked)
                if self.fitp1.item(row + 1, colPosition_fitp1 - 2).checkState() == 2:
                    val = 2
                    item.setCheckState(QtCore.Qt.Checked)
                else:
                    val = 0
                    item.setCheckState(QtCore.Qt.Unchecked)
            else:
                val = 0
                item.setText('')
            new_comp[row + 1][0] = val
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
        new_comp_lims = [[0,'',''] for idx in range(self.fitp1_lims.rowCount())]
        for row in range(len(self.pre[2])):
            self.pre[2][row].extend(new_comp[row])
        self.pre[3]=[self.pre[3][row]+new_comp_lims[row] for row in range(self.fitp1_lims.rowCount())]
        # add table header
        item = QtWidgets.QTableWidgetItem()
        self.fitp1.setHorizontalHeaderItem(colPosition_fitp1, item)
        item = QtWidgets.QTableWidgetItem('C_' + str(int(1 + colPosition_fitp1 / 2)))
        self.fitp1.setHorizontalHeaderItem(colPosition_fitp1 + 1, item)
        self.fitp1.resizeColumnsToContents()
        item = QtWidgets.QTableWidgetItem('C_' + str(int(1 + colPosition_res)))
        self.res_tab.setHorizontalHeaderItem(colPosition_res, item)
        self.res_tab.resizeColumnsToContents()
        self.res_tab.resizeRowsToContents()
        item = QtWidgets.QTableWidgetItem('C_' + str(int(1 + colPosition_fitp1 / 2)))
        self.fitp1_lims.setHorizontalHeaderItem(colPosition_fitp1_lims, item)
        item = QtWidgets.QTableWidgetItem('min')
        self.fitp1_lims.setHorizontalHeaderItem(colPosition_fitp1_lims + 1, item)
        item = QtWidgets.QTableWidgetItem('max')
        self.fitp1_lims.setHorizontalHeaderItem(colPosition_fitp1_lims + 2, item)
        self.fitp1_lims.resizeColumnsToContents()
        self.fitp1_lims.resizeRowsToContents()
        self.activeParameters()
        # self.fitp1.setColumnWidth(1, 55)

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
            self.pre[3]=[self.pre[3][row][:-3]for row in range(self.fitp1_lims.rowCount())]
        if colPosition > 2:
            self.fitp1.removeColumn(colPosition - 1)
            self.fitp1.removeColumn(colPosition - 2)
            self.list_component.remove(str(int(colPosition / 2)))
            self.pre[2] = [self.pre[2][row][:-2] for row in range(self.fitp1.rowCount())]
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
                    self.rem_col()
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
                return self.raise_error(windowTitle="Error: Could not load parameters!")
            # print(self.df[0], self.df[1], self.df[2])
            if (len(str(self.pre[0])) != 0 and len(self.pre[1]) != 0 and len(self.pre[2]) != 0 and len(self.pre) == 3):
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
                return self.raise_error("Error: could not add parameters")
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
                return self.raise_error("Error: could not save parameters")
            try:
                self.savePresetDia()
            except Exception as e:
                return self.raise_error("Error: could not save data")
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
            if not self.pt.isActiveWindow():
                self.pt.close()
                self.pt.show()

        self.idx_pres = 0
        self.fitp1.resizeColumnsToContents()
        self.fitp1.resizeRowsToContents()

    def setPreset(self, list_pre_com, list_pre_bg, list_pre_pk, list_pre_pk_lims=[[0, '', '']] * 19):
        if len(list_pre_com) == 1:
            index_bg = list_pre_com[0]
        else:
            index_bg = list_pre_com[0]
            self.xmin = list_pre_com[1]
            self.xmin_item.setText(str(format(self.xmin, self.floating)))
            self.xmax = list_pre_com[2]
            self.xmax_item.setText(str(format(self.xmax, self.floating)))
            self.hv = list_pre_com[3]
            self.hv_item.setText(str(format(self.hv, self.floating)))
            self.wf = list_pre_com[4]
            self.wf_item.setText(str(format(self.wf, self.floating)))
        if len(str(index_bg)) > 0 and self.addition == 0:
            if int(index_bg) < len(self.bgMenu.actions()) or int(index_bg) in [100, 101]:
                # self.comboBox_bg.setCurrentIndex(int(index_bg))
                self.idx_bg = int(index_bg)
        self.displayChoosenBG.setText('Choosen Background: {}'.format(dictBG[str(self.idx_bg)]))
        # load preset for bg
        if len(list_pre_bg) != 0 and self.addition == 0:
            for row in range(len(list_pre_bg)):
                for col in range(len(list_pre_bg[0])):
                    item = self.fitp0.item(row, col)
                    if (row >= 2 or (row == 0 and 8 > col >= 4) or (row == 1 and col == 0)) and col % 2 == 0:
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
        print(self.fitp1.columnCount())
        fitp1_col_count=self.fitp1.columnCount()
        print(fitp1_col_count, len(list_pre_pk[0]) )
        while fitp1_col_count< len(list_pre_pk[0]):
            self.fitp1.insertColumn(fitp1_col_count)
            self.fitp1.insertColumn(fitp1_col_count + 1)
            for row in range(len(list_pre_pk)):
                for c in range(2):
                    col=c+fitp1_col_count
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
                                    comboBox.setCurrentIndex(list_pre_pk[row][col] + colPosition)
                                else:
                                    comboBox.setCurrentIndex(list_pre_pk[row][col])
                        else:
                            item = self.fitp1.item(row, col)
                            if self.addition == 0:
                                if str(list_pre_pk[row][col]) == '':
                                    item.setText('')
                                else:
                                    item.setText(str(format(list_pre_pk[row][col], self.floating)))
                            else:
                                if str(list_pre_pk[row][col]) == '':
                                    item.setText('')
                                else:
                                    item.setText(str(format(list_pre_pk[row][col], self.floating)))

                    else:
                        if row != 0 and row != 13 and row != 15 and row != 17 and row != 19 and row != 21 and row != 23 and row != 25:
                            item = self.fitp1.item(row, col)
                            print(row, col)
                            if list_pre_pk[row][col] == 2:
                                item.setCheckState(QtCore.Qt.Checked)
                            else:
                                item.setCheckState(QtCore.Qt.Unchecked)
                            if self.addition == 0:
                                item.setText('')
                            else:
                                self.fitp1.setItem(row, col + colPosition * 2, item)
            fitp1_col_count += 2

        fitp1_lims_col_count=self.fitp1_lims.columnCount()
        while fitp1_lims_col_count<len(list_pre_pk_lims[0]):
            self.fitp1_lims.insertColumn(fitp1_lims_col_count)
            self.fitp1_lims.insertColumn(fitp1_lims_col_count + 1)
            self.fitp1_lims.insertColumn(fitp1_lims_col_count + 2)
            for row in range(self.fitp1_lims.rowCount()):
                item = QtWidgets.QTableWidgetItem()
                item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.Unchecked)
                item.setToolTip('Check to use limit during fit procedure')
                self.fitp1_lims.setItem(row, fitp1_lims_col_count, item)
                item = QtWidgets.QTableWidgetItem()
                item.setText('')
                self.fitp1_lims.setItem(row, fitp1_lims_col_count + 1, item)
                item = QtWidgets.QTableWidgetItem()
                item.setText('')
                self.fitp1_lims.setItem(row, fitp1_lims_col_count + 2, item)
            fitp1_lims_col_count+=3
        for row in range(len(list_pre_pk_lims)):
            for col in range(len(list_pre_pk_lims[0])):
                item = self.fitp1_lims.item(row, col)
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

    def loadPreset(self):
        print("test")
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
        for row in range(rowPosition):  # [bug]
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
                if (col % 2) != 0:  # [bug] test functionality
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
                if (col % 3) != 0:  # [bug] test functionality
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

        self.parText = [[self.idx_bg, self.xmin, self.xmax, self.hv, self.wf]]
        self.parText.append(list_pre_bg)
        self.parText.append(list_pre_pk)
        self.parText.append(list_pre_lims)
        self.pre = [[self.idx_bg, self.xmin, self.xmax, self.hv, self.wf]]
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
            self.raise_error("Error: could not export the results.")
        try:
            self.savePreset()
        except Exception as e:
            self.raise_error("Error: could not save parameters.")
        try:
            self.savePresetDia()
        except Exception as e:
            self.raise_error("Error: could not save parameters / export data.")

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

                self.export_pickle(cfilePath)  # export last fit parameters as dict into pickle file

                with open(cfilePath, 'w') as file:
                    file.write(str(Text))
                file.close()
                # print(filePath)

                if cfilePath.split("_")[-1] == "fit.txt":
                    with open(cfilePath.rsplit("_", 1)[0] + '_fit.csv', 'w') as f:
                        f.write('#'+str(self.rows_lightened)+ "\n")
                        self.result.to_csv(f, index=False, mode='a')
                else:
                    with open(cfilePath.rsplit("_", 1)[0] + '.csv', 'w') as f:
                        f.write('#'+str(self.rows_lightened)+"\n")
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
                    return self.raise_error("Error: could not load VAMAS file.")
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
        if self.pt.selectedElements:
            if self.fitp0.item(0, 7).text() is not None and self.fitp0.item(0, 9).text() is not None:
                if len(self.fitp0.item(0, 7).text()) > 0 and len(self.fitp0.item(0, 9).text()) > 0:
                    pe = float(self.fitp0.item(0, 7).text())
                    wf = float(self.fitp0.item(0, 9).text())
                else:
                    pe = 1486.6
                    wf = 4
                    item = QtWidgets.QTableWidgetItem(str(pe))
                    self.fitp0.setItem(0, 7, item)
                    item = QtWidgets.QTableWidgetItem(str(wf))
                    self.fitp0.setItem(0, 9, item)
            else:
                pe = 1486.6
                wf = 4
                item = QtWidgets.QTableWidgetItem(str(pe))
                self.fitp0.setItem(0, 7, item)
                item = QtWidgets.QTableWidgetItem(str(wf))
                self.fitp0.setItem(0, 9, item)
            ymin, ymax = self.ax.get_ylim()
            xmin, xmax = self.ax.get_xlim()
            for obj in self.pt.selectedElements:
                if len(obj.alka['trans']) > 0:
                    for orb in range(len(obj.alka['trans'])):
                        if xmin > xmax:
                            en = float(obj.alka['be'][orb])
                        else:
                            en = pe - wf - float(obj.alka['be'][orb])
                        if (xmin > xmax and xmin > en > xmax) or (xmin < xmax and xmin < en < xmax):
                            elem_x = np.asarray([en])
                            elem_y = np.asarray([float(obj.alka['rsf'][orb])])
                            elem_z = obj.alka['trans'][orb]
                            # obj.symbol+elem_z, color="r", rotation="vertical")
                            self.ax.text(elem_x, ymin + (ymax - ymin) * math.log(elem_y + 1, 10) / 2,
                                         obj.symbol + elem_z, color="r", rotation="vertical")
                if len(obj.aes['trans']) > 0:
                    for orb in range(len(obj.aes['trans'])):
                        if xmin > xmax:
                            en = pe - wf - float(obj.aes['ke'][orb])
                        else:
                            en = float(obj.aes['ke'][orb])
                        if (xmin > xmax and xmin > en > xmax) or (xmin < xmax and xmin < en < xmax):
                            elem_x = np.asarray([en])
                            elem_y = np.asarray([float(obj.aes['rsf'][orb])])
                            elem_z = obj.aes['trans'][orb]
                            # obj.symbol+elem_z, color="g", rotation="vertical")
                            self.ax.text(elem_x, ymin + (ymax - ymin) * math.log(elem_y + 1, 10), obj.symbol + elem_z,
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
                try:
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
                    return self.raise_error("Error: The input .csv is not in the correct format!")

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
                    return self.raise_error("Error: The input file is not in the correct format!")

            # I have moved the error handling here directly to the import, there may exist situations, where already the
            # Import would fail. I still left the following error handling there, but I am not sure if there are cases
            # where this second error handling still will be necessary. However, we should check, if x0 and y0 have same
            # lenght I think

            try:
                x0 = self.df[:, 0]
            except Exception as e:
                return self.raise_error("Error: could not load csv file.")
            try:
                y0 = self.df[:, 1]
            except Exception as e:
                return self.raise_error("Error: could not load csv file.")
            strpe = (str(strpe).split())
            if strpe[0] == 'PE:' and strpe[2] == 'eV':
                pe = float(strpe[1])
                item = QtWidgets.QTableWidgetItem(str(pe))
                self.fitp0.setItem(0, 7, item)
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
            if plottitle == '':
                short_file_name = self.comboBox_file.currentText().split('/')[-1]
                self.ar.set_title(short_file_name, fontsize=11)
                self.plottitle.setText(short_file_name)
            else:
                self.ar.set_title(r"{}".format(plottitle), fontsize=11)
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
                self.df = np.array([[0] * 2] * points, dtype='f')
                self.df[:, 0] = np.linspace(x1, x2, points)

        self.ana('eva')

    def fit(self):
        if self.comboBox_file.currentIndex() > 0:
            try:
                self.ana("fit")
                # self.fitter = Fitting(self.ana, "fit")
                # self.threadpool.start(self.fitter)
            except Exception as e:
                return self.raise_error("Error: Fitting was not successful.")

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
                return self.raise_error('No further steps are saved')
        else:
            self.savePreset()
            self.parameter_history_list.append([pars, self.pre])
            return None

    def clickOnBtnBG(self, idx, activeBG=False):
        if not activeBG:
            self.idx_bg = idx
        else:
            self.idx_bg = idx + 100
        self.activeBG = activeBG
        self.displayChoosenBG.setText('Choosen Background:{}'.format(dictBG[str(self.idx_bg)]))
        self.activeParameters()

    def write_pars(self, pars):
        return None

    def bgSelector(self, x, y, mode):
        if self.idx_bg == 0:
            shA = self.pre[1][0][1]
            shB = self.pre[1][0][3]
            pars = None
            bg_mod = xpy.shirley_calculate(x, y, shA, shB)
        if self.idx_bg == 100:
            if mode == "eva":
                shA = self.pre[1][0][1]
                shB = self.pre[1][0][3]
                pars = None
                bg_mod = xpy.shirley_calculate(x, y, shA, shB)
            else:
                mod = Model(xpy.shirley, independent_vars=["y"], prefix='bg_')
                k = self.pre[1][0][5]
                const = self.pre[1][0][7]
                pars = mod.make_params()
                pars['bg_k'].value = float(k)
                pars['bg_const'].value = float(const)
                if self.pre[1][0][4] == 2:
                    pars['bg_k'].vary = False
                if self.pre[1][0][6] == 2:
                    pars['bg_const'].vary = False
                bg_mod = 0
        if self.idx_bg == 1:
            toB = self.pre[1][1][1]
            toC = self.pre[1][1][3]
            toCd = self.pre[1][1][5]
            toD = self.pre[1][1][7]
            toT0 = self.pre[1][1][9]
            pars = None
            if mode == 'fit':
                toM = self.pre[1][0][3]
                [bg_mod, bg_toB] = xpy.tougaard_calculate(x, y, toB, toC, toCd, toD, toM)
            else:
                toM = 1
                [bg_mod, bg_toB] = xpy.tougaard_calculate(x, y, toB, toC, toCd, toD, toM)
            self.pre[1][1][1] = bg_toB
        if self.idx_bg == 101:
            mod = Model(xpy.tougaard2, independent_vars=["x", "y"], prefix='bg_')
            if self.pre[1][1][1] is None or self.pre[1][1][3] is None or self.pre[1][1][5] is None \
                    or self.pre[1][1][7] is None or len(str(self.pre[1][1][1])) == 0 or len(str(self.pre[1][1][3])) == 0 \
                    or len(str(self.pre[1][1][5])) == 0 or len(str(self.pre[1][1][7])) == 0:
                pars = mod.guess(y, x=x, y=y)
            else:
                pars = mod.make_params()
                pars['bg_B'].value = self.pre[1][1][1]
                if self.pre[1][1][0] == 2:
                    pars['bg_B'].vary = False
                pars['bg_C'].value = self.pre[1][1][3]
                pars['bg_C'].vary = False
                pars['bg_C_d'].value = self.pre[1][1][5]
                pars['bg_C_d'].vary = False
                pars['bg_D'].value = self.pre[1][1][7]
                pars['bg_D'].vary = False
            bg_mod = 0
        if self.idx_bg == 3 or self.idx_bg == 4:
            if self.idx_bg == 3:
                mod = StepModel(prefix='bg_', form='arctan')
            if self.idx_bg == 4:
                mod = StepModel(prefix='bg_', form='erf')
            if self.pre[1][self.idx_bg][1] is None or self.pre[1][self.idx_bg][3] is None or self.pre[1][self.idx_bg][
                5] is None \
                    or len(str(self.pre[1][self.idx_bg][1])) == 0 or len(str(self.pre[1][self.idx_bg][3])) == 0 \
                    or len(str(self.pre[1][self.idx_bg][5])) == 0:
                pars = mod.guess(y, x=x)
            else:
                pars = mod.make_params()
                pars['bg_amplitude'].value = self.pre[1][self.idx_bg][1]
                if self.pre[1][self.idx_bg][0] == 2:
                    pars['bg_amplitude'].vary = False
                pars['bg_center'].value = self.pre[1][self.idx_bg][3]
                if self.pre[1][self.idx_bg][2] == 2:
                    pars['bg_center'].vary = False
                pars['bg_sigma'].value = self.pre[1][self.idx_bg][5]
                if self.pre[1][self.idx_bg][4] == 2:
                    pars['bg_sigma'].vary = False
            bg_mod = 0
        if self.idx_bg == 5:
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

            mod = Model(poly2vbm, prefix='bg_')
            pars = mod.make_params()
            if self.pre[1][self.idx_bg][1] is None or self.pre[1][self.idx_bg][3] is None or self.pre[1][self.idx_bg][
                5] is None \
                    or self.pre[1][self.idx_bg][7] is None or self.pre[1][self.idx_bg][9] is None \
                    or len(str(self.pre[1][self.idx_bg][1])) == 0 or len(str(self.pre[1][self.idx_bg][3])) == 0 \
                    or len(str(self.pre[1][self.idx_bg][5])) == 0 or len(str(self.pre[1][self.idx_bg][7])) == 0 \
                    or len(str(self.pre[1][self.idx_bg][9])) == 0:
                pars['bg_ctr'].value = (x[0] + x[-1]) / 2
                pars['bg_d1'].value = 0
                pars['bg_d2'].value = 0
                pars['bg_d3'].value = 0
                pars['bg_d4'].value = 0
            else:
                pars['bg_ctr'].value = self.pre[1][self.idx_bg][1]
                if self.pre[1][self.idx_bg][0] == 2:
                    pars['bg_ctr'].vary = False
                pars['bg_d1'].value = self.pre[1][self.idx_bg][3]
                if self.pre[1][self.idx_bg][2] == 2:
                    pars['bg_d1'].vary = False
                pars['bg_d2'].value = self.pre[1][self.idx_bg][5]
                if self.pre[1][self.idx_bg][5] == 2:
                    pars['bg_d2'].vary = False
                pars['bg_d3'].value = self.pre[1][self.idx_bg][7]
                if self.pre[1][self.idx_bg][6] == 2:
                    pars['bg_d3'].vary = False
                pars['bg_d4'].value = self.pre[1][self.idx_bg][9]
                if self.pre[1][self.idx_bg][8] == 2:
                    pars['bg_d4'].vary = False
            bg_mod = 0
        if self.idx_bg == 2:
            mod = PolynomialModel(4, prefix='bg_')
            bg_mod = 0
            if self.pre[1][2][1] is None or self.pre[1][2][3] is None or self.pre[1][2][5] is None \
                    or self.pre[1][2][7] is None or self.pre[1][2][9] is None or len(str(self.pre[1][2][1])) == 0 \
                    or len(str(self.pre[1][2][3])) == 0 or len(str(self.pre[1][2][5])) == 0 \
                    or len(str(self.pre[1][2][7])) == 0 or len(str(self.pre[1][2][9])) == 0:
                pars = mod.guess(y, x=x)
            else:
                pars = mod.make_params()
                for index in range(5):
                    pars['bg_c' + str(index)].value = self.pre[1][2][2 * index + 1]
                    if self.pre[1][2][2 * index] == 2:
                        pars['bg_c' + str(index)].vary = False
            if self.fixedBG.isChecked():
                for par in pars:
                    pars[par].vary = False
            return [mod, bg_mod, pars]
        # Polynomial BG to be added for all BG
        modp = PolynomialModel(4, prefix='pg_')
        if self.pre[1][2][1] is None or self.pre[1][2][3] is None or self.pre[1][2][5] is None \
                or self.pre[1][2][7] is None or self.pre[1][2][9] is None or len(str(self.pre[1][2][1])) == 0 \
                or len(str(self.pre[1][2][3])) == 0 or len(str(self.pre[1][2][5])) == 0 \
                or len(str(self.pre[1][2][7])) == 0 or len(str(self.pre[1][2][9])) == 0:
            if pars is None:
                pars = modp.make_params()
                mod = modp
                for index in range(5):
                    pars['pg_c' + str(index)].value = 0
                # make all poly bg parameters fixed
                for col in range(5):
                    self.pre[1][2][2 * col] = 0
                if self.fixedBG.isChecked():
                    for par in pars:
                        pars[par].vary = False
                return [mod, bg_mod, pars]

            else:
                pars.update(modp.make_params())
            for index in range(5):
                pars['pg_c' + str(index)].value = 0
            # make all poly bg parameters fixed
            for col in range(5):
                self.pre[1][2][2 * col] = 0

        else:
            if pars is None:
                pars = modp.make_params()
                mod = modp
                for index in range(5):
                    pars['pg_c' + str(index)].value = self.pre[1][2][2 * index + 1]
                    if self.pre[1][2][2 * index] == 2:
                        pars['pg_c' + str(index)].vary = False
                if self.fixedBG.isChecked():
                    for par in pars:
                        pars[par].vary = False
                return [mod, bg_mod, pars]
            else:
                pars.update(modp.make_params())
            for index in range(5):
                pars['pg_c' + str(index)].value = self.pre[1][2][2 * index + 1]
                if self.pre[1][2][2 * index] == 2:
                    pars['pg_c' + str(index)].vary = False
            pars['pg_c0'].min = 0
        mod += modp
        if self.fixedBG.isChecked():
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
            modp = modelSelector(index, strind, index_pk)
            mod += modp
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
                if self.pre[2][2][2 * index_pk] == 2:
                    pars[strind + str(index_pk + 1) + '_amplitude'].vary = False
            if self.pre[2][14][2 * index_pk + 1] is not None and len(str(self.pre[2][14][2 * index_pk + 1])) > 0:
                pars.add(strind + str(index_pk + 1) + "_center_diff", value=float(self.pre[2][14][2 * index_pk + 1]))
                if self.pre[2][14][2 * index_pk] == 2:
                    pars[strind + str(index_pk + 1) + '_center_diff'].vary = False
            if self.pre[2][16][2 * index_pk + 1] is not None and len(str(self.pre[2][16][2 * index_pk + 1])) > 0:
                pars.add(strind + str(index_pk + 1) + "_amp_ratio", value=float(self.pre[2][16][2 * index_pk + 1]))
                if self.pre[2][16][2 * index_pk] == 2:
                    pars[strind + str(index_pk + 1) + '_amp_ratio'].vary = False
            if index == 0 or index == 2 or index == 4 or index == 5 or index == 6 or index == 7 or index == 8 or index == 12:
                if self.pre[2][4][2 * index_pk + 1] is not None and len(str(self.pre[2][4][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_sigma'].value = float(self.pre[2][4][2 * index_pk + 1])
                    if self.pre[2][4][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_sigma'].vary = False
                if self.pre[2][20][2 * index_pk + 1] is not None and len(str(self.pre[2][20][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_gaussian_ratio",
                             value=float(self.pre[2][20][2 * index_pk + 1]))
                    if self.pre[2][20][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gaussian_ratio'].vary = False
            if index == 10 or index == 11:
                if self.pre[2][4][2 * index_pk + 1] is not None and len(str(self.pre[2][4][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_gaussian_sigma'].value = float(self.pre[2][4][2 * index_pk + 1])
                    if self.pre[2][4][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gaussian_sigma'].vary = False
                if self.pre[2][20][2 * index_pk + 1] is not None and len(str(self.pre[2][20][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_gaussian_ratio",
                             value=float(self.pre[2][20][2 * index_pk + 1]))
                    if self.pre[2][20][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gaussian_ratio'].vary = False
            if index == 1 or index == 3 or index == 9 or index == 10 or index == 11:
                if self.pre[2][3][2 * index_pk + 1] is not None and len(str(self.pre[2][3][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_sigma'].value = float(self.pre[2][3][2 * index_pk + 1])
                    if self.pre[2][3][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_sigma'].vary = False
                if self.pre[2][18][2 * index_pk + 1] is not None and len(str(self.pre[2][18][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_lorentzian_ratio",
                             value=float(self.pre[2][18][2 * index_pk + 1]))
                    if self.pre[2][18][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_lorentzian_ratio'].vary = False
            if index == 2 or index == 6:
                if self.pre[2][3][2 * index_pk + 1] is not None and len(str(self.pre[2][3][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_gamma'].value = float(self.pre[2][3][2 * index_pk + 1])
                    if self.pre[2][3][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gamma'].vary = False
                if self.pre[2][18][2 * index_pk + 1] is not None and len(str(self.pre[2][18][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_lorentzian_ratio",
                             value=float(self.pre[2][18][2 * index_pk + 1]))
                    if self.pre[2][18][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_lorentzian_ratio'].vary = False
            if index == 4 or index == 5 or index == 9 or index == 10 or index == 11:
                if self.pre[2][5][2 * index_pk + 1] is not None and len(str(self.pre[2][5][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_gamma'].value = float(self.pre[2][5][2 * index_pk + 1])
                    if self.pre[2][5][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gamma'].vary = False
                if self.pre[2][22][2 * index_pk + 1] is not None and len(str(self.pre[2][22][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_gamma_ratio",
                             value=float(self.pre[2][22][2 * index_pk + 1]))
                    if self.pre[2][22][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_gamma_ratio'].vary = False
            if index == 3:
                if self.pre[2][6][2 * index_pk + 1] is not None and len(str(self.pre[2][6][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_fraction'].value = float(self.pre[2][6][2 * index_pk + 1])
                    if self.pre[2][6][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_fraction'].vary = False
            if index == 6:
                if self.pre[2][7][2 * index_pk + 1] is not None and len(str(self.pre[2][7][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_skew'].value = float(self.pre[2][7][2 * index_pk + 1])
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
                    if self.pre[2][9][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_kt'].vary = False

            if index == 10:
                if self.pre[2][10][2 * index_pk + 1] is not None and len(str(self.pre[2][10][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_soc'].value = float(self.pre[2][10][2 * index_pk + 1])
                    if self.pre[2][10][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_soc'].vary = False
                if self.pre[2][24][2 * index_pk + 1] is not None and len(str(self.pre[2][24][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_soc_ratio", value=float(self.pre[2][24][2 * index_pk + 1]))
                    if self.pre[2][24][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_soc_ratio'].vary = False
                if self.pre[2][11][2 * index_pk + 1] is not None and len(str(self.pre[2][11][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_height_ratio'].value = float(self.pre[2][11][2 * index_pk + 1])
                    if self.pre[2][11][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_height_ratio'].vary = False
                if self.pre[2][26][2 * index_pk + 1] is not None and len(str(self.pre[2][26][2 * index_pk + 1])) > 0:
                    pars.add(strind + str(index_pk + 1) + "_rel_height_ratio",
                             value=float(self.pre[2][26][2 * index_pk + 1]))
                    if self.pre[2][26][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + '_rel_height_ratio'].vary = False
                if self.pre[2][12][2 * index_pk + 1] is not None and len(str(self.pre[2][12][2 * index_pk + 1])) > 0:
                    pars[strind + str(index_pk + 1) + '_fct_coster_kronig'].value = float(
                        self.pre[2][12][2 * index_pk + 1])
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

    def bgResult2Pre(self, out_params, mode):
        if self.idx_bg == 100:
            if mode != "eva":
                self.pre[1][0][5] = out_params['bg_k'].value
                self.pre[1][0][7] = out_params['bg_const'].value
        if self.idx_bg == 101:
            self.pre[1][1][1] = out_params['bg_B'].value
            self.pre[1][1][3] = out_params['bg_C'].value
            self.pre[1][1][5] = out_params['bg_C_d'].value
            self.pre[1][1][7] = out_params['bg_D'].value
        if self.idx_bg == 3 or self.idx_bg == 4:
            self.pre[1][self.idx_bg][1] = out_params['bg_amplitude'].value
            self.pre[1][self.idx_bg][3] = out_params['bg_center'].value
            self.pre[1][self.idx_bg][5] = out_params['bg_sigma'].value
        if self.idx_bg == 5:
            self.pre[1][self.idx_bg][1] = out_params['bg_ctr'].value
            self.pre[1][self.idx_bg][3] = out_params['bg_d1'].value
            self.pre[1][self.idx_bg][5] = out_params['bg_d2'].value
            self.pre[1][self.idx_bg][7] = out_params['bg_d3'].value
            self.pre[1][self.idx_bg][9] = out_params['bg_d4'].value
        if self.idx_bg == 2:
            for index in range(5):
                self.pre[1][self.idx_bg][2 * index + 1] = out_params['bg_c' + str(index)].value
        if self.idx_bg != 2:
            for index in range(5):
                self.pre[1][2][2 * index + 1] = out_params['pg_c' + str(index)].value

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
        self.bgResult2Pre(out_params, mode)
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
                area = integrate.simps([y for y, x in zip(y_area, x)])
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
                    area = integrate.simps([y for y, x in zip(y_area, x)])
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
                area = integrate.simps([y for y, x in zip(y_area, x)])
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
                area = integrate.simps([y for y, x in zip(y_area, x)])
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

    def ana(self, mode):
        self.savePreset()
        plottitle = self.comboBox_file.currentText().split('/')[-1]
        # self.df = np.loadtxt(str(self.comboBox_file.currentText()), delimiter=',', skiprows=1)
        x0 = self.df[:, 0]
        y0 = self.df[:, 1]
        # print(x0[0], x0[len(x0)-1])

        # plot graph after selection data from popup
        # plt.clf()
        # plt.cla()
        self.ax.cla()
        self.ar.cla()
        # ax = self.figure.add_subplot(211)
        if mode == 'fit':
            self.ax.plot(x0, y0, 'o', color='b', label='raw')
        else:
            # simulation mode
            if self.comboBox_file.currentIndex() == 0:
                pass
                # self.ax.plot(x0, y0, ',', color='b', label='raw')
            # evaluation mode
            else:
                self.ax.plot(x0, y0, 'o', mfc='none', color='b', label='raw')

        if x0[0] > x0[-1]:
            self.ax.set_xlabel('Binding energy (eV)', fontsize=11)
        else:
            self.ax.set_xlabel('Energy (eV)', fontsize=11)
        plt.xlim(x0[0], x0[-1])
        self.ax.grid(True)
        self.ax.set_ylabel('Intensity (arb. unit)', fontsize=11)
        if plottitle == "":

            if self.comboBox_file.currentIndex() == 0:
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
            self.pre[0][1] = x0[0]
        if self.pre[0][2] is None or len(str(self.pre[0][2])) == 0:
            self.pre[0][2] = x0[-1]
        # check if limits are out of of data range, If incorrect, back to default
        x1 = self.pre[0][1]
        if ((x1 > x0[0] or x1 < x0[-1]) and x0[0] > x0[-1]) or (
                (x1 < x0[0] or x1 > x0[-1]) and x0[0] < x0[-1]):
            x1 = x0[0]
            self.pre[0][1] = x1
        x2 = self.pre[0][2]
        if ((x2 < x0[-1] or x2 > x1) and x0[0] > x0[-1]) or (
                (x2 > x0[-1] or x2 < x1) and x0[0] < x0[-1]):
            x2 = x0[-1]
            self.pre[0][2] = x2

        [x, y] = xpy.fit_range(x0, y0, x1, x2)
        raw_y = y
        # BG model selection and call shirley and tougaard
        # colPosition = self.fitp1.columnCount()
        temp_res = self.bgSelector(x, y, mode=mode)
        mod = temp_res[0]
        bg_mod = temp_res[1]
        pars = temp_res[2]
        self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
        # component model selection and construction
        y -= bg_mod
        temp_res = self.PeakSelector(mod)
        pars.update(temp_res[1])

        mod = temp_res[0]

        if mode == 'eva':
            for par in pars:
                pars[par].vary = False
        else:
            temp = self.peak_limits(pars)
            pars.update(temp)  # update pars before using expr, to prevent missing pars

        # evaluate model and optimize parameters for fitting in lmfit
        if mode == 'eva':
            strmode = 'Evaluation'
        else:
            strmode = 'Fitting'
        self.statusBar().showMessage(strmode + ' running.')
        init = mod.eval(pars, x=x, y=y)
        if mode == 'eva':
            out = mod.fit(y, pars, x=x, weights=1 / (np.sqrt(y) * np.sqrt(self.rows_lightened)), y=y)
        else:
            try_me_out = self.history_manager(pars)
            if try_me_out is not None:
                pars, pre = try_me_out
                self.pre = pre
                self.setPreset(pre[0], pre[1], pre[2], pre[3])
            out = mod.fit(y, pars, x=x, weights=1 / (np.sqrt(raw_y) * np.sqrt(self.rows_lightened)), y=raw_y)
        comps = out.eval_components(x=x)
        # fit results to be checked
        for key in out.params:
            print(key, "=", out.params[key].value)

        # fit results print

        results = strmode + ' done: ' + out.method + ', # data: ' + str(out.ndata) + ', # func evals: ' + str(
            out.nfev) + ', # varys: ' + str(out.nvarys) + ', r chi-sqr: ' + str(
            format(out.redchi, self.floating)) + ', Akaike info crit: ' + str(format(out.aic, self.floating))
        self.statusBar().showMessage(results)

        # component results into table
        self.result2Par(out.params, mode)
        self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
        self.fillTabResults(x, y, out)
        # Fit stats to GUI:
        if mode == 'eva':
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
            item = QtWidgets.QTableWidgetItem(str(format(out.redchi, self.floating)))
            self.stats_tab.setItem(7, 0, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.aic, self.floating)))
            self.stats_tab.setItem(8, 0, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.bic, self.floating)))
            self.stats_tab.setItem(9, 0, item)
        self.stats_tab.resizeColumnsToContents()
        self.stats_tab.resizeRowsToContents()
        if mode == 'eva':
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
                if self.idx_bg > 100:
                    self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'],
                                         comps['bg_'] + comps['pg_'], label='C_' + str(index_pk + 1))
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'])
                    if index_pk == len_idx_pk - 1:
                        self.ax.plot(x, comps['bg_'] + comps['pg_'], label='BG')
                if self.idx_bg < 2 or self.idx_bg == 100:
                    self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + bg_mod + comps['pg_'],
                                         bg_mod + comps['pg_'], label='C_' + str(index_pk + 1))
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + bg_mod + comps['pg_'])
                    if index_pk == len_idx_pk - 1:
                        self.ax.plot(x, bg_mod + comps['pg_'], label='BG')
                if self.idx_bg == 2:
                    self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'], comps['bg_'],
                                         label='C_' + str(index_pk + 1))
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'], comps['bg_'])
                    if index_pk == len_idx_pk - 1:
                        self.ax.plot(x, comps['bg_'], label='BG')
                if 100 > self.idx_bg > 2:
                    self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'],
                                         comps['bg_'] + comps['pg_'], label='C_' + str(index_pk + 1))
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'])
                    if index_pk == len_idx_pk - 1:
                        self.ax.plot(x, comps['bg_'] + comps['pg_'], label='BG')
            self.ax.set_xlim(left=self.xmin)
            self.ar.set_xlim(left=self.xmin)
            self.ax.set_xlim(right=self.xmax)
            self.ar.set_xlim(right=self.xmax)
            self.ax.plot(x, out.best_fit + bg_mod, 'r-', lw=2, label='sum')
            self.ar.plot(x, out.residual, 'g.', label='residual')
            autoscale_y(self.ax)

        else:
            # ax.plot(x, init+bg_mod, 'k:', label='initial')
            plottitle = self.comboBox_file.currentText().split('/')[-1]
            if plottitle != '':
                self.ar.set_title(r"{}".format(plottitle), fontsize=11)
            len_idx_pk = int(self.fitp1.columnCount() / 2)
            for index_pk in range(len_idx_pk):
                strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
                strind = strind.split(":", 1)[0]
                if self.idx_bg >= 100:
                    self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'],
                                         comps['bg_'] + comps['pg_'], label='C_' + str(index_pk + 1))
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'])
                    if index_pk == len_idx_pk - 1:
                        self.ax.plot(x, comps['bg_'] + comps['pg_'], label="BG")
                if self.idx_bg < 2:
                    self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + bg_mod + comps['pg_'],
                                         bg_mod + comps['pg_'], label='C_' + str(index_pk + 1))
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + bg_mod + comps['pg_'])
                    if index_pk == len_idx_pk - 1:
                        self.ax.plot(x, bg_mod + comps['pg_'], label="BG")
                if self.idx_bg == 2:
                    self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'], comps['bg_'],
                                         label='C_' + str(index_pk + 1))
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'])
                    if index_pk == len_idx_pk - 1:
                        self.ax.plot(x, comps['bg_'], label="BG")
                if 100 > self.idx_bg > 2:
                    self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'],
                                         comps['bg_'] + comps['pg_'], label='C_' + str(index_pk + 1))
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'])
                    if index_pk == len_idx_pk - 1:
                        self.ax.plot(x, comps['bg_'] + comps['pg_'], label="BG")

                #
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
        df_x = pd.DataFrame(x, columns=['x'])
        df_raw_y = pd.DataFrame(raw_y, columns=['raw_y'])
        if self.idx_bg > 100:
            df_y = pd.DataFrame(raw_y - comps['pg_'] - comps['bg_'], columns=['data-bg'])
            df_pks = pd.DataFrame(out.best_fit - comps['pg_'] - comps['bg_'], columns=['sum_components'])
            df_sum = pd.DataFrame(out.best_fit, columns=['sum_fit'])
        elif self.idx_bg == 100:
            if mode == 'eva':
                df_y = pd.DataFrame(raw_y - comps['pg_'] - bg_mod, columns=['data-bg'])
                df_pks = pd.DataFrame(out.best_fit - comps['pg_'] - bg_mod, columns=['sum_components'])
                df_sum = pd.DataFrame(out.best_fit, columns=['sum_fit'])
            else:
                df_y = pd.DataFrame(raw_y - comps['pg_'] - comps['bg_'], columns=['data-bg'])
                df_pks = pd.DataFrame(out.best_fit - comps['pg_'] - comps['bg_'], columns=['sum_components'])
                df_sum = pd.DataFrame(out.best_fit, columns=['sum_fit'])

        elif self.idx_bg == 2:
            df_y = pd.DataFrame(raw_y - bg_mod - comps['bg_'], columns=['data-bg'])
            df_pks = pd.DataFrame(out.best_fit - comps['bg_'], columns=['sum_components'])
            df_sum = pd.DataFrame(out.best_fit + comps['bg_'], columns=['sum_fit'])
        else:
            df_y = pd.DataFrame(raw_y - bg_mod - comps['pg_'], columns=['data-bg'])
            df_pks = pd.DataFrame(out.best_fit - comps['pg_'], columns=['sum_components'])
            df_sum = pd.DataFrame(out.best_fit + bg_mod, columns=['sum_fit'])
        if self.idx_bg > 100:
            df_b = pd.DataFrame(comps['pg_'] + comps['bg_'], columns=['bg'])
        if self.idx_bg < 2:
            df_b = pd.DataFrame(bg_mod + comps['pg_'], columns=['bg'])
        if self.idx_bg == 2:
            df_b = pd.DataFrame(comps['bg_'], columns=['bg'])
        if 100 > self.idx_bg > 2:
            df_b = pd.DataFrame(comps['bg_'] + comps['pg_'], columns=['bg'])
        if self.idx_bg == 100:
            df_b = pd.DataFrame(comps['bg_'], columns=['bg'])
        if self.idx_bg == 2:
            df_b_pg = pd.DataFrame(comps['bg_'], columns=['pg'])
        else:
            df_b_pg = pd.DataFrame(comps['pg_'], columns=['pg'])
        self.result = pd.concat([df_x, df_raw_y, df_y, df_pks, df_b, df_b_pg, df_sum], axis=1)
        for index_pk in range(int(self.fitp1.columnCount() / 2)):
            strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
            strind = strind.split(":", 1)[0]
            df_c = pd.DataFrame(comps[strind + str(index_pk + 1) + '_'], columns=[strind + str(index_pk + 1)])
            self.result = pd.concat([self.result, df_c], axis=1)
        print(out.fit_report())
        # macOS's compatibility issue on pyqt5, add below to update window
        self.repaint()

    def center(self):
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def handleElementClicked(self, elementObject, checked):
        symbol = elementObject.symbol
        if symbol == 'Clear':
            self.pt.selectedElements = []
        elif symbol == 'Refresh':
            pass
        elif checked and elementObject not in self.pt.selectedElements:
            self.pt.selectedElements.append(elementObject)
        elif not checked:
            self.pt.selectedElements.remove(elementObject)
        self.plot_pt()

    def closeEvent(self, event):
        event.accept()
        sys.exit(0)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = PrettyWidget()
    sys.exit(app.exec_())
