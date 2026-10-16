# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'AutoCompressionDetail.ui'
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
    QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_AutoCompressionDetail(object):
    def setupUi(self, AutoCompressionDetail):
        if not AutoCompressionDetail.objectName():
            AutoCompressionDetail.setObjectName(u"AutoCompressionDetail")
        AutoCompressionDetail.resize(560, 460)
        self.verticalLayout = QVBoxLayout(AutoCompressionDetail)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tblAudioDetails = QTableWidget(AutoCompressionDetail)
        if (self.tblAudioDetails.columnCount() < 3):
            self.tblAudioDetails.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblAudioDetails.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblAudioDetails.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblAudioDetails.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.tblAudioDetails.setObjectName(u"tblAudioDetails")
        self.tblAudioDetails.setAlternatingRowColors(True)
        self.tblAudioDetails.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblAudioDetails.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblAudioDetails.setSortingEnabled(True)

        self.verticalLayout.addWidget(self.tblAudioDetails)


        self.retranslateUi(AutoCompressionDetail)

        QMetaObject.connectSlotsByName(AutoCompressionDetail)
    # setupUi

    def retranslateUi(self, AutoCompressionDetail):
        AutoCompressionDetail.setWindowTitle(QCoreApplication.translate("AutoCompressionDetail", u"\u97f3\u6548\u8be6\u60c5", None))
        ___qtablewidgetitem = self.tblAudioDetails.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("AutoCompressionDetail", u"\u540d\u79f0", None))
        ___qtablewidgetitem1 = self.tblAudioDetails.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("AutoCompressionDetail", u"\u65f6\u957f\uff08\u79d2\uff09", None))
        ___qtablewidgetitem2 = self.tblAudioDetails.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("AutoCompressionDetail", u"\u5206\u7c7b", None))
    # retranslateUi

