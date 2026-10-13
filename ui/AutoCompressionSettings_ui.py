# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'AutoCompressionSettings.ui'
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
    QLabel, QPlainTextEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_AutoCompressionSettings(object):
    def setupUi(self, AutoCompressionSettings):
        if not AutoCompressionSettings.objectName():
            AutoCompressionSettings.setObjectName(u"AutoCompressionSettings")
        AutoCompressionSettings.resize(1180, 650)
        self.verticalLayout = QVBoxLayout(AutoCompressionSettings)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.settingsLayout = QHBoxLayout()
        self.settingsLayout.setObjectName(u"settingsLayout")
        self.lblConversion = QLabel(AutoCompressionSettings)
        self.lblConversion.setObjectName(u"lblConversion")

        self.settingsLayout.addWidget(self.lblConversion)

        self.lblLongConversion = QLabel(AutoCompressionSettings)
        self.lblLongConversion.setObjectName(u"lblLongConversion")

        self.settingsLayout.addWidget(self.lblLongConversion)

        self.cbbLongConversion = QComboBox(AutoCompressionSettings)
        self.cbbLongConversion.setObjectName(u"cbbLongConversion")
        self.cbbLongConversion.setMinimumSize(QSize(160, 0))
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cbbLongConversion.sizePolicy().hasHeightForWidth())
        self.cbbLongConversion.setSizePolicy(sizePolicy)

        self.settingsLayout.addWidget(self.cbbLongConversion)

        self.lblShortConversion = QLabel(AutoCompressionSettings)
        self.lblShortConversion.setObjectName(u"lblShortConversion")

        self.settingsLayout.addWidget(self.lblShortConversion)

        self.cbbShortConversion = QComboBox(AutoCompressionSettings)
        self.cbbShortConversion.setObjectName(u"cbbShortConversion")
        self.cbbShortConversion.setMinimumSize(QSize(160, 0))
        sizePolicy.setHeightForWidth(self.cbbShortConversion.sizePolicy().hasHeightForWidth())
        self.cbbShortConversion.setSizePolicy(sizePolicy)

        self.settingsLayout.addWidget(self.cbbShortConversion)

        self.settingsGroupGap = QSpacerItem(16, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.settingsLayout.addItem(self.settingsGroupGap)

        self.lblDurationThreshold = QLabel(AutoCompressionSettings)
        self.lblDurationThreshold.setObjectName(u"lblDurationThreshold")

        self.settingsLayout.addWidget(self.lblDurationThreshold)

        self.spbDurationThreshold = QDoubleSpinBox(AutoCompressionSettings)
        self.spbDurationThreshold.setObjectName(u"spbDurationThreshold")
        self.spbDurationThreshold.setDecimals(2)
        self.spbDurationThreshold.setMaximum(9999.000000000000000)
        self.spbDurationThreshold.setSingleStep(0.100000000000000)
        self.spbDurationThreshold.setValue(0.500000000000000)

        self.settingsLayout.addWidget(self.spbDurationThreshold)

        self.btnAnalyze = QPushButton(AutoCompressionSettings)
        self.btnAnalyze.setObjectName(u"btnAnalyze")

        self.settingsLayout.addWidget(self.btnAnalyze)

        self.btnApplySelected = QPushButton(AutoCompressionSettings)
        self.btnApplySelected.setObjectName(u"btnApplySelected")
        self.btnApplySelected.setEnabled(False)

        self.settingsLayout.addWidget(self.btnApplySelected)


        self.verticalLayout.addLayout(self.settingsLayout)

        self.pteResult = QPlainTextEdit(AutoCompressionSettings)
        self.pteResult.setObjectName(u"pteResult")
        self.pteResult.setMaximumSize(QSize(16777215, 95))
        self.pteResult.setReadOnly(True)

        self.verticalLayout.addWidget(self.pteResult)

        self.tableActionsLayout = QHBoxLayout()
        self.tableActionsLayout.setObjectName(u"tableActionsLayout")
        self.cbxSelectAll = QCheckBox(AutoCompressionSettings)
        self.cbxSelectAll.setObjectName(u"cbxSelectAll")
        self.cbxSelectAll.setEnabled(False)
        self.cbxSelectAll.setMaximumSize(QSize(60, 16777215))
        self.cbxSelectAll.setChecked(True)

        self.tableActionsLayout.addWidget(self.cbxSelectAll)

        self.tableActionsSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.tableActionsLayout.addItem(self.tableActionsSpacer)


        self.verticalLayout.addLayout(self.tableActionsLayout)

        self.tblPlanResults = QTableWidget(AutoCompressionSettings)
        if (self.tblPlanResults.columnCount() < 7):
            self.tblPlanResults.setColumnCount(7)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        self.tblPlanResults.setObjectName(u"tblPlanResults")
        self.tblPlanResults.setAlternatingRowColors(True)
        self.tblPlanResults.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblPlanResults.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblPlanResults.setSortingEnabled(False)

        self.verticalLayout.addWidget(self.tblPlanResults)


        self.retranslateUi(AutoCompressionSettings)

        QMetaObject.connectSlotsByName(AutoCompressionSettings)
    # setupUi

    def retranslateUi(self, AutoCompressionSettings):
        AutoCompressionSettings.setWindowTitle(QCoreApplication.translate("AutoCompressionSettings", u"\u81ea\u52a8\u8f6c\u7801\u8bbe\u7f6e", None))
        self.lblConversion.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u97f3\u6548 Conversion", None))
        self.lblLongConversion.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u957f\u97f3\u6548", None))
        self.lblShortConversion.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u77ed\u97f3\u6548", None))
        self.lblDurationThreshold.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u957f\u97f3\u6548\u65f6\u957f\u9608\u503c\uff08\u79d2\uff09", None))
#if QT_CONFIG(tooltip)
        self.lblDurationThreshold.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u65f6\u957f\u5927\u4e8e\u9608\u503c\u7684\u6837\u672c\u5224\u5b9a\u4e3a\u957f\u97f3\u6548\uff1b\u5c0f\u4e8e\u6216\u7b49\u4e8e\u9608\u503c\u7684\u6837\u672c\u5224\u5b9a\u4e3a\u77ed\u97f3\u6548\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.spbDurationThreshold.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u65f6\u957f\u5927\u4e8e\u9608\u503c\u7684\u6837\u672c\u5224\u5b9a\u4e3a\u957f\u97f3\u6548\uff1b\u5c0f\u4e8e\u6216\u7b49\u4e8e\u9608\u503c\u7684\u6837\u672c\u5224\u5b9a\u4e3a\u77ed\u97f3\u6548\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.btnAnalyze.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u5206\u6790", None))
        self.btnApplySelected.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u5e94\u7528\u52fe\u9009\u9879", None))
        self.pteResult.setPlaceholderText(QCoreApplication.translate("AutoCompressionSettings", u"\u5206\u6790\u7edf\u8ba1\u548c\u5e94\u7528\u7ed3\u679c\u5c06\u663e\u793a\u5728\u8fd9\u91cc\u3002", None))
        self.cbxSelectAll.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u5168\u9009", None))
        ___qtablewidgetitem = self.tblPlanResults.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u5e94\u7528", None))
        ___qtablewidgetitem1 = self.tblPlanResults.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u540d\u79f0", None))
        ___qtablewidgetitem2 = self.tblPlanResults.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u7c7b\u578b", None))
        ___qtablewidgetitem3 = self.tblPlanResults.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u8def\u5f84", None))
        ___qtablewidgetitem4 = self.tblPlanResults.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u957f\u97f3\u6548\u6570", None))
        ___qtablewidgetitem5 = self.tblPlanResults.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u77ed\u97f3\u6548\u6570", None))
        ___qtablewidgetitem6 = self.tblPlanResults.horizontalHeaderItem(6)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u5e94\u7528 Conversion", None))
    # retranslateUi

