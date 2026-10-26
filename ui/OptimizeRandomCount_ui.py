# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'OptimizeRandomCount.ui'
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
    QFrame, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_OptimizeRandomCount(object):
    def setupUi(self, OptimizeRandomCount):
        if not OptimizeRandomCount.objectName():
            OptimizeRandomCount.setObjectName(u"OptimizeRandomCount")
        OptimizeRandomCount.resize(1120, 560)
        OptimizeRandomCount.setMinimumSize(QSize(1050, 360))
        self.verticalLayout = QVBoxLayout(OptimizeRandomCount)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.topRow = QHBoxLayout()
        self.topRow.setObjectName(u"topRow")
        self.limitLabelColumn = QVBoxLayout()
        self.limitLabelColumn.setSpacing(4)
        self.limitLabelColumn.setObjectName(u"limitLabelColumn")
        self.limitLabelColumn.setContentsMargins(0, 0, 0, 0)
        self.lblRandomLimit = QLabel(OptimizeRandomCount)
        self.lblRandomLimit.setObjectName(u"lblRandomLimit")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lblRandomLimit.sizePolicy().hasHeightForWidth())
        self.lblRandomLimit.setSizePolicy(sizePolicy)
        self.lblRandomLimit.setMinimumSize(QSize(100, 20))
        self.lblRandomLimit.setMaximumSize(QSize(100, 20))

        self.limitLabelColumn.addWidget(self.lblRandomLimit)

        self.cbxSelectAllPlatforms = QCheckBox(OptimizeRandomCount)
        self.cbxSelectAllPlatforms.setObjectName(u"cbxSelectAllPlatforms")
        sizePolicy.setHeightForWidth(self.cbxSelectAllPlatforms.sizePolicy().hasHeightForWidth())
        self.cbxSelectAllPlatforms.setSizePolicy(sizePolicy)
        self.cbxSelectAllPlatforms.setMinimumSize(QSize(100, 0))
        self.cbxSelectAllPlatforms.setMaximumSize(QSize(100, 16777215))

        self.limitLabelColumn.addWidget(self.cbxSelectAllPlatforms)

        self.limitLabelSpacer = QSpacerItem(20, 24, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.limitLabelColumn.addItem(self.limitLabelSpacer)


        self.topRow.addLayout(self.limitLabelColumn)

        self.tblAllowedCounts = QTableWidget(OptimizeRandomCount)
        self.tblAllowedCounts.setObjectName(u"tblAllowedCounts")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.tblAllowedCounts.sizePolicy().hasHeightForWidth())
        self.tblAllowedCounts.setSizePolicy(sizePolicy1)
        self.tblAllowedCounts.setMinimumSize(QSize(0, 72))
        self.tblAllowedCounts.setMaximumSize(QSize(520, 84))
        self.tblAllowedCounts.setFrameShape(QFrame.NoFrame)
        self.tblAllowedCounts.setEditTriggers(QAbstractItemView.DoubleClicked|QAbstractItemView.EditKeyPressed)
        self.tblAllowedCounts.setAlternatingRowColors(False)
        self.tblAllowedCounts.setShowGrid(False)
        self.tblAllowedCounts.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.tblAllowedCounts.verticalHeader().setVisible(False)

        self.topRow.addWidget(self.tblAllowedCounts)

        self.filterColumn = QVBoxLayout()
        self.filterColumn.setSpacing(2)
        self.filterColumn.setObjectName(u"filterColumn")
        self.filterColumn.setContentsMargins(0, 0, 0, 0)
        self.cbxOnlyOverLimit = QCheckBox(OptimizeRandomCount)
        self.cbxOnlyOverLimit.setObjectName(u"cbxOnlyOverLimit")
        sizePolicy.setHeightForWidth(self.cbxOnlyOverLimit.sizePolicy().hasHeightForWidth())
        self.cbxOnlyOverLimit.setSizePolicy(sizePolicy)

        self.filterColumn.addWidget(self.cbxOnlyOverLimit)

        self.cbxShowMultiGroup = QCheckBox(OptimizeRandomCount)
        self.cbxShowMultiGroup.setObjectName(u"cbxShowMultiGroup")
        sizePolicy.setHeightForWidth(self.cbxShowMultiGroup.sizePolicy().hasHeightForWidth())
        self.cbxShowMultiGroup.setSizePolicy(sizePolicy)

        self.filterColumn.addWidget(self.cbxShowMultiGroup)

        self.filterSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.filterColumn.addItem(self.filterSpacer)


        self.topRow.addLayout(self.filterColumn)

        self.btnAnalyze = QPushButton(OptimizeRandomCount)
        self.btnAnalyze.setObjectName(u"btnAnalyze")

        self.topRow.addWidget(self.btnAnalyze)

        self.btnOptimizeSelected = QPushButton(OptimizeRandomCount)
        self.btnOptimizeSelected.setObjectName(u"btnOptimizeSelected")

        self.topRow.addWidget(self.btnOptimizeSelected)

        self.btnOptimizeAll = QPushButton(OptimizeRandomCount)
        self.btnOptimizeAll.setObjectName(u"btnOptimizeAll")

        self.topRow.addWidget(self.btnOptimizeAll)


        self.verticalLayout.addLayout(self.topRow)

        self.tblRandomContainers = QTableWidget(OptimizeRandomCount)
        self.tblRandomContainers.setObjectName(u"tblRandomContainers")
        self.tblRandomContainers.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblRandomContainers.setAlternatingRowColors(True)
        self.tblRandomContainers.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblRandomContainers.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tblRandomContainers.setSortingEnabled(False)
        self.tblRandomContainers.horizontalHeader().setStretchLastSection(False)
        self.tblRandomContainers.verticalHeader().setVisible(False)

        self.verticalLayout.addWidget(self.tblRandomContainers)


        self.retranslateUi(OptimizeRandomCount)

        QMetaObject.connectSlotsByName(OptimizeRandomCount)
    # setupUi

    def retranslateUi(self, OptimizeRandomCount):
        OptimizeRandomCount.setWindowTitle(QCoreApplication.translate("OptimizeRandomCount", u"\u4f18\u5316\u968f\u673a\u6570\u91cf", None))
