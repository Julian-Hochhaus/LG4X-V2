from PyQt5 import QtWidgets
from helpers import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from periodictable import PeriodicTable
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QMenu, QComboBox, QWidget, QHBoxLayout, QWidgetAction,QSpacerItem, QSizePolicy, QDockWidget
from PyQt5.QtCore import Qt
import qdarktheme

def setupWindow(parent):
    """Set up basic window properties."""
    screen_index = config.getint('GUI', 'main_window_screen', fallback=0)
    screens = QtWidgets.QApplication.screens()

    if screen_index >= len(screens):
        screen_index = 0  # fallback if monitor is unplugged

    screen_geometry = screens[screen_index].availableGeometry()
    x = screen_geometry.x() + (screen_geometry.width() - parent.resolution[0]) // 2
    y = screen_geometry.y() + (screen_geometry.height() - parent.resolution[1]) // 2
    parent.setGeometry(x, y, parent.resolution[0], parent.resolution[1])

    parent.setWindowTitle(parent.version)
    parent.statusBar().showMessage(
        'Copyright (C) 2022, Julian Hochhaus, TU Dortmund University'
    )
    parent.showNormal()  # Only show after geometry is set


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
    parent.bgMenu = menubar.addMenu('&Choose BG')

    parent.btn_bg_shirley_act = QtWidgets.QAction('&Active &Shirley BG', parent)
    parent.btn_bg_shirley_act.setCheckable(True)
    parent.btn_bg_shirley_act.triggered.connect(parent.clickOnBtnBG)
    parent.bgMenu.addAction(parent.btn_bg_shirley_act)

    parent.btn_bg_shirley_static = QtWidgets.QAction('&Static &Shirley BG', parent)
    parent.btn_bg_shirley_static.setCheckable(True)
    parent.btn_bg_shirley_static.triggered.connect(parent.clickOnBtnBG)
    parent.bgMenu.addAction(parent.btn_bg_shirley_static)

    parent.btn_bg_tougaard_act = QtWidgets.QAction('&Active &Tougaard BG', parent)
    parent.btn_bg_tougaard_act.setCheckable(True)
    parent.btn_bg_tougaard_act.triggered.connect(parent.clickOnBtnBG)
    parent.bgMenu.addAction(parent.btn_bg_tougaard_act)

    parent.btn_bg_tougaard_static = QtWidgets.QAction('&Static &Tougaard BG', parent)
    parent.btn_bg_tougaard_static.setCheckable(True)
    parent.btn_bg_tougaard_static.triggered.connect(parent.clickOnBtnBG)
    parent.bgMenu.addAction(parent.btn_bg_tougaard_static)

    parent.btn_bg_polynomial = QtWidgets.QAction('&Polynomial BG', parent)
    parent.btn_bg_polynomial.setCheckable(True)
    parent.btn_bg_polynomial.setShortcut('Ctrl+Alt+P')
    parent.btn_bg_polynomial.triggered.connect(parent.clickOnBtnBG)
    parent.bgMenu.addAction(parent.btn_bg_polynomial)

    parent.btn_bg_slope = QtWidgets.QAction('&Slope BG', parent)
    parent.btn_bg_slope.setCheckable(True)
    parent.btn_bg_slope.setShortcut('Ctrl+Alt+S')
    parent.btn_bg_slope.triggered.connect(parent.clickOnBtnBG)
    parent.bgMenu.addAction(parent.btn_bg_slope)

    parent.btn_bg_arctan = QtWidgets.QAction('&Arctan BG', parent)
    parent.btn_bg_arctan.setCheckable(True)
    parent.btn_bg_arctan.triggered.connect(parent.clickOnBtnBG)
    parent.bgMenu.addAction(parent.btn_bg_arctan)

    parent.btn_bg_erf = QtWidgets.QAction('&Erf BG', parent)
    parent.btn_bg_erf.setCheckable(True)
    parent.btn_bg_erf.triggered.connect(parent.clickOnBtnBG)
    parent.bgMenu.addAction(parent.btn_bg_erf)

    parent.btn_bg_vbm = QtWidgets.QAction('&VBM/Cutoff BG', parent)
    parent.btn_bg_vbm.setCheckable(True)
    parent.btn_bg_vbm.triggered.connect(parent.clickOnBtnBG)
    parent.bgMenu.addAction(parent.btn_bg_vbm)

    # Tougaard Cross Section Action
    btn_tougaard_cross_section = QtWidgets.QAction('Tougaard &Cross Section', parent)
    btn_tougaard_cross_section.triggered.connect(parent.clicked_cross_section)

    parent.bgMenu.addSeparator()
    parent.bgMenu.addAction(btn_tougaard_cross_section)

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

    # Add theme switcher to the right corner
    theme_menu = menubar.addMenu("Switch Theme")  # Empty title

    # Create the theme combo box layout
    theme_widget = QWidget()
    theme_layout = QHBoxLayout(theme_widget)
    theme_layout.setContentsMargins(0, 0, 0, 0)  # No margins


    parent.theme_combo = QComboBox()
    parent.theme_combo.addItems(qdarktheme.get_themes())
    parent.theme_combo.setCurrentText('dark')
    parent.current_theme = 'dark'
    parent.theme_combo.currentTextChanged.connect(qdarktheme.setup_theme)
    parent.theme_combo.currentTextChanged.connect(lambda theme: on_theme_changed(parent, theme))
    parent.theme_combo.setMinimumWidth(100)
    theme_layout.addWidget(parent.theme_combo)

    # Create a QWidgetAction and set the theme widget
    theme_action = QWidgetAction(parent)
    theme_action.setDefaultWidget(theme_widget)

    # Add the theme switcher to the menu
    theme_menu.addAction(theme_action)

    # Set initial theme
    qdarktheme.setup_theme('dark')

