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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog,
    QDoubleSpinBox, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_LoudnessAdjustment(object):
    def setupUi(self, LoudnessAdjustment):
        if not LoudnessAdjustment.objectName():
            LoudnessAdjustment.setObjectName(u"LoudnessAdjustment")
        LoudnessAdjustment.resize(880, 520)
        LoudnessAdjustment.setMinimumSize(QSize(720, 400))
        self.verticalLayout = QVBoxLayout(LoudnessAdjustment)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.toolsRow = QHBoxLayout()
        self.toolsRow.setObjectName(u"toolsRow")
        self.cbxSelectAll = QCheckBox(LoudnessAdjustment)
        self.cbxSelectAll.setObjectName(u"cbxSelectAll")

        self.toolsRow.addWidget(self.cbxSelectAll)

        self.btnImportFiles = QPushButton(LoudnessAdjustment)
        self.btnImportFiles.setObjectName(u"btnImportFiles")

        self.toolsRow.addWidget(self.btnImportFiles)

        self.btnImportFolder = QPushButton(LoudnessAdjustment)
        self.btnImportFolder.setObjectName(u"btnImportFolder")

        self.toolsRow.addWidget(self.btnImportFolder)

        self.btnAnalyzeLoudness = QPushButton(LoudnessAdjustment)
        self.btnAnalyzeLoudness.setObjectName(u"btnAnalyzeLoudness")

        self.toolsRow.addWidget(self.btnAnalyzeLoudness)

        self.lblTargetLoudness = QLabel(LoudnessAdjustment)
        self.lblTargetLoudness.setObjectName(u"lblTargetLoudness")

        self.toolsRow.addWidget(self.lblTargetLoudness)

        self.spbTargetLoudness = QDoubleSpinBox(LoudnessAdjustment)
        self.spbTargetLoudness.setObjectName(u"spbTargetLoudness")
        self.spbTargetLoudness.setDecimals(0)
        self.spbTargetLoudness.setMinimum(-60.000000000000000)
        self.spbTargetLoudness.setMaximum(0.000000000000000)
        self.spbTargetLoudness.setSingleStep(1.000000000000000)
        self.spbTargetLoudness.setValue(-18.000000000000000)

        self.toolsRow.addWidget(self.spbTargetLoudness)

        self.lblTolerance = QLabel(LoudnessAdjustment)
        self.lblTolerance.setObjectName(u"lblTolerance")

        self.toolsRow.addWidget(self.lblTolerance)

        self.spbTolerance = QDoubleSpinBox(LoudnessAdjustment)
        self.spbTolerance.setObjectName(u"spbTolerance")
        self.spbTolerance.setDecimals(1)
        self.spbTolerance.setMinimum(0.000000000000000)
        self.spbTolerance.setMaximum(20.000000000000000)
        self.spbTolerance.setSingleStep(0.500000000000000)
        self.spbTolerance.setValue(1.000000000000000)

        self.toolsRow.addWidget(self.spbTolerance)

        self.btnUnifyLoudness = QPushButton(LoudnessAdjustment)
        self.btnUnifyLoudness.setObjectName(u"btnUnifyLoudness")
        font = QFont()
        font.setBold(True)
        self.btnUnifyLoudness.setFont(font)

        self.toolsRow.addWidget(self.btnUnifyLoudness)

        self.toolsSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.toolsRow.addItem(self.toolsSpacer)


        self.verticalLayout.addLayout(self.toolsRow)

        self.tblAudioList = QTableWidget(LoudnessAdjustment)
        if (self.tblAudioList.columnCount() < 4):
            self.tblAudioList.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblAudioList.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblAudioList.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblAudioList.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tblAudioList.setHorizontalHeaderItem(3, __qtablewidgetitem3)
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
        self.cbxSelectAll.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u5168\u9009", None))
        self.btnImportFiles.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u5bfc\u5165\u6587\u4ef6", None))
        self.btnImportFolder.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u5bfc\u5165\u6587\u4ef6\u5939", None))
        self.btnAnalyzeLoudness.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u5206\u6790\u54cd\u5ea6", None))
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
        ___qtablewidgetitem3.setText(QCoreApplication.translate("LoudnessAdjustment", u"\u72b6\u6001", None))
    # retranslateUi

