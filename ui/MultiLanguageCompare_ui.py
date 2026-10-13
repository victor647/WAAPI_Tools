# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MultiLanguageCompare.ui'
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

class Ui_MultiLanguageCompare(object):
    def setupUi(self, MultiLanguageCompare):
        if not MultiLanguageCompare.objectName():
            MultiLanguageCompare.setObjectName(u"MultiLanguageCompare")
        MultiLanguageCompare.resize(1080, 580)
        MultiLanguageCompare.setMinimumSize(QSize(820, 420))
        self.verticalLayout = QVBoxLayout(MultiLanguageCompare)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.toolsRow = QHBoxLayout()
        self.toolsRow.setObjectName(u"toolsRow")
        self.cbxSelectAll = QCheckBox(MultiLanguageCompare)
        self.cbxSelectAll.setObjectName(u"cbxSelectAll")
        self.cbxSelectAll.setChecked(True)

        self.toolsRow.addWidget(self.cbxSelectAll)

        self.selectAllSpacer = QSpacerItem(24, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.toolsRow.addItem(self.selectAllSpacer)

        self.lblReferenceLanguage = QLabel(MultiLanguageCompare)
        self.lblReferenceLanguage.setObjectName(u"lblReferenceLanguage")

        self.toolsRow.addWidget(self.lblReferenceLanguage)

        self.cbbReferenceLanguage = QComboBox(MultiLanguageCompare)
        self.cbbReferenceLanguage.setObjectName(u"cbbReferenceLanguage")
        self.cbbReferenceLanguage.setMinimumSize(QSize(120, 0))

        self.toolsRow.addWidget(self.cbbReferenceLanguage)

        self.btnUnifyLoudness = QPushButton(MultiLanguageCompare)
        self.btnUnifyLoudness.setObjectName(u"btnUnifyLoudness")
        font = QFont()
        font.setBold(True)
        self.btnUnifyLoudness.setFont(font)

        self.toolsRow.addWidget(self.btnUnifyLoudness)

        self.btnRefresh = QPushButton(MultiLanguageCompare)
        self.btnRefresh.setObjectName(u"btnRefresh")

        self.toolsRow.addWidget(self.btnRefresh)

        self.toolsSpacer = QSpacerItem(24, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.toolsRow.addItem(self.toolsSpacer)

        self.lblLoudnessStandard = QLabel(MultiLanguageCompare)
        self.lblLoudnessStandard.setObjectName(u"lblLoudnessStandard")

        self.toolsRow.addWidget(self.lblLoudnessStandard)

        self.cbbLoudnessStandard = QComboBox(MultiLanguageCompare)
        self.cbbLoudnessStandard.addItem("")
        self.cbbLoudnessStandard.addItem("")
        self.cbbLoudnessStandard.setObjectName(u"cbbLoudnessStandard")
        self.cbbLoudnessStandard.setMinimumSize(QSize(120, 0))

        self.toolsRow.addWidget(self.cbbLoudnessStandard)

        self.lblTolerance = QLabel(MultiLanguageCompare)
        self.lblTolerance.setObjectName(u"lblTolerance")

        self.toolsRow.addWidget(self.lblTolerance)

        self.spbTolerance = QDoubleSpinBox(MultiLanguageCompare)
        self.spbTolerance.setObjectName(u"spbTolerance")
        self.spbTolerance.setDecimals(1)
        self.spbTolerance.setMinimum(0.000000000000000)
        self.spbTolerance.setMaximum(20.000000000000000)
        self.spbTolerance.setSingleStep(0.500000000000000)
        self.spbTolerance.setValue(1.000000000000000)

        self.toolsRow.addWidget(self.spbTolerance)

        self.settingsSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.toolsRow.addItem(self.settingsSpacer)


        self.verticalLayout.addLayout(self.toolsRow)

        self.tblCompare = QTableWidget(MultiLanguageCompare)
        self.tblCompare.setObjectName(u"tblCompare")
        self.tblCompare.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblCompare.setAlternatingRowColors(True)
        self.tblCompare.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.verticalLayout.addWidget(self.tblCompare)


        self.retranslateUi(MultiLanguageCompare)

        QMetaObject.connectSlotsByName(MultiLanguageCompare)
    # setupUi

    def retranslateUi(self, MultiLanguageCompare):
        MultiLanguageCompare.setWindowTitle(QCoreApplication.translate("MultiLanguageCompare", u"\u591a\u8bed\u8a00\u5bf9\u6bd4", None))
        self.cbxSelectAll.setText(QCoreApplication.translate("MultiLanguageCompare", u"\u5168\u9009", None))
        self.lblReferenceLanguage.setText(QCoreApplication.translate("MultiLanguageCompare", u"\u53c2\u8003\u8bed\u8a00", None))
        self.btnUnifyLoudness.setText(QCoreApplication.translate("MultiLanguageCompare", u"\u7edf\u4e00\u54cd\u5ea6", None))
        self.btnRefresh.setText(QCoreApplication.translate("MultiLanguageCompare", u"\u91cd\u65b0\u5206\u6790", None))
        self.lblLoudnessStandard.setText(QCoreApplication.translate("MultiLanguageCompare", u"\u54cd\u5ea6\u6807\u51c6", None))
        self.cbbLoudnessStandard.setItemText(0, QCoreApplication.translate("MultiLanguageCompare", u"RMS", None))
        self.cbbLoudnessStandard.setItemText(1, QCoreApplication.translate("MultiLanguageCompare", u"LUFS", None))

        self.lblTolerance.setText(QCoreApplication.translate("MultiLanguageCompare", u"\u5bbd\u5bb9\u5ea6", None))
        self.spbTolerance.setSuffix(QCoreApplication.translate("MultiLanguageCompare", u" dB", None))
    # retranslateUi

