from PyQt5 import QtWidgets
from helpers import *
from matplotlib.backends.backend_qt5agg import FigureCanvas, NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from periodictable import PeriodicTable

def setupWindow(parent):
    """Set up basic window properties."""
    parent.setGeometry(0, 0, parent.resolution[0], parent.resolution[1])
    parent.showNormal()
    parent.center()
    parent.setWindowTitle(parent.version)
    parent.statusBar().showMessage(
        'Copyright (C) 2022, Julian Hochhaus, TU Dortmund University'
    )



def setupMainWindow(parent):
    setupWindow(parent=parent)
    parent.pt = PeriodicTable()
    parent.pt.setWindowTitle('Periodic Table')

def initializeData(parent):
    parent.df = []
    parent.result = pd.DataFrame()
    parent.static_bg = 0
    parent.idx_imp = 0
    parent.idx_bg = [2]
    parent.idx_pres = 0

def createBottomLeftLayout(parent):
    layout = QtWidgets.QVBoxLayout()
    layout.addWidget(parent.toolbar)
    layout.addWidget(parent.canvas)
    return layout

def createMiddleLayout(parent):
    layout = QtWidgets.QVBoxLayout()

    componentbuttons_layout, parent.status_label, parent.status_text = createComponentButtons(parent)
    layout.addLayout(componentbuttons_layout)
    parent.pars_label = QtWidgets.QLabel()
    parent.pars_label.setText("Peak parameters:")
    parent.pars_label.setStyleSheet("font-weight: bold; font-size:12pt")
    layout.addWidget(parent.pars_label)

    parent.fitp1, parent.list_shape, parent.list_component, parent.fitp1_lims, list_col = createFitTables(parent)
    initializePresets(parent)
    layout.addWidget(parent.fitp1)

    return layout, list_col

def setupSecondWindow(parent, bottom_layout):
    parent.second_window = QtWidgets.QMainWindow()
    parent.second_window.setGeometry(0, 0, parent.resolution[0], parent.resolution[1])
    parent.second_window.setWindowTitle(parent.version + '-second screen-')

    second_window_layout = QtWidgets.QVBoxLayout()
    central_widget = QtWidgets.QWidget(parent.second_window)
    central_widget.setLayout(second_window_layout)
    parent.second_window.setCentralWidget(central_widget)

    second_window_layout.addLayout(bottom_layout, 6)
    parent.second_window.showNormal()

def createTopLeftLayout(parent):
    """Create the top-left layout with buttons, dropdowns, and plot settings."""
    layout_top_left = QtWidgets.QVBoxLayout()

    # Add Fit Buttons
    fitbuttons_layout, parent.fit_buttons = createFitButtons(parent)
    layout_top_left.addLayout(fitbuttons_layout)

    # Dropdown menu for file list
    parent.list_file = ['File list', 'Clear list']
    parent.comboBox_file = QtWidgets.QComboBox(parent)
    parent.comboBox_file.addItems(parent.list_file)
    parent.comboBox_file.currentIndexChanged.connect(parent.value_change_filelist)
    layout_top_left.addWidget(parent.comboBox_file)

    # Horizontal line separator
    layout_top_left.addWidget(LayoutHline())

    # Plot title input form
    plottitle_form = QtWidgets.QFormLayout()
    parent.plottitle = QtWidgets.QLineEdit()
    plottitle_form.addRow("Plot title: ", parent.plottitle)

    # Add plot settings form
    plot_settings_layout = createPlotSettingsForm(parent=parent)

    layout_top_left.addLayout(plottitle_form)
    layout_top_left.addLayout(plot_settings_layout)

    # Add stretch for alignment
    layout_top_left.addStretch(1)

    return layout_top_left


def createBottomRightLayout(parent, list_col):
    """
    Create result and statistics tables.

    """
    layout_bottom_right = QtWidgets.QVBoxLayout()

    # Result Table Section
    parent.res_label = QtWidgets.QLabel("Fit results:")
    parent.res_label.setStyleSheet("font-weight: bold; font-size:12pt")
    parent.res_tab = createResultTable(parent, list_col)

    # Add result label and table to layout
    layout_bottom_right.addWidget(parent.res_label)
    layout_bottom_right.addWidget(parent.res_tab)

    # Statistics Table Section
    parent.stats_label = QtWidgets.QLabel("Fit statistics:")
    parent.stats_label.setStyleSheet("font-weight: bold; font-size:12pt")
    parent.stats_tab = createStatsTable()

    # Add stats label and table to layout
    layout_bottom_right.addWidget(parent.stats_label)
    layout_bottom_right.addWidget(parent.stats_tab)

    return layout_bottom_right

    return layout_bottom_right


