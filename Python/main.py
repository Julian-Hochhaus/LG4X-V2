#!/usr/bin/python3
# LG4X-V2: lmfit gui for xps curve fitting Copyright (C) 2023, Julian Hochhaus, TU Dortmund University.
# based on LG4X: Copyright (C) 2021, Hideki NAKAJIMA, Synchrotron Light Research Institute, Thailand.

import ast
import math
import sys
import base64
import pickle
import webbrowser
import matplotlib.pyplot as plt
import pandas as pd
from PyQt5.QtCore import QTime
from lmfitxps.models import TougaardBG, ShirleyBG, SlopeBG
from lmfitxps.lineshapes import singlett
import lmfitxps.backgrounds as xpy
from lmfit import Model
from matplotlib import style
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import QApplication, QDesktopWidget

import vamas_export as vpy
from periodictable import PeriodicTable
from scipy import integrate
from helpers import *
from gui_helpers import *
import threading

import traceback  # error handling
import logging  # error handling
from logging.handlers import RotatingFileHandler
import configparser

if os.environ.get("container") == "flatpak":
    log_folder = ".var/app/io.github.julian_hochhaus.LG4X_V2/cache/Logs"
    os.makedirs(log_folder, exist_ok=True)
    log_file_path = ".var/app/io.github.julian_hochhaus.LG4X_V2/cache/Logs/app.log"
    config_file_path = "/app/config/config.ini"
else:
    script_directory = os.path.dirname(os.path.abspath(__file__))
    log_folder = os.path.join(script_directory, "../Logs")
    os.makedirs(log_folder, exist_ok=True)
    log_file_path = os.path.join(script_directory, "../Logs/app.log")
    config_file_path = os.path.join(script_directory, "../config/config.ini")

max_log_size = 4 * 1024 * 1024  # 4MB
backup_count = 5  # Number of backup files to keep
handler = RotatingFileHandler(
    log_file_path, maxBytes=max_log_size, backupCount=backup_count
)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

config = configparser.ConfigParser()

if len(config_file_path) >= 256:
    print(
        "Error: config file path too long (more than 256 characters). Please move the install directory of the project to a shorter path. Otherwise, configparser cannot read the config file and the program does not work."
    )
config.read(config_file_path)

__version__ = "2.4.2"
# style.use('ggplot')
style.use("seaborn-v0_8-colorblind")
dictBG = {
    "0": "static Shirley BG",
    "100": "active Shirley BG ",
    "1": "static Tougaard BG",
    "101": "active Tougaard BG",
    "2": "Polynomial BG",
    "3": "arctan",
    "4": "Error function",
    "5": "CutOff",
    "6": "Slope BG",
}