def on_theme_changed(parent, theme_name):
    qdarktheme.setup_theme(theme_name)
    update_matplotlib_style(parent,theme_name)
    parent.current_theme = theme_name

    # IMPORTANT: redraw your plot after changing style
    #parent.plot()


def update_matplotlib_style(parent, theme):
    import matplotlib.pyplot as plt

    # Define colors based on theme
    if theme == 'dark':
        plt.style.use('dark_background')
        background_color = '#121212'
        text_color = 'white'
        grid_color = 'white'
    else:
        plt.style.use('default')
        background_color = 'white'
        text_color = 'black'
        grid_color = 'black'

    # Get the current figure
    fig = parent.canvas.figure

    # Iterate over all axes in the figure
    for ax in fig.get_axes():
        current_lines = ax.get_lines()
        ax.cla()

        # Apply the new style to the axis
        ax.set_facecolor(background_color)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.title.set_color(text_color)
        ax.tick_params(axis='x', colors=text_color)
        ax.tick_params(axis='y', colors=text_color)
        ax.spines['bottom'].set_color(text_color)
        ax.spines['top'].set_color(text_color)
        ax.spines['left'].set_color(text_color)
        ax.spines['right'].set_color(text_color)

        # Set grid color for the axis
        ax.grid(True, color=grid_color)

        # Reapply figure background color
        fig.patch.set_facecolor(background_color)

        # Get all current lines in the axis

        for line, color in zip(current_lines,get_current_style_colors(len(current_lines))) :
            ax.plot(line.get_xdata(), line.get_ydata(), linestyle=line.get_linestyle(), color=color,
                    label=line.get_label())


        # Reapply the legend if it exists
        ax.legend(loc='best')

    # Redraw the canvas to apply changes
    parent.canvas.draw()
def get_current_style_colors(num_colors):
    # Get the current color cycle from rcParams
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

    # Return the first 'num_colors' from the color cycle
    return colors[:num_colors]

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
    parent.pars_label.setStyleSheet("font-weight: bold")
    layout.addWidget(parent.pars_label)

    parent.fitp1, parent.list_shape, parent.list_component, parent.fitp1_lims, list_col = createFitTables(parent)
    initializePresets(parent)
    layout.addWidget(parent.fitp1)

    return layout, list_col