def createBackgroundLayout(parent, dictBG):
    #Create layout for background configuration.

    # Create a horizontal layout for background settings
    bg_fixed_layout = QtWidgets.QHBoxLayout()

    # Create checkbox for "Keep background fixed"
    fixedBG_checkbox = QtWidgets.QCheckBox('Keep background fixed')
    parent.fixedBG = fixedBG_checkbox

    # Create label to display chosen backgrounds
    displayChosenBG_label = QtWidgets.QLabel()
    displayChosenBG_label.setText(
        'Choosen Background: {}'.format('+ '.join([dictBG[str(idx)] for idx in parent.idx_bg]))
    )
    displayChosenBG_label.setStyleSheet("font-weight: bold")
    parent.displayChoosenBG = displayChosenBG_label  # Assign to parent for later use

    # Add widgets to the layout
    bg_fixed_layout.addWidget(displayChosenBG_label)
    bg_fixed_layout.addWidget(fixedBG_checkbox)

    return bg_fixed_layout


def createTopRowLayout(parent, dictBG):
    #Create top row layout for the UI.
    # Create the top-left layout (buttons, dropdowns, etc.)
    layout_top_left = createTopLeftLayout(parent)

    layout_top_mid = QtWidgets.QVBoxLayout()

    parent.fitp0 = createBGTable(parent, dictBG)  # Fit table for background
    bg_fixed_layout = createBackgroundLayout(parent, dictBG)  # Background configuration

    layout_top_mid.addWidget(parent.fitp0)  # Add fit table widget
    layout_top_mid.addLayout(bg_fixed_layout)  # Add background settings

    toprow_layout = QtWidgets.QHBoxLayout()
    toprow_layout.addLayout(layout_top_left, 4)  # Add top-left section
    toprow_layout.addLayout(layout_top_mid, 4)  # Add top-mid section

    return toprow_layout
def setupCanvas(parent):
    ##Set up the matplotlib canvas and navigation toolbar.
    figure, (ar, ax) = plt.subplots(
        2,
        sharex=True,
        gridspec_kw={'height_ratios': [1, 5], 'hspace': 0}
    )

    # Create the canvas for displaying the figure
    canvas = FigureCanvas(figure)

    # Create the navigation toolbar to interact with the plot
    toolbar = NavigationToolbar(canvas, parent)

    # Style the toolbar
    toolbar.setMaximumHeight(20)
    toolbar.setMinimumHeight(15)
    toolbar.setStyleSheet("QToolBar { border: 0px }")

    return figure, ar, ax, canvas, toolbar
def createFitButtons(parent):
    """Create fit-related buttons and returns both layout and button references."""
    layout = QtWidgets.QHBoxLayout()
    btn_fit = QtWidgets.QPushButton('Fit', parent)
    btn_fit.clicked.connect(parent.fit)

    btn_eva = QtWidgets.QPushButton('Evaluate', parent)
    btn_eva.clicked.connect(parent.eva)

    btn_undoFit = QtWidgets.QPushButton('Undo Fit', parent)
    btn_undoFit.clicked.connect(parent.one_step_back_in_params_history)

    btn_interrupt = QtWidgets.QPushButton('Interrupt fitting', parent)
    btn_interrupt.clicked.connect(parent.interrupt_fit)

    for button in [btn_fit, btn_eva, btn_undoFit, btn_interrupt]:
        button.resize(button.sizeHint())
        layout.addWidget(button)

    return layout, {
        'btn_fit': btn_fit,
        'btn_eva': btn_eva,
        'btn_undoFit': btn_undoFit,
        'btn_interrupt': btn_interrupt,
    }
