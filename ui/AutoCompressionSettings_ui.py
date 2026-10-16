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
    QSpacerItem, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

from libraries.widgets.map_edit_widget import MapEdit

class Ui_AutoCompressionSettings(object):
    def setupUi(self, AutoCompressionSettings):
        if not AutoCompressionSettings.objectName():
            AutoCompressionSettings.setObjectName(u"AutoCompressionSettings")
        AutoCompressionSettings.resize(1040, 650)
        self.verticalLayout = QVBoxLayout(AutoCompressionSettings)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabModes = QTabWidget(AutoCompressionSettings)
        self.tabModes.setObjectName(u"tabModes")
        self.tabDuration = QWidget()
        self.tabDuration.setObjectName(u"tabDuration")
        self.tabDurationLayout = QVBoxLayout(self.tabDuration)
        self.tabDurationLayout.setObjectName(u"tabDurationLayout")
        self.settingsLayout = QHBoxLayout()
        self.settingsLayout.setObjectName(u"settingsLayout")
        self.lblConversion = QLabel(self.tabDuration)
        self.lblConversion.setObjectName(u"lblConversion")

        self.settingsLayout.addWidget(self.lblConversion)

        self.cbbDefaultConversion = QComboBox(self.tabDuration)
        self.cbbDefaultConversion.setObjectName(u"cbbDefaultConversion")
        self.cbbDefaultConversion.setMinimumSize(QSize(220, 0))
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cbbDefaultConversion.sizePolicy().hasHeightForWidth())
        self.cbbDefaultConversion.setSizePolicy(sizePolicy)

        self.settingsLayout.addWidget(self.cbbDefaultConversion)

        self.settingsGroupGap = QSpacerItem(16, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.settingsLayout.addItem(self.settingsGroupGap)

        self.cbxUseShort = QCheckBox(self.tabDuration)
        self.cbxUseShort.setObjectName(u"cbxUseShort")

        self.settingsLayout.addWidget(self.cbxUseShort)

        self.spbShortThreshold = QDoubleSpinBox(self.tabDuration)
        self.spbShortThreshold.setObjectName(u"spbShortThreshold")
        self.spbShortThreshold.setDecimals(2)
        self.spbShortThreshold.setMaximum(9999.000000000000000)
        self.spbShortThreshold.setSingleStep(0.100000000000000)
        self.spbShortThreshold.setValue(0.500000000000000)

        self.settingsLayout.addWidget(self.spbShortThreshold)

        self.cbxUseLong = QCheckBox(self.tabDuration)
        self.cbxUseLong.setObjectName(u"cbxUseLong")

        self.settingsLayout.addWidget(self.cbxUseLong)

        self.spbLongThreshold = QDoubleSpinBox(self.tabDuration)
        self.spbLongThreshold.setObjectName(u"spbLongThreshold")
        self.spbLongThreshold.setDecimals(2)
        self.spbLongThreshold.setMaximum(9999.000000000000000)
        self.spbLongThreshold.setSingleStep(0.500000000000000)
        self.spbLongThreshold.setValue(5.000000000000000)

        self.settingsLayout.addWidget(self.spbLongThreshold)

        self.btnAnalyze = QPushButton(self.tabDuration)
        self.btnAnalyze.setObjectName(u"btnAnalyze")

        self.settingsLayout.addWidget(self.btnAnalyze)

        self.btnApply = QPushButton(self.tabDuration)
        self.btnApply.setObjectName(u"btnApply")
        self.btnApply.setEnabled(False)

        self.settingsLayout.addWidget(self.btnApply)


        self.tabDurationLayout.addLayout(self.settingsLayout)

        self.analysisRow = QHBoxLayout()
        self.analysisRow.setObjectName(u"analysisRow")
        self.analysisPanel = QWidget(self.tabDuration)
        self.analysisPanel.setObjectName(u"analysisPanel")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.analysisPanel.sizePolicy().hasHeightForWidth())
        self.analysisPanel.setSizePolicy(sizePolicy1)
        self.analysisPanelLayout = QVBoxLayout(self.analysisPanel)
        self.analysisPanelLayout.setObjectName(u"analysisPanelLayout")
        self.analysisPanelLayout.setContentsMargins(0, 0, 0, 0)
        self.pteResult = QPlainTextEdit(self.analysisPanel)
        self.pteResult.setObjectName(u"pteResult")
        self.pteResult.setReadOnly(True)

        self.analysisPanelLayout.addWidget(self.pteResult)

        self.analysisActionsLayout = QHBoxLayout()
        self.analysisActionsLayout.setObjectName(u"analysisActionsLayout")
        self.cbxOverwriteConflicts = QCheckBox(self.analysisPanel)
        self.cbxOverwriteConflicts.setObjectName(u"cbxOverwriteConflicts")

        self.analysisActionsLayout.addWidget(self.cbxOverwriteConflicts)

        self.analysisActionsSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.analysisActionsLayout.addItem(self.analysisActionsSpacer)

        self.lblConversionPlatform = QLabel(self.analysisPanel)
        self.lblConversionPlatform.setObjectName(u"lblConversionPlatform")

        self.analysisActionsLayout.addWidget(self.lblConversionPlatform)

        self.cbbConversionPlatform = QComboBox(self.analysisPanel)
        self.cbbConversionPlatform.setObjectName(u"cbbConversionPlatform")
        self.cbbConversionPlatform.setMinimumSize(QSize(100, 0))
        self.cbbConversionPlatform.setMaximumSize(QSize(100, 16777215))

        self.analysisActionsLayout.addWidget(self.cbbConversionPlatform)


        self.analysisPanelLayout.addLayout(self.analysisActionsLayout)


        self.analysisRow.addWidget(self.analysisPanel)

        self.conversionPanel = QWidget(self.tabDuration)
        self.conversionPanel.setObjectName(u"conversionPanel")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.conversionPanel.sizePolicy().hasHeightForWidth())
        self.conversionPanel.setSizePolicy(sizePolicy2)
        self.conversionPanelLayout = QVBoxLayout(self.conversionPanel)
        self.conversionPanelLayout.setObjectName(u"conversionPanelLayout")
        self.conversionPanelLayout.setContentsMargins(0, 0, 0, 0)
        self.tblConversionSettings = QTableWidget(self.conversionPanel)
        if (self.tblConversionSettings.columnCount() < 4):
            self.tblConversionSettings.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblConversionSettings.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblConversionSettings.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblConversionSettings.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tblConversionSettings.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        self.tblConversionSettings.setObjectName(u"tblConversionSettings")
        self.tblConversionSettings.setAlternatingRowColors(True)
        self.tblConversionSettings.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblConversionSettings.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblConversionSettings.setSortingEnabled(False)

        self.conversionPanelLayout.addWidget(self.tblConversionSettings)


        self.analysisRow.addWidget(self.conversionPanel)


        self.tabDurationLayout.addLayout(self.analysisRow)

        self.tblPlanResults = QTableWidget(self.tabDuration)
        if (self.tblPlanResults.columnCount() < 6):
            self.tblPlanResults.setColumnCount(6)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(0, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(1, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(2, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(3, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(4, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.tblPlanResults.setHorizontalHeaderItem(5, __qtablewidgetitem9)
        self.tblPlanResults.setObjectName(u"tblPlanResults")
        self.tblPlanResults.setAlternatingRowColors(True)
        self.tblPlanResults.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblPlanResults.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblPlanResults.setSortingEnabled(False)

        self.tabDurationLayout.addWidget(self.tblPlanResults)

        self.tabModes.addTab(self.tabDuration, "")
        self.tabName = QWidget()
        self.tabName.setObjectName(u"tabName")
        self.tabNameLayout = QVBoxLayout(self.tabName)
        self.tabNameLayout.setObjectName(u"tabNameLayout")
        self.nameActionsLayout = QHBoxLayout()
        self.nameActionsLayout.setObjectName(u"nameActionsLayout")
        self.btnNameAnalyze = QPushButton(self.tabName)
        self.btnNameAnalyze.setObjectName(u"btnNameAnalyze")

        self.nameActionsLayout.addWidget(self.btnNameAnalyze)

        self.btnNameApply = QPushButton(self.tabName)
        self.btnNameApply.setObjectName(u"btnNameApply")
        self.btnNameApply.setEnabled(False)

        self.nameActionsLayout.addWidget(self.btnNameApply)

        self.cbxNameOverwriteConflicts = QCheckBox(self.tabName)
        self.cbxNameOverwriteConflicts.setObjectName(u"cbxNameOverwriteConflicts")

        self.nameActionsLayout.addWidget(self.cbxNameOverwriteConflicts)

        self.lblNameStatus = QLabel(self.tabName)
        self.lblNameStatus.setObjectName(u"lblNameStatus")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(1)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.lblNameStatus.sizePolicy().hasHeightForWidth())
        self.lblNameStatus.setSizePolicy(sizePolicy3)
        self.lblNameStatus.setWordWrap(True)

        self.nameActionsLayout.addWidget(self.lblNameStatus)


        self.tabNameLayout.addLayout(self.nameActionsLayout)

        self.nameMap = MapEdit(self.tabName)
        self.nameMap.setObjectName(u"nameMap")

        self.tabNameLayout.addWidget(self.nameMap)

        self.tblNamePlanResults = QTableWidget(self.tabName)
        if (self.tblNamePlanResults.columnCount() < 5):
            self.tblNamePlanResults.setColumnCount(5)
        __qtablewidgetitem10 = QTableWidgetItem()
        self.tblNamePlanResults.setHorizontalHeaderItem(0, __qtablewidgetitem10)
        __qtablewidgetitem11 = QTableWidgetItem()
        self.tblNamePlanResults.setHorizontalHeaderItem(1, __qtablewidgetitem11)
        __qtablewidgetitem12 = QTableWidgetItem()
        self.tblNamePlanResults.setHorizontalHeaderItem(2, __qtablewidgetitem12)
        __qtablewidgetitem13 = QTableWidgetItem()
        self.tblNamePlanResults.setHorizontalHeaderItem(3, __qtablewidgetitem13)
        __qtablewidgetitem14 = QTableWidgetItem()
        self.tblNamePlanResults.setHorizontalHeaderItem(4, __qtablewidgetitem14)
        self.tblNamePlanResults.setObjectName(u"tblNamePlanResults")
        self.tblNamePlanResults.setAlternatingRowColors(True)
        self.tblNamePlanResults.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblNamePlanResults.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblNamePlanResults.setSortingEnabled(False)

        self.tabNameLayout.addWidget(self.tblNamePlanResults)

        self.tabModes.addTab(self.tabName, "")

        self.verticalLayout.addWidget(self.tabModes)


        self.retranslateUi(AutoCompressionSettings)

        QMetaObject.connectSlotsByName(AutoCompressionSettings)
    # setupUi

    def retranslateUi(self, AutoCompressionSettings):
        AutoCompressionSettings.setWindowTitle(QCoreApplication.translate("AutoCompressionSettings", u"\u81ea\u52a8\u8f6c\u7801\u8bbe\u7f6e", None))
        self.lblConversion.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u9ed8\u8ba4\u6863 Conversion", None))
#if QT_CONFIG(tooltip)
        self.lblConversion.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u4e2d\u6863\uff08\u65f6\u957f\u4ecb\u4e8e\u4e24\u4e2a\u9608\u503c\u4e4b\u95f4\uff09\u4f7f\u7528\u7684 Conversion\u3002\u957f\u97f3\u6548\u6863\u7528\u300c\u540d\u79f0_Long\u300d\u3001\u77ed\u97f3\u6548\u6863\u7528\u300c\u540d\u79f0_Short\u300d\uff1b\u5de5\u7a0b\u91cc\u627e\u4e0d\u5230\u65f6\u4f1a\u590d\u5236\u8be5 Conversion \u518d\u6539\u540d\u751f\u6210\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.cbbDefaultConversion.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u4e2d\u6863\uff08\u65f6\u957f\u4ecb\u4e8e\u4e24\u4e2a\u9608\u503c\u4e4b\u95f4\uff09\u4f7f\u7528\u7684 Conversion\u3002\u957f\u97f3\u6548\u6863\u7528\u300c\u540d\u79f0_Long\u300d\u3001\u77ed\u97f3\u6548\u6863\u7528\u300c\u540d\u79f0_Short\u300d\uff1b\u5de5\u7a0b\u91cc\u627e\u4e0d\u5230\u65f6\u4f1a\u590d\u5236\u8be5 Conversion \u518d\u6539\u540d\u751f\u6210\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxUseShort.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u77ed\u97f3\u6548", None))
#if QT_CONFIG(tooltip)
        self.cbxUseShort.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u52fe\u9009\u65f6\u533a\u5206\u77ed\u97f3\u6548\u6863\uff1a\u64ad\u653e\u65f6\u957f\u5c0f\u4e8e\u6216\u7b49\u4e8e\u53f3\u4fa7\u9608\u503c\uff08\u79d2\uff09\u7684\u6837\u672c\u7b97\u77ed\u97f3\u6548\uff0c\u7528\u300c\u540d\u79f0_Short\u300d\u7684 Conversion\uff1b\u4e0d\u52fe\u9009\u65f6\u8fd9\u4e9b\u6837\u672c\u7b97\u9ed8\u8ba4\u6863\uff08\u4e2d\u6863\uff09\u3002\u9ed8\u8ba4\u52fe\u9009\uff0c\u9608\u503c 0.5 \u79d2\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.spbShortThreshold.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u77ed\u97f3\u6548\u5224\u5b9a\u9608\u503c\uff1a\u64ad\u653e\u65f6\u957f\u5c0f\u4e8e\u6216\u7b49\u4e8e\u8be5\u503c\u7684\u6837\u672c\u7b97\u77ed\u97f3\u6548\u6863\u3002\u53d6\u6d88\u52fe\u9009\u5de6\u4fa7\u300c\u77ed\u97f3\u6548\u9608\u503c\u300d\u65f6\u4e0d\u751f\u6548\u3002\u9ed8\u8ba4 0.5 \u79d2\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxUseLong.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u957f\u97f3\u6548", None))
#if QT_CONFIG(tooltip)
        self.cbxUseLong.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u52fe\u9009\u65f6\u533a\u5206\u957f\u97f3\u6548\u6863\uff1a\u64ad\u653e\u65f6\u957f\u5927\u4e8e\u6216\u7b49\u4e8e\u53f3\u4fa7\u9608\u503c\uff08\u79d2\uff09\u7684\u6837\u672c\u7b97\u957f\u97f3\u6548\uff0c\u7528\u300c\u540d\u79f0_Long\u300d\u7684 Conversion\uff1b\u4e0d\u52fe\u9009\u65f6\u8fd9\u4e9b\u6837\u672c\u7b97\u9ed8\u8ba4\u6863\uff08\u4e2d\u6863\uff09\u3002\u9ed8\u8ba4\u52fe\u9009\uff0c\u9608\u503c 5 \u79d2\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.spbLongThreshold.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u957f\u97f3\u6548\u5224\u5b9a\u9608\u503c\uff1a\u64ad\u653e\u65f6\u957f\u5927\u4e8e\u6216\u7b49\u4e8e\u8be5\u503c\u7684\u6837\u672c\u7b97\u957f\u97f3\u6548\u6863\u3002\u53d6\u6d88\u52fe\u9009\u5de6\u4fa7\u300c\u957f\u97f3\u6548\u9608\u503c\u300d\u65f6\u4e0d\u751f\u6548\u3002\u9ed8\u8ba4 5 \u79d2\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.btnAnalyze.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u5206\u6790", None))
        self.btnApply.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u5e94\u7528", None))
        self.pteResult.setPlaceholderText(QCoreApplication.translate("AutoCompressionSettings", u"\u5206\u6790\u7edf\u8ba1\u548c\u5e94\u7528\u7ed3\u679c\u5c06\u663e\u793a\u5728\u8fd9\u91cc\u3002", None))
        self.cbxOverwriteConflicts.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u8986\u76d6\u5df2\u6709\u5176\u5b83 Conversion \u7684\u8282\u70b9", None))
#if QT_CONFIG(tooltip)
        self.cbxOverwriteConflicts.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u5206\u6790\u51fa\u300c\u5df2\u7ecf\u6253\u5f00 Override\uff0c\u4f46\u6307\u5411\u7684\u4e0d\u662f\u672c\u6b21\u65b9\u6848\u6307\u5b9a\u7684 Conversion\u300d\u7684\u8282\u70b9\uff08\u8868\u683c\u91cc\u6807\u7ea2\uff09\u3002\u52fe\u9009\u65f6\u6309\u65b9\u6848\u6539\u5199\u8fd9\u4e9b\u8282\u70b9\uff0c\u4e0d\u52fe\u9009\u65f6\u8df3\u8fc7\u5b83\u4eec\u3001\u4fdd\u7559\u539f\u6709\u8bbe\u7f6e\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblConversionPlatform.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u5e73\u53f0", None))
#if QT_CONFIG(tooltip)
        self.lblConversionPlatform.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u53f3\u4fa7\u4e09\u4e2a\u6863\u4f4d Conversion \u7684 Format / Quality \u6309\u8be5\u5e73\u53f0\u663e\u793a\uff08\u53d6\u81ea\u5de5\u7a0b WorkUnit \u91cc\u7684 Conversion \u8bbe\u7f6e\uff09\uff0c\u9ed8\u8ba4\u8ddf\u968f Wwise \u5f53\u524d\u5e73\u53f0\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.cbbConversionPlatform.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u53f3\u4fa7\u4e09\u4e2a\u6863\u4f4d Conversion \u7684 Format / Quality \u6309\u8be5\u5e73\u53f0\u663e\u793a\uff08\u53d6\u81ea\u5de5\u7a0b WorkUnit \u91cc\u7684 Conversion \u8bbe\u7f6e\uff09\uff0c\u9ed8\u8ba4\u8ddf\u968f Wwise \u5f53\u524d\u5e73\u53f0\u3002", None))
#endif // QT_CONFIG(tooltip)
        ___qtablewidgetitem = self.tblConversionSettings.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u91c7\u6837\u7387", None))
        ___qtablewidgetitem1 = self.tblConversionSettings.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u7f16\u7801\u683c\u5f0f", None))
        ___qtablewidgetitem2 = self.tblConversionSettings.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u97f3\u8d28", None))
        ___qtablewidgetitem3 = self.tblConversionSettings.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u6587\u4ef6\u6570\u91cf", None))
        ___qtablewidgetitem4 = self.tblPlanResults.horizontalHeaderItem(0)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u540d\u79f0", None))
        ___qtablewidgetitem5 = self.tblPlanResults.horizontalHeaderItem(1)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u7c7b\u578b", None))
        ___qtablewidgetitem6 = self.tblPlanResults.horizontalHeaderItem(2)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u8def\u5f84", None))
        ___qtablewidgetitem7 = self.tblPlanResults.horizontalHeaderItem(3)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u77ed\u97f3\u6548\u6570", None))
        ___qtablewidgetitem8 = self.tblPlanResults.horizontalHeaderItem(4)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u4e2d\u97f3\u6548\u6570", None))
        ___qtablewidgetitem9 = self.tblPlanResults.horizontalHeaderItem(5)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u957f\u97f3\u6548\u6570", None))
        self.tabModes.setTabText(self.tabModes.indexOf(self.tabDuration), QCoreApplication.translate("AutoCompressionSettings", u"\u6309\u65f6\u957f", None))
        self.btnNameAnalyze.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u5206\u6790", None))
        self.btnNameApply.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u5e94\u7528", None))
        self.cbxNameOverwriteConflicts.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u8986\u76d6\u5df2\u6709\u5176\u5b83 Conversion \u7684\u8282\u70b9", None))
#if QT_CONFIG(tooltip)
        self.cbxNameOverwriteConflicts.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u5206\u6790\u51fa\u300c\u5f53\u524d Conversion \u4e0d\u662f\u6620\u5c04\u8868\u6307\u5b9a\u7684\u90a3\u4e00\u4e2a\u300d\u7684\u8282\u70b9\uff08\u8868\u683c\u91cc\u6807\u7ea2\uff09\u3002\u52fe\u9009\u65f6\u6309\u6620\u5c04\u8868\u6539\u5199\u8fd9\u4e9b\u8282\u70b9\uff0c\u4e0d\u52fe\u9009\u65f6\u8df3\u8fc7\u5b83\u4eec\u3001\u4fdd\u7559\u539f\u6709\u8bbe\u7f6e\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblNameStatus.setText("")
#if QT_CONFIG(tooltip)
        self.lblNameStatus.setToolTip(QCoreApplication.translate("AutoCompressionSettings", u"\u4ece\u6839\u8282\u70b9\u5f80\u4e0b\u904d\u5386\uff1a\u8282\u70b9\u540d\u5305\u542b\u914d\u7f6e\u7684\u5173\u952e\u8bcd\u65f6\uff0c\u5c31\u7ed9\u8be5\u8282\u70b9\u8bbe\u7f6e\u5bf9\u5e94\u7684 Conversion\uff08\u540c\u4e00\u8282\u70b9\u547d\u4e2d\u591a\u4e2a\u5173\u952e\u8bcd\u65f6\u6309\u5217\u8868\u987a\u5e8f\u53d6\u7b2c\u4e00\u4e2a\uff09\u3002", None))
#endif // QT_CONFIG(tooltip)
        ___qtablewidgetitem10 = self.tblNamePlanResults.horizontalHeaderItem(0)
        ___qtablewidgetitem10.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u540d\u79f0", None))
        ___qtablewidgetitem11 = self.tblNamePlanResults.horizontalHeaderItem(1)
        ___qtablewidgetitem11.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u7c7b\u578b", None))
        ___qtablewidgetitem12 = self.tblNamePlanResults.horizontalHeaderItem(2)
        ___qtablewidgetitem12.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u8def\u5f84", None))
        ___qtablewidgetitem13 = self.tblNamePlanResults.horizontalHeaderItem(3)
        ___qtablewidgetitem13.setText(QCoreApplication.translate("AutoCompressionSettings", u"\u5339\u914d\u5173\u952e\u8bcd", None))
        ___qtablewidgetitem14 = self.tblNamePlanResults.horizontalHeaderItem(4)
        ___qtablewidgetitem14.setText(QCoreApplication.translate("AutoCompressionSettings", u"Conversion", None))
        self.tabModes.setTabText(self.tabModes.indexOf(self.tabName), QCoreApplication.translate("AutoCompressionSettings", u"\u6309\u540d\u79f0", None))
    # retranslateUi