#if QT_CONFIG(tooltip)
        self.lblRandomLimit.setToolTip(QCoreApplication.translate("OptimizeRandomCount", u"\u5404\u5e73\u53f0\u7684\u968f\u673a\u6570\u9650\u5236\uff1b\u5f53\u524d\u5e73\u53f0\u5728\u4e0b\u65b9\u5bf9\u8c61\u8868\u5934\u4e2d\u6807\u8bb0\u4e3a\u300c\uff08\u5f53\u524d\uff09\u300d\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.lblRandomLimit.setText(QCoreApplication.translate("OptimizeRandomCount", u"\u968f\u673a\u6570\u9650\u5236", None))
#if QT_CONFIG(tooltip)
        self.cbxSelectAllPlatforms.setToolTip(QCoreApplication.translate("OptimizeRandomCount", u"\u52fe\u9009\u6216\u53d6\u6d88\u52fe\u9009\u6240\u6709\u5e73\u53f0\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxSelectAllPlatforms.setText(QCoreApplication.translate("OptimizeRandomCount", u"\u5168\u9009\u5e73\u53f0", None))
#if QT_CONFIG(tooltip)
        self.tblAllowedCounts.setToolTip(QCoreApplication.translate("OptimizeRandomCount", u"\u7b2c\u4e00\u884c\u52fe\u9009\u9700\u8981\u4f18\u5316\u7684\u5e73\u53f0\uff0c\u7b2c\u4e8c\u884c\u7f16\u8f91\u5404\u5e73\u53f0\u5141\u8bb8\u6570\u91cf\uff1b\u7f16\u8f91\u540e\u7acb\u5373\u540c\u6b65\u5230\u7528\u6237\u8bbe\u7f6e\uff0c\u672a\u914d\u7f6e\u7684\u5e73\u53f0\u4f7f\u7528\u9ed8\u8ba4\u503c 3\u3002", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.cbxOnlyOverLimit.setToolTip(QCoreApplication.translate("OptimizeRandomCount", u"\u52fe\u9009\u540e\u53ea\u663e\u793a\u81f3\u5c11\u6709\u4e00\u4e2a\u5e73\u53f0\u7684\u542f\u7528\u6570\u91cf\u8d85\u8fc7\u8be5\u5e73\u53f0\u5141\u8bb8\u6570\u91cf\u7684\u968f\u673a\u5bb9\u5668\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxOnlyOverLimit.setText(QCoreApplication.translate("OptimizeRandomCount", u"\u4ec5\u663e\u793a\u8d85\u6807\u5bf9\u8c61", None))
#if QT_CONFIG(tooltip)
        self.cbxShowMultiGroup.setToolTip(QCoreApplication.translate("OptimizeRandomCount", u"\u52fe\u9009\u540e\u663e\u793a\u5305\u542b\u591a\u79cd\u540d\u79f0\u524d\u7f00\u7684\u968f\u673a\u5bb9\u5668\uff1b\u4e0d\u52fe\u9009\u65f6\u8fc7\u6ee4\u6389\u8fd9\u4e9b\u5bf9\u8c61\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.cbxShowMultiGroup.setText(QCoreApplication.translate("OptimizeRandomCount", u"\u663e\u793a\u591a\u64ad\u5bf9\u8c61", None))
#if QT_CONFIG(tooltip)
        self.btnAnalyze.setToolTip(QCoreApplication.translate("OptimizeRandomCount", u"\u8bfb\u53d6\u4e3b\u7a97\u53e3\u5bf9\u8c61\u4e0b\u6240\u6709 Random \u6a21\u5f0f\u7684 Random Container\uff0c\u5e76\u7edf\u8ba1\u5404\u5e73\u53f0\u542f\u7528\u7684\u5b50\u5bf9\u8c61\u6570\u91cf\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.btnAnalyze.setText(QCoreApplication.translate("OptimizeRandomCount", u"\u5206\u6790", None))
#if QT_CONFIG(tooltip)
        self.btnOptimizeSelected.setToolTip(QCoreApplication.translate("OptimizeRandomCount", u"\u53ea\u4fee\u6539\u8868\u683c\u4e2d\u52fe\u9009\u5e73\u53f0\u7684 Inclusion\uff1a\u6309\u5b50\u5bf9\u8c61\u987a\u5e8f\u4fdd\u7559\u5404\u5e73\u53f0\u5141\u8bb8\u6570\u91cf\uff0c\u5176\u4f59\u5148 unlink \u518d\u505c\u7528\uff1b\u672a\u52fe\u9009\u7684\u5e73\u53f0\u4e0d\u53d7\u5f71\u54cd\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.btnOptimizeSelected.setText(QCoreApplication.translate("OptimizeRandomCount", u"\u4f18\u5316\u6240\u9009\u5e73\u53f0", None))
#if QT_CONFIG(tooltip)
        self.btnOptimizeAll.setToolTip(QCoreApplication.translate("OptimizeRandomCount", u"\u76f4\u63a5\u4fee\u6539\u6240\u6709\u5e73\u53f0\u7684 Inclusion\uff1a\u6bcf\u4e2a\u5e73\u53f0\u4f7f\u7528\u8be5\u5e73\u53f0\u914d\u7f6e\u7684\u5141\u8bb8\u6570\u91cf\uff1b\u8d85\u51fa\u6240\u6709\u5e73\u53f0\u4e0a\u9650\u7684\u5c3e\u90e8\u5bf9\u8c61\u76f4\u63a5\u5168\u5c40\u505c\u7528\uff0c\u5176\u4f59\u6309\u5e73\u53f0\u5148 unlink \u518d\u505c\u7528\u3002", None))
#endif // QT_CONFIG(tooltip)
        self.btnOptimizeAll.setText(QCoreApplication.translate("OptimizeRandomCount", u"\u4f18\u5316\u5168\u90e8\u5e73\u53f0", None))
    # retranslateUi