def createComponentButtons(parent):
    """Create add/remove component and limits buttons and limits status indicator and returns both layout and limit status/text."""
    layout = QtWidgets.QHBoxLayout()
    # Add Button
    btn_add = QtWidgets.QPushButton('add component', parent)
    btn_add.resize(btn_add.sizeHint())
    btn_add.clicked.connect(parent.add_col)
    layout.addWidget(btn_add)
    # Remove Button
    btn_rem = QtWidgets.QPushButton('rem component', parent)
    btn_rem.resize(btn_rem.sizeHint())
    btn_rem.clicked.connect(lambda: parent.removeCol(idx=None,text=None ))
    layout.addWidget(btn_rem)

    btn_limit_set = QtWidgets.QPushButton('&Set/Show Limits', parent)
    btn_limit_set.resize(btn_limit_set.sizeHint())
    btn_limit_set.clicked.connect(parent.setLimits)
    layout.addWidget(btn_limit_set)

    # indicator for limits
    status_label = QtWidgets.QLabel()
    status_label.setFixedSize(18, 18)
    status_label.setAlignment(QtCore.Qt.AlignCenter)
    status_label.setStyleSheet("background-color: grey; border-radius: 9px")

    # Create a QLabel for the status text
    status_text = QtWidgets.QLabel("Limits not used")
    status_text.setAlignment(QtCore.Qt.AlignLeft)
    status_text.setAlignment(QtCore.Qt.AlignVCenter)

    # Create a QVBoxLayout to hold the status widgets
    status_layout = QtWidgets.QHBoxLayout()
    status_layout.addWidget(status_label)
    status_layout.addWidget(status_text)
    status_layout.setAlignment(QtCore.Qt.AlignVCenter)
    layout.addLayout(status_layout)
    layout.setAlignment(QtCore.Qt.AlignVCenter)
    return layout, status_label,status_text
def initializePresets(parent):
    """Initialize presets for background, peak, and other configurations."""
    # Prepopulate default values for BG table
    pre_bg = [['', 1e-06, '', 10, 2, 0.0003, 2, 1000, '', ''],
              [2, 2866.0, '', 1643.0, '', 1.0, '', 1.0, '', 50],
              [2, 0, 2, 0, 2, 0, 2, 0, 2, 0],
              [2, 0.0, '', '', '', '', '', '', '', '', '']]

    # Default values for peak presets
    pre_pk = [[0, 0], [2, 284.6], [0, 20000], [2, 0.2], [2, 0.2], [2, 0.02], [2, 0], [2, 0], [2, 0.0], [2, 0.026],
              [2, 1], [2, 0.7], [2, 1], [0, 0], [2, 0.1], [0, 0], [2, 0.5], [0, 0], [2, 1], [0, 0], [2, 1],
              [0, 0], [2, 1], [0, 0], [2, 1], [0, 0], [2, 1]]

    # Default preset configuration
    parent.pre = [
        [
            parent.idx_bg,
            parent.xmin,
            parent.xmax,
            parent.hv,
            parent.wf,
            parent.correct_energy
        ],
        pre_bg,
        pre_pk,
        [[0, '', '']] * 19
    ]

    # Apply presets using setPreset method
    parent.setPreset(parent.pre[0], parent.pre[1], parent.pre[2], parent.pre[3])
def createPlotSettingsForm(parent):
    """Create the plot settings form layout and assign fields directly to parent."""
    plot_settings_layout = QtWidgets.QHBoxLayout()

    def add_form_row(label_text, default_value, attr_name):
        """Helper to create a labeled row with a DoubleLineEdit and assign it to parent."""
        # Initialize the numerical value as an attribute of parent
        setattr(parent, attr_name, default_value)

        # Create a DoubleLineEdit widget
        form = QtWidgets.QFormLayout()
        line_edit = DoubleLineEdit()
        line_edit.setText(str(default_value))

        # Synchronize changes in the widget with the parent's attribute
        def update_parent_value(value):
            try:
                setattr(parent, attr_name, float(value))  # Update value dynamically
            except ValueError:
                setattr(parent, attr_name, default_value)  # Revert on invalid input

        line_edit.textChanged.connect(update_parent_value)

        form.addRow(label_text + ": ", line_edit)

        # Assign the widget itself as an additional attribute of parent
        setattr(parent, f"{attr_name}_item", line_edit)

        return form

    # Create individual rows for each setting and assign them as attributes
    plot_settings_layout.addLayout(add_form_row("x_min", 270, "xmin"))
    plot_settings_layout.addLayout(add_form_row("x_max", 300, "xmax"))
    plot_settings_layout.addLayout(add_form_row("hv", 1486.6, "hv"))
    plot_settings_layout.addLayout(add_form_row("wf", 4, "wf"))
    plot_settings_layout.addLayout(add_form_row("shift energy", 0, "correct_energy"))

    return plot_settings_layout

