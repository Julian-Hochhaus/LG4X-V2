from PyQt5.QtWidgets import QWidget, QPushButton, QGridLayout, QLabel, QHBoxLayout
import pandas as pd
import os


data = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'elements.csv'))

class PeriodicTable(QWidget):
    def __init__(self):
        super().__init__()
        self.data = data
        self.selected_elements = []
        self.selected_elements_names = []
        self.selected_buttons=[]
        self.initUI()

    def initUI(self):
        self.grid = QGridLayout()
        self.grid.setSpacing(0)  # Remove spacing between buttons
        self.grid.setVerticalSpacing(0)
        self.grid.setHorizontalSpacing(0)
        for i in range(1, 8):
            for j in range(1, 19):
                symbol = self.data[(self.data['period'] == i) & (self.data['group_id'] == j)]['symbol'].values
                if len(symbol) > 0:
                    button = QPushButton(symbol[0], self)
                    button.clicked.connect(lambda checked,s=self.data[(self.data['period'] == i) & (self.data['group_id'] == j)]: self.toggleElementSelection(s))
                    cpk_color = \
                    self.data[(self.data['period'] == i) & (self.data['group_id'] == j)]['cpk_color'].values[0]
                    series_color = \
                        self.data[(self.data['period'] == i) & (self.data['group_id'] == j)]['series_color'].values[0]
                    button.setStyleSheet("background-color: %s" % series_color)
                    button.setMinimumHeight(50)
                    button.setMaximumWidth(80)
                    self.grid.addWidget(button, i, j)
                    self.grid.setRowMinimumHeight(i, 50)
        self.grid.setVerticalSpacing(0)
        self.grid.setHorizontalSpacing(0)
        self.setLayout(self.grid)
        self.setGeometry(100, 100, 600, 500)
        self.setWindowTitle('Clickable Periodic Table')


        self.refresh_button = QPushButton('Refresh', self)
        self.refresh_button.setStyleSheet("font-weight: bold; font-size: 16px")
        self.refresh_button.clicked.connect(self.updateSelectedElements)
        self.refresh_button.setMaximumHeight(50)
        self.grid.addWidget(self.refresh_button, 1, 5,2,3)

        self.clear_button = QPushButton('Clear', self)
        self.clear_button.setStyleSheet("font-weight: bold; font-size: 16px")
        self.clear_button.clicked.connect(self.clearSelection)
        self.clear_button.setMaximumHeight(50)
        self.grid.addWidget(self.clear_button, 1, 8,2,3)

        # create legend
        legend_layout = QHBoxLayout()
        legend = QLabel(self)
        legend.setText("<b>Legend:</b>")
        legend.setStyleSheet("font-size: 16px; margin-top: 20px")
        legend.move(50, 750)
        colors = self.data['series_color'].unique()

        # add legend labels for each color used in the periodic table
        for i, color in enumerate(colors):
            label = QLabel(self)
            label.setStyleSheet("background-color: %s; border: 1px solid black" % color)
            label.setFixedSize(30, 30)
            label.move(40 + i * 50, 780)
            legend_layout.addWidget(label)
            legend_text = QLabel(self)
            legend_text.setText(self.data[(self.data['series_color']==color)]['series_name'].values[0])
            legend_text.setStyleSheet("font-size: 16px; margin-top: 20px")
            legend_text.move(55 + i * 50, 785)
            legend_layout.addWidget(legend_text)
        self.grid.addLayout(legend_layout, 9, 1, 1, 18)
    def toggleElementSelection(self, element):
        if element['symbol'].values[0] in self.selected_elements_names:
            self.selected_elements_names.remove(element['symbol'].values[0])
            self.selected_elements.remove(element)
        else:
            self.selected_elements.append(element)
            self.selected_elements_names.append(element['symbol'].values[0])
        for i in range(1, 8):
            for j in range(1, 19):
                if self.grid.itemAtPosition(i, j) is not None:
                    symbol = self.data[(self.data['period'] == i) & (self.data['group_id'] == j)]['symbol'].values
                    button = self.grid.itemAtPosition(i, j).widget()
                    cpk_color = \
                        self.data[(self.data['period'] == i) & (self.data['group_id'] == j)]['cpk_color'].values[0]
                    series_color = \
                        self.data[(self.data['period'] == i) & (self.data['group_id'] == j)]['series_color'].values[0]
                    if symbol in self.selected_elements_names:
                        button.setStyleSheet("border: 3px solid #FF0000; font-weight: bold; color: #FF0000")
                    else:
                        button.setStyleSheet("background-color: %s" % series_color)
    def clearSelection(self):
        self.selected_elements = []
        self.selected_elements_names = []
        for i in range(1, 8):
            for j in range(1, 19):
                if self.grid.itemAtPosition(i, j) is not None:
                    button = self.grid.itemAtPosition(i, j).widget()
                    cpk_color = \
                        self.data[(self.data['period'] == i) & (self.data['group_id'] == j)]['cpk_color'].values[0]
                    series_color = \
                        self.data[(self.data['period'] == i) & (self.data['group_id'] == j)]['series_color'].values[0]
                    button.setStyleSheet("background-color: %s" % series_color)


    def updateSelectedElements(self):
        return self.selected_elements