def setupSecondWindow(self, config,bottom_layout):
    # --- Cleanup any existing second window ---
    if hasattr(self, 'second_window') and self.second_window is not None:
        self.second_window.close()
        self.second_window.deleteLater()
        self.second_window = None

    # --- Create a fresh second window ---
    self.second_window = QtWidgets.QMainWindow(self)
    self.second_window.setWindowTitle(f"{self.version} - Second Screen")

    # Apply window size from config or fallback defaults
    width = config.getint('GUI', 'second_window_width', fallback=600)
    height = config.getint('GUI', 'second_window_height', fallback=400)
    self.second_window.setGeometry(0, 0, width, height)

    # --- Set up the second window layout ---
    second_window_layout = QtWidgets.QVBoxLayout()
    central_widget = QtWidgets.QWidget(self.second_window)
    central_widget.setLayout(second_window_layout)
    self.second_window.setCentralWidget(central_widget)

    # Add the layout passed as argument (bottom_layout)
    second_window_layout.addLayout(bottom_layout, 6)
    screens = QtWidgets.QApplication.screens()

    if len(screens) > 1:
        second_screen = screens[1]
        screen_geometry = second_screen.availableGeometry()

        # Move the second window to the second screen before showing
        self.second_window.move(screen_geometry.topLeft())

        # Maximize the window after it's moved
        self.second_window.showMaximized()
    else:
        # Fallback: place and maximize on primary screen
        screen_geometry = screens[0].availableGeometry()
        self.second_window.move(screen_geometry.topLeft())
        self.second_window.showMaximized()

    def second_window_close_event(event):
        # Optional: Clean up other things first if needed
        QtWidgets.QApplication.quit()  # or sys.exit(0)

    self.second_window.closeEvent = second_window_close_event
    # Ensure second window closes when the main window closes
    self.destroyed.connect(lambda: self.second_window.close())



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
    parent.res_label.setStyleSheet("font-weight: bold")
    parent.res_tab = createResultTable(parent, list_col)

    # Add result label and table to layout
    layout_bottom_right.addWidget(parent.res_label)
    layout_bottom_right.addWidget(parent.res_tab)

    # Statistics Table Section
    parent.stats_label = QtWidgets.QLabel("Fit statistics:")
    parent.stats_label.setStyleSheet("font-weight: bold")
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
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar

    # Use parent's tracked theme
    is_dark_mode = 'dark' in parent.current_theme.lower()

    if is_dark_mode:
        plt.style.use('dark_background')
    else:
        plt.style.use('default')

    figure, (ar, ax) = plt.subplots(
        2,
        sharex=True,
        gridspec_kw={'height_ratios': [1, 5], 'hspace': 0}
    )

    canvas = FigureCanvas(figure)
    toolbar = NavigationToolbar(canvas, parent)
    toolbar.setMaximumHeight(24)
    toolbar.setMinimumHeight(18)
    toolbar.setIconSize(QtCore.QSize(20, 20))  # Increase icon size
    toolbar.setStyleSheet("QToolBar { border: 0px }")

    return figure, ar, ax, canvas, toolbar
def is_dark_mode(parent):
    return 'dark' in parent.current_theme.lower()

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