def createBGTable(parent, dictBG):
    """Create PolyBG Table (fitp0) and fixed background layout."""
    # Define row and column labels
    list_bg_col = ['bg_c0', 'bg_c1', 'bg_c2', 'bg_c3', 'bg_c4']
    list_bg_row = [
        'Shirley (cv, it, k, c)',
        'Tougaard(B, C, C*, D, extend)',
        'Polynomial',
        'Slope(k)',
        'arctan (amp, ctr, sig)',
        'erf (amp, ctr, sig)',
        'cutoff (ctr, d1-4)'
    ]

    # Create QTableWidget for PolyBG
    fitp0 = QtWidgets.QTableWidget(len(list_bg_row), len(list_bg_col) * 2)
    fitp0.setItemDelegate(parent.delegate)

    # Set headers
    list_bg_colh = ['', 'bg_c0', '', 'bg_c1', '', 'bg_c2', '', 'bg_c3', '', 'bg_c4']
    fitp0.setHorizontalHeaderLabels(list_bg_colh)
    fitp0.setVerticalHeaderLabels(list_bg_row)

    # Populate table with checkboxes or empty cells based on conditions
    for row in range(len(list_bg_row)):
        for col in range(len(list_bg_colh)):
            item = QtWidgets.QTableWidgetItem()
            if (
                (row == 2 or row > 3 or (row == 3 and col < 2) or
                 (row == 0 and 8 > col >= 4) or
                 (row == 1 and col == 0)) and col % 2 == 0
            ):
                item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.Unchecked)
                item.setToolTip('Check to keep fixed during fit procedure')
            else:
                item.setText('')
            fitp0.setItem(row, col, item)

    return fitp0

