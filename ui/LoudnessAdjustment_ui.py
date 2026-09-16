# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'LoudnessAdjustment.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QDialog, QDoubleSpinBox, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_LoudnessAdjustment(object):
    def setupUi(self, LoudnessAdjustment):
        if not LoudnessAdjustment.objectName():
            LoudnessAdjustment.setObjectName(u"LoudnessAdjustment")
        LoudnessAdjustment.resize(960, 540)
        LoudnessAdjustment.setMinimumSize(QSize(760, 400))
        self.verticalLayout = QVBoxLayout(LoudnessAdjustment)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.toolsRow = QHBoxLayout()
        self.toolsRow.setObjectName(u"toolsRow")
        self.btnImportFiles = QPushButton(LoudnessAdjustment)
        self.btnImportFiles.setObjectName(u"btnImportFiles")

        self.toolsRow.addWidget(self.btnImportFiles)

        self.btnImportFolder = QPushButton(LoudnessAdjustment)
        self.btnImportFolder.setObjectName(u"btnImportFolder")

        self.toolsRow.addWidget(self.btnImportFolder)

        self.lblAnalyze = QLabel(LoudnessAdjustment)
        self.lblAnalyze.setObjectName(u"lblAnalyze")

        self.toolsRow.addWidget(self.lblAnalyze)

        self.btnAnalyzeSample = QPushButton(LoudnessAdjustment)
        self.btnAnalyzeSample.setObjectName(u"btnAnalyzeSample")

        self.toolsRow.addWidget(self.btnAnalyzeSample)

        self.btnAnalyzeObject = QPushButton(LoudnessAdjustment)
        self.btnAnalyzeObject.setObjectName(u"btnAnalyzeObject")

        self.toolsRow.addWidget(self.btnAnalyzeObject)

        self.btnAnalyzeAll = QPushButton(LoudnessAdjustment)
        self.btnAnalyzeAll.setObjectName(u"btnAnalyzeAll")

        self.toolsRow.addWidget(self.btnAnalyzeAll)

        self.toolsSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.toolsRow.addItem(self.toolsSpacer)


        self.verticalLayout.addLayout(self.toolsRow)

        self.settingsRow = QHBoxLayout()
        self.settingsRow.setObjectName(u"settingsRow")
        self.cbxSelectAll = QCheckBox(LoudnessAdjustment)
        self.cbxSelectAll.setObjectName(u"cbxSelectAll")
        self.cbxSelectAll.setChecked(True)

        self.settingsRow.addWidget(self.cbxSelectAll)

        self.selectAllSpacer = QSpacerItem(24, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.settingsRow.addItem(self.selectAllSpacer)

        self.lblLoudnessStandard = QLabel(LoudnessAdjustment)
        self.lblLoudnessStandard.setObjectName(u"lblLoudnessStandard")

        self.settingsRow.addWidget(self.lblLoudnessStandard)

        self.cbbLoudnessStandard = QComboBox(LoudnessAdjustment)
        self.cbbLoudnessStandard.addItem("")
        self.cbbLoudnessStandard.addItem("")
        self.cbbLoudnessStandard.setObjectName(u"cbbLoudnessStandard")
        self.cbbLoudnessStandard.setMinimumSize(QSize(120, 0))

        self.settingsRow.addWidget(self.cbbLoudnessStandard)

        self.lblTargetLoudness = QLabel(LoudnessAdjustment)
        self.lblTargetLoudness.setObjectName(u"lblTargetLoudness")

        self.settingsRow.addWidget(self.lblTargetLoudness)

        self.spbTargetLoudness = QDoubleSpinBox(LoudnessAdjustment)
        self.spbTargetLoudness.setObjectName(u"spbTargetLoudness")
        self.spbTargetLoudness.setDecimals(0)
        self.spbTargetLoudness.setMinimum(-60.000000000000000)
        self.spbTargetLoudness.setMaximum(0.000000000000000)
        self.spbTargetLoudness.setSingleStep(1.000000000000000)
        self.spbTargetLoudness.setValue(-18.000000000000000)

        self.settingsRow.addWidget(self.spbTargetLoudness)

        self.lblTolerance = QLabel(LoudnessAdjustment)
        self.lblTolerance.setObjectName(u"lblTolerance")

        self.settingsRow.addWidget(self.lblTolerance)

        self.spbTolerance = QDoubleSpinBox(LoudnessAdjustment)
        self.spbTolerance.setObjectName(u"spbTolerance")
        self.spbTolerance.setDecimals(1)
        self.spbTolerance.setMinimum(0.000000000000000)
        self.spbTolerance.setMaximum(20.000000000000000)
        self.spbTolerance.setSingleStep(0.500000000000000)
        self.spbTolerance.setValue(1.000000000000000)

        self.settingsRow.addWidget(self.spbTolerance)

        self.btnUnifyLoudness = QPushButton(LoudnessAdjustment)
        self.btnUnifyLoudness.setObjectName(u"btnUnifyLoudness")
        font = QFont()
        font.setBold(True)
        self.btnUnifyLoudness.setFont(font)

        self.settingsRow.addWidget(self.btnUnifyLoudness)

        self.settingsSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.settingsRow.addItem(self.settingsSpacer)


        self.verticalLayout.addLayout(self.settingsRow)

        self.tblAudioList = QTableWidget(LoudnessAdjustment)
        if (self.tblAudioList.columnCount() < 7):
            self.tblAudioList.setColumnCount(7)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblAudioList.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblAudioList.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblAudioList.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tblAudioList.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tblAudioList.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tblAudioList.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tblAudioList.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        self.tblAudioList.setObjectName(u"tblAudioList")
        self.tblAudioList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblAudioList.setAlternatingRowColors(True)
        self.tblAudioList.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.verticalLayout.addWidget(self.tblAudioList)


        self.retranslateUi(LoudnessAdjustment)

        QMetaObject.connectSlotsByName(LoudnessAdjustment)
    # setupUi

    def retranslateUi(self, LoudnessAdjustment):
        LoudnessAdjustment.setWindowTitle(QCoreApplication.translate("LoudnessAdjustment", u"\u54cd\u5ea6\u8c03\u6574", None))
        self.btnImportFiles.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u5bfc\u5165\u6587\u4ef6", None))
        self.btnImportFolder.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u5bfc\u5165\u6587\u4ef6\u5939", None))
        self.lblAnalyze.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u5206\u6790", None))
        self.btnAnalyzeSample.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u539f\u59cb\u6837\u672c", None))
        self.btnAnalyzeObject.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u5bf9\u8c61\u8c03\u6574", None))
        self.btnAnalyzeAll.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u4e00\u952e\u5206\u6790", None))
        self.cbxSelectAll.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u5168\u9009", None))
        self.lblLoudnessStandard.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u54cd\u5ea6\u6807\u51c6", None))
        self.cbbLoudnessStandard.setItemText(0, QCoreApplication.translate("LoudnessAdjustment", u"RMS", None))
        self.cbbLoudnessStandard.setItemText(1, QCoreApplication.translate("LoudnessAdjustment", u"LUFS", None))

        self.lblTargetLoudness.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u76ee\u6807\u54cd\u5ea6", None))
        self.spbTargetLoudness.setSuffix(QCoreApplication.translate("LoudnessAdjustment", u" dBFS", None))
        self.lblTolerance.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u5bbd\u5bb9\u5ea6", None))
        self.spbTolerance.setSuffix(QCoreApplication.translate("LoudnessAdjustment", u" dB", None))
        self.btnUnifyLoudness.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u7edf\u4e00\u54cd\u5ea6", None))
        ___qtablewidgetitem = self.tblAudioList.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u9009\u4e2d", None))
        ___qtablewidgetitem1 = self.tblAudioList.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u97f3\u9891\u6587\u4ef6\u8def\u5f84", None))
        ___qtablewidgetitem2 = self.tblAudioList.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u54cd\u5ea6", None))
        ___qtablewidgetitem3 = self.tblAudioList.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u5bf9\u8c61\u97f3\u91cf\u8c03\u6574", None))
        ___qtablewidgetitem4 = self.tblAudioList.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u603b\u7ebf\u97f3\u91cf\u8c03\u6574", None))
        ___qtablewidgetitem5 = self.tblAudioList.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u6700\u7ec8\u54cd\u5ea6", None))
        ___qtablewidgetitem6 = self.tblAudioList.horizontalHeaderItem(6)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u72b6\u6001", None))
    # retranslateUi

