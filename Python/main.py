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
from helpers import autoscale_y
import threading

import traceback  # error handling
import logging  # error handling

# style.use('ggplot')    
style.use('seaborn-pastel')


class Fitting(QRunnable):
    '''
    Worker thread for fitting process
    '''

    def __init__(self, fn, *args):
        super(Fitting, self).__init__()
        self.fn = fn
        self.args = args
    @pyqtSlot()
    def run(self):
        self.fn(*self.args)

class PrettyWidget(QtWidgets.QMainWindow):
    def __init__(self):
        super(PrettyWidget, self).__init__()
        self.threadpool = QThreadPool() #thread pool for worker/stop execution button
        # super(PrettyWidget, self).__init__()
        self.export_out = None
        self.export_pars = None
        self.pre = None
        self.res_label = None
        self.pars_label = None
        self.stats_label = None
        self.list_shape = None
        self.list_vamas = None
        self.parText = None
        self.res_tab = None
        self.fitp0 = None
        #self.comboBox_pres = None
        self.addition = None
        #self.comboBox_bg = None
        self.comboBox_file = None
        self.list_preset = None
        self.list_bg = None
        self.list_file = None
        self.toolbar = None
        self.list_peak = None
        self.stats_tab = None
        self.fitp1 = None
        self.list_imp = None
        self.result = None
        self.canvas = None
        self.figure = None
        self.df = None
        self.filePath = None
        self.pt = None
        self.floating = None
        self.version = None
        self.df = None
        self.parameter_history_list = []
        self.go_back_in_paramaeter_history = False
        self.event_stop = threading.Event()
        self.initUI()
        self.error_dialog = QtWidgets.QErrorMessage()
  
    def initUI(self):
        self.version = 'LG4X: LMFit GUI for XPS curve fitting 2.0.2'
        self.floating = '.4f'
        self.setGeometry(700, 500, 1600, 900)
        self.center()
        self.setWindowTitle(self.version)
        self.statusBar().showMessage(
            'Copyright (C) 2022, Julian Hochhaus, TU Dortmund University; adapted from Hideki NAKAJIMA Hideki '
            'NAKAJIMA, Synchrotron Light Research Institute, Nakhon Ratchasima, Thailand ')
        self.pt = PeriodicTable()
        self.pt.setWindowTitle('Periodic Table')
        self.pt.elementEmitted.connect(self.handleElementClicked)
        self.pt.selectedElements = []
        
        

        # Grid Layout
        grid = QtWidgets.QGridLayout()
        grid.setRowMinimumHeight(0, 25)
        grid.setRowMinimumHeight(1, 25)
        grid.setRowMinimumHeight(2, 25)
        widget = QtWidgets.QWidget(self)
        self.setCentralWidget(widget)
        widget.setLayout(grid)

        # Home directory
        self.filePath = QtCore.QDir.homePath()
        # self.filePath = '/Users/hidekinakajima/Desktop/WFH2021_2/lg4x/LG4X-master/Python/'

        # Figure: Canvas and Toolbar
        # self.figure = plt.figure(figsize=(6.7,5))
        self.figure, (self.ar, self.ax) = plt.subplots(2, sharex=True,
                                                       gridspec_kw={'height_ratios': [1, 5], 'hspace': 0})
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setMaximumHeight(20)
        self.toolbar.setMinimumHeight(15)
        self.toolbar.setStyleSheet("QToolBar { border: 0px }")
        grid.addWidget(self.canvas, 5, 0, 4, 3)
        grid.addWidget(self.toolbar, 4, 0, 1, 3)

        # data template
        # self.df = pd.DataFrame()
        self.df = []
        self.result = pd.DataFrame()

        # lists of dropdown menus
        self.list_imp = ['Importing data', 'Import csv', 'Import txt', 'Import vms', 'Open directory']
        self.list_file = ['File list', 'Clear list']
        self.list_bg = ['Shirley BG', 'Tougaard BG', 'Polynomial BG', 'Fermi-Dirac BG', 'Arctan BG', 'Erf BG',
                        'VBM/Cutoff']
        self.list_preset = ['Fitting preset', 'New', 'Load', 'Append', 'Save', 'C1s', 'C K edge', 'Periodic Table']

        self.idx_imp=0
        # DropDown file list
        self.comboBox_file = QtWidgets.QComboBox(self)
        self.comboBox_file.addItems(self.list_file)
        grid.addWidget(self.comboBox_file, 2, 0, 1, 3)
        self.comboBox_file.currentIndexChanged.connect(self.plot)

        # DropDown BG list
        #self.comboBox_bg = QtWidgets.QComboBox(self)
        #self.comboBox_bg.addItems(self.list_bg)
        #grid.addWidget(self.comboBox_bg, 0, 1, 1, 1)
        #self.comboBox_bg.setCurrentIndex(0)
        self.idx_bg=0

        # DropDown preset list
        #self.comboBox_pres = QtWidgets.QComboBox(self)
        #self.comboBox_pres.addItems(self.list_preset)
        #grid.addWidget(self.comboBox_pres, 2, 0, 1, 1)
        #self.comboBox_pres.currentIndexChanged.connect(self.preset)
        #self.comboBox_pres.setCurrentIndex(0)
        self.idx_pres=0
        self.addition = 0

        # Fit Button
        btn_fit = QtWidgets.QPushButton('Fit', self)
        btn_fit.resize(btn_fit.sizeHint())
        btn_fit.clicked.connect(self.fit)
        grid.addWidget(btn_fit, 0, 0, 1, 1)
        
        # Undo Fit Button
        btn_undoFit = QtWidgets.QPushButton('undo Fit', self)
        btn_undoFit.resize(btn_undoFit.sizeHint())
        btn_undoFit.clicked.connect(self.one_step_back_in_params_history)
        grid.addWidget(btn_undoFit, 0, 1, 1, 1)

        # Menu bar 
        exitAction = QtWidgets.QAction('E&xit', self)        
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(QtWidgets.qApp.quit)
        
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
        #btn_preset_save.setShortcut('Ctrl+Shift+S')
        btn_preset_save.triggered.connect(lambda: self.clickOnBtnPreset(idx=4))
        
        btn_preset_c1s = QtWidgets.QAction('&C1s', self)
        #btn_preset_c1s.setShortcut('Ctrl+Shift+')
        btn_preset_c1s.triggered.connect(lambda: self.clickOnBtnPreset(idx=5))

        btn_preset_ckedge = QtWidgets.QAction('C &K edge', self)
        #btn_preset_ckedge.setShortcut('Ctrl+Shift+')
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



        bgMenu = menubar.addMenu('&Choose BG')
        btn_bg_shirley = QtWidgets.QAction('&Shirley BG', self)
        btn_bg_shirley.setShortcut('Ctrl+Alt+S')
        btn_bg_shirley.triggered.connect(lambda: self.clickOnBtnBG(idx=0))

        btn_bg_tougaard = QtWidgets.QAction('&Tougaard BG', self)
        btn_bg_tougaard.setShortcut('Ctrl+Alt+T')
        btn_bg_tougaard.triggered.connect(lambda: self.clickOnBtnBG(idx=1))

        btn_bg_polynomial = QtWidgets.QAction('&Polynomial BG', self)
        btn_bg_polynomial.setShortcut('Ctrl+Alt+P')
        btn_bg_polynomial.triggered.connect(lambda: self.clickOnBtnBG(idx=2))

        btn_bg_fd = QtWidgets.QAction('&Fermi-Dirac BG', self)
        #btn_bg_fd.setShortcut('Ctrl+Alt+')
        btn_bg_fd.triggered.connect(lambda: self.clickOnBtnBG(idx=3))

        btn_bg_arctan = QtWidgets.QAction('&Arctan BG', self)
        #btn_bg_arctan.setShortcut('Ctrl+Alt+')
        btn_bg_arctan.triggered.connect(lambda: self.clickOnBtnBG(idx=4))

        btn_bg_erf = QtWidgets.QAction('&Erf BG', self)
        # btn_bg_erf.setShortcut('Ctrl+Alt+')
        btn_bg_erf.triggered.connect(lambda: self.clickOnBtnBG(idx=5))

        btn_bg_vbm = QtWidgets.QAction('&VBM/Cutoff BG', self)
        # btn_bg_vbm.setShortcut('Ctrl+Alt+')
        btn_bg_vbm.triggered.connect(lambda: self.clickOnBtnBG(idx=6))

        bgMenu.addAction(btn_bg_shirley)
        bgMenu.addAction(btn_bg_tougaard)
        bgMenu.addAction(btn_bg_polynomial)
        bgMenu.addAction(btn_bg_fd)
        bgMenu.addAction(btn_bg_arctan)
        bgMenu.addAction(btn_bg_erf)
        bgMenu.addAction(btn_bg_vbm)


        # Add Button
        btn_add = QtWidgets.QPushButton('add peak', self)
        btn_add.resize(btn_add.sizeHint())
        btn_add.clicked.connect(self.add_col)
        grid.addWidget(btn_add, 3, 4, 1, 1)

        # Remove Button
        btn_rem = QtWidgets.QPushButton('rem peak', self)
        btn_rem.resize(btn_rem.sizeHint())
        btn_rem.clicked.connect(self.rem_col)
        grid.addWidget(btn_rem, 3, 5, 1, 1)
      
        # Evaluate Button
        btn_eva = QtWidgets.QPushButton('Evaluate', self)
        btn_eva.resize(btn_eva.sizeHint())
        btn_eva.clicked.connect(self.eva)
        grid.addWidget(btn_eva, 1, 0, 1, 1)
        
        # Interrupt fit Button
        btn_interrupt = QtWidgets.QPushButton('Interrupt fitting (not implemented)', self)
        btn_interrupt.resize(btn_interrupt.sizeHint())
        btn_interrupt.clicked.connect(self.interrupt_fit)
        grid.addWidget(btn_interrupt, 0, 2, 1, 1)
        # PolyBG Table
        list_bg_col = ['bg_c0', 'bg_c1', 'bg_c2', 'bg_c3', 'bg_c4']
        list_bg_row = ['Range (x0,x1), pt, hn, wf', 'Shirley', 'Tougaard', 'Polynomial', 'FD (amp, ctr, kt)',
                       'arctan (amp, ctr, sig)', 'erf (amp, ctr, sig)', 'cutoff (ctr, d1-4)']
        self.fitp0 = QtWidgets.QTableWidget(len(list_bg_row), len(list_bg_col) * 2 + 1)
        list_bg_colh = ['', 'bg_c0', '', 'bg_c1', '', 'bg_c2', '', 'bg_c3', '', 'bg_c4', ' active bg']
        self.fitp0.setHorizontalHeaderLabels(list_bg_colh)
        self.fitp0.setVerticalHeaderLabels(list_bg_row)
        # set BG table checkbox
        for row in range(len(list_bg_row)):
            for col in range(len(list_bg_col)):
                item = QtWidgets.QTableWidgetItem()
                item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.Unchecked)
                if (row == 0 and col < 2) or (row > 2 and col < 4) or (row > 6 and col < 5):
                    self.fitp0.setItem(row, col * 2, item)
                if (row == 1 or row == 2) and col == 5:
                    self.fitp0.setItem(row, col * 2 - 1, item)
                    self.fitp0.setItem(row, col * 2, item)
        # set BG table default
        pre_bg = [[0, 300, 0, 270, 'pt', 101, 'hn', 1486.6, 'wf', 4, ''],
                  ['cv', 1e-06, 'it', 10, 'k', 0.0003, 'const', 1000, 'Keep fixed?', 0, 0],
                  ['B', 2866.0, 'C', 1643.0, 'C*', 1.0, 'D', 1.0, 'Keep fixed?', 0, 0],
                  [2, 0, 2, 0, 2, 0, 2, 0, '', '', '']]
        self.setPreset(0, pre_bg, [])

        self.fitp0.resizeColumnsToContents()
        self.fitp0.resizeRowsToContents()
        grid.addWidget(self.fitp0, 0, 3, 3, 6)

        # set Fit Table
        list_col = ['peak_1']
        list_row = ['model', 'center', 'sigma', 'gamma', 'amp', 'frac', 'skew', 'q', 'kt', 'soc', 'height_ratio',
                    'gaussian_sigma', 'fct_coster_kronig', 'center_ref', 'ctr_diff', 'amp_ref', 'ratio', 'soc_ref',
                    'soc_ratio', 'height_r_ref', 'ratio', 'g_s_ref', 'gaussian_ratio', 'lrtzn_s_ref', 'lrtzn_ratio',
                    'ctr_min', 'ctr_max', 'sig_min', 'sig_max', 'gam_min', 'gam_max', 'amp_min', 'amp_max', 'frac_min',
                    'frac_max', 'skew_min', 'skew_max', 'q_min', 'q_max', 'kt_min', 'kt_max', 'soc_min', 'soc_max',
                    'height_rtio_min', 'height_rtio_max', 'gaussian_s_min', 'gaussian_s_max', "coster-kronig_min",
                    "coster-kronig_max", 'ctr_diff_min', 'ctr_diff_max', 'amp_ratio_min', 'amp_ratio_max',
                    'soc_ratio_min', 'soc_ratio_max', 'height_ref_min', 'height_ref_max', 'gaussian_ratio_min',
                    'gaussian_ratio_max', 'lorentz_ratio_min', 'lorentz_ratio_max']
        self.fitp1 = QtWidgets.QTableWidget(len(list_row), len(list_col) * 2)
        list_colh = ['', 'peak_1']
        self.fitp1.setHorizontalHeaderLabels(list_colh)
        self.fitp1.setVerticalHeaderLabels(list_row)

        # self.list_shape = ['g', 'l', 'v', 'p']
        self.list_shape = ['g: Gaussian', 'l: Lorentzian', 'v: Voigt', 'p: PseudoVoigt', 'e: ExponentialGaussian',
                           's: SkewedGaussian', 'a: SkewedVoigt', 'b: BreitWigner', 'n: Lognormal', 'd: Doniach',
                           'gdd: Convolution Gaussian/Doniach-Dublett', 'gds: Convolution Gaussian/Doniach-Singlett',
                           'fe:Convolution FermiDirac/Gaussian']
        self.list_peak = ['', '1']

        # set DropDown peak model
        for col in range(len(list_col)):
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_shape)
            # comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(0, 2 * col + 1, comboBox)
        # set DropDown ctr_ref peak selection
        for col in range(len(list_col)):
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(13, 2 * col + 1, comboBox)
        # set DropDown amp_ref peak selection
        for col in range(len(list_col)):
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(15, 2 * col + 1, comboBox)
        # set DropDown soc_ref peak selection
        for col in range(len(list_col)):
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(17, 2 * col + 1, comboBox)
        # set DropDown height_ratio_ref peak selection
        for col in range(len(list_col)):
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(19, 2 * col + 1, comboBox)
        # set DropDown gaussian_sigma_ref peak selection
        for col in range(len(list_col)):
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(21, 2 * col + 1, comboBox)
        # set Dropdown lorentzian_sigma_ref peak selection
        for col in range(len(list_col)):
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(23, 2 * col + 1, comboBox)
        # set checkbox in fit table
        for row in range(len(list_row) - 1):
            for col in range(len(list_col)):
                item = QtWidgets.QTableWidgetItem()
                item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                if row < 12:
                    item.setCheckState(QtCore.Qt.Checked)
                    self.fitp1.setItem(row + 1, col * 2, item)
                if row > 23:
                    item.setCheckState(QtCore.Qt.Unchecked)
                    self.fitp1.setItem(row + 1, col * 2, item)
                if 12 <= row <= 23 and row % 2 == 1:
                    item.setCheckState(QtCore.Qt.Unchecked)
                    self.fitp1.setItem(row + 1, col * 2, item)
        # load default preset
        # pre_pk = [[0,0],[2,0],[2,0],[2,0],[2,0],[2,0],[2,0],[2,0]]
        pre_pk = [[0, 0], [2, 284.6], [2, 0.25], [2, 0.02], [0, 20000], [2, 0.5], [2, 0], [2, 0], [2, 0.026], [2, 0.1],
                  [2, 0.7], [2, 0.2], [2, 1], [0, 0], [2, 0.1], [0, 0], [2, 0.5], [0, 0], [2, 1], [0, 0], [2, 1],
                  [0, 0], [2, 1], [0, 0], [2, 1]]
        self.setPreset(0, [], pre_pk)

        self.fitp1.resizeColumnsToContents()
        self.fitp1.resizeRowsToContents()
        grid.addWidget(self.fitp1, 4, 3, 5, 4)
        list_res_row = ['gaussian_fwhm', 'lorentzian_fwhm_p1', 'lorentzian_fwhm_p2', 'fwhm_p1', 'fwhm_p2', 'height_p1',
                        'height_p2', 'approx. area_p1', 'approx. area_p2', 'area_total']
        self.res_tab = QtWidgets.QTableWidget(len(list_res_row), len(list_col))
        self.res_tab.setHorizontalHeaderLabels(list_col)
        self.res_tab.setVerticalHeaderLabels(list_res_row)
        self.res_tab.resizeColumnsToContents()
        self.res_tab.resizeRowsToContents()
        grid.addWidget(self.res_tab, 8, 7, 1, 2)
        list_stats_row = ['success?', 'message', 'nfev', 'nvary', 'ndata', 'nfree', 'chisqr', 'redchi', 'aic', 'bic']
        list_stats_col = ['Fit stats']
        self.stats_tab = QtWidgets.QTableWidget(len(list_stats_row), 1)
        self.stats_tab.setHorizontalHeaderLabels(list_stats_col)
        self.stats_tab.setVerticalHeaderLabels(list_stats_row)
        self.stats_tab.resizeColumnsToContents()
        self.stats_tab.resizeRowsToContents()
        grid.addWidget(self.stats_tab, 6, 7, 1, 2)
        self.stats_label = QtWidgets.QLabel()
        self.stats_label.setText("Fit statistics:")
        self.stats_label.setStyleSheet("font-weight: bold; font-size:12pt")
        grid.addWidget(self.stats_label, 5, 7, 1, 1)
        self.pars_label = QtWidgets.QLabel()
        self.pars_label.setText("Peak parameters:")
        self.pars_label.setStyleSheet("font-weight: bold; font-size:12pt")
        grid.addWidget(self.pars_label, 3, 3, 1, 1)
        self.res_label = QtWidgets.QLabel()
        self.res_label.setText("Fit results:")
        self.res_label.setStyleSheet("font-weight: bold; font-size:12pt")
        grid.addWidget(self.res_label, 7, 7, 1, 1)
        self.plottitle_label = QtWidgets.QLabel()
        self.plottitle_label.setText("Plot title:")
        self.plottitle_label.setStyleSheet("font-weight: bold; font-size:12pt")
        grid.addWidget(self.plottitle_label, 3, 7, 1, 1)
        self.plottitle = QtWidgets.QLineEdit()
        grid.addWidget(self.plottitle, 4, 7, 1, 2)
        self.show()

    def raise_error(self, windowTitle: str) -> None:
        self.error_dialog.setWindowTitle(windowTitle)
        self.error_dialog.showMessage(traceback.format_exc())
        logging.error(traceback.format_exc())
        return None

    def add_col(self):
        rowPosition = self.fitp1.rowCount()
        colPosition_fitp1 = self.fitp1.columnCount()
        colPosition_res = self.res_tab.columnCount()
        self.res_tab.insertColumn(colPosition_res)
        self.fitp1.insertColumn(colPosition_fitp1)
        self.fitp1.insertColumn(colPosition_fitp1 + 1)
        # add DropDown peak model
        comboBox = QtWidgets.QComboBox()
        comboBox.addItems(self.list_shape)
        # comboBox.setMaximumWidth(55)
        self.fitp1.setCellWidget(0, colPosition_fitp1 + 1, comboBox)

        # setup new peak parameters
        for row in range(rowPosition):
            add_fac = 0
            if row == 0:
                add_fac = float(self.fitp1.item(row + 2, colPosition_fitp1 - 1).text()) * 1
            if row == 3:
                add_fac = -1 * float(self.fitp1.item(row + 1, colPosition_fitp1 - 1).text()) / 2
            if self.fitp1.item(row + 1, colPosition_fitp1 - 1) is not None \
                    and row != 12 and row != 14 and row != 16 \
                    and row != 18 and row != 20 and row != 22:
                if len(self.fitp1.item(row + 1, colPosition_fitp1 - 1).text()) > 0:
                    item = QtWidgets.QTableWidgetItem(
                        str(format(float(self.fitp1.item(row + 1, colPosition_fitp1 - 1).text()) + add_fac,
                                   self.floating)))
                    self.fitp1.setItem(row + 1, colPosition_fitp1 + 1, item)

        # add DropDown peak selection for amp_ref and ctr_ref and keep values as it is 
        self.list_peak.append(str(int(1 + colPosition_fitp1 / 2)))

        for col in range(int(colPosition_fitp1 / 2) + 1):
            if col < int(colPosition_fitp1 / 2):
                index = self.fitp1.cellWidget(13, 2 * col + 1).currentIndex()
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(13, 2 * col + 1, comboBox)
            if index > 0 and col < int(colPosition_fitp1 / 2):
                comboBox.setCurrentIndex(index)

        for col in range(int(colPosition_fitp1 / 2) + 1):
            if col < int(colPosition_fitp1 / 2):
                index = self.fitp1.cellWidget(15, 2 * col + 1).currentIndex()
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(15, 2 * col + 1, comboBox)
            if index > 0 and col < int(colPosition_fitp1 / 2):
                comboBox.setCurrentIndex(index)
        for col in range(int(colPosition_fitp1 / 2) + 1):
            if col < int(colPosition_fitp1 / 2):
                index = self.fitp1.cellWidget(17, 2 * col + 1).currentIndex()
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(17, 2 * col + 1, comboBox)
            if index > 0 and col < int(colPosition_fitp1 / 2):
                comboBox.setCurrentIndex(index)
        for col in range(int(colPosition_fitp1 / 2) + 1):
            if col < int(colPosition_fitp1 / 2):
                index = self.fitp1.cellWidget(19, 2 * col + 1).currentIndex()
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(19, 2 * col + 1, comboBox)
            if index > 0 and col < int(colPosition_fitp1 / 2):
                comboBox.setCurrentIndex(index)
        for col in range(int(colPosition_fitp1 / 2) + 1):
            if col < int(colPosition_fitp1 / 2):
                index = self.fitp1.cellWidget(21, 2 * col + 1).currentIndex()
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(21, 2 * col + 1, comboBox)
            if index > 0 and col < int(colPosition_fitp1 / 2):
                comboBox.setCurrentIndex(index)
        for col in range(int(colPosition_fitp1 / 2) + 1):
            if col < int(colPosition_fitp1 / 2):
                index = self.fitp1.cellWidget(23, 2 * col + 1).currentIndex()
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(self.list_peak)
            comboBox.setMaximumWidth(55)
            self.fitp1.setCellWidget(23, 2 * col + 1, comboBox)
            if index > 0 and col < int(colPosition_fitp1 / 2):
                comboBox.setCurrentIndex(index)
        # add checkbox
        for row in range(rowPosition - 1):
            item = QtWidgets.QTableWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            if row < 12:
                # item.setCheckState(QtCore.Qt.Checked)
                if self.fitp1.item(row + 1, colPosition_fitp1 - 2).checkState() == 2:
                    item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)
                self.fitp1.setItem(row + 1, colPosition_fitp1, item)
            if row >= 24:
                # item.setCheckState(QtCore.Qt.Unchecked)
                if self.fitp1.item(row + 1, colPosition_fitp1 - 2).checkState() == 2:
                    item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)
                self.fitp1.setItem(row + 1, colPosition_fitp1, item)
            if 12 < row <= 23 and row % 2 == 1:
                if self.fitp1.item(row + 1, colPosition_fitp1 - 2).checkState() == 2:
                    item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)
                self.fitp1.setItem(row + 1, colPosition_fitp1, item)
        # add table header
        item = QtWidgets.QTableWidgetItem()
        self.fitp1.setHorizontalHeaderItem(colPosition_fitp1, item)
        item = QtWidgets.QTableWidgetItem('peak_' + str(int(1 + colPosition_fitp1 / 2)))
        self.fitp1.setHorizontalHeaderItem(colPosition_fitp1 + 1, item)
        self.fitp1.resizeColumnsToContents()
        item = QtWidgets.QTableWidgetItem('peak_' + str(int(1 + colPosition_res)))
        self.res_tab.setHorizontalHeaderItem(colPosition_res, item)
        self.res_tab.resizeColumnsToContents()
        self.res_tab.resizeRowsToContents()
        # self.fitp1.setColumnWidth(1, 55)

    def rem_col(self):
        colPosition = self.fitp1.columnCount()
        colPosition_res = self.res_tab.columnCount()
        if colPosition_res > 1:
            self.res_tab.removeColumn(colPosition_res - 1)
        if colPosition > 2:
            self.fitp1.removeColumn(colPosition - 1)
            self.fitp1.removeColumn(colPosition - 2)
            self.list_peak.remove(str(int(colPosition / 2)))
            # remove peak in dropdown menu and keep values as it is
            for col in range(int(colPosition / 2)):
                if col < int(colPosition / 2) - 1:
                    index = self.fitp1.cellWidget(13, 2 * col + 1).currentIndex()
                comboBox = QtWidgets.QComboBox()
                comboBox.addItems(self.list_peak)
                self.fitp1.setCellWidget(13, 2 * col + 1, comboBox)
                if index > 0:
                    comboBox.setCurrentIndex(index)

            for col in range(int(colPosition / 2)):
                if col < int(colPosition / 2) - 1:
                    index = self.fitp1.cellWidget(15, 2 * col + 1).currentIndex()
                comboBox = QtWidgets.QComboBox()
                comboBox.addItems(self.list_peak)
                self.fitp1.setCellWidget(15, 2 * col + 1, comboBox)
                if index > 0:
                    comboBox.setCurrentIndex(index)
            for col in range(int(colPosition / 2)):
                if col < int(colPosition / 2) - 1:
                    index = self.fitp1.cellWidget(17, 2 * col + 1).currentIndex()
                comboBox = QtWidgets.QComboBox()
                comboBox.addItems(self.list_peak)
                self.fitp1.setCellWidget(17, 2 * col + 1, comboBox)
                if index > 0:
                    comboBox.setCurrentIndex(index)
            for col in range(int(colPosition / 2)):
                if col < int(colPosition / 2) - 1:
                    index = self.fitp1.cellWidget(19, 2 * col + 1).currentIndex()
                comboBox = QtWidgets.QComboBox()
                comboBox.addItems(self.list_peak)
                self.fitp1.setCellWidget(19, 2 * col + 1, comboBox)
                if index > 0:
                    comboBox.setCurrentIndex(index)
            for col in range(int(colPosition / 2)):
                if col < int(colPosition / 2) - 1:
                    index = self.fitp1.cellWidget(21, 2 * col + 1).currentIndex()
                comboBox = QtWidgets.QComboBox()
                comboBox.addItems(self.list_peak)
                self.fitp1.setCellWidget(21, 2 * col + 1, comboBox)
                if index > 0:
                    comboBox.setCurrentIndex(index)
            for col in range(int(colPosition / 2)):
                if col < int(colPosition / 2) - 1:
                    index = self.fitp1.cellWidget(23, 2 * col + 1).currentIndex()
                comboBox = QtWidgets.QComboBox()
                comboBox.addItems(self.list_peak)
                self.fitp1.setCellWidget(23, 2 * col + 1, comboBox)
                if index > 0:
                    comboBox.setCurrentIndex(index)

    def clickOnBtnPreset(self, idx):
        self.idx_pres=idx
        self.preset()

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
                pre_pk = [[0, 0], [0, x0[abs(y0 - y0.max()).argmin()]], [0, abs(x0[0] - x0[-1]) / 23.5], [2, 0],
                          [0, y0[abs(y0 - y0.max()).argmin()] * 2.5 * abs(x0[0] - x0[-1]) / 23.5], [2, 0]]
            else:
                pre_pk = [[0, 0], [0, 1], [0, 1], [2, 0], [0, 1], [2, 0]]
            self.setPreset(0, [], pre_pk)
        if index == 2:
            try:
                self.loadPreset()
            except Exception as e:
                return self.raise_error(windowTitle="Error: Could not load parameters!")
            # print(self.df[0], self.df[1], self.df[2])
            if len(str(self.pre[0])) != 0 and len(self.pre[1]) != 0 and len(self.pre[2]) != 0:
                self.setPreset(self.pre[0], self.pre[1], self.pre[2])
        if index == 3:
            try:
                self.addPreset()
            except Exception as e:
                return self.raise_error("Error: could not add parameters")
            # print(self.df[0], self.df[1], self.df[2])
            if len(str(self.pre[0])) != 0 and len(self.pre[1]) != 0 and len(self.pre[2]) != 0:
                self.setPreset(self.pre[0], self.pre[1], self.pre[2])
        if index == 4:
            try:
                self.savePreset()
            except Exception as e:
                return self.raise_error("Error: could not save parameters")
            try:
                self.savePresetDia()
            except Exception as e:
                return self.raise_error("Error: could not save data")
        if index == 5:
            # load C1s peak preset
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
            self.setPreset(0, pre_bg, pre_pk)
        if index == 6:
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
            self.setPreset(4, pre_bg, pre_pk)
        if index == 7:
            self.pt.show()
            if not self.pt.isActiveWindow():
                self.pt.close()
                self.pt.show()

        self.idx_pres=0
        self.fitp1.resizeColumnsToContents()
        self.fitp1.resizeRowsToContents()

    def setPreset(self, index_bg, list_pre_bg, list_pre_pk):
        if len(str(index_bg)) > 0 and self.addition == 0:
            if int(index_bg) < len(self.list_bg):
                #self.comboBox_bg.setCurrentIndex(int(index_bg))
                self.idx_bg=int(index_bg)

        # load preset for bg
        if len(list_pre_bg) != 0 and self.addition == 0:
            for row in range(len(list_pre_bg)):
                for col in range(len(list_pre_bg[0])):
                    if ((col % 2) != 0 and col <= 8) or (row == 0 and col > 3) or (0 < row <= 2 and col <= 8):
                        item = QtWidgets.QTableWidgetItem(str(list_pre_bg[row][col]))
                    else:
                        item = QtWidgets.QTableWidgetItem()
                        if list_pre_bg[row][col] == 2:
                            item.setCheckState(QtCore.Qt.Checked)
                        else:
                            item.setCheckState(QtCore.Qt.Unchecked)
                    self.fitp0.setItem(row, col, item)

        # load preset for peaks
        # adjust npeak before load
        if len(list_pre_pk) != 0:
            colPosition = int(self.fitp1.columnCount() / 2)
            if self.addition == 0:
                # print(int(colPosition), int(len(list_pre_pk[0])/2), list_pre_pk[0])
                if colPosition > int(len(list_pre_pk[0]) / 2):
                    for col in range(colPosition - int(len(list_pre_pk[0]) / 2)):
                        self.rem_col()
                if colPosition < int(len(list_pre_pk[0]) / 2):
                    for col in range(int(len(list_pre_pk[0]) / 2) - colPosition):
                        self.add_col()
            else:
                for col in range(int(len(list_pre_pk[0]) / 2)):
                    self.add_col()

        for row in range(len(list_pre_pk)):
            for col in range(len(list_pre_pk[0])):
                if (col % 2) != 0:
                    if row == 0 or row == 13 or row == 15 or row == 17 or row == 19 or row == 21 or row == 23:

                        comboBox = QtWidgets.QComboBox()
                        if row == 0:
                            comboBox.addItems(self.list_shape)
                        else:
                            comboBox.addItems(self.list_peak)
                        if self.addition == 0:
                            self.fitp1.setCellWidget(row, col, comboBox)
                            comboBox.setCurrentIndex(list_pre_pk[row][col])
                        else:
                            self.fitp1.setCellWidget(row, col + colPosition * 2, comboBox)
                            if list_pre_pk[row][col] != 0:
                                comboBox.setCurrentIndex(list_pre_pk[row][col] + colPosition)
                            else:
                                comboBox.setCurrentIndex(list_pre_pk[row][col])
                    else:
                        if str(list_pre_pk[row][col]) == '':
                            item = QtWidgets.QTableWidgetItem('')
                        else:
                            item = QtWidgets.QTableWidgetItem(str(format(list_pre_pk[row][col], self.floating)))
                        if self.addition == 0:
                            self.fitp1.setItem(row, col, item)
                        else:
                            self.fitp1.setItem(row, col + colPosition * 2, item)
                else:
                    if row != 0 and row != 13 and row != 15 and row != 17 and row != 19 and row != 21 and row != 23:
                        item = QtWidgets.QTableWidgetItem()
                        if list_pre_pk[row][col] == 2:
                            item.setCheckState(QtCore.Qt.Checked)
                        else:
                            item.setCheckState(QtCore.Qt.Unchecked)
                        if self.addition == 0:
                            self.fitp1.setItem(row, col, item)
                        else:
                            self.fitp1.setItem(row, col + colPosition * 2, item)

    def loadPreset(self):
        cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open data file', self.filePath, "DAT Files (*.dat)")
        if cfilePath != "":
            print(cfilePath)
            self.filePath = cfilePath
            with open(cfilePath, 'r') as file:
                self.pre = file.read()
            file.close()
            # print(self.pre, type(self.pre))
            self.pre = ast.literal_eval(self.pre)
            # self.pre = json.loads(self.pre) #json does not work due to the None issue
            # print(self.pre, type(self.pre))
            self.list_preset.append(str(cfilePath))
            #self.comboBox_pres.clear()
            #self.comboBox_pres.addItems(self.list_preset)
            #self.comboBox_pres.setCurrentIndex(0)
            self.idx_pres=0
            self.addition = 0
        else:
            self.pre = [[], [], []]

    def addPreset(self):
        cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open data file', self.filePath, "DAT Files (*.dat)")
        if cfilePath != "":
            print(cfilePath)
            self.filePath = cfilePath
            with open(cfilePath, 'r') as file:
                self.pre = file.read()
            file.close()
            # print(self.pre, type(self.pre))
            self.pre = ast.literal_eval(self.pre)
            # self.pre = json.loads(self.pre) #json does not work due to the None issue
            # print(self.pre, type(self.pre))
            self.list_preset.append(str(cfilePath))
            #self.comboBox_pres.clear()
            #self.comboBox_pres.addItems(self.list_preset)
            #self.comboBox_pres.setCurrentIndex(0)
            self.idx_pres=0
            self.addition = 1
        else:
            self.pre = [[], [], []]

    def savePreset(self):
        rowPosition = self.fitp0.rowCount()
        colPosition = self.fitp0.columnCount()
        list_pre_bg = []
        # save preset for bg
        for row in range(rowPosition):
            new = []
            for col in range(colPosition):
                if ((col % 2) != 0 and col <= 8) or (col == 9 and row == 0):
                    if self.fitp0.item(row, col) is None or len(self.fitp0.item(row, col).text()) == 0:
                        new.append('')
                    else:
                        new.append(float(self.fitp0.item(row, col).text()))
                elif (row == 0 and col > 3) or (0 < row <= 2 and col <= 8):
                    if self.fitp0.item(row, col) is None or len(self.fitp0.item(row, col).text()) == 0:
                        new.append('')
                    else:
                        new.append(str(self.fitp0.item(row, col).text()))
                else:
                    if self.fitp0.item(row, col) is None:
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
        # save preset for peaks
        for row in range(rowPosition):
            new = []
            for col in range(colPosition):
                if (col % 2) != 0:
                    if row == 0 or row == 13 or row == 15 or row == 17 or row == 19 or row == 21 or row == 23:
                        new.append(self.fitp1.cellWidget(row, col).currentIndex())
                    else:
                        if self.fitp1.item(row, col) is None or len(self.fitp1.item(row, col).text()) == 0:
                            new.append('')
                        else:
                            new.append(float(self.fitp1.item(row, col).text()))
                else:
                    if row != 0 and row != 13 and row != 15 and row != 17 and row != 19 and row != 21 and row != 23:
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

        # self.parText = self.version + 'parameters\n\n[[Data file]]\n\n' + self.comboBox_file.currentText() + '\n\n[
        # [BG type]]\n\n' + str(self.comboBox_bg.currentIndex()) + '\n\n[[BG parameters]]\n\n' + str(list_pre_bg) +
        # '\n\n[[Peak parameters]]\n\n' + str(list_pre_pk) print(Text)
        self.parText = [self.idx_bg]
        self.parText.append(list_pre_bg)
        self.parText.append(list_pre_pk)

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
    
    def export_pickle(self,path_for_export: str):
        
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
        
        with open(path_for_export.replace('.txt','.pickle'), 'wb') as handle:
            pickle.dump({
                'LG4X_parameters':self.parText,
                'lmfit_parameters':self.export_pars,
                #'lmfit_report':self.export_out.fit_report(min_correl=0.1)
                #'lmfit_report': lmfit_attr_dict
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
            cfilePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Fit file',cfilePath + os.sep + fileName + '_fit.txt', "Text Files (*.txt)")
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
                npeak = self.fitp1.columnCount()
                npeak = int(npeak / 2)
                pk_name = np.array([None] * int(npeak), dtype='U')
                par_name = ['amplitude', 'center', 'sigma', 'gamma', 'fwhm', 'height', 'fraction', 'skew',
                            'q']  # [bug] add new params
                par_list = np.array([[None] * 9] * int(npeak), dtype='f')
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
                for indpk in range(npeak):
                    Text += '\t' + pk_name[indpk]
                for indpar in range(9):
                    Text += '\n' + par_name[indpar] + '\t'
                    for indpk in range(npeak):
                        Text += str(par_list[indpk][indpar]) + '\t'

                self.savePreset()
                Text += '\n\n[[LG4X parameters]]\n\n' + str(self.parText) + '\n\n[[lmfit parameters]]\n\n' + str(
                    self.export_pars) + '\n\n' + str(self.export_out.fit_report(min_correl=0.1))
                
                self.export_pickle(cfilePath) #export las fit parameters as dict int po pickle file 

                with open(cfilePath, 'w') as file:
                    file.write(str(Text))
                file.close()
                # print(filePath)
                if cfilePath.split("_")[-1]== "fit.txt":
                    self.result.to_csv(cfilePath.rsplit("_",1)[0] + '_fit.csv', index=False)
                else:
                    self.result.to_csv(cfilePath.rsplit(".", 1)[0] + '.csv', index=False)
                # print(self.result)
    def clickOnBtnImp(self, idx):
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
        self.idx_imp=0

    def plot_pt(self):
        # peak elements from periodic table window selection
        # print('before', len(self.ax.texts))

        while len(self.ax.texts) > 0:
            for txt in self.ax.texts:
                txt.remove()
            self.canvas.draw()
            self.repaint()
            # self.ax.texts.remove()
        # print('after', len(self.ax.texts))
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
            # print(xmin,xmax)
            for obj in self.pt.selectedElements:
                # print(obj.symbol, obj.alka)
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
                            # print(elem_x, elem_y, elem_z) self.ax.text(elem_x, ymin+(ymax-ymin)*elem_y/60,
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
                            # print(elem_x, elem_y, elem_z) self.ax.text(elem_x, ymin+(ymax-ymin)*elem_y/6,
                            # obj.symbol+elem_z, color="g", rotation="vertical")
                            self.ax.text(elem_x, ymin + (ymax - ymin) * math.log(elem_y + 1, 10), obj.symbol + elem_z,
                                         color="g", rotation="vertical")

            self.canvas.draw()
            self.repaint()
        # print('new', len(self.ax.texts))

    def plot(self):
        plottitle = self.plottitle.displayText()
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
                    strpe = np.loadtxt(str(self.comboBox_file.currentText()), dtype='str', delimiter=',', usecols=1, max_rows=1)
                except Exception as e:
                    return self.raise_error("Error: The input .csv is not in the correct format!")

            else:
                try:
                    self.df = np.loadtxt(str(self.comboBox_file.currentText()), delimiter='\t', skiprows=1)
                    # self.df = pd.read_csv(str(self.comboBox_file.currentText()), dtype = float,  skiprows=1,
                    # header=None, delimiter = '\t')
                    strpe = np.loadtxt(str(self.comboBox_file.currentText()), dtype='str', delimiter='\t', usecols=1,
                                   max_rows=1)
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
            #print(strpe)
            strpe = (str(strpe).split())
            # print(pe)
            if strpe[0] == 'PE:' and strpe[2] == 'eV':
                pe = float(strpe[1])
                # print(pe)
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

            item = QtWidgets.QTableWidgetItem(str(x0[0]))
            self.fitp0.setItem(0, 1, item)
            item = QtWidgets.QTableWidgetItem(str(x0[len(x0) - 1]))
            self.fitp0.setItem(0, 3, item)

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
            if self.fitp0.item(0, 1) is not None and self.fitp0.item(0, 3) is not None:
                if len(self.fitp0.item(0, 1).text()) > 0 and len(self.fitp0.item(0, 3).text()) > 0:
                    x1 = float(self.fitp0.item(0, 1).text())
                    x2 = float(self.fitp0.item(0, 3).text())
                    if self.fitp0.item(0, 5) is not None:
                        if len(self.fitp0.item(0, 5).text()) > 0:
                            points = int(self.fitp0.item(0, 5).text())
                        else:
                            points = 101
                    else:
                        points = 101
                    self.df = np.array([[0] * 2] * points, dtype='f')
                    self.df[:, 0] = np.linspace(x1, x2, points)
        self.ana('eva')

    def fit(self):
        if self.comboBox_file.currentIndex() > 0:
            try:
                self.ana("fit")
                #self.fitter = Fitting(self.ana, "fit")
                #self.threadpool.start(self.fitter)
            except Exception as e:
                return self.raise_error("Error: Fitting was not successful.")
    def interrupt_fit(self):
        print("does nothing yet")

    def one_step_back_in_params_history(self):
        """
        Is called if button undo Fit is prest.
        """
        self.go_back_in_paramaeter_history = True
        self.fit()

    def history_manager(self,pars):
        """
        Manages saving of the fit parameters and presets (e.g. how many peaks, aktive backgrounds and so on) in a list.
        In this approach the insane function ana() must be extended. The ana() should be destroyd! and replaaced by couple of smaller methods for better readability
        
        Parameters
        ----------
            pars: list:
                parameters of the fit, whitch have to be saved
        Returns 
            list: [self.pars, self.parText]
            or 
            None: if self.go_back_in_paramaeter_history is False do nothing

        """
        if self.go_back_in_paramaeter_history is True:
                try:
                    pars,parText = self.parameter_history_list.pop()
                    self.go_back_in_paramaeter_history = False
                    return pars, parText
                except IndexError:
                    self.go_back_in_paramaeter_history = False
                    return self.raise_error('No further steps are saved')
        else:
            self.savePreset()       
            self.parameter_history_list.append([pars,self.parText])
            return None
    def clickOnBtnBG(self,idx):
        self.idx_bg=idx

    def ana(self, mode):
        plottitle = self.plottitle.displayText()
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
                self.ar.set_title(self.comboBox_file.currentText(), fontsize=11)
        else:
            self.ar.set_title(r"{}".format(plottitle), fontsize=11)
        # if no range is specified, fill it from data
        if self.fitp0.item(0, 1) is None or len(self.fitp0.item(0, 1).text()) == 0:
            item = QtWidgets.QTableWidgetItem(str(x0[0]))
            self.fitp0.setItem(0, 1, item)
        if self.fitp0.item(0, 3) is None or len(self.fitp0.item(0, 3).text()) == 0:
            item = QtWidgets.QTableWidgetItem(str(x0[len(x0) - 1]))
            self.fitp0.setItem(0, 3, item)
        # fit or simulation range. If range is incorrect, back to default
        if self.fitp0.item(0, 0).checkState() == 2:
            x1 = float(self.fitp0.item(0, 1).text())
            if ((x1 > x0[0] or x1 < x0[len(x0) - 1]) and x0[0] > x0[-1]) or (
                    (x1 < x0[0] or x1 > x0[len(x0) - 1]) and x0[0] < x0[-1]):
                x1 = x0[0]
                item = QtWidgets.QTableWidgetItem(str(x0[0]))
                self.fitp0.setItem(0, 1, item)
        else:
            x1 = x0[0]
        if self.fitp0.item(0, 2).checkState() == 2:
            x2 = float(self.fitp0.item(0, 3).text())
            if ((x2 < x0[len(x0) - 1] or x2 > x1) and x0[0] > x0[-1]) or (
                    (x2 > x0[len(x0) - 1] or x2 < x1) and x0[0] < x0[-1]):
                x2 = x0[len(x0) - 1]
                item = QtWidgets.QTableWidgetItem(str(x0[len(x0) - 1]))
                self.fitp0.setItem(0, 3, item)
        else:
            x2 = x0[len(x0) - 1]

        [x, y] = xpy.fit_range(x0, y0, x1, x2)
        raw_y = y
        # BG model selection and call shirley and tougaard
        # colPosition = self.fitp1.columnCount()
        index_bg = self.idx_bg
        if index_bg == 0:
            if self.fitp0.item(index_bg + 1, 10).checkState() == 0:
                shA = float(self.fitp0.item(index_bg + 1, 1).text())
                shB = float(self.fitp0.item(index_bg + 1, 3).text())
                bg_mod = xpy.shirley_calculate(x, y, shA, shB)
                y = y - bg_mod
            else:
                mod = Model(xpy.shirley, independent_vars=["y"], prefix='bg_')
                k = float(self.fitp0.item(index_bg + 1, 5).text())
                const = float(self.fitp0.item(index_bg + 1, 7).text())
                pars = mod.make_params()
                pars['bg_k'].value = float(k)
                pars['bg_const'].value = float(const)
                if self.fitp0.item(index_bg + 1, 9).checkState() == 2 or mode == "eva":
                    pars['bg_k'].vary = False
                    pars['bg_const'].vary = False
                    bg_mod = xpy.shirley(y, k, const)
                else:
                    bg_mod = 0
        if index_bg == 1 and self.fitp0.item(index_bg + 1, 10).checkState() == 0:
            toB = float(self.fitp0.item(index_bg + 1, 1).text())
            toC = float(self.fitp0.item(index_bg + 1, 3).text())
            toCd = float(self.fitp0.item(index_bg + 1, 5).text())
            toD = float(self.fitp0.item(index_bg + 1, 7).text())
            if mode == 'fit':
                if self.fitp0.item(index_bg + 1, 9).checkState() == 2:
                    [bg_mod, bg_toB] = xpy.tougaard(x, y, toB, toC, toCd, toD)
                else:
                    toM = float(self.fitp0.item(1, 3).text())
                    [bg_mod, bg_toB] = xpy.tougaard_calculate(x, y, toB, toC, toCd, toD, toM)

            else:
                toM = 1
                [bg_mod, bg_toB] = xpy.tougaard_calculate(x, y, toB, toC, toCd, toD, toM)

            item = QtWidgets.QTableWidgetItem(str(format(bg_toB, self.floating)))
            self.fitp0.setItem(index_bg + 1, 1, item)
            y = y - bg_mod
        if index_bg == 1 and self.fitp0.item(index_bg + 1, 10).checkState() == 2:
            toB = float(self.fitp0.item(index_bg + 1, 1).text())
            toC = float(self.fitp0.item(index_bg + 1, 3).text())
            toCd = float(self.fitp0.item(index_bg + 1, 5).text())
            toD = float(self.fitp0.item(index_bg + 1, 7).text())
            mod = Model(xpy.tougaard2, independent_vars=["x", "y"], prefix='bg_')
            if self.fitp0.item(index_bg + 1, 1) is None or self.fitp0.item(index_bg + 1, 3) is None or self.fitp0.item(
                    index_bg + 1, 5) is None or self.fitp0.item(index_bg + 1, 7) is None:
                pars = mod.guess(y, x=x, y=y)
            else:
                if len(self.fitp0.item(index_bg + 1, 1).text()) == 0 or \
                        len(self.fitp0.item(index_bg + 1, 3).text()) == 0 or \
                        len(self.fitp0.item(index_bg + 1, 5).text()) == 0 or \
                        len(self.fitp0.item(index_bg + 1, 7).text()) == 0:
                    pars = mod.guess(y, x=x, y=y)
                else:
                    pars = mod.make_params()
                    pars['bg_B'].value = float(self.fitp0.item(index_bg + 1, 1).text())
                    if self.fitp0.item(index_bg + 1, 9).checkState() == 2:
                        pars['bg_B'].vary = False
                    pars['bg_C'].value = float(self.fitp0.item(index_bg + 1, 3).text())
                    pars['bg_C'].vary = False
                    pars['bg_C_d'].value = float(self.fitp0.item(index_bg + 1, 5).text())
                    pars['bg_C_d'].vary = False
                    pars['bg_D'].value = float(self.fitp0.item(index_bg + 1, 7).text())
                    pars['bg_D'].vary = False
                bg_mod = 0
        if index_bg == 3:
            mod = ThermalDistributionModel(prefix='bg_', form='fermi')
            if self.fitp0.item(index_bg + 1, 1) is None or self.fitp0.item(index_bg + 1, 3) is None or self.fitp0.item(
                    index_bg + 1, 5) is None:
                pars = mod.guess(y, x=x)
            else:
                if len(self.fitp0.item(index_bg + 1, 1).text()) == 0 or \
                        len(self.fitp0.item(index_bg + 1, 3).text()) == 0 or \
                        len(self.fitp0.item(index_bg + 1, 5).text()) == 0:
                    pars = mod.guess(y, x=x)
                else:
                    pars = mod.make_params()
                    pars['bg_amplitude'].value = float(self.fitp0.item(index_bg + 1, 1).text())
                    pars['bg_center'].value = float(self.fitp0.item(index_bg + 1, 3).text())
                    pars['bg_kt'].value = float(self.fitp0.item(index_bg + 1, 5).text())
            bg_mod = 0
        if index_bg == 4 or index_bg == 5:
            if index_bg == 4:
                mod = StepModel(prefix='bg_', form='arctan')
            if index_bg == 5:
                mod = StepModel(prefix='bg_', form='erf')
            if self.fitp0.item(index_bg + 1, 1) is None or self.fitp0.item(index_bg + 1, 3) is None or self.fitp0.item(
                    index_bg + 1, 5) is None:
                pars = mod.guess(y, x=x)
            else:
                if len(self.fitp0.item(index_bg + 1, 1).text()) == 0 or \
                        len(self.fitp0.item(index_bg + 1, 3).text()) == 0 or \
                        len(self.fitp0.item(index_bg + 1, 5).text()) == 0:
                    pars = mod.guess(y, x=x)
                else:
                    pars = mod.make_params()
                    pars['bg_amplitude'].value = float(self.fitp0.item(index_bg + 1, 1).text())
                    pars['bg_center'].value = float(self.fitp0.item(index_bg + 1, 3).text())
                    pars['bg_sigma'].value = float(self.fitp0.item(index_bg + 1, 5).text())
            bg_mod = 0
        if index_bg == 6:
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
            if self.fitp0.item(index_bg + 1, 1) is None or self.fitp0.item(index_bg + 1, 3) is None \
                    or self.fitp0.item(index_bg + 1, 5) is None or self.fitp0.item(index_bg + 1, 7) is None \
                    or self.fitp0.item(index_bg + 1, 9) is None:
                pars['bg_ctr'].value = (x[0] + x[-1]) / 2
                pars['bg_d1'].value = 0
                pars['bg_d2'].value = 0
                pars['bg_d3'].value = 0
                pars['bg_d4'].value = 0
            else:
                if len(self.fitp0.item(index_bg + 1, 1).text()) == 0 or \
                        len(self.fitp0.item(index_bg + 1, 3).text()) == 0 or \
                        len(self.fitp0.item(index_bg + 1, 5).text()) == 0 or \
                        len(self.fitp0.item(index_bg + 1, 7).text()) == 0 or \
                        len(self.fitp0.item(index_bg + 1, 9).text()) == 0:
                    pars['bg_ctr'].value = (x[0] + x[-1]) / 2
                    pars['bg_d1'].value = 0
                    pars['bg_d2'].value = 0
                    pars['bg_d3'].value = 0
                    pars['bg_d4'].value = 0
                else:
                    pars['bg_ctr'].value = float(self.fitp0.item(index_bg + 1, 1).text())
                    pars['bg_d1'].value = float(self.fitp0.item(index_bg + 1, 3).text())
                    pars['bg_d2'].value = float(self.fitp0.item(index_bg + 1, 5).text())
                    pars['bg_d3'].value = float(self.fitp0.item(index_bg + 1, 7).text())
                    pars['bg_d4'].value = float(self.fitp0.item(index_bg + 1, 9).text())
            bg_mod = 0

        # Polynomial BG to be added for all BG
        if index_bg <= 2 and self.fitp0.item(index_bg + 1, 10).checkState() == 0:
            mod = PolynomialModel(3, prefix='pg_')
            if self.fitp0.item(3, 1) is None or self.fitp0.item(3, 3) is None \
                    or self.fitp0.item(3, 5) is None \
                    or self.fitp0.item(3, 7) is None:
                pars = mod.make_params()
                for index in range(4):
                    pars['pg_c' + str(index)].value = 0
                # make all poly bg parameters fixed
                for col in range(4):
                    item = QtWidgets.QTableWidgetItem()
                    item.setCheckState(QtCore.Qt.Checked)
                    self.fitp0.setItem(3, 2 * col, item)
            else:
                if len(self.fitp0.item(3, 1).text()) == 0 or len(self.fitp0.item(3, 3).text()) == 0 or len(
                        self.fitp0.item(3, 5).text()) == 0 or len(self.fitp0.item(3, 7).text()) == 0:
                    pars = mod.make_params()
                    for index in range(4):
                        pars['pg_c' + str(index)].value = 0
                    # make all poly bg parameters fixed
                    for col in range(4):
                        item = QtWidgets.QTableWidgetItem()
                        item.setCheckState(QtCore.Qt.Checked)
                        self.fitp0.setItem(3, 2 * col, item)
                else:
                    pars = mod.make_params()
                    for index in range(4):
                        pars['pg_c' + str(index)].value = float(self.fitp0.item(3, 2 * index + 1).text())
                    pars['pg_c0'].min = 0
            if index_bg == 2:
                bg_mod = 0
        else:
            modp = PolynomialModel(3, prefix='pg_')
            if self.fitp0.item(3, 1) is None or self.fitp0.item(3, 3) is None or \
                    self.fitp0.item(3, 5) is None or self.fitp0.item(3, 7) is None:
                pars.update(modp.make_params())
                for index in range(4):
                    pars['pg_c' + str(index)].value = 0
                # make all poly bg parameters fixed
                for col in range(4):
                    item = QtWidgets.QTableWidgetItem()
                    item.setCheckState(QtCore.Qt.Checked)
                    self.fitp0.setItem(3, 2 * col, item)
            else:
                if len(self.fitp0.item(3, 1).text()) == 0 or len(self.fitp0.item(3, 3).text()) == 0 or len(
                        self.fitp0.item(3, 5).text()) == 0 or len(self.fitp0.item(3, 7).text()) == 0:
                    pars.update(modp.make_params())
                    for index in range(4):
                        pars['pg_c' + str(index)].value = 0
                    # make all poly bg parameters fixed
                    for col in range(4):
                        item = QtWidgets.QTableWidgetItem()
                        item.setCheckState(QtCore.Qt.Checked)
                        self.fitp0.setItem(3, 2 * col, item)
                else:
                    pars.update(modp.make_params())
                    for index in range(4):
                        pars['pg_c' + str(index)].value = float(self.fitp0.item(3, 2 * index + 1).text())
                pars['pg_c0'].min = 0
            mod += modp

        # peak model selection and construction
        npeak = self.fitp1.columnCount()
        npeak = int(npeak / 2)

        for index_pk in range(npeak):
            index = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentIndex()
            strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
            strind = strind.split(":", 1)[0]
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
            pars.update(pk_mod.make_params())
            # fit parameters from table
            if self.fitp1.item(1, 2 * index_pk + 1) is not None:
                if len(self.fitp1.item(1, 2 * index_pk + 1).text()) > 0:
                    pars[strind + str(index_pk + 1) + '_center'].value = float(
                        self.fitp1.item(1, 2 * index_pk + 1).text())
                if len(self.fitp1.item(14, 2 * index_pk + 1).text()) > 0:
                    pars.add(strind + str(index_pk + 1) + "_center_diff",
                             value=float(self.fitp1.item(14, 2 * index_pk + 1).text()))
                if len(self.fitp1.item(16, 2 * index_pk + 1).text()) > 0:
                    pars.add(strind + str(index_pk + 1) + "_amp_ratio",
                             value=float(self.fitp1.item(16, 2 * index_pk + 1).text()))

            if self.fitp1.item(2, 2 * index_pk + 1) is not None:
                if len(self.fitp1.item(2, 2 * index_pk + 1).text()) > 0:
                    pars[strind + str(index_pk + 1) + '_sigma'].value = float(
                        self.fitp1.item(2, 2 * index_pk + 1).text())

            if index == 2 or index == 4 or index == 5 or index == 6 or index == 9 or index == 10 or index == 11:
                if self.fitp1.item(3, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(3, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_gamma'].value = float(
                            self.fitp1.item(3, 2 * index_pk + 1).text())

            if self.fitp1.item(4, 2 * index_pk + 1) is not None:
                if len(self.fitp1.item(4, 2 * index_pk + 1).text()) > 0:
                    pars[strind + str(index_pk + 1) + '_amplitude'].value = float(
                        self.fitp1.item(4, 2 * index_pk + 1).text())

            if index == 3:
                if self.fitp1.item(5, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(5, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_fraction'].value = float(
                            self.fitp1.item(5, 2 * index_pk + 1).text())

            if index == 6:
                if self.fitp1.item(6, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(6, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_skew'].value = float(
                            self.fitp1.item(6, 2 * index_pk + 1).text())

            if index == 7:
                if self.fitp1.item(7, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(7, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_q'].value = float(
                            self.fitp1.item(7, 2 * index_pk + 1).text())

            if index == 10:
                if self.fitp1.item(9, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(9, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_soc'].value = float(
                            self.fitp1.item(9, 2 * index_pk + 1).text())
                if self.fitp1.item(10, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(10, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_height_ratio'].value = float(
                            self.fitp1.item(10, 2 * index_pk + 1).text())
                if self.fitp1.item(12, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(12, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_coster_kronig_factor'].value = float(
                            self.fitp1.item(12, 2 * index_pk + 1).text())
                if self.fitp1.item(18, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(18, 2 * index_pk + 1).text()) > 0:
                        pars.add(strind + str(index_pk + 1) + "_soc_ratio",
                                 value=float(self.fitp1.item(18, 2 * index_pk + 1).text()))
                if self.fitp1.item(20, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(20, 2 * index_pk + 1).text()) > 0:
                        pars.add(strind + str(index_pk + 1) + "_height_r_ratio",
                                 value=float(self.fitp1.item(20, 2 * index_pk + 1).text()))

            if index == 10 or index == 11:
                if self.fitp1.item(11, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(11, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_gaussian_sigma'].value = float(
                            self.fitp1.item(11, 2 * index_pk + 1).text())
                if self.fitp1.item(22, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(22, 2 * index_pk + 1).text()) > 0:
                        pars.add(strind + str(index_pk + 1) + "_gaussian_ratio",
                                 value=float(self.fitp1.item(22, 2 * index_pk + 1).text()))
                if self.fitp1.item(24, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(24, 2 * index_pk + 1).text()) > 0:
                        pars.add(strind + str(index_pk + 1) + "_lorentzian_ratio",
                                 value=float(self.fitp1.item(24, 2 * index_pk + 1).text()))

            if index == 12:
                if self.fitp1.item(8, 2 * index_pk + 1) is not None:
                    if len(self.fitp1.item(8, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_kt'].value = float(
                            self.fitp1.item(8, 2 * index_pk + 1).text())
            # sum of models
            pars.update(pars)
            mod += pk_mod

        if mode == 'eva':
            # constraints of BG parameters (checkbox to hold)
            for index in range(4):
                pars['pg_c' + str(index)].vary = False
            if index_bg == 3:
                pars['bg_amplitude'].vary = False
                pars['bg_center'].vary = False
                pars['bg_kt'].vary = False
            if index_bg == 4 or index_bg == 5:
                pars['bg_amplitude'].vary = False
                pars['bg_center'].vary = False
                pars['bg_sigma'].vary = False
            if index_bg == 6:
                pars['bg_ctr'].vary = False
                pars['bg_d1'].vary = False
                pars['bg_d2'].vary = False
                pars['bg_d3'].vary = False
                pars['bg_d4'].vary = False

            # constraints of peak parameters (checkbox to hold)
            for index_pk in range(npeak):
                index = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentIndex()
                strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
                strind = strind.split(":", 1)[0]
                pars[strind + str(index_pk + 1) + '_center'].vary = False
                pars[strind + str(index_pk + 1) + '_sigma'].vary = False
                pars[strind + str(index_pk + 1) + '_center_diff'].vary = False
                pars[strind + str(index_pk + 1) + '_amp_ratio'].vary = False
                pars[strind + str(index_pk + 1) + '_amplitude'].vary = False

                # amp ratio setup
                if self.fitp1.cellWidget(15, 2 * index_pk + 1).currentIndex() > 0:
                    pktar = self.fitp1.cellWidget(15, 2 * index_pk + 1).currentIndex()
                    strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                    strtar = strtar.split(":", 1)[0]
                    if self.fitp1.item(16, 2 * index_pk + 1) is not None:
                        if len(self.fitp1.item(16, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_amplitude'].expr = strtar + str(
                                pktar) + '_amplitude * ' + str(strind + str(index_pk + 1) + '_amp_ratio')

                # BE diff setup
                if self.fitp1.cellWidget(13, 2 * index_pk + 1).currentIndex() > 0:
                    pktar = self.fitp1.cellWidget(13, 2 * index_pk + 1).currentIndex()
                    strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                    strtar = strtar.split(":", 1)[0]
                    if self.fitp1.item(14, 2 * index_pk + 1) is not None:
                        if len(self.fitp1.item(14, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_center'].expr = strtar + str(
                                pktar) + '_center + ' + str(strind + str(index_pk + 1) + '_center_diff')

                if index == 2 or index == 4 or index == 5 or index == 6 or index == 9 or index == 10 or index == 11:
                    pars[strind + str(index_pk + 1) + '_gamma'].vary = False

                if index == 3:
                    pars[strind + str(index_pk + 1) + '_fraction'].vary = False

                if index == 6:
                    pars[strind + str(index_pk + 1) + '_skew'].vary = False

                if index == 7:
                    pars[strind + str(index_pk + 1) + '_q'].vary = False

                if index == 10:
                    pars[strind + str(index_pk + 1) + '_soc'].vary = False
                    pars[strind + str(index_pk + 1) + '_height_ratio'].vary = False
                    pars[strind + str(index_pk + 1) + '_coster_kronig_factor'].vary = False
                    pars[strind + str(index_pk + 1) + '_soc_ratio'].vary = False
                    pars[strind + str(index_pk + 1) + '_height_r_ratio'].vary = False
                    # soc ref setup
                    if self.fitp1.cellWidget(17, 2 * index_pk + 1).currentIndex() > 0:
                        pktar = self.fitp1.cellWidget(17, 2 * index_pk + 1).currentIndex()
                        strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                        strtar = strtar.split(":", 1)[0]
                        if self.fitp1.item(18, 2 * index_pk + 1) is not None:
                            if len(self.fitp1.item(18, 2 * index_pk + 1).text()) > 0:
                                pars[strind + str(index_pk + 1) + '_soc'].expr = strtar + str(pktar) + '_soc * ' + str(
                                    strind + str(index_pk + 1) + '_soc_ratio')
                    # height ratio ref setup
                    if self.fitp1.cellWidget(19, 2 * index_pk + 1).currentIndex() > 0:
                        pktar = self.fitp1.cellWidget(19, 2 * index_pk + 1).currentIndex()
                        strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                        strtar = strtar.split(":", 1)[0]
                        if self.fitp1.item(20, 2 * index_pk + 1) is not None:
                            if len(self.fitp1.item(20, 2 * index_pk + 1).text()) > 0:
                                pars[strind + str(index_pk + 1) + '_height_ratio'].expr = strtar + str(
                                    pktar) + '_height_ratio * ' + str(strind + str(index_pk + 1) + '_height_r_ratio')

                if index == 10 or index == 11:
                    pars[strind + str(index_pk + 1) + '_gaussian_sigma'].vary = False
                    pars[strind + str(index_pk + 1) + '_gaussian_ratio'].vary = False
                    pars[strind + str(index_pk + 1) + '_lorentzian_ratio'].vary = False
                    # gaussian sigma ref setup
                    if self.fitp1.cellWidget(21, 2 * index_pk + 1).currentIndex() > 0:
                        pktar = self.fitp1.cellWidget(21, 2 * index_pk + 1).currentIndex()
                        strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                        strtar = strtar.split(":", 1)[0]
                        if self.fitp1.item(22, 2 * index_pk + 1) is not None:
                            if len(self.fitp1.item(22, 2 * index_pk + 1).text()) > 0:
                                pars[strind + str(index_pk + 1) + '_gaussian_sigma'].expr = strtar + str(
                                    pktar) + '_gaussian_sigma * ' + str(strind + str(index_pk + 1) + '_gaussian_ratio')
                    # lorentzian sigma ref setup
                    if self.fitp1.cellWidget(23, 2 * index_pk + 1).currentIndex() > 0:
                        pktar = self.fitp1.cellWidget(23, 2 * index_pk + 1).currentIndex()
                        strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                        strtar = strtar.split(":", 1)[0]
                        if self.fitp1.item(24, 2 * index_pk + 1) is not None:
                            if len(self.fitp1.item(24, 2 * index_pk + 1).text()) > 0:
                                pars[strind + str(index_pk + 1) + '_sigma'].expr = strtar + str(
                                    pktar) + '_sigma * ' + str(strind + str(index_pk + 1) + '_lorentzian_ratio')
                if index == 12:
                    pars[strind + str(index_pk + 1) + '_kt'].vary = False

        else:
            # constraints of BG parameters (checkbox to hold)
            for index in range(4):
                if self.fitp0.item(3, 2 * index).checkState() == 2:
                    if len(self.fitp0.item(3, 2 * index + 1).text()) > 0:
                        pars['pg_c' + str(index)].vary = False
            if index_bg == 3:
                if self.fitp0.item(index_bg + 1, 0).checkState() == 2:
                    if len(self.fitp0.item(index_bg + 1, 1).text()) > 0:
                        pars['bg_amplitude'].vary = False
                if self.fitp0.item(index_bg + 1, 2).checkState() == 2:
                    if len(self.fitp0.item(index_bg + 1, 3).text()) > 0:
                        pars['bg_center'].vary = False
                if self.fitp0.item(index_bg + 1, 4).checkState() == 2:
                    if len(self.fitp0.item(index_bg + 1, 5).text()) > 0:
                        pars['bg_kt'].vary = False
            if index_bg == 4 or index_bg == 5:
                if self.fitp0.item(index_bg + 1, 0).checkState() == 2:
                    if len(self.fitp0.item(index_bg + 1, 1).text()) > 0:
                        pars['bg_amplitude'].vary = False
                if self.fitp0.item(index_bg + 1, 2).checkState() == 2:
                    if len(self.fitp0.item(index_bg + 1, 3).text()) > 0:
                        pars['bg_center'].vary = False
                if self.fitp0.item(index_bg + 1, 4).checkState() == 2:
                    if len(self.fitp0.item(index_bg + 1, 5).text()) > 0:
                        pars['bg_sigma'].vary = False
            if index_bg == 6:
                if self.fitp0.item(index_bg + 1, 0).checkState() == 2:
                    if len(self.fitp0.item(index_bg + 1, 1).text()) > 0:
                        pars['bg_ctr'].vary = False
                if self.fitp0.item(index_bg + 1, 2).checkState() == 2:
                    if len(self.fitp0.item(index_bg + 1, 3).text()) > 0:
                        pars['bg_d1'].vary = False
                if self.fitp0.item(index_bg + 1, 4).checkState() == 2:
                    if len(self.fitp0.item(index_bg + 1, 5).text()) > 0:
                        pars['bg_d2'].vary = False
                if self.fitp0.item(index_bg + 1, 6).checkState() == 2:
                    if len(self.fitp0.item(index_bg + 1, 7).text()) > 0:
                        pars['bg_d3'].vary = False
                if self.fitp0.item(index_bg + 1, 8).checkState() == 2:
                    if len(self.fitp0.item(index_bg + 1, 9).text()) > 0:
                        pars['bg_d4'].vary = False

            # Constraints of peak parameters
            for index_pk in range(npeak):
                # fixed peak parameters (checkbox to hold)
                index = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentIndex()
                strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
                strind = strind.split(":", 1)[0]

                if self.fitp1.item(1, 2 * index_pk).checkState() == 2:
                    if len(self.fitp1.item(1, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_center'].vary = False

                if self.fitp1.item(2, 2 * index_pk).checkState() == 2:
                    if len(self.fitp1.item(2, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_sigma'].vary = False

                if self.fitp1.item(14, 2 * index_pk).checkState() == 2:
                    if len(self.fitp1.item(14, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_center_diff'].vary = False

                if self.fitp1.item(16, 2 * index_pk).checkState() == 2:
                    if len(self.fitp1.item(16, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_amp_ratio'].vary = False

                if index == 2 or index == 4 or index == 5 or index == 6 or index == 9 or index == 10 or index == 11:
                    if self.fitp1.item(3, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(3, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_gamma'].vary = False

                if self.fitp1.item(4, 2 * index_pk).checkState() == 2:
                    if len(self.fitp1.item(4, 2 * index_pk + 1).text()) > 0:
                        pars[strind + str(index_pk + 1) + '_amplitude'].vary = False

                if index == 3:
                    if self.fitp1.item(5, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(5, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_fraction'].vary = False

                if index == 6:
                    if self.fitp1.item(6, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(6, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_skew'].vary = False

                if index == 7:
                    if self.fitp1.item(7, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(7, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_q'].vary = False

                if index == 12:
                    if self.fitp1.item(8, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(8, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_kt'].vary = False

                if index == 10:
                    if self.fitp1.item(9, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(9, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_soc'].vary = False
                    if self.fitp1.item(10, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(10, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_height_ratio'].vary = False
                    if self.fitp1.item(12, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(12, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_coster_kronig_factor'].vary = False
                    if self.fitp1.item(18, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(18, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_soc_ratio'].vary = False
                    if self.fitp1.item(20, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(20, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_height_r_ratio'].vary = False

                if index == 10 or index == 11:
                    if self.fitp1.item(11, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(11, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_gaussian_sigma'].vary = False
                    if self.fitp1.item(22, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(22, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_gaussian_ratio'].vary = False
                    if self.fitp1.item(24, 2 * index_pk).checkState() == 2:
                        if len(self.fitp1.item(24, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_lorentzian_ratio'].vary = False

                # additional peak min and max bounds (checkbox to activate)
                # list_para = ['center', 'sigma', 'gamma', 'amplitude', 'fraction', 'skew', 'q', 'kt', 'soc',
                # 'height_ratio', 'gaussian_sigma', 'fct_coster_kronig', 'ctr_diff', 'amp_ratio', 'soc_ratio',
                # 'height_reference_ratio', 'gaussian_ratio', 'lorentz_ratio'] #[feature] add min max for all models
                if index == 0 or index == 1 or index == 8 or index == 12:
                    list_para = ['center', 'sigma', '', 'amplitude', '', '', '']
                if index == 2 or index == 4 or index == 5 or index == 9:
                    list_para = ['center', 'sigma', 'gamma', 'amplitude', '', '', '']
                if index == 3:
                    list_para = ['center', 'sigma', '', 'amplitude', 'fraction', '', '']
                if index == 6:
                    list_para = ['center', 'sigma', 'gamma', 'amplitude', '', 'skew', '']
                if index == 7:
                    list_para = ['center', 'sigma', '', 'amplitude', '', '', 'q']
                if index == 10 or index == 11:
                    list_para = ['center', 'sigma', 'gamma', 'amplitude', '', '', '']
                for para in range(len(list_para)):
                    if len(list_para[para]) != 0 and self.fitp1.item(25 + 2 * para, 2 * index_pk).checkState() == 2 \
                            and self.fitp1.item(25 + 2 * para, 2 * index_pk + 1) is not None:
                        if len(self.fitp1.item(25 + 2 * para, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_' + list_para[para]].min = float(
                                self.fitp1.item(25 + 2 * para, 2 * index_pk + 1).text())
                    if len(list_para[para]) != 0 \
                            and self.fitp1.item(25 + 2 * para + 1, 2 * index_pk).checkState() == 2 \
                            and self.fitp1.item(25 + 2 * para + 1, 2 * index_pk + 1) is not None:
                        if len(self.fitp1.item(25 + 2 * para + 1, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_' + list_para[para]].max = float(
                                self.fitp1.item(25 + 2 * para + 1, 2 * index_pk + 1).text())

                pars.update(pars)  # update pars before using expr, to prevent missing pars
                # amp ratio setup
                if self.fitp1.cellWidget(15, 2 * index_pk + 1).currentIndex() > 0:
                    pktar = self.fitp1.cellWidget(15, 2 * index_pk + 1).currentIndex()
                    strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                    strtar = strtar.split(":", 1)[0]
                    if self.fitp1.item(16, 2 * index_pk + 1) is not None:
                        if len(self.fitp1.item(16, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_amplitude'].expr = strtar + str(
                                pktar) + '_amplitude * ' + str(strind + str(index_pk + 1) + '_amp_ratio')
                            pars[strind + str(index_pk + 1) + '_amplitude'].min = 0

                # BE diff setup
                if self.fitp1.cellWidget(13, 2 * index_pk + 1).currentIndex() > 0:
                    pktar = self.fitp1.cellWidget(13, 2 * index_pk + 1).currentIndex()
                    strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                    strtar = strtar.split(":", 1)[0]
                    if self.fitp1.item(14, 2 * index_pk + 1) is not None:
                        if len(self.fitp1.item(14, 2 * index_pk + 1).text()) > 0:
                            pars[strind + str(index_pk + 1) + '_center'].expr = strtar + str(
                                pktar) + '_center + ' + str(strind + str(index_pk + 1) + '_center_diff')
                if index == 10:
                    # soc ref setup
                    if self.fitp1.cellWidget(17, 2 * index_pk + 1).currentIndex() > 0:
                        pktar = self.fitp1.cellWidget(17, 2 * index_pk + 1).currentIndex()
                        strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                        strtar = strtar.split(":", 1)[0]
                        if self.fitp1.item(18, 2 * index_pk + 1) is not None:
                            if len(self.fitp1.item(18, 2 * index_pk + 1).text()) > 0:
                                pars[strind + str(index_pk + 1) + '_soc'].expr = strtar + str(pktar) + '_soc * ' + str(
                                    strind + str(index_pk + 1) + '_soc_ratio')
                    # height ratio ref setup
                    if self.fitp1.cellWidget(19, 2 * index_pk + 1).currentIndex() > 0:
                        pktar = self.fitp1.cellWidget(19, 2 * index_pk + 1).currentIndex()
                        strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                        strtar = strtar.split(":", 1)[0]
                        if self.fitp1.item(20, 2 * index_pk + 1) is not None:
                            if len(self.fitp1.item(20, 2 * index_pk + 1).text()) > 0:
                                pars[strind + str(index_pk + 1) + '_height_ratio'].expr = strtar + str(
                                    pktar) + '_height_ratio * ' + str(strind + str(index_pk + 1) + '_height_r_ratio')

                if index == 10 or index == 11:
                    # gaussian sigma ref setup
                    if self.fitp1.cellWidget(21, 2 * index_pk + 1).currentIndex() > 0:
                        pktar = self.fitp1.cellWidget(21, 2 * index_pk + 1).currentIndex()
                        strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                        strtar = strtar.split(":", 1)[0]
                        if self.fitp1.item(22, 2 * index_pk + 1) is not None:
                            if len(self.fitp1.item(22, 2 * index_pk + 1).text()) > 0:
                                pars[strind + str(index_pk + 1) + '_gaussian_sigma'].expr = strtar + str(
                                    pktar) + '_gaussian_sigma * ' + str(strind + str(index_pk + 1) + '_gaussian_ratio')
                    # lorentzian sigma ref setup
                    if self.fitp1.cellWidget(23, 2 * index_pk + 1).currentIndex() > 0:
                        pktar = self.fitp1.cellWidget(23, 2 * index_pk + 1).currentIndex()
                        strtar = self.fitp1.cellWidget(0, 2 * pktar - 1).currentText()
                        strtar = strtar.split(":", 1)[0]
                        if self.fitp1.item(24, 2 * index_pk + 1) is not None:
                            if len(self.fitp1.item(24, 2 * index_pk + 1).text()) > 0:
                                pars[strind + str(index_pk + 1) + '_sigma'].expr = strtar + str(
                                    pktar) + '_sigma * ' + str(strind + str(index_pk + 1) + '_lorentzian_ratio')
                    pars.update(pars)
        # evaluate model and optimize parameters for fitting in lmfit
        if mode == 'eva':
            strmode = 'Evaluation'
        else:
            strmode = 'Fitting'
        self.statusBar().showMessage(strmode + 'running.')
        init = mod.eval(pars, x=x, y=y)
        if mode == 'eva':
            out = mod.fit(y, pars, x=x, y=y)
        else:
            try_me_out = self.history_manager(pars)
            if try_me_out is not None:
                pars, parText= try_me_out
                self.setPreset(parText[0],parText[1],parText[2])
            out = mod.fit(y, pars, x=x, weights=1 / np.sqrt(raw_y), y=raw_y)
        comps = out.eval_components(x=x)
        # fit results to be checked
        for key in out.params:
            print(key, "=", out.params[key].value)

        # fit results print

        results = strmode + ' done: ' + out.method + ', # data: ' + str(out.ndata) + ', # func evals: ' + str(
            out.nfev) + ', # varys: ' + str(out.nvarys) + ', r chi-sqr: ' + str(
            format(out.redchi, self.floating)) + ', Akaike info crit: ' + str(format(out.aic, self.floating))
        self.statusBar().showMessage(results)

        # BG results into table
        for index in range(4):
            item = QtWidgets.QTableWidgetItem(str(format(out.params['pg_c' + str(index)].value, self.floating)))
            self.fitp0.setItem(3, 2 * index + 1, item)
        if index_bg == 0 and self.fitp0.item(index_bg + 1, 10).checkState() == 2:
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_k'].value, '.7f')))
            self.fitp0.setItem(index_bg + 1, 5, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_const'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 7, item)
        if index_bg == 1 and self.fitp0.item(index_bg + 1, 10).checkState() == 2:
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_B'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 1, item)
        if index_bg == 3:
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_amplitude'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 1, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_center'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 3, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_kt'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 5, item)
        if index_bg == 4 or index_bg == 5:
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_amplitude'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 1, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_center'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 3, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_sigma'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 5, item)
        if index_bg == 6:
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_ctr'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 1, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_d1'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 3, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_d2'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 5, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_d3'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 7, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.params['bg_d4'].value, self.floating)))
            self.fitp0.setItem(index_bg + 1, 9, item)
        self.fitp0.resizeColumnsToContents()
        self.fitp0.resizeRowsToContents()
        # Peak results into table
        y_peaks = [0 for idx in range(len(y))]
        for index_pk in range(npeak):
            strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
            strind = strind.split(":", 1)[0]
            y_peaks += out.eval_components()[strind + str(index_pk + 1) + '_']
        area_peaks = integrate.simps([y for y, x in zip(y_peaks, x)])
        for index_pk in range(npeak):
            index = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentIndex()
            strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
            strind = strind.split(":", 1)[0]
            # flash variable ratio/diff values to param table
            item = QtWidgets.QTableWidgetItem(
                str(format(out.params[strind + str(index_pk + 1) + '_center'].value, self.floating)))
            self.fitp1.setItem(1, 2 * index_pk + 1, item)
            item = QtWidgets.QTableWidgetItem(
                str(format(out.params[strind + str(index_pk + 1) + '_center_diff'].value, self.floating)))
            self.fitp1.setItem(14, 2 * index_pk + 1, item)
            item = QtWidgets.QTableWidgetItem(
                str(format(out.params[strind + str(index_pk + 1) + '_amp_ratio'].value, self.floating)))
            self.fitp1.setItem(16, 2 * index_pk + 1, item)
            item = QtWidgets.QTableWidgetItem(
                str(format(out.params[strind + str(index_pk + 1) + '_sigma'].value, self.floating)))
            self.fitp1.setItem(2, 2 * index_pk + 1, item)
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
                # included area
                if mode == 'eva':
                    item = QtWidgets.QTableWidgetItem('')
                    self.res_tab.setItem(7, index_pk, item)
                else:
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
                if mode == 'eva':
                    item = QtWidgets.QTableWidgetItem('')
                    self.res_tab.setItem(7, index_pk, item)
                else:
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
            if index == 2 or index == 4 or index == 5 or index == 6 or index == 9 or index == 10 or index == 11:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_gamma'].value, self.floating)))
                self.fitp1.setItem(3, 2 * index_pk + 1, item)

            item = QtWidgets.QTableWidgetItem(
                str(format(out.params[strind + str(index_pk + 1) + '_amplitude'].value, self.floating)))
            self.fitp1.setItem(4, 2 * index_pk + 1, item)

            if index == 3:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_fraction'].value, self.floating)))
                self.fitp1.setItem(5, 2 * index_pk + 1, item)
            if index == 6:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_skew'].value, self.floating)))
                self.fitp1.setItem(6, 2 * index_pk + 1, item)
            if index == 7:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_q'].value, self.floating)))
                self.fitp1.setItem(7, 2 * index_pk + 1, item)
            if index == 10:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_soc'].value, self.floating)))
                self.fitp1.setItem(9, 2 * index_pk + 1, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_height_ratio'].value, self.floating)))
                self.fitp1.setItem(10, 2 * index_pk + 1, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_coster_kronig_factor'].value, self.floating)))
                self.fitp1.setItem(12, 2 * index_pk + 1, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_soc_ratio'].value, self.floating)))
                self.fitp1.setItem(18, 2 * index_pk + 1, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_height_r_ratio'].value, self.floating)))
                self.fitp1.setItem(20, 2 * index_pk + 1, item)
            if index == 10 or index == 11:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_gaussian_fwhm'].value, self.floating)))
                self.res_tab.setItem(0, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_gaussian_sigma'].value, self.floating)))
                self.fitp1.setItem(11, 2 * index_pk + 1, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_gaussian_ratio'].value, self.floating)))
                self.fitp1.setItem(22, 2 * index_pk + 1, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_lorentzian_ratio'].value, self.floating)))
                self.fitp1.setItem(24, 2 * index_pk + 1, item)
            if index == 11:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_lorentzian_fwhm'].value, self.floating)))
                self.res_tab.setItem(1, index_pk, item)
                # included fwhm w spline?!
                if mode == 'eva':
                    item = QtWidgets.QTableWidgetItem('')
                    self.res_tab.setItem(3, index_pk, item)
                    item = QtWidgets.QTableWidgetItem('')
                    self.res_tab.setItem(7, index_pk, item)
                    item = QtWidgets.QTableWidgetItem('')
                    self.res_tab.setItem(9, index_pk, item)
                else:
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
                        str(format(area, '.1f') + r' ({}%)'.format(format(area / area_peaks * 100, '.2f'))))
                    self.res_tab.setItem(7, index_pk, item)
                    item = QtWidgets.QTableWidgetItem(
                        str(format(area, '.1f') + r' ({}%)'.format(format(area / area_peaks * 100, '.2f'))))
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
                if mode == 'eva':
                    item = QtWidgets.QTableWidgetItem('')
                    self.res_tab.setItem(3, index_pk, item)
                    item = QtWidgets.QTableWidgetItem('')
                    self.res_tab.setItem(4, index_pk, item)
                    item = QtWidgets.QTableWidgetItem('')
                    self.res_tab.setItem(7, index_pk, item)
                    item = QtWidgets.QTableWidgetItem('')
                    self.res_tab.setItem(8, index_pk, item)
                else:
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
                                               * out.params[strind + str(index_pk + 1) + '_coster_kronig_factor'].value,
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
                        str(format(area, '.1f') + r' ({}%)'.format(format(area / area_peaks * 100, '.2f'))))
                    self.res_tab.setItem(9, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_height_p1'].value, self.floating)))
                self.res_tab.setItem(5, index_pk, item)
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_height_p2'].value, self.floating)))
                self.res_tab.setItem(6, index_pk, item)
            if index == 12:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.params[strind + str(index_pk + 1) + '_kt'].value, self.floating)))
                self.fitp1.setItem(8, 2 * index_pk + 1, item)
            self.res_tab.resizeColumnsToContents()
            self.res_tab.resizeRowsToContents()
            self.fitp1.resizeColumnsToContents()
            self.fitp1.resizeRowsToContents()
        # Fit stats to GUI:
        if mode == 'eva':
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
            plottitle = self.plottitle.displayText()
            # ax.plot(x, init+bg_mod, 'b--', lw =2, label='initial')
            if plottitle != '':
                self.ar.set_title(r"{}".format(plottitle), fontsize=11)
            #self.ax.plot(x, out.best_fit + bg_mod, 'k-', lw=2, label='initial')

            for index_pk in range(npeak):
                # print(index_pk, color)
                strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
                strind = strind.split(":", 1)[0]
                if index_bg < 2:
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + bg_mod + comps['pg_'],
                                 label='peak_' + str(index_pk + 1))
                if index_bg == 2:
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + comps['pg_'],
                                 label='peak_' + str(index_pk + 1))
                if index_bg > 2:
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'],
                                 label='peak_' + str(index_pk + 1))
            if self.fitp0.item(0, 0).checkState() == 2:
                xlim1 = float(self.fitp0.item(0, 1).text())
                self.ax.set_xlim(left=xlim1)
                self.ar.set_xlim(left=xlim1)
            if self.fitp0.item(0, 2).checkState() == 2:
                xlim2 = float(self.fitp0.item(0, 3).text())
                self.ax.set_xlim(right=xlim2)
                self.ar.set_xlim(right=xlim2)
            autoscale_y(self.ax)

        else:
            # ax.plot(x, init+bg_mod, 'k:', label='initial')
            plottitle = self.plottitle.displayText()
            if plottitle != '':
                self.ar.set_title(r"{}".format(plottitle), fontsize=11)
            for index_pk in range(npeak):
                strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
                strind = strind.split(":", 1)[0]
                if index_bg < 2:
                    if self.fitp0.item(index_bg + 1, 10).checkState() == 2:
                        self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'],
                                             comps['bg_'] + comps['pg_'], label='peak_' + str(index_pk + 1))
                    else:
                        self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + bg_mod + comps['pg_'],
                                             bg_mod + comps['pg_'], label='peak_' + str(index_pk + 1))
                if index_bg == 2:
                    self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + comps['pg_'], comps['pg_'],
                                         label='peak_' + str(index_pk + 1))
                if index_bg > 2:
                    self.ax.fill_between(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'],
                                         comps['bg_'] + comps['pg_'], label='peak_' + str(index_pk + 1))
                # Philipp: 14-07-2022
                if index_bg < 2:
                    if self.fitp0.item(index_bg + 1, 10).checkState() == 0:
                        self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + bg_mod + comps['pg_'])
                    else:
                        self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'])
                if index_bg == 2:
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + comps['pg_'], comps['pg_'])
                if index_bg > 2:
                    self.ax.plot(x, comps[strind + str(index_pk + 1) + '_'] + comps['bg_'] + comps['pg_'])
                #
            if self.fitp0.item(0, 0).checkState() == 2:
                xlim1 = float(self.fitp0.item(0, 1).text())
                self.ax.set_xlim(left=xlim1)
                self.ar.set_xlim(left=xlim1)
            if self.fitp0.item(0, 2).checkState() == 2:
                xlim2 = float(self.fitp0.item(0, 3).text())
                self.ax.set_xlim(right=xlim2)
                self.ar.set_xlim(right=xlim2)
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
        if self.idx_bg<2 and self.fitp0.item(index_bg + 1, 10).checkState() == 2:
            df_y = pd.DataFrame(raw_y -comps['pg_']-comps['bg_'], columns=['data-bg'])
            df_pks = pd.DataFrame(out.best_fit-comps['pg_']-comps['bg_'], columns=['sum_peaks'])
            df_sum=pd.DataFrame(out.best_fit, columns=['sum_fit'])
        else:
            df_y = pd.DataFrame(raw_y-bg_mod-comps['pg_'], columns=['data-bg'])
            df_pks = pd.DataFrame(out.best_fit-comps['pg_'], columns=['sum_peaks'])
            df_sum = pd.DataFrame(out.best_fit+bg_mod, columns=['sum_fit'])
        if index_bg < 2:
            if self.fitp0.item(index_bg + 1, 10).checkState() == 2:
                df_b = pd.DataFrame(comps['pg_']+comps['bg_'], columns=['bg'])
            else:
                df_b = pd.DataFrame(bg_mod + comps['pg_'], columns=['bg'])
        if index_bg == 2:
            df_b = pd.DataFrame(comps['pg_'], columns=['bg'])
        if index_bg > 2:
            df_b = pd.DataFrame(comps['bg_'] + comps['pg_'], columns=['bg'])
        df_b_pg = pd.DataFrame(comps['pg_'], columns=['pg'])
        self.result = pd.concat([df_x, df_raw_y,df_y, df_pks, df_b, df_b_pg,df_sum], axis=1)
        for index_pk in range(npeak):
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