def createFitTables(parent):
    list_col = ['C_1']
    list_row = ['model', 'center', 'amplitude', 'lorentzian (sigma/gamma)', 'gaussian(sigma)', 'asymmetry(gamma)',
                'frac', 'skew', 'q', 'kt', 'soc',
                'height_ratio',
                'fct_coster_kronig', 'center_ref', 'ctr_diff', 'amp_ref', 'ratio', 'lorentzian_ref', 'ratio',
                'gaussian_ref', 'ratio',
                'asymmetry_ref', 'ratio', 'soc_ref', 'ratio', 'height_ref', 'ratio']

    def comps_edit_condition(logicalIndex):
        return logicalIndex % 2 != 0

    fitp1 = RemoveAndEditTableWidget(len(list_row), len(list_col) * 2, comps_edit_condition)
    fitp1.headerTextChanged.connect(parent.updateHeader_lims)
    fitp1.removeOptionChanged.connect(parent.removeCol)
    fitp1.setItemDelegate(parent.delegate)
    list_colh = ['', 'C_1']
    fitp1.setHorizontalHeaderLabels(list_colh)
    fitp1.setVerticalHeaderLabels(list_row)
    list_shape = ['g: Gaussian', 'l: Lorentzian', 'v: Voigt', 'p: PseudoVoigt', 'e: ExponentialGaussian',
                       's: SkewedGaussian', 'a: SkewedVoigt', 'b: BreitWigner', 'n: Lognormal', 'd: Doniach',
                       'gdd: Convolution Gaussian/Doniach-Dublett', 'gds: Convolution Gaussian/Doniach-Singlett',
                       'fe:Convolution FermiDirac/Gaussian']
    list_component = ['', 'C_1']

    # set DropDown component model
    for col in range(len(list_col)):
        comboBox = QtWidgets.QComboBox()
        comboBox.addItems(list_shape)
        # comboBox.setMaximumWidth(55)
        fitp1.setCellWidget(0, 2 * col + 1, comboBox)
    # set DropDown ctr_ref component selection
    for i in range(7):
        for col in range(len(list_col)):
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(list_component)
            comboBox.setMaximumWidth(55)
            fitp1.setCellWidget(13 + 2 * i, 2 * col + 1, comboBox)

    # set checkbox and dropdown in fit table
    for row in range(len(list_row)):
        for col in range(len(list_colh)):
            if col % 2 == 0:
                item = QtWidgets.QTableWidgetItem()
                item.setToolTip('Check to keep fixed during fit procedure')
                item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                if 0 < row < 13:
                    item.setCheckState(QtCore.Qt.Checked)
                    fitp1.setItem(row, col, item)
                if 13 <= row:
                    if row % 2 == 0:
                        item.setCheckState(QtCore.Qt.Unchecked)
                        fitp1.setItem(row, col, item)
                    else:
                        item = QtWidgets.QTableWidgetItem()
                        item.setText('')
                        fitp1.setItem(row, col, item)
            elif col % 2 != 0 and (row == 0 or (12 <= row and row % 2 == 1)):
                comboBox = QtWidgets.QComboBox()
                if row == 0:
                    comboBox.addItems(list_shape)
                    comboBox.currentTextChanged.connect(parent.activeParameters)
                else:
                    comboBox.addItems(list_component)
                fitp1.setCellWidget(row, col, comboBox)
            else:
                item = QtWidgets.QTableWidgetItem()
                item.setText('')
                fitp1.setItem(row, col, item)
    list_row_limits = [
        'center', 'amplitude', 'lorentzian (sigma/gamma)', 'gaussian(sigma)', 'asymmetry(gamma)', 'frac', 'skew',
        'q', 'kt', 'soc',
        'height', "fct_coster_kronig", 'ctr_diff', 'amp_ratio', 'lorentzian_ratio', 'gaussian_ratio',
        'asymmetry_ratio', 'soc_ratio', 'height_ratio']
    list_colh_limits = ['C_1', 'min', 'max']

    def lims_edit_condition(logicalIndex):
        return logicalIndex % 3 == 0

    fitp1_lims = EditableHeaderTableWidget(len(list_row_limits), len(list_col) * 3, lims_edit_condition)
    fitp1_lims.headerTextChanged.connect(parent.updateHeader_comps)
    fitp1_lims.setItemDelegate(parent.delegate)

    fitp1_lims.setHorizontalHeaderLabels(list_colh_limits)
    fitp1_lims.setVerticalHeaderLabels(list_row_limits)
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
            fitp1_lims.setItem(row, col, item)
    fitp1_lims.cellChanged.connect(parent.lims_changed)
    fitp1_lims.setHeaderTooltips()
    fitp1.setHeaderTooltips()
    return fitp1, list_shape, list_component, fitp1_lims, list_col


def createResultTable(parent, list_col):
    """Create the results table (res_tab)."""
    list_res_row = ['gaussian_fwhm', 'lorentzian_fwhm_p1', 'lorentzian_fwhm_p2', 'fwhm_p1', 'fwhm_p2', 'height_p1',
                    'height_p2', 'approx. area_p1', 'approx. area_p2', 'area_total']
    def res_edit_condition(logicalIndex):
        return logicalIndex % 1 == 0  # Editable condition for rows/columns

    # Create the EditableHeaderTableWidget for results
    res_tab = EditableHeaderTableWidget(len(list_res_row), len(list_col), res_edit_condition)

    # Set headers
    res_tab.setHorizontalHeaderLabels(list_col)
    res_tab.setVerticalHeaderLabels(list_res_row)

    # Connect signals if needed
    res_tab.headerTextChanged.connect(parent.updateHeader_res)

    return res_tab


def createStatsTable():
    """Create the statistics table (stats_tab)."""
    list_stats_row = ['success?', 'message', 'nfev', 'nvary', 'ndata', 'nfree', 'chisqr', 'redchi', 'aic', 'bic']
    list_stats_col = ['Fit stats']
    stats_tab = QtWidgets.QTableWidget(len(list_stats_row), len(list_stats_col))

    # Set headers
    stats_tab.setHorizontalHeaderLabels(list_stats_col)
    stats_tab.setVerticalHeaderLabels(list_stats_row)

    return stats_tab
