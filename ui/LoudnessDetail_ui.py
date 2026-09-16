# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'LoudnessDetail.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QHeaderView,
    QLabel, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_LoudnessDetail(object):
    def setupUi(self, LoudnessDetail):
        if not LoudnessDetail.objectName():
            LoudnessDetail.setObjectName(u"LoudnessDetail")
        LoudnessDetail.resize(1040, 520)
        LoudnessDetail.setMinimumSize(QSize(760, 360))
        self.verticalLayout = QVBoxLayout(LoudnessDetail)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.lblTitle = QLabel(LoudnessDetail)
        self.lblTitle.setObjectName(u"lblTitle")
        self.lblTitle.setWordWrap(True)

        self.verticalLayout.addWidget(self.lblTitle)

        self.lblReferences = QLabel(LoudnessDetail)
        self.lblReferences.setObjectName(u"lblReferences")
        self.lblReferences.setWordWrap(True)

        self.verticalLayout.addWidget(self.lblReferences)

        self.tblDetails = QTableWidget(LoudnessDetail)
        if (self.tblDetails.columnCount() < 8):
            self.tblDetails.setColumnCount(8)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblDetails.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblDetails.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblDetails.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tblDetails.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tblDetails.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tblDetails.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tblDetails.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.tblDetails.setHorizontalHeaderItem(7, __qtablewidgetitem7)
        self.tblDetails.setObjectName(u"tblDetails")
        self.tblDetails.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.tblDetails.setAlternatingRowColors(True)
        self.tblDetails.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.verticalLayout.addWidget(self.tblDetails)

        self.lblSummary = QLabel(LoudnessDetail)
        self.lblSummary.setObjectName(u"lblSummary")
        self.lblSummary.setWordWrap(True)

        self.verticalLayout.addWidget(self.lblSummary)


        self.retranslateUi(LoudnessDetail)

        QMetaObject.connectSlotsByName(LoudnessDetail)
    # setupUi

    def retranslateUi(self, LoudnessDetail):
        LoudnessDetail.setWindowTitle(QCoreApplication.translate("LoudnessDetail", u"\u54cd\u5ea6\u8c03\u6574\u660e\u7ec6", None))
        self.lblTitle.setText(QCoreApplication.translate("LoudnessDetail", u"\u97f3\u9891\u6587\u4ef6", None))
        self.lblReferences.setText(QCoreApplication.translate("LoudnessDetail", u"\u5f15\u7528\u5bf9\u8c61", None))
        ___qtablewidgetitem = self.tblDetails.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("LoudnessDetail", u"\u5bf9\u8c61", None))
        ___qtablewidgetitem1 = self.tblDetails.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("LoudnessDetail", u"\u7c7b\u578b", None))
        ___qtablewidgetitem2 = self.tblDetails.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("LoudnessDetail", u"\u8def\u5f84", None))
        ___qtablewidgetitem3 = self.tblDetails.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("LoudnessDetail", u"Volume", None))
        ___qtablewidgetitem4 = self.tblDetails.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("LoudnessDetail", u"MakeupGain", None))
        ___qtablewidgetitem5 = self.tblDetails.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("LoudnessDetail", u"OutputBusVolume", None))
        ___qtablewidgetitem6 = self.tblDetails.horizontalHeaderItem(6)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("LoudnessDetail", u"BusVolume", None))
        ___qtablewidgetitem7 = self.tblDetails.horizontalHeaderItem(7)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("LoudnessDetail", u"\u5c0f\u8ba1", None))
        self.lblSummary.setText(QCoreApplication.translate("LoudnessDetail", u"\u6c47\u603b", None))
    # retranslateUi