class PrettyWidget(QtWidgets.QMainWindow):
    def __init__(self):
        self.two_window_mode = config.getboolean("GUI", "two_window_mode")
        self.resolution = [
            config.getint("GUI", "resolution_width"),
            config.getint("GUI", "resolution_height"),
        ]
        super(PrettyWidget, self).__init__()
        # super(PrettyWidget, self).__init__()
        self.rows_lightened = 1
        self.export_out = None
        self.export_pars = None
        self.pre = [[], [], [], []]
        self.meta_result_export = []
        self.res_label = None
        self.pars_label = None
        self.stats_label = None
        self.list_shape = None
        self.list_vamas = None
        self.parText = None
        self.res_tab = None
        self.fitp0 = None
        self.comboBox_file = None
        self.list_file = None
        self.toolbar = None
        self.list_component = None
        self.stats_tab = None
        self.fitp1 = None
        self.result = None
        self.xmin = 270
        self.xmax = 300
        self.hv = 1486.6
        self.wf = 4
        self.correct_energy = 0
        self.canvas = None
        self.figure = None
        self.df = None
        self.filePath = None
        self.pt = None
        self.floating = None
        self.version = None
        self.settings_dialog = None
        self.parameter_history_list = []
        self.go_back_in_parameter_history = False
        self.event_stop = threading.Event()
        self.error_dialog = QtWidgets.QErrorMessage()
        self.displayChoosenBG = QtWidgets.QLabel()
        self.delegate = TableItemDelegate()
        self.binding_ener = False
        self.column_width = config.getint("GUI", "column_width")
        self.fit_thread = FitThread(self)
        self.version = "LG4X: LMFit GUI for XPS curve fitting v{}".format(__version__)
        self.floating = ".3f"
        self.data_arr = {}
        self.display_name_to_path = {}
        self.current_theme = "dark"
        self.initUI()

    def initUI(self):
        logging.info("Application started.")
        logging.info(f"Version: {__version__}")

        # --- Clear old UI ---
        old_central = self.centralWidget()
        if old_central:
            old_central.deleteLater()

        if hasattr(self, "second_window") and self.second_window is not None:
            self.second_window.close()
            self.second_window.deleteLater()
            self.second_window = None

        if self.menuBar():
            self.menuBar().clear()

        if self.two_window_mode:
            self.initTwoWindowUI()
        else:
            self.initSingleWindowUI()

        # Apply resize after init
        self.resize(self.resolution[0], self.resolution[1])

    def initTwoWindowUI(self):
        # --- Setup main window ---
        setupMainWindow(self)
        initializeData(self)

        # --- Setup central widget and layout ---
        outer_layout = QtWidgets.QVBoxLayout()
        widget = QtWidgets.QWidget(self)
        widget.setLayout(outer_layout)
        self.setCentralWidget(widget)
        createMenuBar(self)

        # --- Home directory and canvas ---
        self.filePath = QtCore.QDir.homePath()
        self.cfilePath = QtCore.QDir.homePath()
        self.figure, self.ar, self.ax, self.canvas, self.toolbar = setupCanvas(self)

        # --- Top row layout ---
        toprow_layout = createTopRowLayout(self, dictBG)
        outer_layout.addLayout(toprow_layout, 1)
        outer_layout.addWidget(LayoutHline())

        # --- First screen bottom layout ---
        bottomrow_layout = QtWidgets.QHBoxLayout()

        layout_bottom_left = createBottomLeftLayout(self)
        bottomrow_layout.addLayout(layout_bottom_left, 4)

        outer_layout.addLayout(bottomrow_layout, 6)

        # --- Second screen bottom layout ---
        bottomrow_second_screen_layout = QtWidgets.QHBoxLayout()

        layout_bottom_mid, list_col = createMiddleLayout(self)
        bottomrow_second_screen_layout.addLayout(layout_bottom_mid, 3)

        layout_bottom_right = createBottomRightLayout(self, list_col)
        bottomrow_second_screen_layout.addLayout(layout_bottom_right, 2)

        # --- Setup second window ---
        setupSecondWindow(self, config, bottomrow_second_screen_layout)

        # --- Final adjustments ---
        self.activeParameters()
        self.resizeAllColumns()

    def initSingleWindowUI(self):
        # --- Setup main window ---
        setupMainWindow(self)
        initializeData(self)

        # --- Setup central widget and layout ---
        outer_layout = QtWidgets.QVBoxLayout()
        widget = QtWidgets.QWidget(self)
        widget.setLayout(outer_layout)
        self.setCentralWidget(widget)
        createMenuBar(self)

        # --- Home directory and canvas ---
        self.filePath = QtCore.QDir.homePath()
        self.cfilePath = QtCore.QDir.homePath()
        self.figure, self.ar, self.ax, self.canvas, self.toolbar = setupCanvas(self)

        # --- Top row layout ---
        toprow_layout = createTopRowLayout(self, dictBG)
        outer_layout.addLayout(toprow_layout, 1)
        outer_layout.addWidget(LayoutHline())

        # --- Bottom row layout ---
        bottomrow_layout = QtWidgets.QHBoxLayout()

        layout_bottom_left = createBottomLeftLayout(self)
        bottomrow_layout.addLayout(layout_bottom_left, 4)

        layout_bottom_mid, list_col = createMiddleLayout(self)
        bottomrow_layout.addLayout(layout_bottom_mid, 3)

        layout_bottom_right = createBottomRightLayout(self, list_col)
        bottomrow_layout.addLayout(layout_bottom_right, 2)

        outer_layout.addLayout(bottomrow_layout, 6)

        # --- Final adjustments ---
        self.activeParameters()
        self.resizeAllColumns()

    def open_settings_window(self):
        self.settings_dialog = SettingsDialog(self, config, config_file_path)
        self.settings_dialog.show()

    def duplicateComponentNames(self, new_label):
        if new_label in self.list_component:
            QtWidgets.QMessageBox.warning(
                self,
                "Duplicate Name",
                "Component name already exists.\n Defaulted to next free name in format 'C_xx' ",
            )
            corrected_label = self.nextFreeComponentName()
            return corrected_label
        else:
            return new_label

    def nextFreeComponentName(self):
        max_num = 0
        for comp_name in self.list_component:
            if "C_" in comp_name:
                num = int(comp_name.split("_")[1])
                if num > max_num:
                    max_num = num
        return "C_" + str(max_num + 1)

    def renameDuplicates(self, headers):
        header_dict = {}
        result_header = []
        for header in headers:
            if header not in header_dict:
                header_dict[header] = 1
                result_header.append(header)
            else:
                idx = header_dict[header]
                header_dict[header] += 1
                result_header.append(header + "_x" + str(idx))
        return result_header

    def updateHeader_lims(self, logicalIndex, new_label):
        if logicalIndex % 2 != 0:
            new_label = self.duplicateComponentNames(new_label)
            self.fitp1_lims.horizontalHeaderItem(
                int((logicalIndex - 1) / 2 * 3)
            ).setText(new_label)
            self.res_tab.horizontalHeaderItem(int((logicalIndex - 1) / 2)).setText(
                new_label
            )
            self.updateDropdown()

    def updateHeader_comps(self, logicalIndex, new_label):
        if logicalIndex % 3 == 0:
            new_label = self.duplicateComponentNames(new_label)
            self.fitp1.horizontalHeaderItem(int(logicalIndex / 3 * 2 + 1)).setText(
                new_label
            )
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
        header_texts = [""]
        for column in range(int(self.fitp1.columnCount() / 2)):
            header_item = self.fitp1.horizontalHeaderItem(int(column * 2 + 1))
            if header_item is not None:
                header_texts.append(header_item.text())
        for i in range(7):
            for col in range(int(colPosition_fitp1 / 2 + 1)):
                if col < int(colPosition_fitp1 / 2):
                    index = self.fitp1.cellWidget(
                        13 + 2 * i, 2 * col + 1
                    ).currentIndex()
                comboBox = QtWidgets.QComboBox()
                comboBox.addItems(header_texts)
                comboBox.setMaximumWidth(55)
                if index > 0 and col < int(colPosition_fitp1 / 2):
                    comboBox.setCurrentIndex(index)
                else:
                    if index > 0:
                        comboBox.setCurrentIndex(1) # init dropdowns for reference with C1
                    else:
                        comboBox.setCurrentIndex(0) #set first column to empty to avoid self recursion
                self.fitp1.setCellWidget(13 + 2 * i, 2 * col + 1, comboBox)
        if int(len(header_texts)) == int(len(self.list_component)):
            self.list_component = header_texts

    def show_citation_dialog(self):
        citation_text = "J. A. Hochhaus and H. Nakajima, LG4X-V2 (Zenodo, 2023), DOI:10.5281/zenodo.7871174"
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("How to cite")
        msg_box.setTextFormat(QtCore.Qt.RichText)
        msg_box.setText(citation_text)
        copy_button = msg_box.addButton(
            "Copy to clipboard", QtWidgets.QMessageBox.AcceptRole
        )
        open_zenodo_button = msg_box.addButton(
            "Open on Zenodo(DOI)", QtWidgets.QMessageBox.ActionRole
        )

        msg_box.exec_()
        if msg_box.clickedButton() == copy_button:
            # Copy citation text to clipboard
            QtWidgets.QApplication.clipboard().setText(citation_text)
        elif msg_box.clickedButton() == open_zenodo_button:
            # Open web link
            url = "https://zenodo.org/record/7871174"
            webbrowser.open(url)

    def setButtonState(self, indices):
        # Clear all button states
        self.btn_bg_shirley_static.setChecked(False)
        self.btn_bg_shirley_act.setChecked(False)
        self.btn_bg_tougaard_static.setChecked(False)
        self.btn_bg_tougaard_act.setChecked(False)
        self.btn_bg_polynomial.setChecked(False)
        self.btn_bg_arctan.setChecked(False)
        self.btn_bg_erf.setChecked(False)
        self.btn_bg_vbm.setChecked(False)
        self.btn_bg_slope.setChecked(False)

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
            self.set_status("limit_set")
        else:
            self.set_status("unset")

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
            self.status_label.setStyleSheet(
                "background-color: grey; border-radius: 9px"
            )
            self.status_text.setText("Status: Limits not used")
        elif status == "limit_set":
            self.status_label.setStyleSheet(
                "background-color: green; border-radius: 9px"
            )
            self.status_text.setText("Limits active")
        elif status == "at_zero":
            self.status_label.setStyleSheet(
                "background-color: yellow; border-radius: 9px"
            )
            self.status_text.setText("Limit at 0. ")
            self.status_text.setToolTip(
                "<html><head/><body><p>If a limit reaches zero, a warning is displayed. Usually, such a case is intended because several parameters such as the amplitude and the assymetry are limited to positive values.</p></body></html>"
            )
        else:
            self.status_label.setStyleSheet(
                "background-color: blue; border-radius: 9px"
            )
            self.status_text.setText("Error, Unknown state!")

    def resizeAllColumns(self):
        self.res_tab.resizeColumnsToContents()
        self.res_tab.resizeRowsToContents()
        self.stats_tab.resizeColumnsToContents()
        self.stats_tab.resizeRowsToContents()
        self.fitp1_lims.resizeColumnsToContents()
        self.fitp1_lims.resizeRowsToContents()
        self.fitp1.resizeColumnsToContents()
        self.fitp1.resizeRowsToContents()
        self.fitp0.resizeColumnsToContents()
        self.fitp0.resizeRowsToContents()
        for column in range(self.fitp1.columnCount()):
            if column % 2 == 1:
                self.fitp1.setColumnWidth(column, self.column_width)
        for column in range(self.fitp1_lims.columnCount()):
            if column % 3 != 0:
                self.fitp1_lims.setColumnWidth(column, self.column_width)
        for column in range(self.res_tab.columnCount()):
            self.res_tab.setColumnWidth(column, self.column_width)

    def clicked_cross_section(self):
        window_cross_section = Window_CrossSection()

        window_cross_section.show()
        window_cross_section.btn_cc.clicked.connect(
            lambda: self.setCrossSection(window_cross_section)
        )

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
                self.fitp0.item(row, col).setFlags(
                    self.fitp0.item(row, col).flags()
                    & ~QtCore.Qt.ItemIsEditable
                    & ~QtCore.Qt.ItemIsEnabled
                    & ~QtCore.Qt.ItemIsSelectable
                )

        for idx in self.idx_bg:
            for col in range(ncols):
                for row in range(nrows):
                    if idx == 0 and row == 0 and col < 4:
                        self.fitp0.item(row, col).setFlags(
                            self.fitp0.item(row, col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                    elif idx == 100 and row == 0:
                        self.fitp0.item(row, col).setFlags(
                            self.fitp0.item(row, col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                    elif idx == 1 and row == 1:
                        self.fitp0.item(row, col).setFlags(
                            self.fitp0.item(row, col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                    elif idx == 101 and row == 1:
                        self.fitp0.item(row, col).setFlags(
                            self.fitp0.item(row, col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                    elif idx == 6 and row == 3 and col < 2:
                        self.fitp0.item(row, col).setFlags(
                            self.fitp0.item(row, col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                    elif idx == 3 and row == 4:
                        self.fitp0.item(row, col).setFlags(
                            self.fitp0.item(row, col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                    elif idx == 2 and row == 2:
                        self.fitp0.item(row, col).setFlags(
                            self.fitp0.item(row, col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )

                    elif idx == 4 and row == 5:
                        self.fitp0.item(row, col).setFlags(
                            self.fitp0.item(row, col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                    elif idx == 5 and row == 6:
                        self.fitp0.item(row, col).setFlags(
                            self.fitp0.item(row, col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
        nrows = self.fitp1.rowCount()
        ncols = self.fitp1.columnCount()
        ncols = int(ncols / 2)
        for col in range(ncols):
            for row in range(nrows - 1):
                if (
                    self.fitp1.item(row + 1, 2 * col + 1) is None
                    and self.fitp1.cellWidget(row + 1, 2 * col + 1) is not None
                ):
                    self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(False)
                if self.fitp1.item(row + 1, 2 * col + 1) is not None:
                    self.fitp1.item(row + 1, 2 * col).setFlags(
                        self.fitp1.item(row + 1, 2 * col).flags()
                        & ~QtCore.Qt.ItemIsEditable
                        & ~QtCore.Qt.ItemIsEnabled
                        & ~QtCore.Qt.ItemIsSelectable
                    )
                    self.fitp1.item(row + 1, 2 * col + 1).setFlags(
                        self.fitp1.item(row + 1, 2 * col + 1).flags()
                        & ~QtCore.Qt.ItemIsEditable
                        & ~QtCore.Qt.ItemIsEnabled
                        & ~QtCore.Qt.ItemIsSelectable
                    )
        for col in range(ncols):
            idx = self.fitp1.cellWidget(0, 2 * col + 1).currentIndex()
            for row in range(nrows - 1):
                if row == 0 or row == 1 or row == 13 or row == 15:
                    self.fitp1.item(row + 1, 2 * col).setFlags(
                        self.fitp1.item(row + 1, 2 * col).flags()
                        | QtCore.Qt.ItemIsEditable
                        | QtCore.Qt.ItemIsEnabled
                        | QtCore.Qt.ItemIsSelectable
                    )
                    self.fitp1.item(row + 1, 2 * col + 1).setFlags(
                        self.fitp1.item(row + 1, 2 * col + 1).flags()
                        | QtCore.Qt.ItemIsEditable
                        | QtCore.Qt.ItemIsEnabled
                        | QtCore.Qt.ItemIsSelectable
                    )
                if row == 12 or row == 14:
                    self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(True)
                if (
                    idx == 1
                    or idx == 2
                    or idx == 3
                    or idx == 6
                    or idx == 9
                    or idx == 10
                    or idx == 11
                ):
                    if row == 2 or row == 17:
                        self.fitp1.item(row + 1, 2 * col).setFlags(
                            self.fitp1.item(row + 1, 2 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(
                            self.fitp1.item(row + 1, 2 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                    if row == 16:
                        self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(True)
                if (
                    idx == 0
                    or idx == 2
                    or idx == 4
                    or idx == 5
                    or idx == 6
                    or idx == 7
                    or idx == 8
                    or idx == 10
                    or idx == 11
                    or idx == 12
                ):
                    if row == 3 or row == 19:
                        self.fitp1.item(row + 1, 2 * col).setFlags(
                            self.fitp1.item(row + 1, 2 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(
                            self.fitp1.item(row + 1, 2 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                    if row == 18:
                        self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(True)
                if idx == 4 or idx == 5 or idx == 9 or idx == 10 or idx == 11:
                    if row == 4 or row == 21:
                        self.fitp1.item(row + 1, 2 * col).setFlags(
                            self.fitp1.item(row + 1, 2 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(
                            self.fitp1.item(row + 1, 2 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                    if row == 20:
                        self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(True)

                if idx == 3:
                    if row == 5:
                        self.fitp1.item(row + 1, 2 * col).setFlags(
                            self.fitp1.item(row + 1, 2 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(
                            self.fitp1.item(row + 1, 2 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )

                if idx == 6:
                    if row == 6:
                        self.fitp1.item(row + 1, 2 * col).setFlags(
                            self.fitp1.item(row + 1, 2 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(
                            self.fitp1.item(row + 1, 2 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )

                if idx == 7:
                    if row == 7:
                        self.fitp1.item(row + 1, 2 * col).setFlags(
                            self.fitp1.item(row + 1, 2 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(
                            self.fitp1.item(row + 1, 2 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                if idx == 12:
                    if row == 8:
                        self.fitp1.item(row + 1, 2 * col).setFlags(
                            self.fitp1.item(row + 1, 2 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(
                            self.fitp1.item(row + 1, 2 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                if idx == 10:
                    if row == 9 or row == 23 or row == 10 or row == 25 or row == 11:
                        self.fitp1.item(row + 1, 2 * col).setFlags(
                            self.fitp1.item(row + 1, 2 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1.item(row + 1, 2 * col + 1).setFlags(
                            self.fitp1.item(row + 1, 2 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                    if row == 22 or row == 24:
                        self.fitp1.cellWidget(row + 1, 2 * col + 1).setEnabled(True)
        nrows = self.fitp1_lims.rowCount()
        ncols = self.fitp1_lims.columnCount()
        ncols = int(ncols / 3)
        for col in range(ncols):
            for row in range(nrows):
                if self.fitp1_lims.item(row, 3 * col + 1) is not None:
                    self.fitp1_lims.item(row, 3 * col).setFlags(
                        self.fitp1_lims.item(row, 3 * col).flags()
                        & ~QtCore.Qt.ItemIsEditable
                        & ~QtCore.Qt.ItemIsEnabled
                        & ~QtCore.Qt.ItemIsSelectable
                    )
                    self.fitp1_lims.item(row, 3 * col + 1).setFlags(
                        self.fitp1_lims.item(row, 3 * col + 1).flags()
                        & ~QtCore.Qt.ItemIsEditable
                        & ~QtCore.Qt.ItemIsEnabled
                        & ~QtCore.Qt.ItemIsSelectable
                    )
                    self.fitp1_lims.item(row, 3 * col + 2).setFlags(
                        self.fitp1_lims.item(row, 3 * col + 2).flags()
                        & ~QtCore.Qt.ItemIsEditable
                        & ~QtCore.Qt.ItemIsEnabled
                        & ~QtCore.Qt.ItemIsSelectable
                    )
        for col in range(ncols):
            idx = self.fitp1.cellWidget(0, 2 * col + 1).currentIndex()
            for row in range(nrows):
                if row == 0 or row == 1 or row == 12 or row == 13:
                    self.fitp1_lims.item(row, 3 * col).setFlags(
                        self.fitp1_lims.item(row, 3 * col).flags()
                        | QtCore.Qt.ItemIsEditable
                        | QtCore.Qt.ItemIsEnabled
                        | QtCore.Qt.ItemIsSelectable
                    )
                    self.fitp1_lims.item(row, 3 * col + 1).setFlags(
                        self.fitp1_lims.item(row, 3 * col + 1).flags()
                        | QtCore.Qt.ItemIsEditable
                        | QtCore.Qt.ItemIsEnabled
                        | QtCore.Qt.ItemIsSelectable
                    )
                    self.fitp1_lims.item(row, 3 * col + 2).setFlags(
                        self.fitp1_lims.item(row, 3 * col + 2).flags()
                        | QtCore.Qt.ItemIsEditable
                        | QtCore.Qt.ItemIsEnabled
                        | QtCore.Qt.ItemIsSelectable
                    )
                if (
                    idx == 1
                    or idx == 2
                    or idx == 3
                    or idx == 6
                    or idx == 9
                    or idx == 10
                    or idx == 11
                ):
                    if row == 2 or row == 14:
                        self.fitp1_lims.item(row, 3 * col).setFlags(
                            self.fitp1_lims.item(row, 3 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 2).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )

                if (
                    idx == 0
                    or idx == 2
                    or idx == 4
                    or idx == 5
                    or idx == 6
                    or idx == 7
                    or idx == 8
                    or idx == 10
                    or idx == 11
                    or idx == 12
                ):
                    if row == 3 or row == 15:
                        self.fitp1_lims.item(row, 3 * col).setFlags(
                            self.fitp1_lims.item(row, 3 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 2).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )

                if idx == 4 or idx == 5 or idx == 9 or idx == 10 or idx == 11:
                    if row == 4 or row == 16:
                        self.fitp1_lims.item(row, 3 * col).setFlags(
                            self.fitp1_lims.item(row, 3 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 2).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )

                if idx == 3:
                    if row == 5:
                        self.fitp1_lims.item(row, 3 * col).setFlags(
                            self.fitp1_lims.item(row, 3 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 2).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )

                if idx == 6:
                    if row == 6:
                        self.fitp1_lims.item(row, 3 * col).setFlags(
                            self.fitp1_lims.item(row, 3 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 2).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )

                if idx == 7:
                    if row == 7:
                        self.fitp1_lims.item(row, 3 * col).setFlags(
                            self.fitp1_lims.item(row, 3 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 2).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                if idx == 12:
                    if row == 8:
                        self.fitp1_lims.item(row, 3 * col).setFlags(
                            self.fitp1_lims.item(row, 3 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 2).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                if idx == 10:
                    if row == 9 or row == 10 or row == 11 or row == 17 or row == 18:
                        self.fitp1_lims.item(row, 3 * col).setFlags(
                            self.fitp1_lims.item(row, 3 * col).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 1).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 1).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )
                        self.fitp1_lims.item(row, 3 * col + 2).setFlags(
                            self.fitp1_lims.item(row, 3 * col + 2).flags()
                            | QtCore.Qt.ItemIsEditable
                            | QtCore.Qt.ItemIsEnabled
                            | QtCore.Qt.ItemIsSelectable
                        )

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
        self.pre[0] = [
            self.idx_bg,
            self.xmin,
            self.xmax,
            self.hv,
            self.wf,
            self.correct_energy,
        ]

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
        error_message = (
            error_message + "\n *******************\n" + traceback.format_exc()
        )
        self.error_dialog.showMessage(error_message)
        logging.error(error_message)

    def add_col(self, loaded=False):
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
                add_fac = (
                    -float(self.fitp1.item(row + 3, colPosition_fitp1 - 1).text()) * 2
                )
            if row == 1:
                add_fac = (
                    -1
                    * float(self.fitp1.item(row + 1, colPosition_fitp1 - 1).text())
                    / 2
                )
            if (
                self.fitp1.item(row + 1, colPosition_fitp1 - 1) is not None
                and row != 12
                and row != 14
                and row != 16
                and row != 18
                and row != 20
                and row != 22
                and row != 24
            ):
                if len(self.fitp1.item(row + 1, colPosition_fitp1 - 1).text()) > 0:
                    item = QtWidgets.QTableWidgetItem(
                        str(
                            format(
                                float(
                                    self.fitp1.item(
                                        row + 1, colPosition_fitp1 - 1
                                    ).text()
                                )
                                + add_fac,
                                self.floating,
                            )
                        )
                    )
                    self.fitp1.setItem(row + 1, colPosition_fitp1 + 1, item)

        # add table header
        if loaded:
            fitp1 = [item for string in loaded[1:] for item in ["", string]]
            fitp1_lims = [
                item for string in loaded[1:] for item in [string, "min", "max"]
            ]
            self.fitp1.setHorizontalHeaderLabels(fitp1)
            self.fitp1_lims.setHorizontalHeaderLabels(fitp1_lims)
            self.res_tab.setHorizontalHeaderLabels(loaded[1:])
            self.list_component = loaded

        else:
            comp_name = self.nextFreeComponentName()
            item = QtWidgets.QTableWidgetItem("")
            self.fitp1.setHorizontalHeaderItem(colPosition_fitp1, item)
            item = QtWidgets.QTableWidgetItem(str(comp_name))
            self.fitp1.setHorizontalHeaderItem(colPosition_fitp1 + 1, item)

            item = QtWidgets.QTableWidgetItem(str(comp_name))
            self.res_tab.setHorizontalHeaderItem(colPosition_res, item)
            item = QtWidgets.QTableWidgetItem(str(comp_name))
            self.fitp1_lims.setHorizontalHeaderItem(colPosition_fitp1_lims, item)
            item = QtWidgets.QTableWidgetItem("min")
            self.fitp1_lims.setHorizontalHeaderItem(colPosition_fitp1_lims + 1, item)
            item = QtWidgets.QTableWidgetItem("max")
            self.fitp1_lims.setHorizontalHeaderItem(colPosition_fitp1_lims + 2, item)
            self.list_component.append(comp_name)
        self.resizeAllColumns()

        # add DropDown component selection for amp_ref and ctr_ref and keep values as it is
        self.updateDropdown(colposition=colPosition_fitp1)

        # add checkbox
        for row in range(rowPosition - 1):
            item = QtWidgets.QTableWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            item.setToolTip("Check to keep fixed during fit procedure")
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
                item.setText("")
            self.fitp1.setItem(row + 1, colPosition_fitp1, item)

        # add checkbox and entries in limits table
        for row in range(self.fitp1_lims.rowCount()):
            item = QtWidgets.QTableWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            item.setCheckState(QtCore.Qt.Unchecked)
            item.setToolTip("Check to use limit during fit procedure")
            self.fitp1_lims.setItem(row, colPosition_fitp1_lims, item)
            item = QtWidgets.QTableWidgetItem()
            item.setText("")
            self.fitp1_lims.setItem(row, colPosition_fitp1_lims + 1, item)
            item = QtWidgets.QTableWidgetItem()
            item.setText("")
            self.fitp1_lims.setItem(row, colPosition_fitp1_lims + 2, item)

        self.activeParameters()
        self.savePreset()

    def removeCol(self, idx=None, text=None):
        if text == "--":
            pass
        else:
            if idx == None or text == "Remove Last Column":
                colPosition = self.fitp1.columnCount() - 2
                colPosition_lims = self.fitp1_lims.columnCount() - 3
                colPosition_res = self.res_tab.columnCount() - 1
            elif idx != None:
                colPosition = (idx - 2) * 2
                colPosition_lims = int((idx - 2) * 3)
                colPosition_res = int(idx - 2)
            if (
                self.res_tab.columnCount() > 1
                and self.fitp1_lims.columnCount() > 3
                and self.fitp1.columnCount() > 2
            ):
                self.res_tab.removeColumn(colPosition_res)
                self.fitp1_lims.removeColumn(colPosition_lims + 2)
                self.fitp1_lims.removeColumn(colPosition_lims + 1)
                self.fitp1_lims.removeColumn(colPosition_lims)
                self.fitp1.removeColumn(colPosition + 1)
                self.fitp1.removeColumn(colPosition)
                self.updateDropdown()
            else:
                print("Cannot remove the last remaining column.")
        self.savePreset()
        header_texts = [""]
        for column in range(int(self.fitp1.columnCount() / 2)):
            header_item = self.fitp1.horizontalHeaderItem(int(column * 2 + 1))
            if header_item is not None:
                header_texts.append(header_item.text())
        self.list_component = header_texts

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

        self.pre[0] = [
            temp_pre[0],
            temp_pre[1][0][1],
            temp_pre[1][0][3],
            temp_pre[1][0][7],
            temp_pre[1][0][9],
        ]
        temp = []
        for i in range(len(temp_pre[1]) - 2):
            if i == 0:
                entry = []
                for j in range(int(len(temp_pre[1][i + 1]) / 2 - 1)):
                    if j < 2:
                        entry.append("")
                    else:
                        entry.append(0)
                    entry.append(temp_pre[1][i + 1][2 * j + 1])
                entry.append("")
                entry.append("")
            elif i == 1:
                entry = [0]
                for j in range(int(len(temp_pre[1][i + 1]) / 2 - 1)):
                    entry.append(temp_pre[1][i + 1][2 * j + 1])
                    entry.append("")
                entry.append("")
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
        temp.append(["", 0] * int(len(temp_pre[2][0]) / 2))
        temp.append([2, 1] * int(len(temp_pre[2][0]) / 2))
        temp.extend(temp_pre[2][17:21])
        self.pre[2] = temp
        self.pre.append(
            [[0, "", ""]] * 19
        )  # currently, limits of old format are ignored!

    def preset(self):
        index = self.idx_pres
        colPosition = self.fitp1.columnCount()

        if index == 1:
            if colPosition > 2:
                for col in range(int(colPosition / 2) - 1):
                    self.removeCol(idx=None)
            # load default preset
            if self.comboBox_file.currentIndex() > 0:
                x0 = self.df.iloc[:, 0].to_numpy()
                y0 = self.df.iloc[:, 1].to_numpy()
                pre_pk = [
                    [0, 0],
                    [0, x0[abs(y0 - y0.max()).argmin()]],
                    [0, y0[abs(y0 - y0.max()).argmin()]],
                    [2, 0],
                    [0, abs(x0[0] - x0[-1]) / (0.2 * len(x0))],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                ]
            else:
                pre_pk = [
                    [0, 0],
                    [0, 285],
                    [0, 20000],
                    [2, 0],
                    [0, 0.2],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                    [2, 0],
                ]
            self.setPreset([0], [], pre_pk)
        if index == 2:
            try:
                self.loadPreset()
            except Exception as e:
                return self.raise_error(
                    window_title="Error: Could not load parameters!",
                    error_message="Loading parameters failed. The following traceback may help to solve the issue:",
                )
            if (
                len(str(self.pre[0])) != 0
                and len(self.pre[1]) != 0
                and len(self.pre[2]) != 0
                and len(self.pre) == 3
            ):
                # old format, reorder data!
                self.reformat_pre()
                self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
            elif (
                len(str(self.pre[0])) != 0
                and len(self.pre[1]) != 0
                and len(self.pre[2]) != 0
                and len(self.pre[3]) != 0
            ):
                # new format
                self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
        if index == 3:
            try:
                self.addPreset()
            except Exception as e:
                return self.raise_error(
                    window_title="Error: Could not add parameters!",
                    error_message="Adding parameters failed. The following traceback may help to solve the issue:",
                )
            if (
                len(str(self.pre[0])) != 0
                and len(self.pre[1]) != 0
                and len(self.pre[2]) != 0
                and len(self.pre) == 3
            ):
                # old format, reorder data!
                self.reformat_pre()
                self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
            elif (
                len(str(self.pre[0])) != 0
                and len(self.pre[1]) != 0
                and len(self.pre[2]) != 0
                and len(self.pre[3]) != 0
            ):
                # new format
                self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
        if index == 4:
            try:
                self.savePreset()
            except Exception as e:
                return self.raise_error(
                    window_title="Error: Could not save parameters!",
                    error_message="Save parameters failed. The following traceback may help to solve the issue:",
                )
            try:
                self.savePresetDia()
            except Exception as e:
                return self.raise_error(
                    window_title="Error: Could not save!",
                    error_message="Saving data failed. The following traceback may help to solve the issue:",
                )
        if index == 5:  # reformat inputs [bug]
            # load C1s component preset
            pre_bg = [
                [2, 295, 2, 275, "", "", "", "", "", ""],
                ["cv", 1e-06, "it", 10, "", "", "", "", "", ""],
                ["B", 2866.0, "C", 1643.0, "C*", 1.0, "D", 1.0, "Keep fixed?", 0],
                [2, 0, 2, 0, 2, 0, 2, 0, "", ""],
            ]
            if self.comboBox_file.currentIndex() > 0:
                y0 = self.df.iloc[:, 1].to_numpy()
                pre_pk = [
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [2, 284.6, 2, 286.5, 2, 288.0, 2, 291.0],
                    [2, 0.85, 2, 0.85, 2, 1.28, 2, 1.28],
                    [2, 0.85, 2, 0.85, 2, 1.28, 2, 1.28],
                    [
                        0,
                        y0[abs(y0 - y0.max()).argmin()] * 2.5 * 0.85,
                        0,
                        y0[abs(y0 - y0.max()).argmin()] * 2.5 * 0.85 * 0.1,
                        0,
                        y0[abs(y0 - y0.max()).argmin()] * 2.5 * 0.85 * 0.05,
                        0,
                        y0[abs(y0 - y0.max()).argmin()] * 2.5 * 0.85 * 0.05,
                    ],
                    [2, 0.5, 2, 0.5, 2, 0.5, 2, 0.5],
                ]
            else:
                pre_pk = [
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [2, 284.6, 2, 286.5, 2, 288.0, 2, 291.0],
                    [2, 0.85, 2, 0.85, 2, 1.28, 2, 1.28],
                    [2, 0.85, 2, 0.85, 2, 1.28, 2, 1.28],
                    [0, 20000, 0, 2000, 0, 750, 0, 750],
                    [2, 0.5, 2, 0.5, 2, 0.5, 2, 0.5],
                ]
            self.setPreset([0], pre_bg, pre_pk)
        if index == 6:  # reformat inputs [bug]
            # load C K edge preset
            pre_bg = [
                [2, 270.7, 2, 320.7, "", "", "", "", "", ""],
                ["cv", 1e-06, "it", 10.0, "", "", "", "", "", ""],
                ["B", 2866.0, "C", 1643.0, "C*", 1.0, "D", 1.0, "Keep fixed?", 0],
                [2, 0.07, 2, 0.0, 2, 0.0, 2, 0.0, "", ""],
                [2, 12.05, 2, 43.36, 2, 0.05, 0, "", "", ""],
                [2, 0.27, 2, 291.82, 2, 0.72, 0, "", "", ""],
                [0, "", 0, "", 0, "", 0, "", "", ""],
            ]

            pre_pk = [
                ["", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0],
                [
                    0,
                    284.95,
                    0,
                    286.67,
                    0,
                    287.57,
                    0,
                    289.0,
                    0,
                    290.69,
                    0,
                    292.27,
                    2,
                    296.0,
                    2,
                    302.0,
                    2,
                    310.0,
                ],
                [
                    0,
                    0.67,
                    0,
                    0.5,
                    0,
                    0.8,
                    0,
                    0.8,
                    0,
                    1.0,
                    0,
                    1.5,
                    0,
                    3.0,
                    0,
                    5.0,
                    0,
                    5.0,
                ],
                [
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                ],
                [
                    0,
                    0.51,
                    0,
                    0.1,
                    0,
                    0.32,
                    0,
                    0.37,
                    0,
                    0.28,
                    0,
                    0.29,
                    0,
                    0.59,
                    0,
                    1.21,
                    0,
                    0.2,
                ],
                [
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                    2,
                    0.0,
                ],
                [2, "", 2, "", 2, "", 2, "", 2, "", 2, "", 2, "", 2, "", 2, ""],
                [2, "", 2, "", 2, "", 2, "", 2, "", 2, "", 2, "", 2, "", 2, ""],
                ["", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0],
                [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
                ["", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0],
                [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
                [0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, ""],
                [0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, ""],
                [
                    2,
                    0.5,
                    2,
                    0.5,
                    2,
                    0.5,
                    2,
                    0.5,
                    2,
                    0.5,
                    2,
                    1.0,
                    2,
                    2.0,
                    2,
                    2.0,
                    2,
                    2.0,
                ],
                [
                    2,
                    0.8,
                    2,
                    0.8,
                    2,
                    0.8,
                    2,
                    0.8,
                    2,
                    1.0,
                    2,
                    1.5,
                    2,
                    3.0,
                    2,
                    5.0,
                    2,
                    5.0,
                ],
                [0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, ""],
                [0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, "", 0, ""],
                [
                    2,
                    0.1,
                    2,
                    0.1,
                    2,
                    0.1,
                    2,
                    0.1,
                    2,
                    0.0,
                    2,
                    0.1,
                    2,
                    0.1,
                    2,
                    0.1,
                    2,
                    0.0,
                ],
            ]
            self.setPreset([4], pre_bg, pre_pk)
        if index == 7:
            self.pt.show()
            self.pt.refresh_button.clicked.connect(self.plot_pt)
            self.pt.clear_button.clicked.connect(self.plot_pt)
            if not self.pt.isActiveWindow():
                self.pt.close()
                self.pt.show()

        self.idx_pres = 0
        self.resizeAllColumns()

    def setPreset(
        self,
        list_pre_com,
        list_pre_bg,
        list_pre_pk,
        list_pre_pk_lims=[[0, "", ""]] * 19,
    ):
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
            if len(list_pre_com) == 6:
                self.correct_energy = list_pre_com[5]
                self.correct_energy_item.setText(
                    str(format(self.correct_energy, self.floating))
                )
        self.displayChoosenBG.setText(
            "Choosen Background: {}".format(
                "+ ".join([dictBG[str(idx)] for idx in self.idx_bg])
            )
        )
        # load preset for bg
        if len(list_pre_bg) != 0:
            for row in range(len(list_pre_bg)):
                for col in range(len(list_pre_bg[0])):
                    item = self.fitp0.item(row, col)
                    if (
                        row == 2
                        or row > 3
                        or (row == 3 and col < 2)
                        or (row == 0 and 8 > col >= 4)
                        or (row == 1 and col == 0)
                    ) and col % 2 == 0:
                        if list_pre_bg[row][col] == 2:
                            item.setCheckState(QtCore.Qt.Checked)
                        else:
                            item.setCheckState(QtCore.Qt.Unchecked)
                    elif row <= 1 and col % 2 == 0:
                        item.setText("")
                    else:
                        item.setText(str(list_pre_bg[row][col]))
        # load preset for components
        # adjust ncomponent before load
        if len(list_pre_pk) != 0:
            colPosition = int(self.fitp1.columnCount() / 2)
            # print(int(colPosition), int(len(list_pre_pk[0])/2), list_pre_pk[0])
            if colPosition > int(len(list_pre_pk[0]) / 2):
                for col in range(colPosition - int(len(list_pre_pk[0]) / 2)):
                    self.removeCol(idx=None)
            if colPosition < int(len(list_pre_pk[0]) / 2):
                for col in range(int(len(list_pre_pk[0]) / 2) - colPosition):
                    self.add_col(loaded=self.list_component)
        for row in range(len(list_pre_pk)):
            for col in range(len(list_pre_pk[0])):
                if (col % 2) != 0:
                    if (
                        row == 0
                        or row == 13
                        or row == 15
                        or row == 17
                        or row == 19
                        or row == 21
                        or row == 23
                        or row == 25
                    ):
                        comboBox = QtWidgets.QComboBox()
                        if row == 0:
                            comboBox.addItems(self.list_shape)
                            comboBox.currentTextChanged.connect(self.activeParameters)
                        else:
                            comboBox.addItems(self.list_component)
                        self.fitp1.setCellWidget(row, col, comboBox)
                        comboBox.setCurrentIndex(int(float(list_pre_pk[row][col])))
                    else:
                        item = self.fitp1.item(row, col)
                        if str(list_pre_pk[row][col]) == "":
                            item.setText("")
                        else:
                            item.setText(
                                str(format(float(list_pre_pk[row][col]), self.floating))
                            )
                else:
                    if (
                        row != 0
                        and row != 13
                        and row != 15
                        and row != 17
                        and row != 19
                        and row != 21
                        and row != 23
                        and row != 25
                    ):
                        item = self.fitp1.item(row, col)
                        item.setText("")
                        if list_pre_pk[row][col] == 2:
                            item.setCheckState(QtCore.Qt.Checked)
                        else:
                            item.setCheckState(QtCore.Qt.Unchecked)
            for row in range(len(list_pre_pk_lims)):
                for col in range(len(list_pre_pk_lims[0])):
                    item = self.fitp1_lims.item(row, col)
                    if (col % 3) != 0:
                        if str(list_pre_pk_lims[row][col]) == "":
                            item.setText("")
                        else:
                            item.setText(
                                str(
                                    format(
                                        float(list_pre_pk_lims[row][col]), self.floating
                                    )
                                )
                            )
                    else:
                        if list_pre_pk_lims[row][col] == 2:
                            item.setCheckState(QtCore.Qt.Checked)
                        else:
                            item.setCheckState(QtCore.Qt.Unchecked)
        self.activeParameters()
        self.lims_changed()
        self.list_component = self.renameDuplicates(self.list_component)
        fitp1_comps = [
            item for string in self.list_component[1:] for item in ["", string]
        ]
        fitp1_lims = [
            item
            for string in self.list_component[1:]
            for item in [string, "min", "max"]
        ]
        self.fitp1.setHorizontalHeaderLabels(fitp1_comps)
        self.fitp1_lims.setHorizontalHeaderLabels(fitp1_lims)
        if self.res_tab:
            self.res_tab.setHorizontalHeaderLabels(self.list_component[1:])
        self.savePreset()

    def loadPreset(self):
        cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open data file", self.filePath, "DAT Files (*.dat)"
        )
        if cfilePath != "":
            self.cfilePath = cfilePath
            self.filePath = self.cfilePath.rsplit("/", 1)[0]
            with open(self.cfilePath, "r") as file:
                temp_pre = file.read()
            file.close()
            # print(self.pre, type(self.pre))
            self.pre = ast.literal_eval(temp_pre)
            if (
                type(self.pre[0][0]) == int
            ):  # backwards compatibility for old presets which only allowed one single BG
                self.idx_bg = [self.pre[0][0]]
            else:
                self.idx_bg = self.pre[0][0]
            if len(self.pre) == 5 and len(self.pre[4]) - 1 == int(
                len(self.pre[2][0]) / 2
            ):
                self.list_component = self.pre[4]
            else:
                list_component = [""]
                for i in range(int(len(self.pre[2][0]) / 2)):
                    list_component.append("C_{}".format(str(int(i + 1))))
                self.list_component = list_component
            self.list_component = self.renameDuplicates(self.list_component)
            fitp1_comps = [
                item for string in self.list_component[1:] for item in ["", string]
            ]
            fitp1_lims = [
                item
                for string in self.list_component[1:]
                for item in [string, "min", "max"]
            ]
            self.fitp1.setHorizontalHeaderLabels(fitp1_comps)
            self.fitp1_lims.setHorizontalHeaderLabels(fitp1_lims)
            self.res_tab.setHorizontalHeaderLabels(self.list_component[1:])

            self.setButtonState(self.idx_bg)
            # self.pre = json.loads(self.pre) #json does not work due to the None issue
            # print(self.pre, type(self.pre))
            # self.comboBox_pres.clear()
            # self.comboBox_pres.setCurrentIndex(0)
            self.idx_pres = 0
        else:
            self.pre = [[], [], [], []]

    def addPreset(self):
        cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open data file", self.filePath, "DAT Files (*.dat)"
        )
        if cfilePath != "":
            self.cfilePath = cfilePath
            self.filePath = self.cfilePath.rsplit("/", 1)[0]
            with open(self.cfilePath, "r") as file:
                temp_pre = file.read()
            file.close()
            temp_settings = self.pre[0]
            temp_bg = self.pre[1]
            temp_pre = ast.literal_eval(temp_pre)
            temp_pks = temp_pre[2]
            current_len = int(len(self.pre[2][0]) / 2)
            for col in range(int(len(temp_pks[0]) / 2)):
                for row in range(len(temp_pks)):
                    if (
                        row == 13
                        or row == 15
                        or row == 17
                        or row == 19
                        or row == 21
                        or row == 23
                        or row == 25
                    ):
                        if not temp_pks[row][2 * col + 1] == 0:
                            temp_pks[row][2 * col + 1] = (
                                temp_pks[row][2 * col + 1] + current_len
                            )
            temp_peaks = np.concatenate((self.pre[2], temp_pks), axis=1)
            temp_lims = np.concatenate((self.pre[3], temp_pre[3]), axis=1)
            if len(temp_pre) == 5 and len(temp_pre[4]) - 1 == int(
                len(temp_pre[2][0]) / 2
            ):
                self.list_component = np.concatenate(
                    (self.list_component, temp_pre[4][1:]), axis=0
                )
            else:
                temp_list_component = []
                for i in range(int(len(temp_pre[2][0]) / 2)):
                    temp_list_component.append("C_{}".format(str(int(i + 1))))
                self.list_component = np.concatenate(
                    (self.list_component, temp_list_component), axis=0
                )
            self.list_component = self.renameDuplicates(self.list_component)
            self.pre = [
                temp_settings,
                temp_bg,
                temp_peaks,
                temp_lims,
                self.list_component,
            ]
            fitp1_comps = [
                item for string in self.list_component[1:] for item in ["", string]
            ]
            fitp1_lims = [
                item
                for string in self.list_component[1:]
                for item in [string, "min", "max"]
            ]
            self.fitp1.setHorizontalHeaderLabels(fitp1_comps)
            self.fitp1_lims.setHorizontalHeaderLabels(fitp1_lims)
            self.res_tab.setHorizontalHeaderLabels(self.list_component[1:])
            self.idx_pres = 0
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
                if (col % 2) != 0:
                    if (
                        self.fitp0.item(row, col) is None
                        or len(self.fitp0.item(row, col).text()) == 0
                    ):
                        new.append("")
                    else:
                        new.append(float(self.fitp0.item(row, col).text()))
                else:
                    if self.fitp0.item(row, col) is None:
                        new.append("")
                    elif (row == 0 and col in [0, 2, 8]) or (
                        row == 1 and col in [2, 4, 6, 8]
                    ):
                        new.append("")
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
                    if (
                        row == 0
                        or row == 13
                        or row == 15
                        or row == 17
                        or row == 19
                        or row == 21
                        or row == 23
                        or row == 25
                    ):
                        new.append(self.fitp1.cellWidget(row, col).currentIndex())
                    else:
                        if (
                            self.fitp1.item(row, col) is None
                            or len(self.fitp1.item(row, col).text()) == 0
                        ):
                            new.append("")
                        else:
                            new.append(float(self.fitp1.item(row, col).text()))
                else:
                    if (
                        row != 0
                        and row != 13
                        and row != 15
                        and row != 17
                        and row != 19
                        and row != 21
                        and row != 23
                        and row != 25
                    ):
                        if self.fitp1.item(row, col).checkState() == 2:
                            new.append(2)
                        else:
                            new.append(0)
                    else:
                        if (
                            self.fitp1.item(row, col) is None
                            or len(self.fitp1.item(row, col).text()) == 0
                        ):
                            new.append("")
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
                    if (
                        self.fitp1_lims.item(row, col) is None
                        or len(self.fitp1_lims.item(row, col).text()) == 0
                    ):
                        new.append("")
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

        self.parText = [
            [self.idx_bg, self.xmin, self.xmax, self.hv, self.wf, self.correct_energy]
        ]
        self.parText.append(list_pre_bg)
        self.parText.append(list_pre_pk)
        self.parText.append(list_pre_lims)
        self.parText.append(self.list_component)
        self.pre = [
            [self.idx_bg, self.xmin, self.xmax, self.hv, self.wf, self.correct_energy]
        ]
        self.pre.append(list_pre_bg)
        self.pre.append(list_pre_pk)
        self.pre.append(list_pre_lims)
        self.pre.append(self.list_component)

    def savePresetDia(self, savename=None):
        if self.comboBox_file.currentIndex() > 0:
            fileName = os.path.basename(str(self.comboBox_file.currentText()))
            fileName = os.path.splitext(fileName)[0] + "_pars"
        else:
            fileName = "sample_pars"

        if savename is not None:
            cfilePath = savename
        else:
            cfilePath, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Preset file",
                self.cfilePath, fileName + ".dat",
                "DAT Files (*.dat)",
            )

        if cfilePath:
            self.cfilePath = cfilePath
            self.filePath = os.path.dirname(cfilePath)
            with open(cfilePath, "w") as file:
                file.write(str(self.parText))


    def export_all(self):
        try:
            savename=self.exportResults()
        except Exception as e:
            return self.raise_error(
                window_title="Error: could not export the results.",
                error_message="Exporting results failed. The following traceback may help to solve the issue:",
            )
        try:
            self.savePreset()
        except Exception as e:
            return self.raise_error(
                window_title="Error: could not save parameters.",
                error_message="Saving parameters failed. The following traceback may help to solve the issue:",
            )
        try:
            self.savePresetDia(savename+'.dat')
        except Exception as e:
            return self.raise_error(
                window_title="Error: could not save parameters /export data.",
                error_message="Saving parameters /exporting data failed. The following traceback may help to solve the issue:",
            )

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

        with open(path_for_export.replace(".txt", ".pickle"), "wb") as handle:
            pickle.dump(
                {
                    "LG4X_parameters": self.parText,
                    "lmfit_parameters": self.export_pars,
                    # 'lmfit_report':self.export_out.fit_report(min_correl=0.1)
                    # 'lmfit_report': lmfit_attr_dict
                    "lmfit_result": self.export_out.result,
                },
                handle,
                protocol=pickle.HIGHEST_PROTOCOL,
            )

    def exportResults(self):
        if self.result.empty:
            self.raise_error(
                window_title="Error: No Results exported!",
                error_message="There is nothing to export here, results are empty.",
            )
            return None
        else:
            if self.comboBox_file.currentIndex() > 0:
                # print(self.export_pars)
                # print(self.export_out.fit_report(min_correl=0.5))
                fileName = os.path.basename(str(self.comboBox_file.currentText()))
                fileName = os.path.splitext(fileName)[0]
            else:
                cfilePath = self.filePath.rsplit("/", 1)[0]
                fileName = "sample"

            # S_File will get the directory path and extension.
            cfilePath, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Fit file",
                self.cfilePath + os.sep + fileName + "_fit.txt",
                "Text Files (*.txt)",
            )
            if cfilePath != "":
                self.cfilePath = cfilePath
                self.filePath = self.cfilePath.rsplit("/", 1)[0]
                savename=os.path.splitext(cfilePath)[0]

                if self.comboBox_file.currentIndex() == 0:
                    strmode = "simulation mode"
                else:
                    strmode = self.comboBox_file.currentText()
                Text = (
                    self.version
                    + "\n\n[[Data file]]\n\n"
                    + strmode
                    + "\n\n[[Fit results]]\n\n"
                )
                self.savePreset()
                Text += (
                    "\n\n[[LG4X parameters]]\n\n"
                    + str(self.parText)
                    + "\n\n"
                    + str(self.export_out.fit_report(min_correl=0.1))
                )
                Text += "\n\n[[lmfit parameters]]\n\n" + str(self.export_pars)
                Text += "\n\n[[Peak Metadata]]\n\n"
                row_labels = list(
                    dict.fromkeys(
                        [
                            key.split("_", 1)[-1]
                            for d in self.meta_result_export
                            for key in d.keys()
                        ]
                    )
                )

                column_titles = list(
                    dict.fromkeys(
                        [
                            key.split("_", 1)[0]
                            for d in self.meta_result_export
                            for key in d.keys()
                        ]
                    )
                )
                column_widths = {
                    "Property\\Component": max(
                        len("Property\\Component"),
                        max(len(row_label) for row_label in row_labels),
                    )
                }
                for column_title in column_titles:
                    column_widths[column_title] = max(
                        len(column_title), 20
                    )  # Set minimum width for readability

                for d in self.meta_result_export:
                    for key, value in d.items():
                        component, property_name = key.split("_", 1)
                        column_widths[property_name] = max(
                            column_widths.get(property_name, 0), len(str(value))
                        )

                header = [
                    "Property\\Component".ljust(column_widths["Property\\Component"])
                ]
                for column_title in column_titles:
                    header.append(column_title.ljust(column_widths[column_title]))
                Text += "\t".join(header) + "\n"

                table_data = []
                for row_label in row_labels:
                    row = [row_label.ljust(column_widths["Property\\Component"])]
                    for column_title in column_titles:
                        value = None
                        for d in self.meta_result_export:
                            key = f"{column_title}_{row_label}"
                            if key in d:
                                value = d[key]
                                break
                        formatted_value = (
                            str(value).ljust(column_widths[column_title])
                            if value is not None
                            else "N/A".ljust(column_widths[column_title])
                        )
                        row.append(formatted_value)  # Ensure the value is aligned
                    table_data.append(row)

                for row in table_data:
                    Text += "\t".join(row) + "\n"

                Text += "\n\n[[Parameters and Metaparameters as dictionaries]]\n\n"
                Text += "\n\n[[Fit parameters as dictionary]]\n\n" + str(
                    self.export_pars.valuesdict()
                )
                Text += (
                    "\n\n[[Metadata/Values of the Components as dictionary ]]\n\n{\n"
                )
                for dic in self.meta_result_export:
                    for key in dic.keys():
                        Text += "'" + key + "' : " + str(dic[key]) + ",\n"
                Text += "}\n"
                self.export_pickle(
                    self.cfilePath
                )  # export las fit parameters as dict int po pickle file

                with open(self.cfilePath, "w") as file:
                    file.write(str(Text))
                file.close()
                # print(filePath)
                if self.cfilePath.split("_")[-1] == "fit.txt":
                    with open(self.cfilePath.rsplit("_", 1)[0] + "_fit.csv", "w") as f:
                        f.write(
                            "#No of rows lightened (2D detector)"
                            + str(self.rows_lightened)
                            + "(if not using 2D detector, value is 1 and can be ignored!)\n"
                        )
                        self.result.to_csv(f, index=False, mode="a")
                else:
                    with open(self.cfilePath.rsplit(".", 1)[0] + ".csv", "w") as f:
                        f.write(
                            "#No of rows lightened (2D detector)"
                            + str(self.rows_lightened)
                            + "(if not using 2D detector, value is 1 and can be ignored!)\n"
                        )
                        self.result.to_csv(f, index=False, mode="a")
                return savename

    def clickOnBtnImp(self, idx):
        self.plottitle.setText(
            ""
        )  # reset text in plot title QlineEdit, otherwise the old one will remain
        self.idx_imp = idx
        self.imp()

    import pandas as pd
    import os
    def format_display_name(self, path):
        filename = os.path.basename(path)
        parent_folder = os.path.basename(os.path.dirname(path))
        return f"{parent_folder}/{filename}"

    def imp_csv_or_txt(self, cfilePath, remember_settings=True):
        try:
            cfilePath = os.path.abspath(cfilePath)
            fname = os.path.basename(cfilePath)
            if cfilePath in self.data_arr.keys():
                print(f'The file "{cfilePath}" has already been loaded. Skipping')
                QtWidgets.QMessageBox.information(
                    self,
                    "Filename already used",
                    f'The file "{cfilePath}" has already been loaded. Skipping',
                )
                return  # Skip further processing

            if ".txt" in fname:
                df = pd.read_csv(cfilePath, comment="#")
                num_columns = len(df.columns)
            elif ".csv" in fname:
                df = pd.read_csv(cfilePath, comment="#", usecols=[0, 1])
                num_columns = len(df.columns)
            if not num_columns == 2 and not remember_settings:
                remember_settings = False
            if not remember_settings:
                preview_dialog = PreviewDialog(cfilePath, config, config_file_path)
                if preview_dialog.exec_():
                    df = preview_dialog.df
                    filename = preview_dialog.fname
                    if df.isna().any().any():
                        print("automatic import failed, please select correct format!")
                        self.imp_csv_or_txt(cfilePath, remember_settings=False)
                    if df is not None:
                        self.data_arr[cfilePath] = DataSet(
                            filepath=cfilePath, df=df, pe=None
                        )
                else:
                    filename = None
            elif not num_columns == 2:
                if config.getboolean("Import", "has_header"):
                    temp_header = pd.read_csv(
                        cfilePath,
                        delimiter=config.get("Import", "separator"),
                        header=int(config.get("Import", "header_row")),
                        engine="python",
                        nrows=0,
                    )
                    if temp_header.columns.values.tolist()[0] == "#":
                        cols = [col + 1 for col in config.get("Import", "columns")]
                        df = pd.read_csv(
                            cfilePath,
                            delimiter=config.get("Import", "separator"),
                            engine="python",
                            names=temp_header.columns.values.tolist()[1:],
                            skiprows=int(config.get("Import", "header_row")) + 1,
                            comment="#",
                        )
                    else:
                        df = pd.read_csv(
                            cfilePath,
                            delimiter=config.get("Import", "separator"),
                            engine="python",
                            skiprows=int(config.get("Import", "header_row")),
                            comment="#",
                        )
                else:
                    df = pd.read_csv(
                        cfilePath,
                        delimiter=config.get("Import", "separator"),
                        engine="python",
                        skiprows=int(config.get("Import", "header_row")),
                        header=None,
                        comment="#",
                    )
                    df.columns = [f"col{i + 1}" for i in range(len(df.columns))]
                df = df.iloc[:, eval(config.get("Import", "columns"))]
                if df.isna().any().any():
                    print("automatic import failed, please select correct format")
                    self.imp_csv_or_txt(cfilePath, remember_settings=False)
                filename = os.path.basename(cfilePath)
                self.data_arr[cfilePath] = DataSet(filepath=cfilePath, df=df, pe=None)
            else:
                filename = os.path.basename(cfilePath)
                self.data_arr[cfilePath] = DataSet(filepath=cfilePath, df=df, pe=None)

            self.comboBox_file.clear()
            self.comboBox_file.addItems(self.list_file)
            self.display_name_to_path = {
                self.format_display_name(fpath): fpath for fpath in self.data_arr.keys()
            }
            self.comboBox_file.addItems(self.display_name_to_path.keys())
            if filename:
                display_name=self.format_display_name(cfilePath)
                index = self.comboBox_file.findText(display_name, QtCore.Qt.MatchFixedString)
            else:
                index = -1
            if index >= 0:
                self.comboBox_file.setCurrentIndex(index)

        except Exception as e:
            # Raise your custom error popup with the exception message
            self.raise_error(
                window_title="File Import Error",
                error_message=f"An error occurred while importing the file:\n{cfilePath}\n\nError details:\n{e}",
            )

    def imp(self):
        index = self.idx_imp
        if index == 1 or index == 2:
            if index == 1:
                cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(
                    self, "Open csv file", self.filePath, "CSV Files (*.csv)"
                )
            else:
                cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(
                    self,
                    "Open tab-separated text file",
                    self.filePath,
                    "TXT Files (*.txt)",
                )
            if cfilePath != "":
                self.cfilePath = cfilePath
                self.filePath = self.cfilePath.rsplit("/", 1)[0]
                remember_settings = config.getboolean("Import", "remember_settings")
                try:
                    self.imp_csv_or_txt(self.cfilePath, remember_settings=remember_settings)
                except Exception as e:
                    print(
                        f"Error: could not auto-load file. Please select correct format!\n Traceback:\n ****************** \n  {e}"
                    )
                    self.imp_csv_or_txt(self.cfilePath, remember_settings=False)
            if self.comboBox_file.currentIndex() > 1:
                self.plot()

        if index == 3:
            cfilePath, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open VAMAS file", self.filePath, "VMS Files (*.vms *.npl)"
            )
            if cfilePath != "":
                self.cfilePath = cfilePath
                self.filePath = self.cfilePath.rsplit("/", 1)[0]
                # print (self.cfilePath)
                try:
                    self.list_vamas = vpy.list_vms(self.cfilePath)
                except Exception as e:
                    return self.raise_error(
                        window_title="Error: could not load VAMAS file.",
                        error_message="Loading VAMAS file failed. The following traceback may help to solve the issue:",
                    )
                try:
                    wf = vpy.get_wf(self.cfilePath)
                    if isinstance(wf, float):
                        self.wf = abs(wf)
                        self.wf_item.setText(
                            str(abs(wf))
                        )  # we assume in the following, that the wf is defined positive
                        self.pre[0][4] = self.wf
                    else:
                        self.wf = 4.0
                        self.wf_item.setText(str(4.0))
                        self.pre[0][4] = self.wf
                        raise Exception(
                            "Different work functions were detected for the different blocks in your Vamas file. Work function is defaulted to 4.0eV and needs to be adjusted manually."
                        )
                except Exception as e:
                    return self.raise_error(
                        window_title="Error: could not load VAMAS work function.",
                        error_message=e.args[0],
                    )
                try:
                    hv = vpy.get_hv(self.cfilePath)
                    if isinstance(hv, float):
                        self.hv = hv
                        self.hv_item.setText(str(hv))
                        self.pre[0][3] = self.hv
                    else:
                        self.hv = 1486.6
                        self.hv_item.setText(str(1486.6))
                        self.pre[0][3] = self.hv

                        raise Exception(
                            "Different source energies were detected for the different blocks in your Vamas file. Source energy (hv) is defaulted to 1486.6eV and needs to be adjusted manually."
                        )
                except Exception as e:
                    return self.raise_error(
                        window_title="Error: could not load VAMAS source energy.",
                        error_message=e.args[0],
                    )

                for file in self.list_vamas:
                    df = pd.read_csv(file, delimiter="\t", skiprows=1)
                    strpe = np.loadtxt(
                        file, dtype="str", delimiter="\t", usecols=1, max_rows=1
                    )
                    strpe = str(strpe).split()

                    if strpe[0] == "PE:" and strpe[2] == "eV":
                        pe = float(strpe[1])
                        self.data_arr[file] = DataSet(
                            filepath=file, df=df, pe=pe
                        )
                    else:
                        self.data_arr[file] = DataSet(
                            filepath=file, df=df, pe=None
                        )

                self.comboBox_file.clear()
                self.comboBox_file.addItems(self.list_file)
                self.display_name_to_path = {
                    self.format_display_name(fpath): fpath for fpath in self.data_arr.keys()
                }
                self.comboBox_file.addItems(self.display_name_to_path.keys())
                display_name = self.format_display_name(self.list_vamas[0])
                index = self.comboBox_file.findText(display_name, QtCore.Qt.MatchFixedString)
                if index >= 0:
                    self.comboBox_file.setCurrentIndex(index)
                if self.comboBox_file.currentIndex() > 1:
                    self.plot()
        if index == 4:
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Open Directory",
                self.filePath,
                QtWidgets.QFileDialog.ShowDirsOnly,
            )
            if directory != "":
                self.filePath = directory
                entries = os.listdir(directory)
                entries.sort(key=lambda x: (os.path.splitext(x)[1] != ".txt", x))
                self.comboBox_file.blockSignals(True)
                for entry in entries:
                    if (
                        os.path.splitext(entry)[1] == ".csv"
                        or os.path.splitext(entry)[1] == ".txt"
                    ):
                        self.cfilePath = os.path.join(directory, entry)
                        try:
                            self.imp_csv_or_txt(self.cfilePath, remember_settings=True)
                        except Exception as e:
                            print(
                                f"Error: could not auto-load file. Please select correct format!\n Traceback:\n ****************** \n  {e}"
                            )
                            self.imp_csv_or_txt(self.cfilePath, remember_settings=False)

                self.comboBox_file.clear()
                self.comboBox_file.addItems(self.list_file)
                self.display_name_to_path = {
                    self.format_display_name(fpath): fpath for fpath in self.data_arr.keys()
                }
                self.comboBox_file.addItems(self.display_name_to_path.keys())
                display_name = self.format_display_name(self.cfilePath)
                index = self.comboBox_file.findText(display_name, QtCore.Qt.MatchFixedString)
                self.comboBox_file.blockSignals(False)
                if index >= 0:
                    self.comboBox_file.setCurrentIndex(index)
        if index == 5:
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Open Directory",
                self.filePath,
                QtWidgets.QFileDialog.ShowDirsOnly,
            )
            if directory != "":
                self.filePath = directory
                csv_files = [
                    entry
                    for entry in os.listdir(directory)
                    if os.path.splitext(entry)[1] == ".csv"
                ]
                if csv_files:
                    csv_files.sort()
                    for entry in csv_files:
                        self.comboBox_file.blockSignals(True)
                        cfile_path = os.path.join(directory, entry)
                        try:
                            self.imp_csv_or_txt(cfile_path, remember_settings=True)
                        except Exception as e:
                            print(
                                f"Error: could not auto-load file. Please select correct format!\n Traceback:\n ****************** \n  {e}"
                            )
                            self.imp_csv_or_txt(cfile_path, remember_settings=False)

                    self.comboBox_file.clear()
                    self.comboBox_file.addItems(self.list_file)
                    self.display_name_to_path = {
                        self.format_display_name(fpath): fpath for fpath in self.data_arr.keys()
                    }
                    self.comboBox_file.addItems(self.display_name_to_path.keys())
                    display_name = self.format_display_name(f"{directory}/{csv_files[0]}")
                    index = self.comboBox_file.findText(display_name, QtCore.Qt.MatchFixedString)
                    self.comboBox_file.blockSignals(False)
                    if index >= 0:
                        self.comboBox_file.setCurrentIndex(index)
        if index == 6:
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Open Directory",
                self.filePath,
                QtWidgets.QFileDialog.ShowDirsOnly,
            )

            if directory != "":
                self.filePath = directory
                txt_files = [
                    entry
                    for entry in os.listdir(directory)
                    if os.path.splitext(entry)[1] == ".txt"
                ]
                if txt_files:
                    txt_files.sort()
                    for entry in txt_files:
                        self.comboBox_file.blockSignals(True)
                        cfile_path = os.path.join(directory, entry)
                        try:
                            self.imp_csv_or_txt(cfile_path, remember_settings=True)
                        except Exception as e:
                            print(
                                f"Error: could not auto-load file. Please select correct format!\n Traceback:\n ****************** \n  {e}"
                            )
                            self.imp_csv_or_txt(cfile_path, remember_settings=False)

                    self.comboBox_file.clear()
                    self.comboBox_file.addItems(self.list_file)
                    self.display_name_to_path = {
                        self.format_display_name(fpath): fpath for fpath in self.data_arr.keys()
                    }
                    self.comboBox_file.addItems(self.display_name_to_path.keys())
                    display_name = self.format_display_name(f"{directory}/{txt_files[0]}")
                    index = self.comboBox_file.findText(display_name, QtCore.Qt.MatchFixedString)
                    self.comboBox_file.blockSignals(False)
                    if index >= 0:
                        self.comboBox_file.setCurrentIndex(index)
        self.idx_imp = 0

    def value_change_filelist(self):
        if self.comboBox_file.currentIndex() == 1:
            self.comboBox_file.clear()
            self.list_file = ["File list", "Clear list"]
            self.data_arr = {}
            self.display_name_to_path={}
            self.comboBox_file.addItems(self.list_file)
            self.comboBox_file.setCurrentIndex(0)
        elif self.comboBox_file.currentIndex() > 1:
            self.plot()
        if self.comboBox_file.currentIndex() == 0 and self.comboBox_file.count() > 1:
            # plt.cla()
            self.ar.cla()
            self.ax.cla()
            self.canvas.draw()

    def plot(self):
        display_name = self.comboBox_file.currentText()
        if not display_name or display_name not in self.display_name_to_path:  # If nothing selected
            self.ax.cla()
            self.ax.set_xlabel("Energy (eV)", fontsize=11)
            self.ax.set_ylabel("Intensity (arb. unit)", fontsize=11)
            self.ax.grid(True)
            self.canvas.draw()
            self.repaint()
            return

        plottitle = self.comboBox_file.currentText().split("/")[-1]
        file_path = self.display_name_to_path[display_name]

        if file_path not in self.data_arr:
            self.ax.cla()
            self.ax.set_xlabel("Energy (eV)", fontsize=11)
            self.ax.set_ylabel("Intensity (arb. unit)", fontsize=11)
            self.ax.grid(True)
            self.canvas.draw()
            self.repaint()
            return

        filePath = file_path
        try:
            with open(filePath, "r") as f:
                header_line = str(f.readline())
        except Exception as e:
            return self.raise_error(
                window_title="Error: could not open file.",
                error_message="Could not open the selected file.",
            )

        if "rows_lightened" in header_line:
            self.rows_lightened = int(header_line.split("=")[1])
        else:
            self.rows_lightened = 1

        self.df = self.data_arr[filePath].df

        try:
            x0 = self.df.iloc[:, 0].to_numpy()
            y0 = self.df.iloc[:, 1].to_numpy()
        except Exception as e:
            return self.raise_error(
                window_title="Error: could not load .csv file.",
                error_message="The input .csv is not in the correct format!. The following traceback may help to solve the issue:",
            )

        pe = self.data_arr[filePath].pe
        if pe is not None:
            print("Current Pass energy is PE= ", pe, "eV")

        self.ax.cla()

        try:
            self.ax.plot(x0, y0, linestyle="-", color="b", label="raw")
        except Exception as e:
            return self.raise_error(
                window_title="Error: could not plot data.",
                error_message="Plotting data failed. The following traceback may help to solve the issue:",
            )

        if x0[0] > x0[-1]:
            self.ax.set_xlabel("Binding energy (eV)", fontsize=11)
        else:
            self.ax.set_xlabel("Energy (eV)", fontsize=11)

        self.ax.set_ylabel("Intensity (arb. unit)", fontsize=11)
        self.ax.grid(True)
        self.ax.legend(loc=0)
        self.canvas.draw()
        self.repaint()

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
                if len(self.hv) == 0:
                    self.pre[0][3] = 1486.6
                    self.hv = 1486.6
                else:
                    self.pre[0][3] = self.hv
            if self.pre[0][4] == None:
                if len(self.wf) == 0:
                    self.pre[0][4] = 4
                    self.wf = 4
                else:
                    self.pre[0][4] = self.wf
            if self.pre[0][5] == None:
                if len(self.correct_energy) == 0:
                    self.pre[0][5] = 0
                    self.correct_energy = 0
                else:
                    self.pre[0][5] = self.correct_energy
            self.hv_item.setText(str(self.hv))
            self.wf_item.setText(str(self.wf))
            self.correct_energy_item.setText(str(self.correct_energy))
            hv = self.hv
            wf = self.wf

            ymin, ymax = self.ax.get_ylim()
            xmin, xmax = self.ax.get_xlim()
            for obj in self.pt.selected_elements:
                alka = ast.literal_eval(obj["alka"].values[0])
                if len(ast.literal_eval(alka["trans"])) > 0:
                    for orb in range(len(ast.literal_eval(alka["trans"]))):
                        if xmin > xmax:
                            en = float(ast.literal_eval(alka["be"])[orb])
                        else:
                            en = (
                                hv
                                - wf
                                - float(ast.literal_eval(alka["be"])[orb])
                                - self.correct_energy
                            )
                        if (xmin > xmax and xmin > en > xmax) or (
                            xmin < xmax and xmin < en < xmax
                        ):
                            elem_x = np.asarray([en])
                            elem_y = np.asarray(
                                [float(ast.literal_eval(alka["rsf"])[orb])]
                            )
                            elem_z = ast.literal_eval(alka["trans"])[orb]
                            # obj.symbol+elem_z, color="r", rotation="vertical")
                            self.ax.text(
                                elem_x,
                                ymin + (ymax - ymin) * math.log(elem_y + 1, 10) / 2,
                                obj["symbol"].values[0] + elem_z,
                                color="r",
                                rotation="vertical",
                            )
                aes = ast.literal_eval(obj["aes"].values[0])
                if len(ast.literal_eval(aes["trans"])) > 0:
                    for orb in range(len(ast.literal_eval(aes["trans"]))):
                        if xmin > xmax:
                            en = (
                                hv
                                - wf
                                - float(ast.literal_eval(aes["ke"])[orb])
                                - self.correct_energy
                            )
                        else:
                            en = float(ast.literal_eval(aes["ke"])[orb])
                        if (xmin > xmax and xmin > en > xmax) or (
                            xmin < xmax and xmin < en < xmax
                        ):
                            elem_x = np.asarray([en])
                            elem_y = np.asarray(
                                [float(ast.literal_eval(aes["rsf"])[orb])]
                            )
                            elem_z = ast.literal_eval(aes["trans"])[orb]
                            # obj.symbol+elem_z, color="g", rotation="vertical")
                            self.ax.text(
                                elem_x,
                                ymin + (ymax - ymin) * math.log(elem_y + 1, 10),
                                obj["symbol"].values[0] + elem_z,
                                color="g",
                                rotation="vertical",
                            )
            self.canvas.draw()
            self.repaint()

    def eva(self):
        # simulation mode if no data in file list, otherwise evaluation mode
        if self.comboBox_file.currentIndex() == 0:
            if (
                self.xmin is not None
                and self.xmax is not None
                and len(str(self.xmin)) > 0
                and len(str(self.xmax)) > 0
            ):
                x1 = float(self.xmin)
                x2 = float(self.xmax)
            points = 999
            self.df = np.zeros((points, 2)) + 0.01
            self.df[:, 0] = np.linspace(x1, x2, points)
            self.ana("sim")
        else:
            self.ana("eva")

    def fit(self):
        if self.comboBox_file.currentIndex() > 0:
            try:
                self.ana("fit")
                # self.fitter = Fitting(self.ana, "fit")
                # self.threadpool.start(self.fitter)
            except Exception as e:
                return self.raise_error(
                    window_title="Error: Fitting failed!",
                    error_message="Fitting was not successful. The following traceback may help to solve the issue:",
                )
        else:
            print("No Data present, Switching to simulation mode!")
            if (
                self.xmin is not None
                and self.xmax is not None
                and len(str(self.xmin)) > 0
                and len(str(self.xmax)) > 0
            ):
                x1 = float(self.xmin)
                x2 = float(self.xmax)
            points = 999
            self.df = np.zeros((points, 2)) + 0.01
            self.df[:, 0] = np.linspace(x1, x2, points)
            self.ana("sim")

    def interrupt_fit(self):
        if self.fit_thread:
            self.fit_thread.interrupt_fit()

    def one_step_back_in_params_history(self):
        """
        Is called if button undo Fit is prest.
        """
        self.go_back_in_parameter_history = True
        self.fit()

    def history_manager(self, pars):
        """
        Manages saving of the fit parameters and presets (e.g. how many components, aktive backgrounds and so on) in
        a list. In this approach the insane function ana() must be extended. The ana() should be destroyd! and
        replaaced by couple of smaller methods for better readability

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
                return self.raise_error(
                    window_title="Error: History empty!",
                    error_message="First entry in parameter history reached. No further steps saved. The following traceback may help to solve the issue:",
                )

        else:
            self.savePreset()
            self.parameter_history_list.append([pars, self.pre])
            return None

    def clickOnBtnBG(self):
        checked_actions = [
            action for action in self.bgMenu.actions() if action.isChecked()
        ]
        idx_bg = set()
        for checked_action in checked_actions:
            if (
                checked_action.text() == "&Static &Shirley BG"
                and "&Static &Tougaard BG"
                not in [checked_act.text() for checked_act in checked_actions]
            ):
                idx_bg.add(0)
            elif (
                checked_action.text() == "&Active &Shirley BG"
                and "&Static &Shirley BG"
                in [checked_act.text() for checked_act in checked_actions]
            ):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Warning",
                    "You cannot choose both Active Shirley BG and Static "
                    "Shirley BG at the same time! Static Shirley BG set! To use Active Shirley BG, please uncheck Static "
                    "Shirley BG!",
                )
                checked_action.setChecked(False)
                idx_bg.add(0)
            elif (
                checked_action.text() == "&Active &Shirley BG"
                and "&Static &Shirley BG"
                not in [checked_act.text() for checked_act in checked_actions]
            ):
                idx_bg.add(100)
            elif (
                checked_action.text() == "&Static &Tougaard BG"
                and "&Static &Shirley BG"
                not in [checked_act.text() for checked_act in checked_actions]
            ):
                idx_bg.add(1)
            elif (
                checked_action.text() == "&Active &Tougaard BG"
                and "&Static &Tougaard BG"
                in [checked_act.text() for checked_act in checked_actions]
            ):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Warning",
                    "You cannot choose both Active Tougaard BG and Static Tougaard BG at "
                    "the same time! Static Tougaard BG set! To use Active Tougaard BG, "
                    "please uncheck Static Tougaard BG!",
                )
                idx_bg.add(1)
                checked_action.setChecked(False)
            elif (
                checked_action.text() == "&Active &Tougaard BG"
                and "&Static &Tougaard BG"
                not in [checked_act.text() for checked_act in checked_actions]
            ):
                idx_bg.add(101)
            elif checked_action.text() == "&Polynomial BG":
                idx_bg.add(2)
            elif checked_action.text() == "&Slope BG":
                idx_bg.add(6)
            elif checked_action.text() == "&Arctan BG":
                idx_bg.add(3)
            elif checked_action.text() == "&Erf BG":
                idx_bg.add(4)
            elif checked_action.text() == "&VBM/Cutoff BG":
                idx_bg.add(5)
        if "&Static &Shirley BG" in [
            checked_act.text() for checked_act in checked_actions
        ] and "&Static &Tougaard BG" in [
            checked_act.text() for checked_act in checked_actions
        ]:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "You cannot choose both Static Shirley BG and Static Tougaard BG at "
                "the same time! Background was set to Static Shirley BG.",
            )
            idx_bg.add(0)
            for checked_action in checked_actions:
                if checked_action.text() == "&Static &Tougaard BG":
                    checked_action.setChecked(False)
        if len(checked_actions) == 0:
            QtWidgets.QMessageBox.information(
                self,
                "Info",
                "No background was choosen, a polynomial BG was set as default.",
            )
            idx_bg.add(2)  # if no background was selected, a polynomial will be used
        self.idx_bg = sorted(idx_bg)
        try:
            self.pre[0][0] = self.idx_bg
        except Exception as e:
            logging.error(
                "Loading of background failed, self.pre[0][0]={}, self.idx_bg={}".format(
                    self.pre[0][0], self.idx_bg
                )
            )
            return self.raise_error(
                window_title="Error while setting background!",
                error_message="Error while loading/changing background!",
            )

        self.displayChoosenBG.setText(
            "Choosen Background: {}".format(
                "+ ".join([dictBG[str(idx)] for idx in self.idx_bg])
            )
        )
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
            mod = ShirleyBG(independent_vars=["y"], prefix="bg_shirley_")
            k = self.pre[1][0][5]
            const = self.pre[1][0][7]
            pars = mod.make_params()
            pars["bg_shirley_k"].value = float(k)
            pars["bg_shirley_const"].value = float(const)
            if self.pre[1][0][4] == 2:
                pars["bg_shirley_k"].vary = False
            if self.pre[1][0][6] == 2:
                pars["bg_shirley_const"].vary = False
            bg_mod = 0
        if idx_bg == 1:
            toB = self.pre[1][1][1]
            toC = self.pre[1][1][3]
            toCd = self.pre[1][1][5]
            toD = self.pre[1][1][7]
            toT0 = self.pre[1][1][9]
            pars = None
            mod = None
            if mode == "fit":
                toM = self.pre[1][0][3]
                [bg_mod, bg_toB] = xpy.tougaard_calculate(
                    x, y, toB, toC, toCd, toD, toM
                )
            else:
                toM = 1
                [bg_mod, bg_toB] = xpy.tougaard_calculate(
                    x, y, toB, toC, toCd, toD, toM
                )
            self.pre[1][1][1] = bg_toB
        if idx_bg == 101:
            mod = TougaardBG(independent_vars=["x", "y"], prefix="bg_tougaard_")
            if (
                self.pre[1][1][1] is None
                or self.pre[1][1][3] is None
                or self.pre[1][1][5] is None
                or self.pre[1][1][7] is None
                or self.pre[1][1][9] is None
                or len(str(self.pre[1][1][1])) == 0
                or len(str(self.pre[1][1][3])) == 0
                or len(str(self.pre[1][1][5])) == 0
                or len(str(self.pre[1][1][7])) == 0
                or len(str(self.pre[1][1][9])) == 0
            ):
                pars = mod.guess(y, x=x, y=y)
            else:
                pars = mod.make_params()
                pars["bg_tougaard_B"].value = self.pre[1][1][1]
                if self.pre[1][1][0] == 2:
                    pars["bg_tougaard_B"].vary = False
                pars["bg_tougaard_C"].value = self.pre[1][1][3]
                pars["bg_tougaard_C"].vary = False
                pars["bg_tougaard_C_d"].value = self.pre[1][1][5]
                pars["bg_tougaard_C_d"].vary = False
                pars["bg_tougaard_D"].value = self.pre[1][1][7]
                pars["bg_tougaard_D"].vary = False
                pars["bg_tougaard_extend"].value = self.pre[1][1][9]
                pars["bg_tougaard_extend"].vary = False
            bg_mod = 0
        if idx_bg == 3:
            mod = StepModel(prefix="bg_arctan_", form="arctan")
            if (
                self.pre[1][idx_bg + 1][1] is None
                or self.pre[1][idx_bg + 1][3] is None
                or self.pre[1][idx_bg + 1][5] is None
                or len(str(self.pre[1][idx_bg + 1][1])) == 0
                or len(str(self.pre[1][idx_bg + 1][3])) == 0
                or len(str(self.pre[1][idx_bg + 1][5])) == 0
            ):
                pars = mod.guess(y, x=x)
            else:
                pars = mod.make_params()
                pars["bg_arctan_amplitude"].value = self.pre[1][idx_bg + 1][1]
                if self.pre[1][idx_bg + 1][0] == 2:
                    pars["bg_arctan_amplitude"].vary = False
                pars["bg_arctan_center"].value = self.pre[1][idx_bg + 1][3]
                if self.pre[1][idx_bg + 1][2] == 2:
                    pars["bg_arctan_center"].vary = False
                pars["bg_arctan_sigma"].value = self.pre[1][idx_bg + 1][5]
                if self.pre[1][idx_bg + 1][4] == 2:
                    pars["bg_arctan_sigma"].vary = False
            bg_mod = 0
        if idx_bg == 4:
            mod = StepModel(prefix="bg_step_", form="erf")
            if (
                self.pre[1][idx_bg + 1][1] is None
                or self.pre[1][idx_bg + 1][3] is None
                or self.pre[1][idx_bg + 1][5] is None
                or len(str(self.pre[1][idx_bg + 1][1])) == 0
                or len(str(self.pre[1][idx_bg + 1][3])) == 0
                or len(str(self.pre[1][idx_bg + 1][5])) == 0
            ):
                pars = mod.guess(y, x=x)
            else:
                pars = mod.make_params()
                pars["bg_step_amplitude"].value = self.pre[1][idx_bg + 1][1]
                if self.pre[1][idx_bg + 1][0] == 2:
                    pars["bg_step_amplitude"].vary = False
                pars["bg_step_center"].value = self.pre[1][idx_bg + 1][3]
                if self.pre[1][idx_bg + 1][2] == 2:
                    pars["bg_step_center"].vary = False
                pars["bg_step_sigma"].value = self.pre[1][idx_bg + 1][5]
                if self.pre[1][idx_bg + 1][4] == 2:
                    pars["bg_step_sigma"].vary = False
            bg_mod = 0

        if idx_bg == 5:
            if (x[0] > x[-1] and y[0] > y[-1]) or (x[0] < x[-1] and y[0] < y[-1]):
                # VBM
                def poly2vbm(x, ctr, d1, d2, d3, d4):
                    return (
                        d1 * (x - ctr)
                        + d2 * (x - ctr) ** 2
                        + d3 * (x - ctr) ** 3
                        + d4 * (x - ctr) ** 4
                    ) * (x >= ctr)

            else:
                # cutoff/wf
                def poly2vbm(x, ctr, d1, d2, d3, d4):
                    return (
                        d1 * (x - ctr)
                        + d2 * (x - ctr) ** 2
                        + d3 * (x - ctr) ** 3
                        + d4 * (x - ctr) ** 4
                    ) * (x <= ctr)

            mod = Model(poly2vbm, prefix="bg_vbm_")
            pars = mod.make_params()
            if (
                self.pre[1][idx_bg + 1][1] is None
                or self.pre[1][idx_bg + 1][3] is None
                or self.pre[1][idx_bg + 1][5] is None
                or self.pre[1][idx_bg + 1][7] is None
                or self.pre[1][idx_bg + 1][9] is None
                or len(str(self.pre[1][idx_bg + 1][1])) == 0
                or len(str(self.pre[1][idx_bg + 1][3])) == 0
                or len(str(self.pre[1][idx_bg + 1][5])) == 0
                or len(str(self.pre[1][idx_bg + 1][7])) == 0
                or len(str(self.pre[1][idx_bg + 1][9])) == 0
            ):
                pars["bg_vbm_ctr"].value = (x[0] + x[-1]) / 2
                pars["bg_vbm_d1"].value = 0
                pars["bg_vbm_d2"].value = 0
                pars["bg_vbm_d3"].value = 0
                pars["bg_vbm_d4"].value = 0
            else:
                pars["bg_vbm_ctr"].value = self.pre[1][idx_bg + 1][1]
                if self.pre[1][idx_bg + 1][0] == 2:
                    pars["bg_vbm_ctr"].vary = False
                pars["bg_vbm_d1"].value = self.pre[1][idx_bg + 1][3]
                if self.pre[1][idx_bg + 1][2] == 2:
                    pars["bg_vbm_d1"].vary = False
                pars["bg_vbm_d2"].value = self.pre[1][idx_bg + 1][5]
                if self.pre[1][idx_bg + 1][5] == 2:
                    pars["bg_vbm_d2"].vary = False
                pars["bg_vbm_d3"].value = self.pre[1][idx_bg + 1][7]
                if self.pre[1][idx_bg + 1][6] == 2:
                    pars["bg_vbm_d3"].vary = False
                pars["bg_vbm_d4"].value = self.pre[1][idx_bg + 1][9]
                if self.pre[1][idx_bg + 1][8] == 2:
                    pars["bg_vbm_d4"].vary = False
            bg_mod = 0
        if idx_bg == 2:
            mod = PolynomialModel(4, prefix="bg_poly_")
            bg_mod = 0
            if (
                self.pre[1][2][1] is None
                or self.pre[1][2][3] is None
                or self.pre[1][2][5] is None
                or self.pre[1][2][7] is None
                or self.pre[1][2][9] is None
                or len(str(self.pre[1][2][1])) == 0
                or len(str(self.pre[1][2][3])) == 0
                or len(str(self.pre[1][2][5])) == 0
                or len(str(self.pre[1][2][7])) == 0
                or len(str(self.pre[1][2][9])) == 0
            ):
                pars = mod.guess(y, x=x)
            else:
                pars = mod.make_params()
                for index in range(5):
                    pars["bg_poly_c" + str(index)].value = self.pre[1][2][2 * index + 1]
                    if self.pre[1][2][2 * index] == 2:
                        pars["bg_poly_c" + str(index)].vary = False
                pars["bg_poly_c0"].max = np.mean(y[-5:])
                # pars['bg_poly_c0'].min = 0
        if idx_bg == 6:
            mod = SlopeBG(independent_vars=["y"], prefix="bg_slope_")
            bg_mod = 0
            if self.pre[1][3][1] is None or len(str(self.pre[1][3][1])) == 0:
                pars = mod.guess(y, x=x)
            else:
                pars = mod.make_params()
                pars["bg_slope_k"].value = self.pre[1][3][1]
                if self.pre[1][3][0] == 2:
                    pars["bg_slope_k"].vary = False
        if self.fixedBG.isChecked() and pars != None:
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
                mod = modp
            if index_pk == 0:
                pars = modp.make_params()
            else:
                pars.update(modp.make_params())
            # fit parameters from self.pre
            if (
                self.pre[2][1][2 * index_pk + 1] is not None
                and len(str(self.pre[2][1][2 * index_pk + 1])) > 0
            ):
                pars[strind + str(index_pk + 1) + "_center"].value = float(
                    self.pre[2][1][2 * index_pk + 1]
                )
                if self.pre[2][1][2 * index_pk] == 2:
                    pars[strind + str(index_pk + 1) + "_center"].vary = False
            if (
                self.pre[2][2][2 * index_pk + 1] is not None
                and len(str(self.pre[2][2][2 * index_pk + 1])) > 0
            ):
                pars[strind + str(index_pk + 1) + "_amplitude"].value = float(
                    self.pre[2][2][2 * index_pk + 1]
                )
                pars[strind + str(index_pk + 1) + "_amplitude"].min = 0.0
                if self.pre[2][2][2 * index_pk] == 2:
                    pars[strind + str(index_pk + 1) + "_amplitude"].vary = False
            if (
                self.pre[2][14][2 * index_pk + 1] is not None
                and len(str(self.pre[2][14][2 * index_pk + 1])) > 0
            ):
                pars.add(
                    strind + str(index_pk + 1) + "_center_diff",
                    value=float(self.pre[2][14][2 * index_pk + 1]),
                )
                if self.pre[2][14][2 * index_pk] == 2:
                    pars[strind + str(index_pk + 1) + "_center_diff"].vary = False
            if (
                self.pre[2][16][2 * index_pk + 1] is not None
                and len(str(self.pre[2][16][2 * index_pk + 1])) > 0
            ):
                pars.add(
                    strind + str(index_pk + 1) + "_amp_ratio",
                    value=float(self.pre[2][16][2 * index_pk + 1]),
                    min=0,
                )
                if self.pre[2][16][2 * index_pk] == 2:
                    pars[strind + str(index_pk + 1) + "_amp_ratio"].vary = False
            if (
                index == 0
                or index == 2
                or index == 4
                or index == 5
                or index == 6
                or index == 7
                or index == 8
                or index == 12
            ):
                if (
                    self.pre[2][4][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][4][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_sigma"].value = float(
                        self.pre[2][4][2 * index_pk + 1]
                    )
                    pars[strind + str(index_pk + 1) + "_sigma"].min = 0
                    if self.pre[2][4][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_sigma"].vary = False
                if (
                    self.pre[2][20][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][20][2 * index_pk + 1])) > 0
                ):
                    pars.add(
                        strind + str(index_pk + 1) + "_gaussian_ratio",
                        value=float(self.pre[2][20][2 * index_pk + 1]),
                        min=0,
                    )
                    if self.pre[2][20][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_gaussian_ratio"].vary = (
                            False
                        )
            if index == 10 or index == 11:
                if (
                    self.pre[2][4][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][4][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_gaussian_sigma"].value = float(
                        self.pre[2][4][2 * index_pk + 1]
                    )
                    pars[strind + str(index_pk + 1) + "_gaussian_sigma"].min = 0
                    if self.pre[2][4][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_gaussian_sigma"].vary = (
                            False
                        )
                if (
                    self.pre[2][20][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][20][2 * index_pk + 1])) > 0
                ):
                    pars.add(
                        strind + str(index_pk + 1) + "_gaussian_ratio",
                        value=float(self.pre[2][20][2 * index_pk + 1]),
                        min=0,
                    )
                    if self.pre[2][20][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_gaussian_ratio"].vary = (
                            False
                        )
            if index == 1 or index == 3 or index == 9 or index == 10 or index == 11:
                if (
                    self.pre[2][3][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][3][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_sigma"].value = float(
                        self.pre[2][3][2 * index_pk + 1]
                    )
                    pars[strind + str(index_pk + 1) + "_sigma"].min = 0
                    if self.pre[2][3][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_sigma"].vary = False
                if (
                    self.pre[2][18][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][18][2 * index_pk + 1])) > 0
                ):
                    pars.add(
                        strind + str(index_pk + 1) + "_lorentzian_ratio",
                        value=float(self.pre[2][18][2 * index_pk + 1]),
                        min=0,
                    )
                    if self.pre[2][18][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_lorentzian_ratio"].vary = (
                            False
                        )
            if index == 2 or index == 6:
                if (
                    self.pre[2][3][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][3][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_gamma"].value = float(
                        self.pre[2][3][2 * index_pk + 1]
                    )
                    pars[strind + str(index_pk + 1) + "_gamma"].min = 0
                    if self.pre[2][3][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_gamma"].vary = False
                if (
                    self.pre[2][18][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][18][2 * index_pk + 1])) > 0
                ):
                    pars.add(
                        strind + str(index_pk + 1) + "_lorentzian_ratio",
                        value=float(self.pre[2][18][2 * index_pk + 1]),
                        min=0,
                    )
                    if self.pre[2][18][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_lorentzian_ratio"].vary = (
                            False
                        )
            if index == 4 or index == 5 or index == 9 or index == 10 or index == 11:
                if (
                    self.pre[2][5][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][5][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_gamma"].value = float(
                        self.pre[2][5][2 * index_pk + 1]
                    )
                    if self.binding_ener:
                        pars[strind + str(index_pk + 1) + "_gamma"].max = 0
                        pars[strind + str(index_pk + 1) + "_gamma"].min = -1
                    else:
                        pars[strind + str(index_pk + 1) + "_gamma"].min = 0
                        pars[strind + str(index_pk + 1) + "_gamma"].max = 1
                    pars[strind + str(index_pk + 1) + "_gamma"].max = 1
                    if self.pre[2][5][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_gamma"].vary = False
                if (
                    self.pre[2][22][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][22][2 * index_pk + 1])) > 0
                ):
                    pars.add(
                        strind + str(index_pk + 1) + "_gamma_ratio",
                        value=float(self.pre[2][22][2 * index_pk + 1]),
                        min=0,
                    )
                    if self.pre[2][22][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_gamma_ratio"].vary = False
            if index == 3:
                if (
                    self.pre[2][6][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][6][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_fraction"].value = float(
                        self.pre[2][6][2 * index_pk + 1]
                    )
                    pars[strind + str(index_pk + 1) + "_fraction"].min = 0
                    pars[strind + str(index_pk + 1) + "_fraction"].max = 1
                    if self.pre[2][6][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_fraction"].vary = False
            if index == 6:
                if (
                    self.pre[2][7][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][7][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_skew"].value = float(
                        self.pre[2][7][2 * index_pk + 1]
                    )
                    pars[strind + str(index_pk + 1) + "_skew"].min = -1
                    pars[strind + str(index_pk + 1) + "_skew"].max = 1
                    if self.pre[2][7][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_skew"].vary = False
            if index == 7:
                if (
                    self.pre[2][8][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][8][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_q"].value = float(
                        self.pre[2][8][2 * index_pk + 1]
                    )
                    if self.pre[2][8][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_q"].vary = False
            if index == 12:
                if (
                    self.pre[2][9][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][9][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_kt"].value = float(
                        self.pre[2][9][2 * index_pk + 1]
                    )
                    pars[strind + str(index_pk + 1) + "_kt"].min = 0
                    pars[strind + str(index_pk + 1) + "_kt"].max = 1
                    if self.pre[2][9][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_kt"].vary = False

            if index == 10:
                if (
                    self.pre[2][10][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][10][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_soc"].value = float(
                        self.pre[2][10][2 * index_pk + 1]
                    )
                    if self.pre[2][10][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_soc"].vary = False
                if (
                    self.pre[2][24][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][24][2 * index_pk + 1])) > 0
                ):
                    pars.add(
                        strind + str(index_pk + 1) + "_soc_ratio",
                        value=float(self.pre[2][24][2 * index_pk + 1]),
                        min=0,
                    )
                    if self.pre[2][24][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_soc_ratio"].vary = False
                if (
                    self.pre[2][11][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][11][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_height_ratio"].value = float(
                        self.pre[2][11][2 * index_pk + 1]
                    )
                    pars[strind + str(index_pk + 1) + "_height_ratio"].min = 0
                    if self.pre[2][11][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_height_ratio"].vary = False
                if (
                    self.pre[2][26][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][26][2 * index_pk + 1])) > 0
                ):
                    pars.add(
                        strind + str(index_pk + 1) + "_rel_height_ratio",
                        value=float(self.pre[2][26][2 * index_pk + 1]),
                        min=0,
                    )
                    if self.pre[2][26][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_rel_height_ratio"].vary = (
                            False
                        )
                if (
                    self.pre[2][12][2 * index_pk + 1] is not None
                    and len(str(self.pre[2][12][2 * index_pk + 1])) > 0
                ):
                    pars[strind + str(index_pk + 1) + "_fct_coster_kronig"].value = (
                        float(self.pre[2][12][2 * index_pk + 1])
                    )
                    pars[strind + str(index_pk + 1) + "_fct_coster_kronig"].min = 0
                    if self.pre[2][12][2 * index_pk] == 2:
                        pars[strind + str(index_pk + 1) + "_fct_coster_kronig"].vary = (
                            False
                        )
            pars = self.ratio_setup(pars, index_pk, strind, index)
            pars_all.append(pars)
        return [mod, pars]

    def assign_expr_safe(
            self,
            pars,
            target_id: str,
            current_id: str,
            param_name: str,
            expr: str,
    ) -> None:
        """
        Assign an expression to a parameter if it's not self-referencing.
        Otherwise, raise an error.

        Args:
            pars: Parameter dictionary (e.g., from lmfit).
            target_id (str): Target peak ID.
            current_id (str): Current peak ID.
            param_name (str): Name of the parameter (e.g. "sigma", "gamma").
            expr (str): Expression to assign (e.g. "C1_sigma * C2_ratio").

        Returns:
            None
        """
        if target_id == current_id:
            return self.raise_error(
                window_title="Error: Self-referencing parameters.",
                error_message=(
                    f"Parameter '{current_id}_{param_name}' references itself.\n"
                    f"This is invalid. Please select another peak or leave it blank."
                ),
            )
        pars[f"{current_id}_{param_name}"].expr = expr

    def ratio_setup(self, pars, index_pk, strind, index):
        if (
            index == 2 or index == 6
        ):  # unset default expression which sets sigma and gamma for the voigt and skewed-voigt always to the same value
            pars[strind + str(index_pk + 1) + "_gamma"].expr = ""
            if not self.pre[2][3][2 * index_pk] == 2:
                pars[strind + str(index_pk + 1) + "_gamma"].vary = True
        # amp ratio setup
        if self.pre[2][15][2 * index_pk + 1] > 0:
            pktar = self.pre[2][15][2 * index_pk + 1]
            strtar_raw = self.list_shape[self.pre[2][0][2 * pktar - 1]]
            strtar = strtar_raw.split(":", 1)[0]

            if (
                    self.pre[2][16][2 * index_pk + 1] is not None and
                    str(self.pre[2][16][2 * index_pk + 1]).strip()
            ):
                target_id = strtar + str(pktar)
                current_id = strind + str(index_pk + 1)
                expr = f"{target_id}_amplitude * {current_id}_amp_ratio"

                self.assign_expr_safe(pars, target_id, current_id, "amplitude", expr)

        # BE diff setup
        if self.pre[2][13][2 * index_pk + 1] > 0:
            pktar = self.pre[2][13][2 * index_pk + 1]
            strtar_raw = self.list_shape[self.pre[2][0][2 * pktar - 1]]
            strtar = strtar_raw.split(":", 1)[0]

            if (
                    self.pre[2][14][2 * index_pk + 1] is not None and
                    str(self.pre[2][14][2 * index_pk + 1]).strip()
            ):
                target_id = strtar + str(pktar)
                current_id = strind + str(index_pk + 1)
                expr = f"{target_id}_center + {current_id}_center_diff"

                self.assign_expr_safe(pars, target_id, current_id, "center", expr)

        # lorentzian sigma ref setup
        if self.pre[2][17][2 * index_pk + 1] > 0:
            pktar = self.pre[2][17][2 * index_pk + 1]
            strtar_raw = self.list_shape[self.pre[2][0][2 * pktar - 1]]
            strtar = strtar_raw.split(":", 1)[0]

            if (
                    self.pre[2][18][2 * index_pk + 1] is not None and
                    str(self.pre[2][18][2 * index_pk + 1]).strip()
            ):
                target_id = strtar + str(pktar)
                current_id = strind + str(index_pk + 1)

                # Assign sigma expression
                if index in [1, 3, 9, 10, 11]:
                    if strtar in ["v", "a"]:
                        expr = f"{target_id}_gamma * {current_id}_lorentzian_ratio"
                    else:
                        expr = f"{target_id}_sigma * {current_id}_lorentzian_ratio"

                    self.assign_expr_safe(pars, target_id, current_id, "sigma", expr)

                # Assign gamma expression
                if index in [2, 6]:
                    if strtar not in ["v", "a"]:
                        expr = f"{target_id}_sigma * {current_id}_lorentzian_ratio"
                    else:
                        expr = f"{target_id}_gamma * {current_id}_lorentzian_ratio"

                    self.assign_expr_safe(pars, target_id, current_id, "gamma", expr)

        # gaussian sigma ref setup
        if self.pre[2][19][2 * index_pk + 1] > 0:
            pktar = self.pre[2][19][2 * index_pk + 1]
            strtar_raw = self.list_shape[self.pre[2][0][2 * pktar - 1]]
            strtar = strtar_raw.split(":", 1)[0]

            if (
                    self.pre[2][20][2 * index_pk + 1] is not None and
                    str(self.pre[2][20][2 * index_pk + 1]).strip()
            ):
                target_id = strtar + str(pktar)
                current_id = strind + str(index_pk + 1)

                # For sigma assignment
                if index in [0, 2, 4, 5, 6, 7, 8, 12]:
                    if strtar in ["gds", "gdd"]:
                        expr = f"{target_id}_gaussian_sigma * {current_id}_gaussian_ratio"
                    else:
                        expr = f"{target_id}_sigma * {current_id}_gaussian_ratio"

                    self.assign_expr_safe(pars, target_id, current_id, "sigma", expr)

                # For gaussian_sigma assignment
                if index in [10, 11]:
                    if strtar not in ["gds", "gdd"]:
                        expr = f"{target_id}_sigma * {current_id}_gaussian_ratio"
                    else:
                        expr = f"{target_id}_gaussian_sigma * {current_id}_gaussian_ratio"

                    self.assign_expr_safe(pars, target_id, current_id, "gaussian_sigma", expr)

        # gamma ref setup
        if self.pre[2][21][2 * index_pk + 1] > 0:
            pktar = self.pre[2][21][2 * index_pk + 1]
            strtar_raw = self.list_shape[self.pre[2][0][2 * pktar - 1]]
            strtar = strtar_raw.split(":", 1)[0]

            if (
                    self.pre[2][22][2 * index_pk + 1] is not None and
                    str(self.pre[2][22][2 * index_pk + 1]).strip()
            ):
                current_id = strind + str(index_pk + 1)
                target_id = strtar + str(pktar)

                valid_gamma_refs = (
                        (index in [9, 10, 11] and strtar in ["d", "gdd", "gds"]) or
                        (index == 4 and strtar == "e") or
                        (index == 5 and strtar == "s")
                )

                if valid_gamma_refs:
                    expr = f"{target_id}_gamma * {current_id}_gamma_ratio"
                    self.assign_expr_safe(pars, target_id, current_id, "gamma", expr)

        # soc ref and height ratio ref setup
        if index == 10:
            current_id = strind + str(index_pk + 1)

            # SOC reference
            if self.pre[2][23][2 * index_pk + 1] > 0:
                pktar = self.pre[2][23][2 * index_pk + 1]
                strtar_raw = self.list_shape[self.pre[2][0][2 * pktar - 1]]
                strtar = strtar_raw.split(":", 1)[0]

                if self.pre[2][24][2 * index_pk + 1] is not None and str(self.pre[2][24][2 * index_pk + 1]).strip():
                    target_id = strtar + str(pktar)
                    expr = f"{target_id}_soc * {current_id}_soc_ratio"
                    self.assign_expr_safe(pars, target_id, current_id, "soc", expr)

            # Height ratio reference
            if self.pre[2][25][2 * index_pk + 1] > 0:
                pktar = self.pre[2][25][2 * index_pk + 1]
                strtar_raw = self.list_shape[self.pre[2][0][2 * pktar - 1]]
                strtar = strtar_raw.split(":", 1)[0]

                if self.pre[2][26][2 * index_pk + 1] is not None and str(self.pre[2][26][2 * index_pk + 1]).strip():
                    target_id = strtar + str(pktar)
                    expr = f"{target_id}_height_ratio * {current_id}_rel_height_ratio"
                    self.assign_expr_safe(pars, target_id, current_id, "height_ratio", expr)

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
                    if (
                        self.pre[3][row][3 * index_pk + 1] is not None
                        and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                    ):
                        pars[strind + str(index_pk + 1) + "_center"].min = self.pre[3][
                            row
                        ][3 * index_pk + 1]
                    if (
                        self.pre[3][row][3 * index_pk + 2] is not None
                        and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                    ):
                        pars[strind + str(index_pk + 1) + "_center"].max = self.pre[3][
                            row
                        ][3 * index_pk + 2]
                if row == 1 and self.pre[3][row][3 * index_pk] == 2:
                    if (
                        self.pre[3][row][3 * index_pk + 1] is not None
                        and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                    ):
                        pars[strind + str(index_pk + 1) + "_amplitude"].min = self.pre[
                            3
                        ][row][3 * index_pk + 1]
                    if (
                        self.pre[3][row][3 * index_pk + 2] is not None
                        and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                    ):
                        pars[strind + str(index_pk + 1) + "_amplitude"].max = self.pre[
                            3
                        ][row][3 * index_pk + 2]
                if row == 12 and self.pre[3][row][3 * index_pk] == 2:
                    if (
                        self.pre[3][row][3 * index_pk + 1] is not None
                        and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                    ):
                        pars[strind + str(index_pk + 1) + "_center_diff"].min = (
                            self.pre[3][row][3 * index_pk + 1]
                        )
                    if (
                        self.pre[3][row][3 * index_pk + 2] is not None
                        and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                    ):
                        pars[strind + str(index_pk + 1) + "_center_diff"].max = (
                            self.pre[3][row][3 * index_pk + 2]
                        )
                if row == 13 and self.pre[3][row][3 * index_pk] == 2:
                    if (
                        self.pre[3][row][3 * index_pk + 1] is not None
                        and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                    ):
                        pars[strind + str(index_pk + 1) + "_amp_ratio"].min = self.pre[
                            3
                        ][row][3 * index_pk + 1]
                    if (
                        self.pre[3][row][3 * index_pk + 2] is not None
                        and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                    ):
                        pars[strind + str(index_pk + 1) + "_amp_ratio"].max = self.pre[
                            3
                        ][row][3 * index_pk + 2]
                if (
                    index == 0
                    or index == 2
                    or index == 4
                    or index == 5
                    or index == 6
                    or index == 7
                    or index == 8
                    or index == 12
                ):
                    if row == 3 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_sigma"].min = self.pre[
                                3
                            ][row][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_sigma"].max = self.pre[
                                3
                            ][row][3 * index_pk + 2]
                    if row == 15 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gaussian_ratio"].min = (
                                self.pre[3][row][3 * index_pk + 1]
                            )
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gaussian_ratio"].max = (
                                self.pre[3][row][3 * index_pk + 2]
                            )
                if index == 10 or index == 11:
                    if row == 3 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gaussian_sigma"].min = (
                                self.pre[3][row][3 * index_pk + 1]
                            )
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gaussian_sigma"].max = (
                                self.pre[3][row][3 * index_pk + 2]
                            )
                    if row == 15 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gaussian_ratio"].min = (
                                self.pre[3][row][3 * index_pk + 1]
                            )
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gaussian_ratio"].max = (
                                self.pre[3][row][3 * index_pk + 2]
                            )
                if index == 1 or index == 3 or index == 9 or index == 10 or index == 11:
                    if row == 2 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_sigma"].min = self.pre[
                                3
                            ][row][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_sigma"].max = self.pre[
                                3
                            ][row][3 * index_pk + 2]
                    if row == 14 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[
                                strind + str(index_pk + 1) + "_lorentzian_ratio"
                            ].min = self.pre[3][row][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[
                                strind + str(index_pk + 1) + "_lorentzian_ratio"
                            ].max = self.pre[3][row][3 * index_pk + 2]
                if index == 2 or index == 6:
                    if row == 2 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gamma"].min = self.pre[
                                3
                            ][row][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gamma"].max = self.pre[
                                3
                            ][row][3 * index_pk + 2]
                    if row == 14 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[
                                strind + str(index_pk + 1) + "_lorentzian_ratio"
                            ].min = self.pre[3][row][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[
                                strind + str(index_pk + 1) + "_lorentzian_ratio"
                            ].max = self.pre[3][row][3 * index_pk + 2]
                if index == 4 or index == 5 or index == 9 or index == 10 or index == 11:
                    if row == 4 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gamma"].min = self.pre[
                                3
                            ][row][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gamma"].max = self.pre[
                                3
                            ][row][3 * index_pk + 2]
                    if row == 16 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gamma_ratio"].min = (
                                self.pre[3][row][3 * index_pk + 1]
                            )
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_gamma_ratio"].max = (
                                self.pre[3][row][3 * index_pk + 2]
                            )
                if index == 3:
                    if row == 5 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_fraction"].min = (
                                self.pre[3][row][3 * index_pk + 1]
                            )
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_fraction"].max = (
                                self.pre[3][row][3 * index_pk + 2]
                            )
                if index == 6:
                    if row == 6 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_skew"].min = self.pre[
                                3
                            ][row][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_skew"].max = self.pre[
                                3
                            ][row][3 * index_pk + 2]
                if index == 7:
                    if row == 7 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_q"].min = self.pre[3][
                                row
                            ][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_q"].max = self.pre[3][
                                row
                            ][3 * index_pk + 2]
                if index == 12:
                    if row == 8 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_kt"].min = self.pre[3][
                                row
                            ][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_kt"].max = self.pre[3][
                                row
                            ][3 * index_pk + 2]

                if index == 10:
                    if row == 9 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_soc"].min = self.pre[3][
                                row
                            ][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_soc"].max = self.pre[3][
                                row
                            ][3 * index_pk + 2]
                    if row == 17 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_soc_ratio"].min = (
                                self.pre[3][row][3 * index_pk + 1]
                            )
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_soc_ratio"].max = (
                                self.pre[3][row][3 * index_pk + 2]
                            )
                    if row == 10 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_height_ratio"].min = (
                                self.pre[3][row][3 * index_pk + 1]
                            )
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[strind + str(index_pk + 1) + "_height_ratio"].max = (
                                self.pre[3][row][3 * index_pk + 2]
                            )
                    if row == 18 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[
                                strind + str(index_pk + 1) + "_rel_height_ratio"
                            ].min = self.pre[3][row][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[
                                strind + str(index_pk + 1) + "_rel_height_ratio"
                            ].max = self.pre[3][row][3 * index_pk + 2]
                    if row == 11 and self.pre[3][row][3 * index_pk] == 2:
                        if (
                            self.pre[3][row][3 * index_pk + 1] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 1])) > 0
                        ):
                            pars[
                                strind + str(index_pk + 1) + "_fct_coster_kronig"
                            ].min = self.pre[3][row][3 * index_pk + 1]
                        if (
                            self.pre[3][row][3 * index_pk + 2] is not None
                            and len(str(self.pre[3][row][3 * index_pk + 2])) > 0
                        ):
                            pars[
                                strind + str(index_pk + 1) + "_fct_coster_kronig"
                            ].max = self.pre[3][row][3 * index_pk + 2]
        return pars

    def bgResult2Pre(self, out_params, mode, idx_bgs):
        for idx_bg in idx_bgs:
            if idx_bg == 6:
                self.pre[1][3][1] = out_params["bg_slope_k"].value
            if idx_bg == 100:
                if mode != "eva" and mode != "sim":
                    self.pre[1][0][5] = out_params["bg_shirley_k"].value
                    self.pre[1][0][7] = out_params["bg_shirley_const"].value
            if idx_bg == 101:
                self.pre[1][1][1] = out_params["bg_tougaard_B"].value
                self.pre[1][1][3] = out_params["bg_tougaard_C"].value
                self.pre[1][1][5] = out_params["bg_tougaard_C_d"].value
                self.pre[1][1][7] = out_params["bg_tougaard_D"].value
                self.pre[1][1][9] = out_params["bg_tougaard_extend"].value
            if idx_bg == 3:
                self.pre[1][idx_bg + 1][1] = out_params["bg_arctan_amplitude"].value
                self.pre[1][idx_bg + 1][3] = out_params["bg_arctan_center"].value
                self.pre[1][idx_bg + 1][5] = out_params["bg_arctan_sigma"].value

            if idx_bg == 4:
                self.pre[1][idx_bg + 1][1] = out_params["bg_step_amplitude"].value
                self.pre[1][idx_bg + 1][3] = out_params["bg_step_center"].value
                self.pre[1][idx_bg + 1][5] = out_params["bg_step_sigma"].value
            if idx_bg == 5:
                self.pre[1][idx_bg + 1][1] = out_params["bg_vbm_ctr"].value
                self.pre[1][idx_bg + 1][3] = out_params["bg_vbm_d1"].value
                self.pre[1][idx_bg + 1][5] = out_params["bg_vbm_d2"].value
                self.pre[1][idx_bg + 1][7] = out_params["bg_vbm_d3"].value
                self.pre[1][idx_bg + 1][9] = out_params["bg_vbm_d4"].value
            if idx_bg == 2:
                for index in range(5):
                    self.pre[1][2][2 * index + 1] = out_params[
                        "bg_poly_c" + str(index)
                    ].value

    def peakResult2Pre(self, out_params, mode):
        ncomponent = self.fitp1.columnCount()
        nrows = self.fitp1.rowCount()
        ncomponent = int(ncomponent / 2)
        for index_pk in range(ncomponent):
            index = self.pre[2][0][2 * index_pk + 1]
            strind = self.list_shape[index]
            strind = strind.split(":", 1)[0]
            # fit parameters from self.pre
            self.pre[2][1][2 * index_pk + 1] = out_params[
                strind + str(index_pk + 1) + "_center"
            ].value
            self.pre[2][2][2 * index_pk + 1] = out_params[
                strind + str(index_pk + 1) + "_amplitude"
            ].value
            self.pre[2][14][2 * index_pk + 1] = out_params[
                strind + str(index_pk + 1) + "_center_diff"
            ].value
            self.pre[2][16][2 * index_pk + 1] = out_params[
                strind + str(index_pk + 1) + "_amp_ratio"
            ].value
            if (
                index == 0
                or index == 2
                or index == 4
                or index == 5
                or index == 6
                or index == 7
                or index == 8
                or index == 12
            ):
                self.pre[2][4][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_sigma"
                ].value
                self.pre[2][20][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_gaussian_ratio"
                ].value
            if index == 10 or index == 11:
                self.pre[2][4][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_gaussian_sigma"
                ].value
                self.pre[2][20][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_gaussian_ratio"
                ].value
            if index == 1 or index == 3 or index == 9 or index == 10 or index == 11:
                self.pre[2][3][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_sigma"
                ].value
                self.pre[2][18][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_lorentzian_ratio"
                ].value
            if index == 2 or index == 6:
                self.pre[2][3][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_gamma"
                ].value
                self.pre[2][18][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_lorentzian_ratio"
                ].value
            if index == 4 or index == 5 or index == 9 or index == 10 or index == 11:
                self.pre[2][5][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_gamma"
                ].value
                self.pre[2][22][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_gamma_ratio"
                ].value
            if index == 3:
                self.pre[2][6][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_fraction"
                ].value
            if index == 6:
                self.pre[2][7][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_skew"
                ].value
            if index == 7:
                self.pre[2][8][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_q"
                ].value
            if index == 12:
                self.pre[2][9][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_kt"
                ].value

            if index == 10:
                self.pre[2][10][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_soc"
                ].value
                self.pre[2][24][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_soc_ratio"
                ].value
                self.pre[2][11][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_height_ratio"
                ].value
                self.pre[2][26][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_rel_height_ratio"
                ].value
                self.pre[2][12][2 * index_pk + 1] = out_params[
                    strind + str(index_pk + 1) + "_fct_coster_kronig"
                ].value

    def result2Par(self, out_params, mode):
        self.bgResult2Pre(out_params, mode, self.idx_bg)
        self.peakResult2Pre(out_params, mode)

    def approx_fwhm(self, x, peak):
        peak_norm = peak / np.max(peak)
        indices = np.where(peak_norm >= 0.5)[0]
        i1 = indices[0]
        if i1 > 0:
            x1 = x[i1 - 1] + (0.5 - peak_norm[i1 - 1]) * (x[i1] - x[i1 - 1]) / (
                peak_norm[i1] - peak_norm[i1 - 1]
            )
        else:
            x1 = x[i1]

        i2 = indices[-1]
        if i2 < len(peak_norm) - 1:
            x2 = x[i2] + (0.5 - peak_norm[i2]) * (x[i2 + 1] - x[i2]) / (
                peak_norm[i2 + 1] - peak_norm[i2]
            )
        else:
            x2 = x[i2]
        return abs(x2 - x1)

    def fillTabResults(self, x, y, out):
        self.meta_result_export = []
        precision = int(self.floating.split(".")[1].split("f")[0]) + 2
        y_components = [0 for idx in range(len(y))]
        x_interpolate = np.linspace(x[0], x[-1], 10 * len(x))
        nrows = len(self.pre[2])
        ncols = int(len(self.pre[2][0]) / 2)
        for index_pk in range(int(len(self.pre[2][0]) / 2)):
            index = self.pre[2][0][2 * index_pk + 1]
            strind = self.list_shape[index]
            strind = strind.split(":", 1)[0]
            y_components += out.eval_components()[strind + str(index_pk + 1) + "_"]
        if self.binding_ener:
            area_components = integrate.simpson(y_components, x=x[::-1])
        else:
            area_components = integrate.simpson(y_components, x=x)
        for index_pk in range(int(len(self.pre[2][0]) / 2)):
            index = self.pre[2][0][2 * index_pk + 1]
            strind = self.list_shape[index]
            strind = strind.split(":", 1)[0]
            temp_result_export = {
                strind + str(index_pk + 1) + "_gaussian_fwhm": None,
                strind + str(index_pk + 1) + "_lorentzian_fwhm_p1": None,
                strind + str(index_pk + 1) + "_lorentzian_fwhm_p2": None,
                strind + str(index_pk + 1) + "_fwhm_p1": None,
                strind + str(index_pk + 1) + "_fwhm_p2": None,
                strind + str(index_pk + 1) + "_height_p1": None,
                strind + str(index_pk + 1) + "_height_p2": None,
                strind + str(index_pk + 1) + "_approx_area_p1": None,
                strind + str(index_pk + 1) + "_approx_area_p2": None,
                strind + str(index_pk + 1) + "_area_total": None,
            }
            if index == 0:
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[strind + str(index_pk + 1) + "_fwhm"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(0, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_gaussian_fwhm"] = (
                    np.round(
                        out.params[strind + str(index_pk + 1) + "_fwhm"].value,
                        precision,
                    )
                )
                item = QtWidgets.QTableWidgetItem("")
                temp_result_export[
                    strind + str(index_pk + 1) + "_lorentzian_fwhm_p1"
                ] = None
                self.res_tab.setItem(1, index_pk, item)
            if index == 1:
                item = QtWidgets.QTableWidgetItem("")
                self.res_tab.setItem(0, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_gaussian_fwhm"] = None
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            2 * out.params[strind + str(index_pk + 1) + "_fwhm"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(1, index_pk, item)
                temp_result_export[
                    strind + str(index_pk + 1) + "_lorentzian_fwhm_p1"
                ] = np.round(
                    out.params[strind + str(index_pk + 1) + "_fwhm"].value, precision
                )
            if index == 0 or index == 1 or index == 2 or index == 3:
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[strind + str(index_pk + 1) + "_fwhm"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(3, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_fwhm_p1"] = np.round(
                    out.params[strind + str(index_pk + 1) + "_fwhm"].value, precision
                )
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[strind + str(index_pk + 1) + "_height"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(5, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_height_p1"] = (
                    np.round(
                        out.params[strind + str(index_pk + 1) + "_height"].value,
                        precision,
                    )
                )
            if index == 0 or index == 1 or index == 2 or index == 3 or index == 4:
                y_area = out.eval_components(x=x_interpolate)[
                    strind + str(index_pk + 1) + "_"
                ]
                if self.binding_ener:
                    area = abs(integrate.simpson(y_area, x=x_interpolate[::-1]))
                else:
                    area = abs(integrate.simpson(y_area, x=x_interpolate))
                item = QtWidgets.QTableWidgetItem(
                    str(format(area, ".1f") + r" ({}%)".format(format(100, ".2f")))
                )
                self.res_tab.setItem(7, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_approx_area_p1"] = (
                    str(format(area, ".1f") + r" ({}%)".format(format(100, ".2f")))
                )
                item = QtWidgets.QTableWidgetItem(
                    str(format(area, ".1f") + r" ({}%)".format(format(100, ".2f")))
                )
                self.res_tab.setItem(9, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_area_total"] = str(
                    format(area, ".1f") + r" ({}%)".format(format(100, ".2f"))
                )
                item = QtWidgets.QTableWidgetItem("")
                self.res_tab.setItem(2, index_pk, item)
                temp_result_export[
                    strind + str(index_pk + 1) + "_lorentzian_fwhm_p2"
                ] = None
                item = QtWidgets.QTableWidgetItem("")
                self.res_tab.setItem(4, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_fwhm_p2"] = None
                item = QtWidgets.QTableWidgetItem("")
                self.res_tab.setItem(6, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_height_p2"] = None
                item = QtWidgets.QTableWidgetItem("")
                self.res_tab.setItem(8, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_approx_area_p2"] = (
                    None
                )
            if (
                index == 4
                or index == 5
                or index == 6
                or index == 7
                or index == 8
                or index == 9
                or index == 12
            ):
                rows = self.res_tab.rowCount()
                for row in range(rows):
                    if row != 7:
                        item = QtWidgets.QTableWidgetItem("")
                        self.res_tab.setItem(row, index_pk, item)
                    # included area
                    y_area = out.eval_components(x=x_interpolate)[
                        strind + str(index_pk + 1) + "_"
                    ]
                    if self.binding_ener:
                        area = abs(integrate.simpson(y_area, x=x_interpolate[::-1]))
                    else:
                        area = abs(integrate.simpson(y_area, x=x_interpolate))
                    item = QtWidgets.QTableWidgetItem(
                        str(format(area, ".1f") + r" ({}%)".format(format(100, ".2f")))
                    )
                    self.res_tab.setItem(7, index_pk, item)
                    temp_result_export[
                        strind + str(index_pk + 1) + "_approx_area_p1"
                    ] = str(format(area, ".1f") + r" ({}%)".format(format(100, ".2f")))
                    item = QtWidgets.QTableWidgetItem(
                        str(format(area, ".1f") + r" ({}%)".format(format(100, ".2f")))
                    )
                    self.res_tab.setItem(9, index_pk, item)
                    temp_result_export[strind + str(index_pk + 1) + "_area_total"] = (
                        str(format(area, ".1f") + r" ({}%)".format(format(100, ".2f")))
                    )
            if index == 2:
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[strind + str(index_pk + 1) + "_sigma"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(0, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_gaussian_fwhm"] = (
                    np.round(
                        out.params[strind + str(index_pk + 1) + "_sigma"].value,
                        precision,
                    )
                )
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            2 * out.params[strind + str(index_pk + 1) + "_gamma"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(1, index_pk, item)
                temp_result_export[
                    strind + str(index_pk + 1) + "_lorentzian_fwhm_p1"
                ] = np.round(
                    2 * out.params[strind + str(index_pk + 1) + "_gamma"].value,
                    precision,
                )
            if index == 3:
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[strind + str(index_pk + 1) + "_sigma"].value
                            / np.sqrt(2 * np.log(2)),
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(0, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_gaussian_fwhm"] = (
                    np.round(
                        out.params[strind + str(index_pk + 1) + "_sigma"].value
                        / np.sqrt(2 * np.log(2)),
                        precision,
                    )
                )
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            2 * out.params[strind + str(index_pk + 1) + "_sigma"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(1, index_pk, item)
                temp_result_export[
                    strind + str(index_pk + 1) + "_lorentzian_fwhm_p1"
                ] = np.round(
                    2 * out.params[strind + str(index_pk + 1) + "_sigma"].value,
                    precision,
                )
            if index == 9:
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            2 * out.params[strind + str(index_pk + 1) + "_sigma"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(1, index_pk, item)
                temp_result_export[
                    strind + str(index_pk + 1) + "_lorentzian_fwhm_p1"
                ] = np.round(
                    2 * out.params[strind + str(index_pk + 1) + "_sigma"].value,
                    precision,
                )
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[strind + str(index_pk + 1) + "_amplitude"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(5, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_height_p1"] = (
                    np.round(
                        out.params[strind + str(index_pk + 1) + "_amplitude"].value,
                        precision,
                    )
                )
                y_area = out.eval_components(x=x_interpolate)[
                    strind + str(index_pk + 1) + "_"
                ]
                fwhm_temp = self.approx_fwhm(x_interpolate, y_area)
                item = QtWidgets.QTableWidgetItem(str(format(fwhm_temp, self.floating)))
                self.res_tab.setItem(3, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_fwhm_p1"] = np.round(
                    fwhm_temp, precision
                )
            if index == 11:
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            2
                            * out.params[
                                strind + str(index_pk + 1) + "_lorentzian_fwhm"
                            ].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(1, index_pk, item)
                temp_result_export[
                    strind + str(index_pk + 1) + "_lorentzian_fwhm_p1"
                ] = np.round(
                    2
                    * out.params[strind + str(index_pk + 1) + "_lorentzian_fwhm"].value,
                    precision,
                )
                y_area = out.eval_components(x=x_interpolate)[
                    strind + str(index_pk + 1) + "_"
                ]
                if np.max(y_area) != 0:
                    fwhm_temp = self.approx_fwhm(x_interpolate, y_area)
                    item = QtWidgets.QTableWidgetItem(
                        str(format(fwhm_temp, self.floating))
                    )
                    self.res_tab.setItem(3, index_pk, item)
                    temp_result_export[strind + str(index_pk + 1) + "_fwhm_p1"] = (
                        np.round(fwhm_temp, precision)
                    )
                else:
                    print(
                        "WARNING: Invalid value encountered in true division: Probably one of the amplitudes is "
                        "set to 0."
                    )
                    item = QtWidgets.QTableWidgetItem("Error in calculation")
                    self.res_tab.setItem(3, index_pk, item)
                    temp_result_export[strind + str(index_pk + 1) + "_fwhm_p1"] = (
                        "Error in calculation"
                    )
                # included area
                if self.binding_ener:
                    area = abs(integrate.simpson(y_area, x=x[::-1]))
                else:
                    area = abs(integrate.simpson(y_area, x=x))
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(area, ".1f")
                        + r" ({}%)".format(format(area / area_components * 100, ".2f"))
                    )
                )
                self.res_tab.setItem(7, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_approx_area_p1"] = (
                    str(
                        format(area, ".1f")
                        + r" ({}%)".format(format(area / area_components * 100, ".2f"))
                    )
                )
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(area, ".1f")
                        + r" ({}%)".format(format(area / area_components * 100, ".2f"))
                    )
                )
                self.res_tab.setItem(9, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_area_total"] = str(
                    format(area, ".1f")
                    + r" ({}%)".format(format(area / area_components * 100, ".2f"))
                )
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[strind + str(index_pk + 1) + "_amplitude"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(5, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_height_p1"] = (
                    np.round(
                        out.params[strind + str(index_pk + 1) + "_amplitude"].value,
                        precision,
                    )
                )
                item = QtWidgets.QTableWidgetItem("")
                self.res_tab.setItem(2, index_pk, item)
                temp_result_export[
                    strind + str(index_pk + 1) + "_lorentzian_fwhm_p2"
                ] = None
                item = QtWidgets.QTableWidgetItem("")
                self.res_tab.setItem(4, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_fwhm_p2"] = None
                item = QtWidgets.QTableWidgetItem("")
                self.res_tab.setItem(6, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_height_p2"] = None
                item = QtWidgets.QTableWidgetItem("")
                self.res_tab.setItem(8, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_approx_area_p2"] = (
                    None
                )
            if index == 10:
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[
                                strind + str(index_pk + 1) + "_lorentzian_fwhm_p1"
                            ].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(1, index_pk, item)
                temp_result_export[
                    strind + str(index_pk + 1) + "_lorentzian_fwhm_p1"
                ] = np.round(
                    out.params[
                        strind + str(index_pk + 1) + "_lorentzian_fwhm_p1"
                    ].value,
                    precision,
                )
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[
                                strind + str(index_pk + 1) + "_lorentzian_fwhm_p2"
                            ].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(2, index_pk, item)
                temp_result_export[
                    strind + str(index_pk + 1) + "_lorentzian_fwhm_p2"
                ] = np.round(
                    out.params[
                        strind + str(index_pk + 1) + "_lorentzian_fwhm_p2"
                    ].value,
                    precision,
                )
                # included fwhm
                x_interpol = np.linspace(x[0], x[-1], 10 * len(x))
                y_area_p1 = singlett(
                    x_interpol,
                    amplitude=out.params[
                        strind + str(index_pk + 1) + "_amplitude"
                    ].value,
                    sigma=out.params[strind + str(index_pk + 1) + "_sigma"].value,
                    gamma=out.params[strind + str(index_pk + 1) + "_gamma"].value,
                    gaussian_sigma=out.params[
                        strind + str(index_pk + 1) + "_gaussian_sigma"
                    ].value,
                    center=out.params[strind + str(index_pk + 1) + "_center"].value,
                )
                y_area_p2 = singlett(
                    x_interpol,
                    amplitude=out.params[
                        strind + str(index_pk + 1) + "_amplitude"
                    ].value
                    * out.params[strind + str(index_pk + 1) + "_height_ratio"].value,
                    sigma=out.params[strind + str(index_pk + 1) + "_sigma"].value
                    * out.params[
                        strind + str(index_pk + 1) + "_fct_coster_kronig"
                    ].value,
                    gamma=out.params[strind + str(index_pk + 1) + "_gamma"].value,
                    gaussian_sigma=out.params[
                        strind + str(index_pk + 1) + "_gaussian_sigma"
                    ].value,
                    center=out.params[strind + str(index_pk + 1) + "_center"].value
                    - out.params[strind + str(index_pk + 1) + "_soc"].value,
                )
                if np.max(y_area_p1) != 0 and np.max(y_area_p2) != 0:
                    fwhm_temp_p1 = self.approx_fwhm(x_interpol, y_area_p1)
                    item = QtWidgets.QTableWidgetItem(
                        str(format(fwhm_temp_p1, self.floating))
                    )
                    self.res_tab.setItem(3, index_pk, item)
                    temp_result_export[strind + str(index_pk + 1) + "_fwhm_p1"] = (
                        np.round(fwhm_temp_p1, precision)
                    )
                    fwhm_temp_p2 = self.approx_fwhm(x_interpol, y_area_p2)
                    item = QtWidgets.QTableWidgetItem(
                        str(format(fwhm_temp_p2, self.floating))
                    )
                    self.res_tab.setItem(4, index_pk, item)
                    temp_result_export[strind + str(index_pk + 1) + "_fwhm_p2"] = (
                        np.round(fwhm_temp_p2, precision)
                    )
                else:
                    print(
                        "WARNING: Invalid value encountered in true division: Probably one of the amplitudes is "
                        "set to 0."
                    )
                    item = QtWidgets.QTableWidgetItem("Error in calculation")
                    self.res_tab.setItem(3, index_pk, item)
                    temp_result_export[strind + str(index_pk + 1) + "_fwhm_p1"] = (
                        "Error in calculation"
                    )
                    self.res_tab.setItem(4, index_pk, item)
                    temp_result_export[strind + str(index_pk + 1) + "_fwhm_p2"] = (
                        "Error in calculation"
                    )
                    # included area

                if self.binding_ener:
                    area_p1 = abs(integrate.simpson(y_area_p1, x=x_interpol[::-1]))
                    area_p2 = abs(integrate.simpson(y_area_p2, x=x_interpol[::-1]))
                else:
                    area_p1 = integrate.simpson(y_area_p1, x=x_interpol)
                    area_p2 = integrate.simpson(y_area_p2, x=x_interpol)
                area_ges = area_p1 + area_p2
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(area_p1, ".1f")
                        + r" ({}%)".format(format(area_p1 / area_ges * 100, ".2f"))
                    )
                )
                self.res_tab.setItem(7, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_approx_area_p1"] = (
                    str(
                        format(area_p1, ".1f")
                        + r" ({}%)".format(format(area_p1 / area_ges * 100, ".2f"))
                    )
                )
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(area_p2, ".1f")
                        + r" ({}%)".format(format(area_p2 / area_ges * 100, ".2f"))
                    )
                )
                self.res_tab.setItem(8, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_approx_area_p2"] = (
                    str(
                        format(area_p2, ".1f")
                        + r" ({}%)".format(format(area_p2 / area_ges * 100, ".2f"))
                    )
                )
                y_area = out.eval_components(x=x_interpolate)[
                    strind + str(index_pk + 1) + "_"
                ]
                area = abs(integrate.simpson(y_area, x=x_interpolate))
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(area, ".1f")
                        + r" ({}%)".format(format(area / area_components * 100, ".2f"))
                    )
                )
                self.res_tab.setItem(9, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_area_total"] = str(
                    format(area, ".1f")
                    + r" ({}%)".format(format(area / area_components * 100, ".2f"))
                )
                h_p1_expr = "{pre:s}amplitude"
                h_p2_expr = "{pre:s}amplitude*{pre:s}height_ratio"
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[strind + str(index_pk + 1) + "_amplitude"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(5, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_height_p1"] = (
                    np.round(
                        out.params[strind + str(index_pk + 1) + "_amplitude"].value,
                        precision,
                    )
                )
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[strind + str(index_pk + 1) + "_amplitude"].value
                            * out.params[
                                strind + str(index_pk + 1) + "_height_ratio"
                            ].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(6, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_height_p2"] = (
                    np.round(
                        out.params[strind + str(index_pk + 1) + "_amplitude"].value
                        * out.params[
                            strind + str(index_pk + 1) + "_height_ratio"
                        ].value,
                        precision,
                    )
                )
            if index == 10 or index == 11:
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[
                                strind + str(index_pk + 1) + "_gaussian_sigma"
                            ].value
                            * 2
                            * np.sqrt(2 * np.log(2)),
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(0, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_gaussian_fwhm"] = (
                    np.round(
                        out.params[strind + str(index_pk + 1) + "_gaussian_sigma"].value
                        * 2
                        * np.sqrt(2 * np.log(2)),
                        precision,
                    )
                )
            if index == 12:
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[strind + str(index_pk + 1) + "_amplitude"].value,
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(5, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_height_p1"] = (
                    np.round(
                        out.params[strind + str(index_pk + 1) + "_amplitude"].value,
                        precision,
                    )
                )
                item = QtWidgets.QTableWidgetItem(
                    str(
                        format(
                            out.params[strind + str(index_pk + 1) + "_sigma"].value
                            * 2
                            * np.sqrt(2 * np.log(2)),
                            self.floating,
                        )
                    )
                )
                self.res_tab.setItem(0, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_gaussian_fwhm"] = (
                    np.round(
                        out.params[strind + str(index_pk + 1) + "_sigma"].value
                        * 2
                        * np.sqrt(2 * np.log(2)),
                        precision,
                    )
                )
                self.res_tab.setItem(3, index_pk, item)
                temp_result_export[strind + str(index_pk + 1) + "_fwhm_p1"] = np.round(
                    out.params[strind + str(index_pk + 1) + "_sigma"].value
                    * 2
                    * np.sqrt(2 * np.log(2)),
                    precision,
                )
            self.meta_result_export.append(temp_result_export)

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
                pars = temp_res[2]
        return mod, bg_mod, pars

    def ana(self, mode):
        self.savePreset()
        plottitle = self.plottitle.text()
        self.ax.cla()
        self.ar.cla()
        # ax = self.figure.add_subplot(211)
        if mode == "fit":
            x0 = self.df.iloc[:, 0].to_numpy()
            if x0[-1] < x0[0]:
                self.binding_ener = True
            x0_corrected = np.copy(x0)
            if self.correct_energy is not None:
                x0_corrected -= self.correct_energy
            y0 = self.df.iloc[:, 1].to_numpy()
            self.ax.plot(x0_corrected, y0, "o", color="b", label="raw")
        else:
            # simulation mode
            if mode == "sim":
                x0 = self.df[:, 0]
                if x0[-1] < x0[0]:
                    self.binding_ener = True
                x0_corrected = np.copy(x0)
                if self.correct_energy is not None:
                    x0_corrected -= self.correct_energy
                y0 = self.df[:, 1]
                self.ax.plot(x0_corrected, y0, ",", color="b", label="raw")
            # evaluation mode
            else:
                x0 = self.df.iloc[:, 0].to_numpy()
                if x0[-1] < x0[0]:
                    self.binding_ener = True
                x0_corrected = np.copy(x0)
                if self.correct_energy is not None:
                    x0_corrected -= self.correct_energy
                y0 = self.df.iloc[:, 1].to_numpy()
                self.ax.plot(x0_corrected, y0, "o", mfc="none", color="b", label="raw")

        if x0_corrected[0] > x0_corrected[-1]:
            self.ax.set_xlabel("Binding energy (eV)", fontsize=11)
        else:
            self.ax.set_xlabel("Energy (eV)", fontsize=11)
        plt.xlim(x0_corrected[0], x0_corrected[-1])
        self.ax.grid(True)
        self.ax.set_ylabel("Intensity (arb. unit)", fontsize=11)
        if len(plottitle) == 0:
            if mode == "sim":
                # simulation mode
                self.ar.set_title("Simulation", fontsize=11)
            else:
                short_file_name = self.comboBox_file.currentText().split("/")[-1]
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
        if (
            (x1 > x0_corrected[0] or x1 < x0_corrected[-1]) and x0_corrected[0] > x0[-1]
        ) or (
            (x1 < x0_corrected[0] or x1 > x0_corrected[-1])
            and x0_corrected[0] < x0_corrected[-1]
        ):
            x1 = x0_corrected[0]
            self.pre[0][1] = x1
        x2 = self.pre[0][2]
        if (
            (x2 < x0_corrected[-1] or x2 > x1) and x0_corrected[0] > x0_corrected[-1]
        ) or ((x2 > x0_corrected[-1] or x2 < x1) and x0_corrected[0] < x0[-1]):
            x2 = x0_corrected[-1]
            self.pre[0][2] = x2

        [x, y] = fit_range(x0_corrected, y0, x1, x2)
        raw_y = y.copy()
        raw_x = x.copy()
        if self.correct_energy is not None:
            raw_x += self.correct_energy
        # BG model selection and call shirley and tougaard
        # colPosition = self.fitp1.columnCount()

        temp_res = self.BGModCreator(x, y, mode=mode)
        mod = temp_res[0]
        self.static_bg = temp_res[1]
        pars = temp_res[2]
        self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
        # component model selection and construction
        y = raw_y - self.static_bg
        temp_res = self.PeakSelector(mod)
        if pars != None:
            pars.update(temp_res[1])
        else:
            pars = temp_res[1]

        mod = temp_res[0]

        if mode == "eva" or mode == "sim":
            for par in pars:
                pars[par].vary = False
        else:
            temp = self.peak_limits(pars)
            pars.update(temp)  # update pars before using expr, to prevent missing pars

        # evaluate model and optimize parameters for fitting in lmfit
        if mode == "eva":
            strmode = "Evaluation"
        elif mode == "sim":
            strmode = "Simulation"
        else:
            strmode = "Fitting"
        self.statusBar().showMessage(
            strmode + " running.",
        )
        init = mod.eval(pars, x=x, y=y)
        zeros_in_data = False
        if np.any(raw_y == 0):
            zeros_in_data = True
            print(
                "There were 0's in your data. The residuals are therefore not weighted by sqrt(data)!"
            )
        if mode == "eva" or mode == "sim":
            try:
                if zeros_in_data:
                    out = mod.fit(
                        y, pars, x=x, weights=1 / (np.sqrt(self.rows_lightened)), y=y
                    )
                else:
                    out = mod.fit(
                        y,
                        pars,
                        x=x,
                        weights=1 / (np.sqrt(raw_y) * np.sqrt(self.rows_lightened)),
                        y=y,
                    )
            except Exception as e:
                return self.raise_error(
                    window_title="Error: Could not evaluate fit model.",
                    error_message="Evaluation of the fit model failed. Please try different parameters! The following traceback may help to solve the issue:",
                )

            self.fitting_finished(
                out,
                strmode=strmode,
                mode=mode,
                x=x,
                y=y,
                zeros_in_data=zeros_in_data,
                raw_x=raw_x,
                raw_y=raw_y,
                pars=pars,
            )
        else:
            try_me_out = self.history_manager(pars)
            if try_me_out is not None:
                pars, pre = try_me_out
                self.pre = pre
                self.setPreset(pre[0], pre[1], pre[2], pre[3])
            if zeros_in_data:
                self.fit_thread = FitThread(
                    model=mod,
                    data=y,
                    params=pars,
                    x=x,
                    weights=1 / (np.sqrt(self.rows_lightened)),
                    y=raw_y,
                )
                self.fit_thread.fitting_finished.connect(
                    lambda out: self.fitting_finished(
                        out,
                        x=x,
                        y=y,
                        strmode=strmode,
                        mode=mode,
                        zeros_in_data=zeros_in_data,
                        raw_x=raw_x,
                        raw_y=raw_y,
                        pars=pars,
                    )
                )
                self.fit_thread.start()
                # out = mod.fit(y, pars, x=x, weights=1 / (np.sqrt(self.rows_lightened)), y=raw_y)
            else:
                self.fit_thread = FitThread(
                    model=mod,
                    data=y,
                    params=pars,
                    x=x,
                    weights=1 / (np.sqrt(raw_y) * np.sqrt(self.rows_lightened)),
                    y=raw_y,
                )
                self.fit_thread.fitting_finished.connect(
                    lambda out: self.fitting_finished(
                        out,
                        x=x,
                        y=y,
                        strmode=strmode,
                        mode=mode,
                        zeros_in_data=zeros_in_data,
                        raw_x=raw_x,
                        raw_y=raw_y,
                        pars=pars,
                    )
                )
                self.fit_thread.start()
                # out = mod.fit(y, pars, x=x, weights=1 / (np.sqrt(raw_y) * np.sqrt(self.rows_lightened)), y=raw_y)
            self.fit_thread.thread_started.connect(self.fit_thread_started)
            self.fit_thread.error_occurred.connect(self.handle_thread_exception)

    def handle_thread_exception(self, error_message):
        self.raise_error("Error in FitThread", error_message)
        self.statusBar().showMessage("Fitting failed! NaN in data/fit-model occured!")
        self.enable_buttons_after_fit_thread()

    def fit_thread_started(self):
        """Update button states when the fit thread starts."""
        self.fit_buttons["btn_fit"].setEnabled(False)
        self.fit_buttons["btn_fit"].setStyleSheet(
            "QPushButton:disabled { background-color: rgba(200, 200, 200, 128); }"
        )

        self.fit_buttons["btn_eva"].setEnabled(False)
        self.fit_buttons["btn_eva"].setStyleSheet(
            "QPushButton:disabled { background-color: rgba(200, 200, 200, 128); }"
        )

        self.fit_buttons["btn_interrupt"].setEnabled(True)
        self.fit_buttons["btn_interrupt"].setStyleSheet("")

        self.fit_buttons["btn_undoFit"].setEnabled(False)
        self.fit_buttons["btn_undoFit"].setStyleSheet(
            "QPushButton:disabled { background-color: rgba(200, 200, 200, 128); }"
        )

    def enable_buttons_after_fit_thread(self):
        """Enable buttons after the fit thread finishes."""
        self.fit_buttons["btn_fit"].setEnabled(True)
        self.fit_buttons["btn_fit"].setStyleSheet("")

        self.fit_buttons["btn_eva"].setEnabled(True)
        self.fit_buttons["btn_eva"].setStyleSheet("")

        self.fit_buttons["btn_interrupt"].setEnabled(True)
        self.fit_buttons["btn_interrupt"].setStyleSheet("")

        self.fit_buttons["btn_undoFit"].setEnabled(True)
        self.fit_buttons["btn_undoFit"].setStyleSheet("")

    def get_attr(self, obj, attr):
        """Format an attribute of an object for printing."""
        val = getattr(obj, attr, None)
        if val is None:
            return "unknown"
        if isinstance(val, int):
            return f"{val}"
        if isinstance(val, float):
            return str(format(val, self.floating))
        return repr(val)

    def fitting_finished(
        self, out, x, y, strmode, mode, zeros_in_data, pars, raw_x, raw_y
    ):
        self.enable_buttons_after_fit_thread()
        comps = out.eval_components(x=x)
        # fit results to be checked
        for key in out.params:
            print(key, "=", out.params[key].value)

        # fit results print
        if (
            self.get_attr(out, "aic") == "unknown"
            or self.get_attr(out, "bic") == "unknown"
            or self.get_attr(out, "redchi") == "unknown"
            or self.get_attr(out, "chisqr") == "unknown"
        ):
            results = (
                "Fitting interrupted: "
                + out.method
                + ", # data: "
                + str(out.ndata)
                + ", # func evals: "
                + str(out.nfev)
                + ", # varys: "
                + str(out.nvarys)
                + ", r chi-sqr: "
                + self.get_attr(out, "redchi")
                + ", Akaike info crit: "
                + self.get_attr(out, "aic")
                + ", Last run finished: "
                + QTime.currentTime().toString()
            )
        else:
            results = (
                strmode
                + " done: "
                + out.method
                + ", # data: "
                + str(out.ndata)
                + ", # func evals: "
                + str(out.nfev)
                + ", # varys: "
                + str(out.nvarys)
                + ", r chi-sqr: "
                + self.get_attr(out, "redchi")
                + ", Akaike info crit: "
                + self.get_attr(out, "aic")
                + ", Last run finished: "
                + QTime.currentTime().toString()
            )
        self.statusBar().showMessage(results)

        # component results into table
        self.result2Par(out.params, mode)
        self.setPreset(self.pre[0], self.pre[1], self.pre[2], self.pre[3])
        self.fillTabResults(x, y, out)
        # Fit stats to GUI:
        if mode == "eva" or mode == "sim":
            # for index_pk in range(int(len(self.pre[2][0]))):
            #    item = QtWidgets.QTableWidgetItem('Evaluation mode')
            #    self.res_tab.setItem(0, index_pk, item)
            #    for i in range(self.res_tab.rowCount() - 1):
            #        item = QtWidgets.QTableWidgetItem('-')
            #        self.res_tab.setItem(i, index_pk, item)
            item = QtWidgets.QTableWidgetItem("-")
            self.stats_tab.setItem(0, 0, item)
            item = QtWidgets.QTableWidgetItem("Evaluation mode.")
            self.stats_tab.setItem(1, 0, item)
            for i in range(2, 6, 1):
                item = QtWidgets.QTableWidgetItem("-")
                self.stats_tab.setItem(i, 0, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.chisqr, self.floating)))
            self.stats_tab.setItem(6, 0, item)
            item = QtWidgets.QTableWidgetItem(str(format(out.redchi, self.floating)))
            self.stats_tab.setItem(7, 0, item)
            for i in range(8, 10, 1):
                item = QtWidgets.QTableWidgetItem("-")
                self.stats_tab.setItem(i, 0, item)
        else:
            item = QtWidgets.QTableWidgetItem(str(out.success))
            self.stats_tab.setItem(0, 0, item)
            message = "\n".join(
                out.message[i : i + 64] for i in range(0, len(out.message), 64)
            )
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
            item = QtWidgets.QTableWidgetItem(self.get_attr(out, "chisqr"))
            self.stats_tab.setItem(6, 0, item)
            if zeros_in_data:
                item = QtWidgets.QTableWidgetItem(
                    str(format(out.redchi, self.floating))
                    + " not weigthed by sqrt(data)"
                )
            else:
                item = QtWidgets.QTableWidgetItem(self.get_attr(out, "redchi"))
            self.stats_tab.setItem(7, 0, item)
            item = QtWidgets.QTableWidgetItem(self.get_attr(out, "aic"))
            self.stats_tab.setItem(8, 0, item)
            item = QtWidgets.QTableWidgetItem(self.get_attr(out, "bic"))
            self.stats_tab.setItem(9, 0, item)
        self.resizeAllColumns()

        sum_background = np.array([0.0] * len(x))
        self.bg_comps = dict()
        for key in comps:
            if "bg_" in key:
                self.bg_comps[key] = comps[key]
                sum_background += comps[key]
        if mode == "sim":
            self.ar.set_title(r"Simulation mode", fontsize=11)
        if mode == "eva":
            plottitle = self.plottitle.text()
            if len(plottitle) == 0:
                plottitle = self.comboBox_file.currentText().split("/")[-1]
            if plottitle != "":
                self.ar.set_title(r"{}".format(plottitle), fontsize=11)
            len_idx_pk = int(self.fitp1.columnCount() / 2)
            for index_pk in range(len_idx_pk):
                # print(index_pk, color)
                strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
                strind = strind.split(":", 1)[0]
                self.ax.fill_between(
                    x,
                    comps[strind + str(index_pk + 1) + "_"]
                    + sum_background
                    + self.static_bg,
                    sum_background + self.static_bg,
                    label=self.fitp1.horizontalHeaderItem(2 * index_pk + 1).text(),
                )
                self.ax.plot(
                    x,
                    comps[strind + str(index_pk + 1) + "_"]
                    + sum_background
                    + self.static_bg,
                )
                if index_pk == len_idx_pk - 1:
                    self.ax.plot(x, +sum_background + self.static_bg, label="BG")
            self.ax.set_xlim(left=self.xmin)
            self.ar.set_xlim(left=self.xmin)
            self.ax.set_xlim(right=self.xmax)
            self.ar.set_xlim(right=self.xmax)
            self.ax.plot(x, out.best_fit + self.static_bg, "r-", lw=2, label="sum")
            self.ar.plot(x, out.residual, "g.", label="residual")
            autoscale_y(self.ax)

        else:
            # ax.plot(x, init+bg_mod, 'k:', label='initial')
            plottitle = self.plottitle.text()
            if len(plottitle) == 0:
                plottitle = self.comboBox_file.currentText().split("/")[-1]
            if plottitle != "":
                self.ar.set_title(r"{}".format(plottitle), fontsize=11)
            len_idx_pk = int(self.fitp1.columnCount() / 2)
            for index_pk in range(len_idx_pk):
                strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
                strind = strind.split(":", 1)[0]
                self.ax.fill_between(
                    x,
                    comps[strind + str(index_pk + 1) + "_"]
                    + self.static_bg
                    + sum_background,
                    self.static_bg + sum_background,
                    label=self.fitp1.horizontalHeaderItem(2 * index_pk + 1).text(),
                )
                self.ax.plot(
                    x,
                    comps[strind + str(index_pk + 1) + "_"]
                    + self.static_bg
                    + sum_background,
                )
                if index_pk == len_idx_pk - 1:
                    self.ax.plot(x, +self.static_bg + sum_background, label="BG")
            self.ax.set_xlim(left=self.xmin)
            self.ar.set_xlim(left=self.xmin)
            self.ax.set_xlim(right=self.xmax)
            self.ar.set_xlim(right=self.xmax)
            self.ax.plot(x, out.best_fit + self.static_bg, "r-", lw=2, label="fit")
            self.ar.plot(
                x, out.residual, "g.", label="residual"
            )  # modify residual and red chi-squared [feature]
            lines = self.ax.get_lines()
            autoscale_y(self.ax)
        self.ax.legend(loc=0)
        self.ar.legend(loc=0)
        self.canvas.draw()
        self.resizeAllColumns()

        # make fit results to be global to export
        self.export_pars = pars
        self.export_out = out
        # for key in out.params:
        # print(key, "=", out.params[key].value)
        # make dataFrame and concat to export
        df_raw_x = pd.DataFrame(raw_x, columns=["raw_x"])
        df_raw_y = pd.DataFrame(raw_y, columns=["raw_y"])
        df_corrected_x = pd.DataFrame(x, columns=["corrected x"])
        df_y = pd.DataFrame(
            raw_y - sum_background - self.static_bg, columns=["data-bg"]
        )
        df_pks = pd.DataFrame(out.best_fit - sum_background, columns=["sum_components"])
        df_b = pd.DataFrame(sum_background + self.static_bg, columns=["bg"])
        df_residual = pd.DataFrame(out.residual, columns=["residual"])
        if isinstance(self.static_bg, int):
            df_b_static = pd.DataFrame(
                [0] * len(sum_background), columns=["bg_static (not used)"]
            )
            df_sum = pd.DataFrame(out.best_fit, columns=["sum_fit"])
        else:
            df_b_static = pd.DataFrame(self.static_bg, columns=["bg_static"])
            df_sum = pd.DataFrame(out.best_fit + self.static_bg, columns=["sum_fit"])
        self.result = pd.concat(
            [
                df_raw_x,
                df_raw_y,
                df_corrected_x,
                df_y,
                df_pks,
                df_b,
                df_b_static,
                df_sum,
                df_residual,
            ],
            axis=1,
        )
        df_bg_comps = pd.DataFrame.from_dict(self.bg_comps, orient="columns")
        self.result = pd.concat([self.result, df_bg_comps], axis=1)
        for index_pk in range(int(self.fitp1.columnCount() / 2)):
            strind = self.fitp1.cellWidget(0, 2 * index_pk + 1).currentText()
            strind = strind.split(":", 1)[0]
            df_c = pd.DataFrame(
                comps[strind + str(index_pk + 1) + "_"],
                columns=[self.fitp1.horizontalHeaderItem(2 * index_pk + 1).text()],
            )
            self.result = pd.concat([self.result, df_c], axis=1)
        print(out.fit_report())
        logging.info(out.fit_report())
        lim_reached = False
        at_zero = False
        for key in out.params:
            if (
                out.params[key].value == out.params[key].min
                or out.params[key].value == out.params[key].max
            ):
                if out.params[key].value != 0:
                    lim_reached = True
                    print("Limit reached for ", key)
                else:
                    at_zero = True
                    print(
                        key,
                        " is at limit. Value is at 0.0. That was probably intended and can be ignored!",
                    )

        if at_zero:
            self.set_status("at_zero")
        if lim_reached:
            self.set_status("limit_reached")
        # macOS's compatibility issue on pyqt5, add below to update window
        self.repaint()

    def center(self):
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def closeEvent(self, event):
        self.interrupt_fit()
        # Close settings dialog if open
        if self.settings_dialog is not None and self.settings_dialog.isVisible():
            self.settings_dialog.close()

        event.accept()
        sys.exit(0)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = PrettyWidget()
    sys.exit(app.exec_())
