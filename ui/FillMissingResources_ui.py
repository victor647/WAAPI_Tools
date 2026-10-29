# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'FillMissingResources.ui'
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
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_FillMissingResources(object):
    def setupUi(self, FillMissingResources):
        if not FillMissingResources.objectName():
            FillMissingResources.setObjectName(u"FillMissingResources")
        FillMissingResources.resize(1140, 560)
        FillMissingResources.setMinimumSize(QSize(1000, 360))
        self.verticalLayout = QVBoxLayout(FillMissingResources)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.topRow = QHBoxLayout()
        self.topRow.setObjectName(u"topRow")
        self.cbxSelectAll = QCheckBox(FillMissingResources)
        self.cbxSelectAll.setObjectName(u"cbxSelectAll")

        self.topRow.addWidget(self.cbxSelectAll)

        self.lblFillMode = QLabel(FillMissingResources)
        self.lblFillMode.setObjectName(u"lblFillMode")

        self.topRow.addWidget(self.lblFillMode)

        self.cbbFillMode = QComboBox(FillMissingResources)
        self.cbbFillMode.addItem("")
        self.cbbFillMode.addItem("")
        self.cbbFillMode.setObjectName(u"cbbFillMode")

        self.topRow.addWidget(self.cbbFillMode)

        self.lblFillDuration = QLabel(FillMissingResources)
        self.lblFillDuration.setObjectName(u"lblFillDuration")

        self.topRow.addWidget(self.lblFillDuration)

        self.spbFillDuration = QDoubleSpinBox(FillMissingResources)
        self.spbFillDuration.setObjectName(u"spbFillDuration")
        self.spbFillDuration.setDecimals(1)
        self.spbFillDuration.setMinimum(0.100000000000000)
        self.spbFillDuration.setMaximum(60.000000000000000)
        self.spbFillDuration.setSingleStep(0.500000000000000)
        self.spbFillDuration.setValue(2.000000000000000)

        self.topRow.addWidget(self.spbFillDuration)

        self.lblSineFrequency = QLabel(FillMissingResources)
        self.lblSineFrequency.setObjectName(u"lblSineFrequency")

        self.topRow.addWidget(self.lblSineFrequency)

        self.spbSineFrequency = QSpinBox(FillMissingResources)
        self.spbSineFrequency.setObjectName(u"spbSineFrequency")
        self.spbSineFrequency.setMinimum(20)
        self.spbSineFrequency.setMaximum(20000)
        self.spbSineFrequency.setSingleStep(10)
        self.spbSineFrequency.setValue(1000)

        self.topRow.addWidget(self.spbSineFrequency)

        self.lblFillLanguages = QLabel(FillMissingResources)
        self.lblFillLanguages.setObjectName(u"lblFillLanguages")

        self.topRow.addWidget(self.lblFillLanguages)

        self.tblLanguages = QTableWidget(FillMissingResources)
        self.tblLanguages.setObjectName(u"tblLanguages")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tblLanguages.sizePolicy().hasHeightForWidth())
        self.tblLanguages.setSizePolicy(sizePolicy)
        self.tblLanguages.setMinimumSize(QSize(0, 58))
        self.tblLanguages.setMaximumSize(QSize(16777215, 64))
        self.tblLanguages.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblLanguages.setAlternatingRowColors(False)
        self.tblLanguages.setSelectionMode(QAbstractItemView.NoSelection)
        self.tblLanguages.setShowGrid(False)
        self.tblLanguages.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tblLanguages.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tblLanguages.verticalHeader().setVisible(False)

        self.topRow.addWidget(self.tblLanguages)

        self.topSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.topRow.addItem(self.topSpacer)

        self.btnAnalyze = QPushButton(FillMissingResources)
        self.btnAnalyze.setObjectName(u"btnAnalyze")

        self.topRow.addWidget(self.btnAnalyze)

        self.btnProcess = QPushButton(FillMissingResources)
        self.btnProcess.setObjectName(u"btnProcess")

        self.topRow.addWidget(self.btnProcess)


        self.verticalLayout.addLayout(self.topRow)

        self.tblMissing = QTableWidget(FillMissingResources)
        self.tblMissing.setObjectName(u"tblMissing")
        self.tblMissing.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblMissing.setAlternatingRowColors(True)
        self.tblMissing.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblMissing.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tblMissing.verticalHeader().setVisible(False)

        self.verticalLayout.addWidget(self.tblMissing)


        self.retranslateUi(FillMissingResources)

        QMetaObject.connectSlotsByName(FillMissingResources)
    # setupUi

    def retranslateUi(self, FillMissingResources):
        FillMissingResources.setWindowTitle(QCoreApplication.translate("FillMissingResources", u"\u586b\u8865\u7f3a\u5931\u8d44\u6e90", None))