class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, mainGUI, config, config_file_path, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Settings")
        self.config = config
        config.read(config_file_path)
        self.config_file_path = config_file_path
        self.main_gui = mainGUI

        label_column_width = QtWidgets.QLabel("Column Width:")
        self.line_edit_column_width = QtWidgets.QLineEdit()
        current_column_width = config.getint('GUI', 'column_width')
        self.line_edit_column_width.setText(str(current_column_width))
        apply_column_button = QtWidgets.QPushButton("Apply Column width")
        apply_column_button.clicked.connect(self.apply_to_main)

        # GUI settings

        self.checkbox_two_window_mode = QtWidgets.QCheckBox("Two Window Mode")
        self.checkbox_two_window_mode.setChecked(config.getboolean('GUI', 'two_window_mode'))
        apply_window_mode_button = QtWidgets.QPushButton("Apply Window Mode Now")
        apply_window_mode_button.clicked.connect(self.apply_window_mode_to_main)

        label_resolution_width = QtWidgets.QLabel("Resolution Width:")
        label_resolution_width.setToolTip("Set the width of the main window.")
        self.line_edit_resolution_width = QtWidgets.QLineEdit()
        self.line_edit_resolution_width.setText(str(config.getint('GUI', 'resolution_width')))

        label_resolution_height = QtWidgets.QLabel("Resolution Height:")
        label_resolution_height.setToolTip("Set the height of the main window.")
        self.line_edit_resolution_height = QtWidgets.QLineEdit()
        self.line_edit_resolution_height.setText(str(config.getint('GUI', 'resolution_height')))
        label_second_window_width = QtWidgets.QLabel("Second Window Width:")
        self.line_edit_second_window_width = QtWidgets.QLineEdit()
        current_second_window_width = self.config.getint('GUI', 'second_window_width', fallback=600)
        self.line_edit_second_window_width.setText(str(current_second_window_width))

        label_second_window_height = QtWidgets.QLabel("Second Window Height:")
        self.line_edit_second_window_height = QtWidgets.QLineEdit()
        current_second_window_height = self.config.getint('GUI', 'second_window_height', fallback=400)
        self.line_edit_second_window_height.setText(str(current_second_window_height))


        apply_resolution_button = QtWidgets.QPushButton("Apply Window Size Now")
        apply_resolution_button.clicked.connect(self.apply_resolution_to_main)

        # File import settings
        label_file_settings = QtWidgets.QLabel("Import settings, applied when opening a file.")
        label_separator = QtWidgets.QLabel("Separator:")
        self.line_edit_separator = QtWidgets.QLineEdit()
        self.line_edit_separator.setText(config.get('Import', 'separator'))

        label_columns = QtWidgets.QLabel("Columns (Format e.g.: [0,1]):")
        self.line_edit_columns = QtWidgets.QLineEdit()
        self.line_edit_columns.setText(str(config.get('Import', 'columns')))

        label_header_row = QtWidgets.QLabel("Header Row (or Rows to skip):")
        self.line_edit_header_row = QtWidgets.QLineEdit()
        self.line_edit_header_row.setText(str(config.getint('Import', 'header_row')))

        self.checkbox_has_header = QtWidgets.QCheckBox("Has Header")
        self.checkbox_has_header.setChecked(config.getboolean('Import', 'has_header'))

        self.checkbox_remember_settings = QtWidgets.QCheckBox("No Preview dialogue on file open\n (unset to get Preview Dialog)")
        self.checkbox_remember_settings.setChecked(config.getboolean('Import', 'remember_settings'))

        save_button = QtWidgets.QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)

        # Layouts
        gui_layout = QtWidgets.QVBoxLayout()
        gui_layout_dynamic = QtWidgets.QVBoxLayout()
        layout_column_width = QtWidgets.QHBoxLayout()
        gui_layout_dynamic.addWidget(label_column_width)
        layout_column_width.addWidget(self.line_edit_column_width)
        layout_column_width.addWidget(apply_column_button)
        gui_layout_dynamic.addLayout(layout_column_width)

        gui_layout_static = QtWidgets.QVBoxLayout()
        gui_layout_static.addWidget(self.checkbox_two_window_mode)
        gui_layout_static.addWidget(apply_window_mode_button)
        gui_layout_static.addWidget(label_resolution_width)
        gui_layout_static.addWidget(self.line_edit_resolution_width)
        gui_layout_static.addWidget(label_resolution_height)
        gui_layout_static.addWidget(self.line_edit_resolution_height)

        gui_layout_static.addWidget(label_second_window_width)
        gui_layout_static.addWidget(self.line_edit_second_window_width)
        gui_layout_static.addWidget(label_second_window_height)
        gui_layout_static.addWidget(self.line_edit_second_window_height)

        gui_layout_static.addWidget(apply_resolution_button)

        gui_layout.addLayout(gui_layout_dynamic)
        gui_layout.addWidget(LayoutHline())
        gui_layout.addLayout(gui_layout_static)

        import_layout = QtWidgets.QVBoxLayout()
        import_layout.addWidget(label_file_settings)
        import_layout.addWidget(label_separator)
        import_layout.addWidget(self.line_edit_separator)
        import_layout.addWidget(label_columns)
        import_layout.addWidget(self.line_edit_columns)
        import_layout.addWidget(label_header_row)
        import_layout.addWidget(self.line_edit_header_row)
        import_layout.addWidget(self.checkbox_has_header)
        import_layout.addWidget(self.checkbox_remember_settings)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(gui_layout)
        main_layout.addWidget(LayoutHline())
        main_layout.addLayout(import_layout)
        main_layout.addWidget(LayoutHline())
        main_layout.addWidget(save_button)
        self.setLayout(main_layout)

    def save_settings(self):
        try:
            new_column_width = int(self.line_edit_column_width.text())
            if new_column_width > 0:
                self.config.set('GUI', 'column_width', str(new_column_width))
                self.main_gui.column_width = new_column_width
            else:
                self.main_gui.raise_error("Invalid Column Width", "Please enter a valid positive integer for column width.")

            self.config.set('GUI', 'two_window_mode', str(self.checkbox_two_window_mode.isChecked()))
            self.config.set('GUI', 'resolution_width', str(self.line_edit_resolution_width.text()))
            self.config.set('GUI', 'resolution_height', str(self.line_edit_resolution_height.text()))
            self.config.set('GUI', 'second_window_width', str(self.line_edit_second_window_width.text()))
            self.config.set('GUI', 'second_window_height', str(self.line_edit_second_window_height.text()))

            # Save Import settings
            self.config.set('Import', 'separator', self.line_edit_separator.text())
            self.config.set('Import', 'columns', str(self.line_edit_columns.text()))
            self.config.set('Import', 'header_row', str(self.line_edit_header_row.text()))
            self.config.set('Import', 'has_header', str(self.checkbox_has_header.isChecked()))
            self.config.set('Import', 'remember_settings', str(self.checkbox_remember_settings.isChecked()))

            with open(self.config_file_path, 'w') as config_file:
                self.config.write(config_file)

            self.accept()
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Saving settings failed", str(e))

    def apply_to_main(self):
        """Apply column width to the main GUI immediately."""
        self.main_gui.column_width = int(self.line_edit_column_width.text())
        for column in range(self.main_gui.fitp1.columnCount()):
            if column % 2 != 0:
                self.main_gui.fitp1.setColumnWidth(column, self.main_gui.column_width)
        for column in range(self.main_gui.fitp1_lims.columnCount()):
            if column % 3 != 0:
                self.main_gui.fitp1_lims.setColumnWidth(column, self.main_gui.column_width)
        for column in range(self.main_gui.res_tab.columnCount()):
            self.main_gui.res_tab.setColumnWidth(column, self.main_gui.column_width)

    def apply_window_mode_to_main(self):
        """Switch between single and two window mode dynamically."""
        self.main_gui.two_window_mode = self.checkbox_two_window_mode.isChecked()
        geometry = self.main_gui.saveGeometry()  # save current position
        self.main_gui.initUI()
        self.main_gui.restoreGeometry(geometry)

    def apply_resolution_to_main(self):
        """Apply new resolution to the main and second window immediately."""
        try:
            width = int(self.line_edit_resolution_width.text())
            height = int(self.line_edit_resolution_height.text())

            # Update main window resolution
            self.main_gui.resize(width, height)
            self.main_gui.update()

            # Update second window resolution (if it exists)
            if hasattr(self.main_gui, 'second_window') and self.main_gui.second_window is not None:
                self.main_gui.second_window.resize(width, height)
                self.main_gui.second_window.update()

        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid input", "Please enter valid numbers for resolution.")
