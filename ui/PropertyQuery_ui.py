# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'PropertyQuery.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_PropertyQuery(object):
    def setupUi(self, PropertyQuery):
        if not PropertyQuery.objectName():
            PropertyQuery.setObjectName(u"PropertyQuery")
        PropertyQuery.resize(900, 560)
        self.verticalLayout = QVBoxLayout(PropertyQuery)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.layoutPropertyNames = QHBoxLayout()
        self.layoutPropertyNames.setObjectName(u"layoutPropertyNames")
        self.lblPropertyPrompt = QLabel(PropertyQuery)
        self.lblPropertyPrompt.setObjectName(u"lblPropertyPrompt")

        self.layoutPropertyNames.addWidget(self.lblPropertyPrompt)

        self.iptPropertyNames = QLineEdit(PropertyQuery)
        self.iptPropertyNames.setObjectName(u"iptPropertyNames")

        self.layoutPropertyNames.addWidget(self.iptPropertyNames)

        self.lblCommonProperty = QLabel(PropertyQuery)
        self.lblCommonProperty.setObjectName(u"lblCommonProperty")

        self.layoutPropertyNames.addWidget(self.lblCommonProperty)

        self.cbbCommonProperties = QComboBox(PropertyQuery)
        self.cbbCommonProperties.setObjectName(u"cbbCommonProperties")
        self.cbbCommonProperties.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        self.layoutPropertyNames.addWidget(self.cbbCommonProperties)

        self.btnQuery = QPushButton(PropertyQuery)
        self.btnQuery.setObjectName(u"btnQuery")

        self.layoutPropertyNames.addWidget(self.btnQuery)

        self.btnPropertyHelp = QPushButton(PropertyQuery)
        self.btnPropertyHelp.setObjectName(u"btnPropertyHelp")

        self.layoutPropertyNames.addWidget(self.btnPropertyHelp)


        self.verticalLayout.addLayout(self.layoutPropertyNames)

        self.layoutObjectCount = QHBoxLayout()
        self.layoutObjectCount.setObjectName(u"layoutObjectCount")
        self.lblObjectCount = QLabel(PropertyQuery)
        self.lblObjectCount.setObjectName(u"lblObjectCount")

        self.layoutObjectCount.addWidget(self.lblObjectCount)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.layoutObjectCount.addItem(self.horizontalSpacer)

        self.lblDoubleClickHint = QLabel(PropertyQuery)
        self.lblDoubleClickHint.setObjectName(u"lblDoubleClickHint")

        self.layoutObjectCount.addWidget(self.lblDoubleClickHint)


        self.verticalLayout.addLayout(self.layoutObjectCount)

        self.tblPropertyResults = QTableWidget(PropertyQuery)
        self.tblPropertyResults.setObjectName(u"tblPropertyResults")
        self.tblPropertyResults.setAlternatingRowColors(True)
        self.tblPropertyResults.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblPropertyResults.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.verticalLayout.addWidget(self.tblPropertyResults)

        self.layoutButtons = QHBoxLayout()
        self.layoutButtons.setObjectName(u"layoutButtons")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.layoutButtons.addItem(self.horizontalSpacer_2)

        self.btnClose = QPushButton(PropertyQuery)
        self.btnClose.setObjectName(u"btnClose")

        self.layoutButtons.addWidget(self.btnClose)


        self.verticalLayout.addLayout(self.layoutButtons)


        self.retranslateUi(PropertyQuery)

        QMetaObject.connectSlotsByName(PropertyQuery)
    # setupUi

    def retranslateUi(self, PropertyQuery):
        PropertyQuery.setWindowTitle(QCoreApplication.translate("PropertyQuery", u"\u5c5e\u6027\u67e5\u8be2", None))
        self.lblPropertyPrompt.setText(QCoreApplication.translate("PropertyQuery", u"\u5c5e\u6027\u540d\uff08\u591a\u4e2a\u7528 ; \u5206\u9694\uff09", None))
        self.iptPropertyNames.setPlaceholderText(QCoreApplication.translate("PropertyQuery", u"\u4f8b\u5982\uff1aVolume;IsStreamingEnabled", None))
        self.lblCommonProperty.setText(QCoreApplication.translate("PropertyQuery", u"\u5e38\u7528\u5c5e\u6027", None))
        self.btnQuery.setText(QCoreApplication.translate("PropertyQuery", u"\u67e5\u8be2", None))
        self.btnPropertyHelp.setText(QCoreApplication.translate("PropertyQuery", u"\u5c5e\u6027\u8bf4\u660e", None))
        self.lblObjectCount.setText(QCoreApplication.translate("PropertyQuery", u"\u8868\u683c\u5185\u5171 0 \u4e2a\u5bf9\u8c61", None))
        self.lblDoubleClickHint.setText(QCoreApplication.translate("PropertyQuery", u"\u53cc\u51fb\u884c\u53ef\u5728 Wwise \u4e2d\u5b9a\u4f4d\u5bf9\u8c61", None))
        self.btnClose.setText(QCoreApplication.translate("PropertyQuery", u"\u5173\u95ed", None))
    # retranslateUi