#if QT_CONFIG(tooltip)
        self.cbxSelectAll.setToolTip(QCoreApplication.translate("FillMissingResources", u"\u52fe\u9009/\u53d6\u6d88\u52fe\u9009\u7ed3\u679c\u8868\u4e2d\u7684\u6240\u6709 Sound \u884c\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxSelectAll.setText(QCoreApplication.translate("FillMissingResources", u"\u5168\u9009", None))
        self.lblFillMode.setText(QCoreApplication.translate("FillMissingResources", u"\u586b\u8865\u65b9\u5f0f", None))
        self.cbbFillMode.setItemText(0, QCoreApplication.translate("FillMissingResources", u"\u9759\u97f3", None))
        self.cbbFillMode.setItemText(1, QCoreApplication.translate("FillMissingResources", u"\u6b63\u5f26\u6ce2", None))

#if QT_CONFIG(tooltip)
        self.cbbFillMode.setToolTip(QCoreApplication.translate("FillMissingResources", u"\u9759\u97f3\uff1a\u521b\u5efa Wwise Silence \u6e90\uff1b\u6b63\u5f26\u6ce2\uff1a\u521b\u5efa Wwise Sine \u6e90\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblFillDuration.setText(QCoreApplication.translate("FillMissingResources", u"\u65f6\u957f", None))
#if QT_CONFIG(tooltip)
        self.spbFillDuration.setToolTip(QCoreApplication.translate("FillMissingResources", u"\u65b0\u5efa\u9759\u97f3/\u6b63\u5f26\u6ce2\u6e90\u7684\u65f6\u957f\uff08\u79d2\uff09\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.spbFillDuration.setSuffix(QCoreApplication.translate("FillMissingResources", u" \u79d2", None))
        self.lblSineFrequency.setText(QCoreApplication.translate("FillMissingResources", u"\u9891\u7387", None))
#if QT_CONFIG(tooltip)
        self.spbSineFrequency.setToolTip(QCoreApplication.translate("FillMissingResources", u"\u6b63\u5f26\u6ce2\u9891\u7387\uff08Hz\uff09\uff0c\u4ec5\u6b63\u5f26\u6ce2\u6a21\u5f0f\u4f7f\u7528\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.spbSineFrequency.setSuffix(QCoreApplication.translate("FillMissingResources", u" Hz", None))
        self.lblFillLanguages.setText(QCoreApplication.translate("FillMissingResources", u"\u586b\u5145\u8bed\u8a00", None))
#if QT_CONFIG(tooltip)
        self.lblFillLanguages.setToolTip(QCoreApplication.translate("FillMissingResources", u"\u52fe\u9009\u9700\u8981\u586b\u8865\u7684\u8bed\u8a00\uff1b\u672a\u52fe\u9009\u7684\u8bed\u8a00\u5373\u4f7f\u7f3a\u5931\u4e5f\u4e0d\u4f1a\u5904\u7406\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.tblLanguages.setToolTip(QCoreApplication.translate("FillMissingResources", u"\u52fe\u9009\u8981\u586b\u8865\u7684\u8bed\u8a00\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.btnAnalyze.setText(QCoreApplication.translate("FillMissingResources", u"\u5206\u6790", None))
        self.btnProcess.setText(QCoreApplication.translate("FillMissingResources", u"\u5904\u7406\u9009\u4e2d", None))
    # retranslateUi

