# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MediaDuplicateDetail.ui'
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

class Ui_MediaDuplicateDetail(object):
    def setupUi(self, MediaDuplicateDetail):
        if not MediaDuplicateDetail.objectName():
            MediaDuplicateDetail.setObjectName(u"MediaDuplicateDetail")
        MediaDuplicateDetail.resize(550, 520)
        MediaDuplicateDetail.setMinimumSize(QSize(480, 360))
        self.verticalLayout = QVBoxLayout(MediaDuplicateDetail)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.lblTitle = QLabel(MediaDuplicateDetail)
        self.lblTitle.setObjectName(u"lblTitle")
        self.lblTitle.setWordWrap(True)

        self.verticalLayout.addWidget(self.lblTitle)

        self.lblSummary = QLabel(MediaDuplicateDetail)
        self.lblSummary.setObjectName(u"lblSummary")
        self.lblSummary.setWordWrap(True)

        self.verticalLayout.addWidget(self.lblSummary)

        self.tblWemDetails = QTableWidget(MediaDuplicateDetail)
        if (self.tblWemDetails.columnCount() < 12):
            self.tblWemDetails.setColumnCount(12)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(7, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(8, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(9, __qtablewidgetitem9)
        __qtablewidgetitem10 = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(10, __qtablewidgetitem10)
        __qtablewidgetitem11 = QTableWidgetItem()
        self.tblWemDetails.setHorizontalHeaderItem(11, __qtablewidgetitem11)
        self.tblWemDetails.setObjectName(u"tblWemDetails")
        self.tblWemDetails.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tblWemDetails.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblWemDetails.setAlternatingRowColors(True)
        self.tblWemDetails.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblWemDetails.setWordWrap(False)
        self.tblWemDetails.verticalHeader().setVisible(False)

        self.verticalLayout.addWidget(self.tblWemDetails)


        self.retranslateUi(MediaDuplicateDetail)

        QMetaObject.connectSlotsByName(MediaDuplicateDetail)
    # setupUi

    def retranslateUi(self, MediaDuplicateDetail):
        MediaDuplicateDetail.setWindowTitle(QCoreApplication.translate("MediaDuplicateDetail", u"\u5a92\u4f53\u67e5\u91cd\u8be6\u60c5", None))
        self.lblTitle.setText(QCoreApplication.translate("MediaDuplicateDetail", u"\u539f\u59cb\u97f3\u9891", None))
        self.lblSummary.setText(QCoreApplication.translate("MediaDuplicateDetail", u"\u6c47\u603b", None))
        ___qtablewidgetitem = self.tblWemDetails.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MediaDuplicateDetail", u"WEM \u8def\u5f84", None))
        ___qtablewidgetitem1 = self.tblWemDetails.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MediaDuplicateDetail", u"Event \u540d\u79f0", None))
        ___qtablewidgetitem2 = self.tblWemDetails.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("MediaDuplicateDetail", u"Audio Source \u540d\u79f0", None))
        ___qtablewidgetitem3 = self.tblWemDetails.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("MediaDuplicateDetail", u"Conversion", None))
        ___qtablewidgetitem4 = self.tblWemDetails.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("MediaDuplicateDetail", u"\u683c\u5f0f", None))
        ___qtablewidgetitem5 = self.tblWemDetails.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("MediaDuplicateDetail", u"\u91c7\u6837\u7387", None))
        ___qtablewidgetitem6 = self.tblWemDetails.horizontalHeaderItem(6)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("MediaDuplicateDetail", u"\u65f6\u957f", None))
        ___qtablewidgetitem7 = self.tblWemDetails.horizontalHeaderItem(7)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("MediaDuplicateDetail", u"\u5927\u5c0f", None))
        ___qtablewidgetitem8 = self.tblWemDetails.horizontalHeaderItem(8)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("MediaDuplicateDetail", u"Trim Begin", None))
        ___qtablewidgetitem9 = self.tblWemDetails.horizontalHeaderItem(9)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("MediaDuplicateDetail", u"Trim End", None))
        ___qtablewidgetitem10 = self.tblWemDetails.horizontalHeaderItem(10)
        ___qtablewidgetitem10.setText(QCoreApplication.translate("MediaDuplicateDetail", u"Fade In", None))
        ___qtablewidgetitem11 = self.tblWemDetails.horizontalHeaderItem(11)
        ___qtablewidgetitem11.setText(QCoreApplication.translate("MediaDuplicateDetail", u"Fade Out", None))
    # retranslateUi

