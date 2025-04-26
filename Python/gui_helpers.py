from PyQt5 import QtWidgets
from helpers import *
def createFitButtons(parent):
    """Create fit-related buttons and return both layout and button references."""
    layout = QtWidgets.QHBoxLayout()

    # Create buttons
    btn_fit = QtWidgets.QPushButton('Fit', parent)
    btn_fit.clicked.connect(parent.fit)

    btn_eva = QtWidgets.QPushButton('Evaluate', parent)
    btn_eva.clicked.connect(parent.eva)

    btn_undoFit = QtWidgets.QPushButton('Undo Fit', parent)
    btn_undoFit.clicked.connect(parent.one_step_back_in_params_history)

    btn_interrupt = QtWidgets.QPushButton('Interrupt fitting', parent)
    btn_interrupt.clicked.connect(parent.interrupt_fit)

    # Add buttons to layout
    for button in [btn_fit, btn_eva, btn_undoFit, btn_interrupt]:
        button.resize(button.sizeHint())
        layout.addWidget(button)

    # Return both layout and button references
    return layout, {
        'btn_fit': btn_fit,
        'btn_eva': btn_eva,
        'btn_undoFit': btn_undoFit,
        'btn_interrupt': btn_interrupt,
    }


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

    # Prepopulate default values for BG table
    pre_bg = [['', 1e-06, '', 10, 2, 0.0003, 2, 1000, '', ''],
              [2, 2866.0, '', 1643.0, '', 1.0, '', 1.0, '', 50],
              [2, 0, 2, 0, 2, 0, 2, 0, 2, 0],
              [2, 0.0, '', '', '', '', '', '', '', '', '']]
    # Fixed background layout
    bg_fixed_layout = QtWidgets.QHBoxLayout()

    # Create checkbox for "Keep background fixed"
    fixedBG_checkbox = QtWidgets.QCheckBox('Keep background fixed')
    parent.fixedBG = fixedBG_checkbox  # Assign to parent for later use

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

    return fitp0, bg_fixed_layout, pre_bg

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
